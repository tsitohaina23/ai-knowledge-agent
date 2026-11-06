"""Application settings, read from environment variables (or a local .env file)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

Provider = Literal["none", "ollama"]
VectorStoreKind = Literal["chroma", "faiss"]

# Everything runs locally: 'none' = extractive mode, 'ollama' = local open-source LLM.
# Default chat model per provider (overridable with LLM_MODEL).
DEFAULT_MODELS: dict[str, str] = {
    "ollama": "qwen2.5:3b",
    "none": "extractive",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: Provider = "none"
    llm_model: str | None = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 700
    llm_timeout_s: float = 60.0
    ollama_base_url: str = "http://localhost:11434"

    # --- Retrieval ---
    vector_store: VectorStoreKind = "chroma"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    # Below this cosine similarity, the best chunk is considered off-topic -> refusal.
    min_relevance: float = 0.35
    storage_dir: Path = BACKEND_DIR / "storage"
    collection_name: str = "knowledge"

    # --- API / security ---
    max_upload_mb: int = 20
    max_question_chars: int = 500
    rate_limit_ask_per_min: int = 20
    rate_limit_ingest_per_min: int = 5
    cache_ttl_s: int = 3600
    cache_max_entries: int = 256
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_ingest_sample: bool = False
    static_dir: Path | None = None  # serve the built frontend (single-container deploys)
    log_file: Path | None = BACKEND_DIR / "storage" / "requests.jsonl"

    sample_pdf: Path = BACKEND_DIR / "samples" / "guide-employe-ravinala.pdf"

    @property
    def resolved_model(self) -> str:
        return self.llm_model or DEFAULT_MODELS[self.llm_provider]

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings", "DEFAULT_MODELS", "BACKEND_DIR"]
