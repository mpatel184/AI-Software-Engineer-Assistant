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
- **Datastores** — PostgreSQL (metadata), ChromaDB (vectors), Redis (broker/cache/rate-limit)
- **AI** — Claude API behind an `LLMPort`; local embeddings via fastembed

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env      # fill in ANTHROPIC_API_KEY, JWT_SECRET_KEY
cp frontend/.env.example frontend/.env
docker compose up --build
```

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

This project is being built incrementally, module by module. Completed:
- ✅ Architecture & folder structure
- ✅ Database schema design
- ✅ Backend foundation (config, logging, DI, error handling, health, Docker)
- ✅ Frontend foundation (App Router shell, theme, React Query, API client, sidebar)

Upcoming: Authentication → Repository upload/GitHub → Analyzer → Docs → Bugs →
Security → Tests → RAG Chat → Reports → Settings.
