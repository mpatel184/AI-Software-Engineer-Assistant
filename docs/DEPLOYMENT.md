# Deployment Guide

This project is designed to be lightweight and easy to deploy, relying on **free cloud LLMs** (like Gemini 2.5 Flash) instead of requiring expensive local GPUs. 

## Architecture recap

```
API / Worker  ──OpenAI-compatible HTTP──▶  Cloud LLM (Gemini 2.5 Flash / Z.ai GLM)
     │
     ├── embeddings (Google text-embedding-004)
     ├── ChromaDB (vectors)
     └── Postgres (metadata, symbols)
```

The app communicates with the LLM purely via standard environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`). Swapping the backend never touches the core codebase.

## Prerequisites

- **Docker** + Docker Compose
- **LLM API Key** (e.g., from Google AI Studio)

No NVIDIA GPU or local VRAM is required. The embeddings and completion endpoints use the same standard HTTP APIs.

## Deployment with Docker Compose (Recommended)

The entire stack (Postgres, Redis, ChromaDB, FastAPI Backend, Celery Worker, Next.js Frontend) can be brought up in a single command.

1. **Configure Environment**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. **Set your API Keys**
   Open `backend/.env` and add:
   ```env
   LLM_API_KEY=your_google_aistudio_api_key_here
   JWT_SECRET_KEY=your_secure_random_string
   ```

3. **Start the Stack**
   ```bash
   docker compose up --build -d
   ```
   This will spin up all containers in the background. Database migrations (`alembic upgrade head`) run automatically when the API container starts.

## Local Inference Fallback (Ollama / vLLM)

While this project is optimized for cloud LLMs, the architecture remains fully compatible with local inference if you have the necessary hardware (e.g., RTX 3090/4090 or A6000).

To use local inference:
1. Start your local server (e.g. `ollama serve` or vLLM).
2. Update `backend/.env`:
   ```env
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_MODEL=your-local-model
   ```

## Bottlenecks & Mitigations

1. **Prefill cost on large prompts** (whole-repo analysis/findings). → AST-guided context selection + retrieval instead of dumping files; cache per commit SHA.
2. **LLM Rate Limits (Free Tier).** → The Celery worker implements `tenacity` exponential backoff to gracefully handle `429 Too Many Requests` when using free APIs like Gemini.
3. **Structured-JSON reliability.** → All backends fall back to a robust parse-and-repair strategy (`infrastructure/llm/structured.py`) and use strict JSON mode when available.
4. **Indexing throughput** on big repos. → Batched embeddings, idempotent per SHA.
