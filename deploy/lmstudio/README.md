# LM Studio backend (desktop)

LM Studio runs as a desktop app on the host, not as a container, so there is no
compose file — you point the app at it instead.

## Steps

1. Install [LM Studio](https://lmstudio.ai/) and download a Qwen3-Coder-30B
   build (e.g. a GGUF Q4_K_M quant for a 24 GB GPU).
2. In LM Studio → **Developer / Local Server**, load the model and **Start Server**
   (default port `1234`). Enable the OpenAI-compatible endpoint.
3. Point the backend at it. Because the API/worker run in Docker, use the host
   gateway address in `backend/.env`:

   ```env
   LLM_PROVIDER=qwen
   LLM_BASE_URL=http://host.docker.internal:1234/v1
   LLM_MODEL=qwen3-coder-30b           # must match the loaded model id in LM Studio
   LLM_STRUCTURED_MODE=json_schema
   ```

4. Start the rest of the stack normally:

   ```bash
   docker compose up --build
   ```

> On Linux, `host.docker.internal` may require adding
> `extra_hosts: ["host.docker.internal:host-gateway"]` to the `api` and `worker`
> services, or use the host's LAN IP.
