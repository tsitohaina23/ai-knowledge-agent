"""Pydantic request/response models (they also drive the OpenAPI docs at /docs)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, examples=["Combien de jours de congés par an ?"])
    k: int | None = Field(None, ge=1, le=10, description="Number of passages to retrieve")

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("question is too short")
        return v


class SourceOut(BaseModel):
    n: int
    source: str
    page: int
    score: float = Field(..., description="Cosine similarity between question and passage")
    excerpt: str


class Latency(BaseModel):
    retrieval: float
    generation: float
    total: float


class Tokens(BaseModel):
    input: int
    output: int
    total: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    refused: bool = Field(..., description="True when the documents do not cover the question")
    provider: str
    model: str
    latency_ms: Latency
    tokens: Tokens
    cost_usd: float = Field(0.0, description="Always 0: everything runs locally")
    cached: bool
    warnings: list[str] = []


class IngestResponse(BaseModel):
    source: str
    pages: int
    chunks: int
    added: int = Field(..., description="New chunks (re-ingesting the same file adds 0)")
    seconds: float
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    vector_store: str
    embedding_model: str
    indexed_chunks: int
    cache: dict[str, int]


class ErrorResponse(BaseModel):
    detail: str
