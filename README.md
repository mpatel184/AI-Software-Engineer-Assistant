# AI Software Engineer Assistant

An AI-powered platform that analyzes GitHub repositories: it explains codebases,
detects bugs and security issues, generates documentation and unit tests, and
provides repository-aware chat using Retrieval-Augmented Generation (RAG).

## Architecture

```
Web (Next.js)  →  API (FastAPI)  →  Worker (Celery)
                       │                  │
        Postgres ◄─────┼──────► Redis ◄───┘
        Chroma   ◄─────┴──────► Claude API
```

- **Frontend** — Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + React Query
- **Backend** — FastAPI + SQLAlchemy (async) + Pydantic, Clean Architecture
  (`domain` ← `application` ← `infrastructure`/`presentation`)
- **Worker** — Celery + Redis for clone / index / analyze / generate jobs
- **Datastores** — PostgreSQL (metadata + symbol index), ChromaDB (vectors), Redis (broker/cache/rate-limit)
- **AI** — **local Qwen3-Coder-30B** behind a model-agnostic `LLMProvider`
  (vLLM / Ollama / LM Studio); local code-aware embeddings (nomic). No hosted
  LLM APIs. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- **Code understanding** — AST + symbol index (`code_intel`) feeding hybrid
  retrieval (semantic vectors + exact symbol lookup) for RAG chat

## Quick start (Docker)

The AI layer runs a **local Qwen3-Coder-30B** (no hosted LLM APIs). Pick an
inference backend — vLLM is the production default (needs an NVIDIA GPU):

```bash
cp backend/.env.example backend/.env      # set JWT_SECRET_KEY; LLM defaults to local Qwen
cp frontend/.env.example frontend/.env
docker compose -f docker-compose.yml -f deploy/vllm/docker-compose.vllm.yml up --build
```

For dev on a single GPU, use Ollama instead (see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**
for the backend matrix, hardware requirements, and how to swap backends).

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Local development

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Project layout

```
backend/    FastAPI app (clean architecture), Celery worker, Alembic migrations
frontend/   Next.js App Router UI
docker-compose.yml   db + redis + chroma + api + worker + web
```

## Build status

Built incrementally, module by module. All feature modules are implemented:

- ✅ Module 1 — Authentication (JWT, refresh-token rotation)
- ✅ Module 2 — Dashboard
- ✅ Module 3 — Repository Upload (zip, safe extraction)
- ✅ Module 4 — GitHub Integration (clone + RAG indexing)
- ✅ Module 5 — Repository Analyzer (architecture, metrics, health score)
- ✅ Module 6 — Documentation Generator (README / API / function / class docs)
- ✅ Module 7 — Bug Detection (bugs, code smells, performance, duplication, dead code)
- ✅ Module 8 — Security Scanner (severity-rated vulnerability findings)
- ✅ Module 9 — Test Generator (per-file unit-test generation)
- ✅ Module 10 — RAG Chat (repository-aware Q&A with source citations)
- ✅ Module 11 — Report Generator (aggregated reports + PDF export)
- ✅ Module 12 — Settings (profile, password change, appearance)
- ✅ Refactoring — per-file, behavior-preserving refactoring suggestions

### Design notes

- **Bugs & Security** reuse the `analyses` table (`type = bugs|security`); the
  finding-based scan pipeline lives in `application/use_cases/analysis/findings.py`
  and stores severity-rated findings in the analysis `summary`/`metrics`.
- **Test generation** is synchronous and per-file, with path-traversal-safe file
  access (`application/services/repo_files.py`).
- **RAG Chat** retrieves from ChromaDB scoped by `repo_id` **and** `user_id`
  (the authorization boundary) and wraps repo content as untrusted data.
- **Reports** are assembled deterministically from existing analyses; PDF is
  rendered on demand via reportlab (imported lazily).
