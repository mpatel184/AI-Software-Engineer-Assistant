# Deployment Guide — Local Qwen3-Coder

This project runs its entire AI layer on a **locally-served Qwen3-Coder-30B**
behind an OpenAI-compatible API. No hosted LLM APIs are used. The inference
backend is swappable (vLLM / Ollama / LM Studio) by changing a few env vars.

## Architecture recap

```
API / Worker  ──OpenAI-compatible HTTP──▶  inference service (Qwen3-Coder-30B)
     │                                       (vLLM | Ollama | LM Studio)
     ├── embeddings (local: nomic-embed-text / fastembed)
     ├── ChromaDB (vectors)
     └── Postgres (metadata, symbols)
```

The app only knows `LLM_BASE_URL`. Swapping the backend never touches code.

## Backend selection matrix

| Backend | When | `LLM_BASE_URL` | `LLM_STRUCTURED_MODE` | Compose |
|---|---|---|---|---|
| **vLLM** | Production / concurrency | `http://inference:8000/v1` | `guided_json` | `-f deploy/vllm/docker-compose.vllm.yml` |
| **Ollama** | Dev / single GPU | `http://inference:11434/v1` | `ollama_format` | `-f deploy/ollama/docker-compose.ollama.yml` |
| **LM Studio** | Desktop | `http://host.docker.internal:1234/v1` | `json_schema` | host app (see `deploy/lmstudio/`) |

### vLLM (default, recommended)

```bash
cp backend/.env.example backend/.env     # keep the vLLM defaults
cp frontend/.env.example frontend/.env
docker compose -f docker-compose.yml -f deploy/vllm/docker-compose.vllm.yml up --build
```
First boot downloads the weights (several minutes). vLLM provides continuous
batching (good under Celery concurrency) and grammar-constrained `guided_json`
for reliable structured outputs.

### Ollama (easiest)

```bash
docker compose -f docker-compose.yml -f deploy/ollama/docker-compose.ollama.yml up --build
docker compose exec inference ollama pull qwen3-coder:30b
docker compose exec inference ollama pull nomic-embed-text
```
Set in `backend/.env`: `LLM_BASE_URL=http://inference:11434/v1`,
`LLM_MODEL=qwen3-coder:30b`, `LLM_STRUCTURED_MODE=ollama_format`.

## Model

`Qwen3-Coder-30B-A3B-Instruct` — Mixture-of-Experts, ~30.5B total / ~3.3B
**active** parameters, native **256K** context (extendable toward 1M via YaRN).
MoE means decode throughput closer to a ~3B dense model, which is what makes
local serving practical.

## Hardware requirements

VRAM is dominated by weights; KV cache scales with context length.

| Precision | Weights | Fits on | Practical context |
|---|---|---|---|
| BF16 | ~61 GB | 2×A100-80 / H100 | full 256K |
| FP8 / AWQ-8 | ~31 GB | 1×A6000-48 / L40S | 128K+ |
| 4-bit (GGUF Q4_K_M / AWQ) | ~17–19 GB | 1×RTX 4090/3090-24 | 32–64K |

Tiers:
- **Dev**: RTX 4090/3090 (24 GB) + 64 GB RAM, Ollama Q4, ctx 32–64K (~30–60 tok/s).
- **Prod (single)**: A6000 48 GB or L40S, vLLM FP8/AWQ, ctx 128K, batching.
- **Prod (scale)**: H100-80 / 2×A100, BF16-FP8, high concurrency.

Embeddings (`nomic-embed-text` / fastembed) are negligible — CPU or ~1–2 GB VRAM.

## Bottlenecks & mitigations

1. **Prefill cost on large prompts** (whole-repo analysis/findings). → AST-guided
   context selection + retrieval instead of dumping files; cache per commit SHA.
2. **Single-GPU serialization** under Celery. → Prefer vLLM (batches concurrent
   requests); keep `--concurrency` on the worker aligned to GPU capacity.
3. **Structured-JSON reliability.** → `guided_json` (vLLM) is grammar-constrained;
   all backends fall back to parse-and-repair (`infrastructure/llm/structured.py`).
4. **KV cache for long context.** → keep retrieved context small; reserve the full
   window for explicit whole-file requests.
5. **Indexing throughput** on big repos. → batched embeddings, idempotent per SHA.

## Switching the embedding model

`EMBEDDING_MODEL` is config-driven. Changing it changes the vector dimension, so
**a re-index is required** (the app guards against dimension mismatch). Default:
`nomic-embed-text` (local). See `backend/.env.example`.
