"""Backward-compatible entry point: `uvicorn main:app` still works.

The application now lives in the `app` package (see app/main.py).
"""

from app.main import app  # noqa: F401
