# AI Software Engineer Assistant

An AI-powered platform that analyzes GitHub repositories: it explains codebases,
detects bugs and security issues, generates documentation and unit tests, and
provides repository-aware chat using Retrieval-Augmented Generation (RAG).

## Architecture

```
Web (Next.js)  →  API (FastAPI)  →  Worker (Celery)
                       │                  │
        Postgres ◄─────┼──────► Redis ◄───┘
        Chroma   ◄─────┴──────► Inference (Qwen3-Coder via vLLM/Ollama/LM Studio)
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

## Installation

The AI layer runs a **local Qwen3-Coder-30B** — no hosted LLM APIs. The fastest
path is Docker; everything (Postgres, Redis, ChromaDB, API, worker, web, and the
inference server) comes up together.

### Prerequisites

- **Docker** + Docker Compose
- An **NVIDIA GPU** + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  to serve the model (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for hardware
  tiers and CPU/desktop options via Ollama/LM Studio)
- For local (non-Docker) development: **Python 3.11+** and **Node.js 18+**

### 1. Configure environment

```bash
cp backend/.env.example backend/.env      # set JWT_SECRET_KEY (see below)
cp frontend/.env.example frontend/.env
```

Generate a strong JWT secret and paste it into `backend/.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The LLM defaults already point at the in-network inference service
(`LLM_BASE_URL=http://inference:8000/v1`). To change inference backend or model,
see the matrix in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### 2. Start the stack

```bash
# Production default — vLLM (needs an NVIDIA GPU)
docker compose -f docker-compose.yml -f deploy/vllm/docker-compose.vllm.yml up --build

# Or, for a single-GPU dev box — Ollama
docker compose -f docker-compose.yml -f deploy/ollama/docker-compose.ollama.yml up --build
docker compose exec inference ollama pull qwen3-coder:30b
docker compose exec inference ollama pull nomic-embed-text
```

The first run downloads model weights (several minutes). Database migrations run
automatically when the API container starts.

### 3. Verify

- Web UI: <http://localhost:3000>
- API docs (OpenAPI): <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/v1/health>

Sign up at `/signup`, add a repository, and once it finishes indexing you can run
analysis, scans, docs, tests, chat, and reports.

## Development guide

### Project layout

```
backend/
  app/
    domain/          entities, enums, exceptions (no framework deps)
    application/     use-cases, ports (interfaces), services, prompts
    infrastructure/  db, llm (providers), vector, code_intel (AST), git, ...
    presentation/    FastAPI routers, schemas, DI (deps.py)
    workers/         Celery app + tasks (clone/index/analyze/generate)
  alembic/           migrations
  tests/             unit + integration
frontend/            Next.js App Router UI (src/app, components, lib)
deploy/              vllm / ollama / lmstudio inference backends
docs/                DEPLOYMENT.md (model serving + hardware)
docker-compose.yml   db + redis + chroma + api + worker + web
```

Clean Architecture dependency rule: `domain ← application ← infrastructure/presentation`.
Use-cases depend only on ports (e.g. `LLMPort`); concrete providers are wired in
`presentation/deps.py`.

### Run the backend locally

You still need Postgres, Redis, ChromaDB, and an inference server reachable. The
simplest combo is Docker for infra + a local API/worker:

```bash
# infra + inference only
docker compose -f docker-compose.yml -f deploy/ollama/docker-compose.ollama.yml up db redis chroma inference

cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# point the app at the host-published ports (override the in-network defaults)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_swe
export REDIS_URL=redis://localhost:6379/0
export CHROMA_HOST=localhost CHROMA_PORT=8001
export LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=qwen3-coder:30b LLM_STRUCTURED_MODE=ollama_format
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

alembic upgrade head
uvicorn app.main:app --reload
# in another shell, run the worker:
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### Run the frontend locally

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env` if the API isn't proxied at
`/api/v1`.

### Tests, linting, types

```bash
# backend (from backend/)
pytest                       # full suite with coverage (configured in pyproject)
pytest tests/unit/test_prompts.py        # a single file
pytest -k hybrid                          # by keyword
ruff check .                 # lint
mypy app                     # type-check

# frontend (from frontend/)
npm run lint
npm run typecheck            # tsc --noEmit
```

### Database migrations

```bash
cd backend
alembic upgrade head                         # apply
alembic revision -m "describe change"        # new migration (then edit it)
alembic downgrade -1                          # roll back one
```

Register every new ORM model in `app/infrastructure/db/models/__init__.py` so it
is visible to the metadata/migrations.

### Adding a feature module

Follow the established pattern: domain entity/enum → repository port (in
`application/interfaces`) → SQLAlchemy model + migration + repo impl → use-case
service (owner-scoped) and any worker pipeline → centralized prompt in
`application/prompts` → presentation schema + router + DI in `deps.py` → frontend
types, API client, hook, and page. Always pass repository content through
`wrap_untrusted` before sending it to the LLM.

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
