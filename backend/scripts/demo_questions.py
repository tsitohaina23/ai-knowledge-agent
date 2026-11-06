"""Ask a few questions to a running API (default http://localhost:8000).

Usage:  python scripts/demo_questions.py [--url http://localhost:8000]
It indexes the bundled sample PDF first (idempotent), then prints each answer.
"""

from __future__ import annotations

import argparse
import sys

import httpx

QUESTIONS = [
    "Combien de jours de congés payés par an ?",
    "Combien de jours de télétravail par semaine sont autorisés ?",
    "Quel est le plafond de remboursement d'un repas d'affaires ?",
    "Quelle est la longueur minimale d'un mot de passe ?",
    "Quel numéro appeler en cas d'urgence dans les locaux ?",
    "Quelle est la capitale du Japon ?",  # out of corpus -> must be refused
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(base_url=args.url, timeout=120) as http:
        ing = http.post("/ingest/sample").raise_for_status().json()
        print(f"Indexed {ing['source']}: {ing['pages']} pages, {ing['total_chunks']} chunks\n")
        for q in QUESTIONS:
            r = http.post("/ask", json={"question": q})
            r.raise_for_status()
            d = r.json()
            pages = [s["page"] for s in d["sources"]]
            print(f"Q: {q}")
            print(
                f"   refused={d['refused']} pages={pages} latency={d['latency_ms']['total']} ms "
                f"tokens={d['tokens']['total']} cached={d['cached']}"
            )
            for line in d["answer"].splitlines()[:2]:
                print(f"   {line[:180]}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
