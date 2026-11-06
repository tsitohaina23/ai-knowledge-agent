from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.security import safe_filename
from tests.conftest import make_pipeline


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["indexed_chunks"] == 0
    assert body["vector_store"] == "chroma"


def test_ask_before_ingest_returns_409(client):
    r = client.post("/ask", json={"question": "Combien de jours de congés ?"})
    assert r.status_code == 409


def test_ingest_upload_then_ask(client, settings):
    with settings.sample_pdf.open("rb") as f:
        r = client.post("/ingest", files={"file": ("guide.pdf", f, "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["pages"] == 10 and r.json()["total_chunks"] > 0

    r = client.post("/ask", json={"question": "Combien de jours de congés payés par an ?"})
    assert r.status_code == 200
    body = r.json()
    assert body["sources"][0]["page"] == 3
    assert set(body["latency_ms"]) == {"retrieval", "generation", "total"}
    assert body["tokens"]["total"] == 0 and body["cost_usd"] == 0
    assert settings.log_file.exists()
    log = settings.log_file.read_text(encoding="utf-8")
    assert "congés" not in log  # question text is never logged, only its hash


def test_ingest_sample_endpoint(client):
    r = client.post("/ingest/sample")
    assert r.status_code == 200 and r.json()["source"] == "guide-employe-ravinala.pdf"


def test_upload_stream_emits_progress(client, settings):
    with settings.sample_pdf.open("rb") as f:
        r = client.post("/upload-stream", files={"file": ("guide.pdf", f, "application/pdf")})
    assert r.status_code == 200
    assert '"progress": 100' in r.text


def test_rejects_non_pdf(client):
    r = client.post("/ingest", files={"file": ("notes.pdf", b"hello world", "application/pdf")})
    assert r.status_code == 415
    r = client.post("/ingest", files={"file": ("notes.txt", b"%PDF-1.4", "text/plain")})
    assert r.status_code == 415


def test_rejects_too_large_pdf(settings, pipeline):
    settings.max_upload_mb = 0  # every non-empty upload is too large
    with TestClient(create_app(settings, pipeline)) as c:
        r = c.post("/ingest", files={"file": ("big.pdf", b"%PDF-1.4 " + b"x" * 10, "application/pdf")})
    assert r.status_code == 413


def test_question_validation(client):
    assert client.post("/ask", json={"question": "a"}).status_code == 422
    assert client.post("/ask", json={"question": "x" * 501}).status_code == 422
    assert client.post("/ask", json={"question": "valid question", "k": 50}).status_code == 422


def test_rate_limit(settings, embeddings):
    settings.rate_limit_ask_per_min = 2
    pipe = make_pipeline(settings, embeddings)
    pipe.ingest_pdf(settings.sample_pdf)
    with TestClient(create_app(settings, pipe)) as c:
        codes = [c.post("/ask", json={"question": "jours de congés ?"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_safe_filename_blocks_path_traversal():
    assert safe_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert safe_filename("..\\..\\win.pdf").endswith("win.pdf")
    assert "/" not in safe_filename("a/b/c.pdf")
