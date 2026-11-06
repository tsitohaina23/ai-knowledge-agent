"""RAG pipeline: load -> split -> embed/index -> retrieve -> generate (with page citations)."""

from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from app.cache import TTLCache
from app.config import Settings
from app.rag.llm import Usage, build_chat_model, usage_from_message
from app.rag.loader import load_pdf, split_documents
from app.rag.prompts import (
    PROMPT,
    REFUSAL_MESSAGE,
    REFUSAL_SENTINEL,
    format_context,
    looks_like_injection,
)
from app.rag.vectorstore import ScoredDoc, VectorIndex, build_embeddings, build_index

ProgressFn = Callable[[int, str], None]


@dataclass
class Source:
    n: int
    source: str
    page: int
    score: float
    excerpt: str


@dataclass
class Answer:
    answer: str
    sources: list[Source]
    refused: bool
    provider: str
    model: str
    latency_ms: dict[str, float]
    tokens: dict[str, int]
    cost_usd: float = 0.0  # local models only: always 0
    cached: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IngestResult:
    source: str
    pages: int
    chunks: int
    added: int
    seconds: float


class RAGPipeline:
    def __init__(
        self,
        settings: Settings,
        embeddings: Embeddings | None = None,
        index: VectorIndex | None = None,
        llm: BaseChatModel | None = None,
        use_llm_from_settings: bool = True,
    ):
        self.settings = settings
        self.embeddings = embeddings or build_embeddings(settings.embedding_model)
        self.index = index or build_index(
            settings.vector_store, self.embeddings, settings.storage_dir, settings.collection_name
        )
        self.llm = llm if llm is not None else (build_chat_model(settings) if use_llm_from_settings else None)
        self.provider = "custom" if llm is not None else settings.llm_provider
        self.model = settings.resolved_model if llm is None else getattr(llm, "model", "custom")
        self.cache = TTLCache(settings.cache_max_entries, settings.cache_ttl_s)
        self._lock = threading.Lock()
        self._version = 0  # bumped on each ingestion -> invalidates cached answers

    # ---------------------------------------------------------------- ingestion
    def ingest_pdf(
        self, path: Path, source_name: str | None = None, progress: ProgressFn | None = None
    ) -> IngestResult:
        notify = progress or (lambda _p, _m: None)
        t0 = time.perf_counter()
        notify(5, "Lecture du PDF...")
        pages = load_pdf(path, source_name)
        notify(20, f"{len(pages)} pages lues, découpage en blocs...")
        chunks = split_documents(pages, self.settings.chunk_size, self.settings.chunk_overlap)
        added = 0
        with self._lock:
            batch = 32
            for i in range(0, len(chunks), batch):
                added += self.index.add(chunks[i : i + batch])
                done = min(i + batch, len(chunks))
                notify(20 + int(75 * done / max(len(chunks), 1)), f"Indexation : {done}/{len(chunks)} blocs")
            self._version += 1
            self.cache.clear()
        notify(100, f"PDF de {len(pages)} pages indexé ({len(chunks)} blocs).")
        return IngestResult(
            source=source_name or path.name,
            pages=len(pages),
            chunks=len(chunks),
            added=added,
            seconds=round(time.perf_counter() - t0, 3),
        )

    # ---------------------------------------------------------------- retrieval
    def retrieve(self, question: str, k: int | None = None) -> list[ScoredDoc]:
        return self.index.search(question, k or self.settings.top_k)

    # ---------------------------------------------------------------- answering
    def _cache_key(self, question: str, k: int) -> str:
        norm = " ".join(question.lower().split())
        raw = f"{self._version}|{self.index.kind}|{self.provider}|{self.model}|{k}|{norm}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def ask(self, question: str, k: int | None = None) -> Answer:
        k = k or self.settings.top_k
        key = self._cache_key(question, k)
        t0 = time.perf_counter()
        cached = self.cache.get(key)
        if cached is not None:
            return replace(
                cached,
                cached=True,
                latency_ms={
                    "retrieval": 0.0,
                    "generation": 0.0,
                    "total": round((time.perf_counter() - t0) * 1000, 2),
                },
                tokens={"input": 0, "output": 0, "total": 0},  # nothing was generated
            )

        hits = self.retrieve(question, k)
        t_ret = time.perf_counter()
        sources = [
            Source(
                n=i,
                source=str(d.metadata.get("source", "document")),
                page=int(d.metadata.get("page", 0)),
                score=round(s, 4),
                excerpt=d.page_content[:400],
            )
            for i, (d, s) in enumerate(hits, start=1)
        ]
        warnings = (
            ["possible_prompt_injection_in_sources"]
            if any(looks_like_injection(d.page_content) for d, _ in hits)
            else []
        )

        usage = Usage()
        best = hits[0][1] if hits else -1.0
        if not hits or best < self.settings.min_relevance:
            answer_text, refused = REFUSAL_MESSAGE, True
            sources = []
        elif self.llm is None:
            answer_text, refused = self._extractive(question, hits), False
        else:
            answer_text, usage = self._generate(question, [d for d, _ in hits])
            refused = REFUSAL_SENTINEL in answer_text
            if refused:
                answer_text, sources = REFUSAL_MESSAGE, []
        t_end = time.perf_counter()

        result = Answer(
            answer=answer_text,
            sources=sources,
            refused=refused,
            provider=self.provider,
            model=self.model,
            latency_ms={
                "retrieval": round((t_ret - t0) * 1000, 2),
                "generation": round((t_end - t_ret) * 1000, 2),
                "total": round((t_end - t0) * 1000, 2),
            },
            tokens={"input": usage.input_tokens, "output": usage.output_tokens, "total": usage.total},
            warnings=warnings,
        )
        self.cache.set(key, result)
        return result

    def _generate(self, question: str, docs: list[Document]) -> tuple[str, Usage]:
        chain = PROMPT | self.llm  # LangChain LCEL: prompt template -> chat model
        msg = chain.invoke({"context": format_context(docs), "question": question})
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        return text.strip(), usage_from_message(msg)

    def _extractive(self, question: str, hits: list[ScoredDoc], n_sentences: int = 2) -> str:
        """No-LLM answer: the sentences of the top passages closest to the question
        (sentence-level embedding similarity), each with its page citation."""
        candidates: list[tuple[str, int]] = []
        for d, _ in hits[:3]:
            lines = [ln for ln in d.page_content.splitlines() if not _HEADING.match(ln.strip())]
            for sent in _SENTENCE_SPLIT.split(" ".join(lines)):
                sent = " ".join(sent.split())
                if len(sent) >= 25:
                    candidates.append((sent, int(d.metadata.get("page", 0))))
        if not candidates:
            return "Mode extraits (sans LLM) :\n" + hits[0][0].page_content[:300]
        q = self.embeddings.embed_query(question)
        vecs = self.embeddings.embed_documents([c[0] for c in candidates])
        ranked = sorted(zip(candidates, (_cosine(q, v) for v in vecs), strict=True), key=lambda x: -x[1])
        lines = ["Mode extraits (sans LLM) : phrases les plus pertinentes du document."]
        lines += [f"- {text} [p. {page}]" for (text, page), _ in ranked[:n_sentences]]
        return "\n".join(lines)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_HEADING = re.compile(r"^(\d+(\.\d+)*\.\s+[^.]{0,70}|Page \d+ .*)$")  # "2. Title" lines, footers


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
