"""Test fixtures: deterministic bag-of-words embeddings and a fake chat model,
so the suite runs offline in a few seconds (no model download, no LLM)."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import Settings
from app.main import create_app
from app.rag.pipeline import RAGPipeline

DIM = 4096


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+", text) if len(t) > 2]


class HashEmbeddings(Embeddings):
    """Hashed bag-of-words: similar wording -> similar vectors. Good enough for tests."""

    def _embed(self, text: str) -> list[float]:
        v = [0.0] * DIM
        for tok in _tokens(text):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        storage_dir=tmp_path / "storage",
        log_file=tmp_path / "requests.jsonl",
        llm_provider="none",
        min_relevance=0.2,
        rate_limit_ask_per_min=1000,
        rate_limit_ingest_per_min=1000,
    )


@pytest.fixture
def embeddings() -> Embeddings:
    return HashEmbeddings()


def make_pipeline(settings: Settings, embeddings: Embeddings, llm=None) -> RAGPipeline:
    return RAGPipeline(settings, embeddings=embeddings, llm=llm, use_llm_from_settings=False)


@pytest.fixture
def pipeline(settings, embeddings) -> RAGPipeline:
    return make_pipeline(settings, embeddings)


@pytest.fixture
def fake_llm():
    return FakeListChatModel(responses=["Chaque salarié a 30 jours ouvrables de congés par an [p. 3]."])


@pytest.fixture
def client(settings, pipeline):
    with TestClient(create_app(settings, pipeline)) as c:
        yield c
