"""Step 3 of the pipeline: vector index (ChromaDB by default, FAISS optional).

Both back-ends are wrapped behind the same tiny interface and return a **cosine
similarity** in [-1, 1] so the relevance threshold (refusal when the corpus does not
cover the question) means the same thing whatever the store.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

ScoredDoc = tuple[Document, float]


class VectorIndex(Protocol):
    kind: str

    def add(self, chunks: list[Document]) -> int: ...
    def search(self, query: str, k: int) -> list[ScoredDoc]: ...
    def count(self) -> int: ...
    def reset(self) -> None: ...


class ChromaIndex:
    """Persistent ChromaDB collection configured for cosine distance."""

    kind = "chroma"

    def __init__(self, embeddings: Embeddings, directory: Path, collection: str):
        self._embeddings = embeddings
        self._directory = directory
        self._collection_name = collection
        self._db = self._open()

    def _open(self):
        from langchain_chroma import Chroma

        self._directory.mkdir(parents=True, exist_ok=True)
        return Chroma(
            collection_name=self._collection_name,
            embedding_function=self._embeddings,
            persist_directory=str(self._directory),
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Document]) -> int:
        if not chunks:
            return 0
        ids = [c.metadata["chunk_id"] for c in chunks]
        self._db.add_documents(chunks, ids=ids)  # upsert: re-ingestion is idempotent
        return len(chunks)

    def search(self, query: str, k: int) -> list[ScoredDoc]:
        if self.count() == 0:
            return []
        hits = self._db.similarity_search_with_score(query, k=k)
        return [(doc, 1.0 - float(dist)) for doc, dist in hits]  # cosine distance -> sim

    def count(self) -> int:
        return self._db._collection.count()

    def reset(self) -> None:
        self._db.delete_collection()
        self._db = self._open()


class FaissIndex:
    """In-memory FAISS index (inner product on L2-normalised vectors = cosine),
    saved to disk after each ingestion."""

    kind = "faiss"

    def __init__(self, embeddings: Embeddings, directory: Path):
        self._embeddings = embeddings
        self._directory = directory
        self._db = None
        if (directory / "index.faiss").exists():
            from langchain_community.vectorstores import FAISS

            # The pickle docstore was written by this app itself (never load untrusted files).
            self._db = FAISS.load_local(
                str(directory), embeddings, allow_dangerous_deserialization=True
            )

    def _new(self, chunks: list[Document], ids: list[str]):
        from langchain_community.vectorstores import FAISS
        from langchain_community.vectorstores.utils import DistanceStrategy

        return FAISS.from_documents(
            chunks,
            self._embeddings,
            ids=ids,
            normalize_L2=True,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )

    def add(self, chunks: list[Document]) -> int:
        if self._db is not None:
            existing = set(self._db.index_to_docstore_id.values())
            chunks = [c for c in chunks if c.metadata["chunk_id"] not in existing]
        if not chunks:
            return 0
        ids = [c.metadata["chunk_id"] for c in chunks]
        if self._db is None:
            self._db = self._new(chunks, ids)
        else:
            self._db.add_documents(chunks, ids=ids)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._db.save_local(str(self._directory))
        return len(chunks)

    def search(self, query: str, k: int) -> list[ScoredDoc]:
        if self._db is None:
            return []
        return [(d, float(s)) for d, s in self._db.similarity_search_with_score(query, k=k)]

    def count(self) -> int:
        return 0 if self._db is None else int(self._db.index.ntotal)

    def reset(self) -> None:
        self._db = None
        shutil.rmtree(self._directory, ignore_errors=True)


def build_index(kind: str, embeddings: Embeddings, storage_dir: Path, collection: str) -> VectorIndex:
    if kind == "faiss":
        return FaissIndex(embeddings, storage_dir / "faiss")
    if kind == "chroma":
        return ChromaIndex(embeddings, storage_dir / "chroma", collection)
    raise ValueError(f"Unknown VECTOR_STORE '{kind}' (expected 'chroma' or 'faiss')")


def build_embeddings(model_name: str) -> Embeddings:
    """Local CPU embeddings via FastEmbed (ONNX) - no API key, no GPU needed."""
    from langchain_community.embeddings import FastEmbedEmbeddings

    return FastEmbedEmbeddings(model_name=model_name)
