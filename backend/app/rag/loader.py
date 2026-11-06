"""Step 1-2 of the pipeline: load a PDF and split it into page-aware chunks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_WS = re.compile(r"[ \t]+")
_NL = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = _WS.sub(" ", text)
    return _NL.sub("\n\n", text).strip()


def load_pdf(path: Path, source_name: str | None = None) -> list[Document]:
    """Load one Document per PDF page, with a 1-based `page` and a `source` name."""
    source = source_name or path.name
    pages = PyPDFLoader(str(path)).load()
    docs: list[Document] = []
    for d in pages:
        text = _clean(d.page_content)
        if not text:
            continue  # scanned/empty page: nothing to index (no OCR in this project)
        page = int(d.metadata.get("page", 0)) + 1
        docs.append(Document(page_content=text, metadata={"source": source, "page": page}))
    return docs


def split_documents(docs: list[Document], chunk_size: int = 800, chunk_overlap: int = 120) -> list[Document]:
    """Split pages into overlapping chunks; each chunk keeps its page number.

    A deterministic `chunk_id` (hash of source, page and text) makes re-ingesting the
    same file idempotent: the vector store upserts instead of duplicating.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        key = f"{c.metadata['source']}|{c.metadata['page']}|{i}|{c.page_content}"
        c.metadata["chunk_id"] = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return chunks
