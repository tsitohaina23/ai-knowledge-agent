"""Retrieval evaluation + ChromaDB vs FAISS comparison (time and quality).

Metrics (page level, k passages retrieved):
  - hit@1 / hit@k : share of questions whose expected page is ranked 1st / in the top k
  - MRR           : mean of 1 / rank of the first correct page (0 if absent)
  - refusal       : out-of-corpus questions correctly refused (best score < MIN_RELEVANCE)
  - false refusal : in-corpus questions wrongly refused
  - timings       : indexing time, mean / p95 retrieval latency

Usage (from backend/):
  python -m eval.evaluate                 # full grid, writes eval/results/
  python -m eval.evaluate --quick         # default config only
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.rag.pipeline import RAGPipeline
from app.rag.vectorstore import build_embeddings

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"

MULTILINGUAL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ENGLISH_BGE = "BAAI/bge-small-en-v1.5"  # FastEmbed default, used by the first version


@dataclass
class Config:
    store: str
    embedding: str
    chunk_size: int
    chunk_overlap: int

    @property
    def label(self) -> str:
        emb = "multilingual-MiniLM" if self.embedding == MULTILINGUAL else "bge-small-en"
        return f"{self.store} | {emb} | chunk {self.chunk_size}"


GRID = [
    Config("chroma", MULTILINGUAL, 300, 50),  # default configuration (see README)
    Config("faiss", MULTILINGUAL, 300, 50),
    Config("chroma", MULTILINGUAL, 500, 80),
    Config("faiss", MULTILINGUAL, 500, 80),
    Config("chroma", MULTILINGUAL, 800, 120),  # chunk size of the first version
    Config("faiss", MULTILINGUAL, 800, 120),
    Config("chroma", ENGLISH_BGE, 800, 120),  # embedding model + chunk size of the first version
]


def p95(values: list[float]) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def run(cfg: Config, data: dict, k: int, min_relevance: float, embeddings_cache: dict) -> dict:
    emb = embeddings_cache.setdefault(cfg.embedding, build_embeddings(cfg.embedding))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # Chroma locks files on Windows
        settings = Settings(
            vector_store=cfg.store,
            embedding_model=cfg.embedding,
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
            storage_dir=Path(tmp),
            llm_provider="none",
            log_file=None,
        )
        pipe = RAGPipeline(settings, embeddings=emb, use_llm_from_settings=False)
        ing = pipe.ingest_pdf(HERE.parent / data["document"])
        for _ in range(3):  # warm-up so the first configuration is not penalised
            pipe.retrieve("warm-up query", k)

        hits1 = hitsk = 0
        rr: list[float] = []
        lat: list[float] = []
        false_refusals = 0
        in_scores: list[float] = []
        per_question = []
        for item in data["in_corpus"]:
            t0 = time.perf_counter()
            hits = pipe.retrieve(item["question"], k)
            lat.append((time.perf_counter() - t0) * 1000)
            pages = [d.metadata["page"] for d, _ in hits]
            rank = next((i + 1 for i, p in enumerate(pages) if p in item["expected_pages"]), None)
            hits1 += rank == 1
            hitsk += rank is not None
            rr.append(1 / rank if rank else 0.0)
            best = hits[0][1] if hits else -1
            in_scores.append(best)
            false_refusals += best < min_relevance
            per_question.append({"id": item["id"], "rank": rank, "pages": pages, "best": round(best, 3)})

        out_scores = []
        for item in data["out_of_corpus"]:
            hits = pipe.retrieve(item["question"], k)
            out_scores.append(hits[0][1] if hits else -1)
        refused = sum(s < min_relevance for s in out_scores)

        n_in, n_out = len(data["in_corpus"]), len(data["out_of_corpus"])
        return {
            "config": cfg.label,
            "store": cfg.store,
            "embedding": cfg.embedding,
            "chunk_size": cfg.chunk_size,
            "chunks": ing.chunks,
            "index_seconds": ing.seconds,
            "hit_at_1": round(hits1 / n_in, 3),
            f"hit_at_{k}": round(hitsk / n_in, 3),
            "mrr": round(statistics.mean(rr), 3),
            "refusal_rate_out_of_corpus": round(refused / n_out, 3),
            "false_refusal_rate_in_corpus": round(false_refusals / n_in, 3),
            "retrieval_ms_mean": round(statistics.mean(lat), 2),
            "retrieval_ms_p95": round(p95(lat), 2),
            "min_in_corpus_score": round(min(in_scores), 3),
            "max_out_of_corpus_score": round(max(out_scores), 3),
            "per_question": per_question,
        }


def to_markdown(results: list[dict], k: int, n_in: int, n_out: int, min_relevance: float) -> str:
    lines = [
        f"Questions: {n_in} in-corpus, {n_out} out-of-corpus. k = {k}, MIN_RELEVANCE = {min_relevance}.",
        "",
        f"| Configuration | Chunks | Index (s) | Hit@1 | Hit@{k} | MRR | Refusal (out) | "
        "False refusal (in) | Retrieval mean / p95 (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['config']} | {r['chunks']} | {r['index_seconds']} | {r['hit_at_1']:.2f} | "
            f"{r[f'hit_at_{k}']:.2f} | {r['mrr']:.2f} | {r['refusal_rate_out_of_corpus']:.0%} | "
            f"{r['false_refusal_rate_in_corpus']:.0%} | {r['retrieval_ms_mean']} / {r['retrieval_ms_p95']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--min-relevance", type=float, default=Settings().min_relevance)
    parser.add_argument("--quick", action="store_true", help="only the default configuration")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    data = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    grid = GRID[:1] if args.quick else GRID
    cache: dict = {}
    results = []
    for cfg in grid:
        print(f"-> {cfg.label}", flush=True)
        res = run(cfg, data, args.k, args.min_relevance, cache)
        print(
            f"   hit@1={res['hit_at_1']} hit@{args.k}={res[f'hit_at_{args.k}']} mrr={res['mrr']} "
            f"refusal={res['refusal_rate_out_of_corpus']} false_refusal="
            f"{res['false_refusal_rate_in_corpus']} ret={res['retrieval_ms_mean']}ms",
            flush=True,
        )
        results.append(res)

    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(results, args.k, len(data["in_corpus"]), len(data["out_of_corpus"]), args.min_relevance)
    (OUT / "results.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
