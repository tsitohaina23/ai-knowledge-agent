# Lignes de CV : AI Knowledge Agent

Chaque ligne ci-dessous est vérifiable dans le dépôt
(github.com/tsitohaina23/ai-knowledge-agent) : code, tests et résultats chiffrés.

## Version française (3 à 4 lignes)

**AI Knowledge Agent : assistant RAG local sur documents PDF** (Python, LangChain, FastAPI, React)
- Conception d'un pipeline RAG avec LangChain (chargement PDF, découpage par page,
  embeddings FastEmbed multilingues, ChromaDB ou FAISS) qui répond en citant les pages
  sources et refuse les questions hors corpus.
- Développement d'une API FastAPI documentée (`/ingest`, `/ask`, `/health`, validation Pydantic)
  avec cache, limite de débit, contrôle des uploads, journal de latence et protection contre
  l'injection de prompt.
- Évaluation de la recherche sur 20 questions : MRR de 0,57 à 0,86 et Hit@1 de 0,44 à 0,81
  (changement de modèle d'embeddings et de taille de blocs), 100 % de refus hors corpus, 0 % de faux refus ;
  comparaison ChromaDB vs FAISS (qualité identique, ~15 à 25 ms par recherche sur CPU).
- 22 tests pytest hors ligne (LLM simulé), CI GitHub Actions (ruff, pytest, build du frontend
  React/TypeScript) ; fonctionnement 100 % local et gratuit (LLM open source optionnel via Ollama).

## English version

**AI Knowledge Agent: local RAG assistant over PDFs** (Python, LangChain, FastAPI, React)
- Built a LangChain RAG pipeline that answers with cited source pages and refuses out-of-corpus
  questions. It covers PDF loading, page-aware chunking, multilingual FastEmbed embeddings and
  ChromaDB or FAISS.
- Developed a documented FastAPI service (`/ingest`, `/ask`, `/health`, Pydantic validation) with
  caching, rate limiting, upload checks, latency logging and prompt-injection hardening.
- Evaluated retrieval on 20 questions. MRR rose from 0.57 to 0.86 and Hit@1 from 0.44 to 0.81,
  with 100 % out-of-corpus refusals and 0 % false refusals. Compared ChromaDB and FAISS: same
  quality, about 15 to 25 ms per query on CPU.
- Wrote 22 offline pytest tests with a mocked LLM and a GitHub Actions CI (ruff, pytest, React
  build). Runs fully locally and for free, with an optional open-source LLM through Ollama.

## Mots-clés exacts à ajouter (section Compétences)

Python · RAG (Retrieval-Augmented Generation) · LangChain · LCEL · FastAPI · Pydantic ·
ChromaDB · FAISS · embeddings · FastEmbed · Sentence-Transformers · recherche sémantique ·
similarité cosinus · LLM open source · Ollama · prompt engineering · injection de prompt ·
évaluation RAG (Hit rate, MRR) · pytest · GitHub Actions (CI) · REST API · OpenAPI / Swagger ·
React · TypeScript · Vite · Tailwind CSS · documentation FR/EN

## À ne pas écrire (ce ne serait pas vrai)

- « en production » ou « utilisé par des clients » : c'est un projet de portfolio local.
- « intégration d'API LLM payantes (OpenAI, Mistral…) » : le projet n'en utilise aucune.
- « réponses générées évaluées » : seule la **recherche** est évaluée, pas la qualité des réponses du LLM.
- « déployé en ligne » : le projet tourne en local.
