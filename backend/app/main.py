"""FastAPI application: /health, /ingest, /ask (+ /upload-stream for the UI progress bar).

Run locally:  uvicorn app.main:app --reload      (interactive docs: http://localhost:8000/docs)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.rag.llm import LLMConfigError
from app.rag.pipeline import RAGPipeline
from app.schemas import AskRequest, AskResponse, ErrorResponse, HealthResponse, IngestResponse
from app.security import RateLimiter, save_pdf_upload

logger = logging.getLogger("rag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

ERRORS = {
    400: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


class RequestLog:
    """Append one JSON line per request (latency, tokens, cache...). The question text
    itself is not stored, only its length and a short hash (privacy by default)."""

    def __init__(self, path: Path | None):
        self.path = path
        self._lock = threading.Lock()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **event) -> None:
        event = {"ts": round(time.time(), 3), **event}
        logger.info(json.dumps(event, ensure_ascii=False))
        if self.path:
            with self._lock, self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")


def create_app(settings: Settings | None = None, pipeline: RAGPipeline | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.pipeline is None:
            app.state.pipeline = RAGPipeline(settings)
        if settings.auto_ingest_sample and app.state.pipeline.index.count() == 0:
            app.state.pipeline.ingest_pdf(settings.sample_pdf)
        yield

    app = FastAPI(
        title="AI Knowledge Agent - local RAG API",
        version="1.0.0",
        description=(
            "Ask questions about your PDFs. Answers cite the source pages. "
            "100 % local: FastEmbed embeddings, ChromaDB/FAISS, optional Ollama LLM."
        ),
        lifespan=lifespan,
    )
    app.state.pipeline = pipeline
    app.state.settings = settings
    app.state.limiter = RateLimiter()
    app.state.log = RequestLog(settings.log_file)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def get_pipeline(request: Request) -> RAGPipeline:
        return request.app.state.pipeline

    def run_ingest(pipe: RAGPipeline, path: Path, name: str, progress=None) -> IngestResponse:
        try:
            res = pipe.ingest_pdf(path, name, progress)
        except Exception as exc:  # corrupted / encrypted PDF...
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Cannot read PDF: {exc}") from exc
        if res.chunks == 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No extractable text (scanned PDF? OCR is not supported).",
            )
        app.state.log.write(
            endpoint="ingest",
            source=name,
            pages=res.pages,
            chunks=res.chunks,
            added=res.added,
            seconds=res.seconds,
        )
        return IngestResponse(**res.__dict__, total_chunks=pipe.index.count())

    # ------------------------------------------------------------------ routes
    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health(pipe: RAGPipeline = Depends(get_pipeline)):
        return HealthResponse(
            status="ok",
            provider=pipe.provider,
            model=pipe.model,
            vector_store=pipe.index.kind,
            embedding_model=settings.embedding_model,
            indexed_chunks=pipe.index.count(),
            cache={"entries": len(pipe.cache), "hits": pipe.cache.hits, "misses": pipe.cache.misses},
        )

    @app.post("/ingest", response_model=IngestResponse, responses=ERRORS, tags=["documents"])
    async def ingest(
        request: Request, file: UploadFile = File(...), pipe: RAGPipeline = Depends(get_pipeline)
    ):
        """Upload a PDF, split it into chunks and index them (idempotent)."""
        app.state.limiter.check(request, "ingest", settings.rate_limit_ingest_per_min)
        path, name = await save_pdf_upload(file, settings.max_upload_bytes)
        try:
            return await asyncio.to_thread(run_ingest, pipe, path, name)
        finally:
            path.unlink(missing_ok=True)

    @app.post("/ingest/sample", response_model=IngestResponse, responses=ERRORS, tags=["documents"])
    def ingest_sample(request: Request, pipe: RAGPipeline = Depends(get_pipeline)):
        """Index the bundled CC0 sample PDF (fictional employee handbook)."""
        app.state.limiter.check(request, "ingest", settings.rate_limit_ingest_per_min)
        return run_ingest(pipe, settings.sample_pdf, settings.sample_pdf.name)

    @app.post("/upload-stream", responses=ERRORS, tags=["documents"])
    async def upload_stream(
        request: Request, file: UploadFile = File(...), pipe: RAGPipeline = Depends(get_pipeline)
    ):
        """Same as /ingest but streams progress as Server-Sent Events (used by the UI)."""
        app.state.limiter.check(request, "ingest", settings.rate_limit_ingest_per_min)
        path, name = await save_pdf_upload(file, settings.max_upload_bytes)
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def progress(pct: int, msg: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, {"progress": pct, "message": msg})

        async def worker():
            try:
                await asyncio.to_thread(run_ingest, pipe, path, name, progress)
            except HTTPException as exc:
                await queue.put({"error": exc.detail})
            finally:
                path.unlink(missing_ok=True)
                await queue.put(None)

        async def events():
            task = asyncio.create_task(worker())
            while (item := await queue.get()) is not None:
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            await task

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/ask", response_model=AskResponse, responses=ERRORS, tags=["questions"])
    def ask(body: AskRequest, request: Request, pipe: RAGPipeline = Depends(get_pipeline)):
        """Answer a question from the indexed documents, with cited pages, latency and tokens."""
        app.state.limiter.check(request, "ask", settings.rate_limit_ask_per_min)
        if pipe.index.count() == 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "No document indexed yet: call /ingest or /ingest/sample first."
            )
        try:
            result = pipe.ask(body.question, body.k)
        except LLMConfigError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        except Exception as exc:  # e.g. Ollama not running
            logger.exception("generation failed")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"LLM unavailable ({type(exc).__name__}). Is Ollama running? "
                "Or set LLM_PROVIDER=none for extractive mode.",
            ) from exc
        app.state.log.write(
            endpoint="ask",
            q_len=len(body.question),
            q_hash=hashlib.sha256(body.question.encode()).hexdigest()[:10],
            provider=result.provider,
            model=result.model,
            refused=result.refused,
            cached=result.cached,
            n_sources=len(result.sources),
            latency_ms=result.latency_ms,
            tokens=result.tokens,
            warnings=result.warnings,
        )
        return result.to_dict()

    if settings.static_dir and Path(settings.static_dir).is_dir():
        # Optional: serve the built React UI from the same local process.
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")

    return app


app = create_app()
