# AI Software Engineer Assistant

An AI-powered platform that analyzes GitHub repositories: it explains codebases,
detects bugs and security issues, generates documentation and unit tests, and
provides repository-aware chat using Retrieval-Augmented Generation (RAG).

## Architecture

```
Web (Next.js)  →  API (FastAPI)  →  Worker (Celery)
                       │                  │
        Postgres ◄─────┼──────► Redis ◄───┘
        Chroma   ◄─────┴──────► Cloud LLM (Gemini 2.5 Flash / Z.ai GLM)
```

- **Frontend** — Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + React Query
- **Backend** — FastAPI + SQLAlchemy (async) + Pydantic, Clean Architecture
  (`domain` ← `application` ← `infrastructure`/`presentation`)
- **Worker** — Celery + Redis for clone / index / analyze / generate jobs
- **Datastores** — PostgreSQL (metadata + symbol index), ChromaDB (vectors), Redis (broker/cache/rate-limit)
- **AI** — **Gemini 2.5 Flash** (free via Google AI Studio) behind a model-agnostic
  `LLMProvider`. Any OpenAI-compatible API (Z.ai GLM, OpenAI, or self-hosted vLLM/Ollama)
  can be used by changing a few env vars — no code changes required.
- **Embeddings** — By default uses Google `text-embedding-004` (768-dim).
  Can be switched to local sentence-transformers model (`BAAI/bge-small-en-v1.5` by default)
  by setting `EMBEDDING_PROVIDER=local` in backend/.env.
- **Code understanding** — AST + symbol index (`code_intel`) feeding hybrid
  retrieval (semantic vectors + exact symbol lookup) for RAG chat

## Installation

The AI layer uses a **free cloud LLM (Gemini 2.5 Flash)**. No GPU required.
The fastest path is Docker; everything (Postgres, Redis, ChromaDB, API, worker,
and web) comes up together.

### Prerequisites

- **Docker** + Docker Compose
- **A free Gemini API key** from [aistudio.google.com](https://aistudio.google.com)
  (no credit card required)
- For local (non-Docker) development: **Python 3.11+** and **Node.js 18+**

### 1. Get a free LLM API key

1. Go to [https://aistudio.google.com](https://aistudio.google.com) and sign in with your Google account.
2. Click **Get API Key** → **Create API key**.
3. Copy the key — you'll paste it into `backend/.env` in the next step.

> **Alternative (Z.ai GLM-4.7-Flash):** Also completely free, no card needed.
> Sign up at [z.ai](https://z.ai), create an API key, and use the commented
> fallback block in `backend/.env.example`.

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Open `backend/.env` and set the following:

```bash
# Required — paste your Google AI Studio key here
LLM_API_KEY=your_google_aistudio_api_key_here

# Required — generate a secure random secret
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
```

All other values in `.env.example` are ready to use as-is. The embeddings
endpoint uses the same `LLM_API_KEY` automatically.

### 3. Start the stack

```bash
docker compose up --build
```

The first run builds images and pulls model weights for the embedding API.
Database migrations run automatically when the API container starts.

### 4. Verify

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
docs/                DEPLOYMENT.md (LLM provider details)
docker-compose.yml   db + redis + chroma + api + worker + web
```

Clean Architecture dependency rule: `domain ← application ← infrastructure/presentation`.
Use-cases depend only on ports (e.g. `LLMPort`); concrete providers are wired in
`presentation/deps.py`.

### Switching the LLM backend

The LLM layer is fully driven by env vars. To switch backends, update `backend/.env`:

| Backend | `LLM_BASE_URL` | `LLM_MODEL` | `LLM_STRUCTURED_MODE` |
|---|---|---|---|
| **Gemini 2.5 Flash** (default) | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` | `json_schema` |
| **Z.ai GLM-4.7-Flash** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4.7-flash` | `json_schema` |
| **OpenAI GPT-4o** | `https://api.openai.com/v1` | `gpt-4o` | `json_schema` |
| **Ollama (local)** | `http://localhost:11434/v1` | `your-model` | `ollama_format` |

Set `LLM_PROVIDER=openai` for all of the above (it's the generic OpenAI-compat provider).

### Switching the Embedding Provider

The embedding layer can use either a local sentence-transformers model or a remote OpenAI-compatible API. To switch embedding providers, update `backend/.env`:

| Setting | Local (Sentence-Transformers) | Remote (OpenAI-Compatible) |
|---|---|---|
| `EMBEDDING_PROVIDER` | `local` | `openai_compat` (default) |
| `EMBEDDING_BASE_URL` | *not used* | `https://generativelanguage.googleapis.com/v1beta/openai` (default) |
| `EMBEDDING_MODEL` | *not used* | `text-embedding-004` (default) |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` (default) | *not used* |
| `LOCAL_EMBEDDING_DEVICE` | `cpu`, `cuda`, `mps`, etc. (optional, auto-detected) | *not used* |
| `LOCAL_EMBEDDING_NORMALIZE` | `true` (default, recommended for BGE models) | *not used* |
| `EMBEDDING_API_KEY` | *not used* | leave blank to reuse `LLM_API_KEY` |

**Note**: When using the local provider, the model will be downloaded and cached on first use. Subsequent starts will use the cached model.

### Run the backend locally

You still need Postgres, Redis, and ChromaDB reachable. The simplest combo is
Docker for infra + a local API/worker:

```bash
# infra only
docker compose up db redis chroma

cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# point the app at the host-published ports
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_swe
export REDIS_URL=redis://localhost:6379/0
export CHROMA_HOST=localhost CHROMA_PORT=8001

# set LLM and JWT vars (or source your .env file)
export LLM_API_KEY=your_google_aistudio_api_key_here
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
