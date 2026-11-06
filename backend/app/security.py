"""Request-level protections: rate limiting and PDF upload validation."""

from __future__ import annotations

import re
import tempfile
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile, status

PDF_MAGIC = b"%PDF-"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


class RateLimiter:
    """Sliding-window limiter per (client IP, bucket). In-memory: fine for one process."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, request: Request, bucket: str, limit: int, window_s: float = 60.0) -> None:
        if limit <= 0:
            return
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            q = self._hits[(client, bucket)]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                retry = int(window_s - (now - q[0])) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded ({limit}/min). Retry in {retry}s.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)


def safe_filename(name: str | None) -> str:
    """Keep only a harmless base name (no path traversal, no odd characters)."""
    base = Path(name or "document.pdf").name
    base = _SAFE_NAME.sub("_", base).strip(" .") or "document.pdf"
    return base[:100]


async def save_pdf_upload(file: UploadFile, max_bytes: int) -> tuple[Path, str]:
    """Validate an uploaded PDF (extension, size, magic bytes) and store it in a temp file.

    Returns (temp_path, display_name). The caller must delete temp_path.
    """
    name = safe_filename(file.filename)
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only .pdf files are accepted.")
    tmp = tempfile.NamedTemporaryFile(prefix="upload_", suffix=".pdf", delete=False)
    size = 0
    try:
        with tmp:
            while chunk := await file.read(1024 * 1024):
                if size == 0 and not chunk.startswith(PDF_MAGIC):
                    raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Not a valid PDF file.")
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"PDF too large (max {max_bytes // (1024 * 1024)} MB).",
                    )
                tmp.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file.")
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return Path(tmp.name), name
