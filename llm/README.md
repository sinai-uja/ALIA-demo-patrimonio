# LLM Service

This directory packages the self-hosted LLM inference server used by the IAPH RAG backend. It supports **two interchangeable engines** behind the same OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`, `/health`):

| Engine     | Image base                                       | Model format | Selection flag        |
|------------|--------------------------------------------------|--------------|-----------------------|
| **vLLM**   | `vllm/vllm-openai:v0.18.1`                       | HF safetensors + GPTQ / bitsandbytes | *(default)* `--engine vllm` |
| **llama.cpp** | `ghcr.io/ggml-org/llama.cpp:server-cuda-bXXXX` | Single-file GGUF (e.g. Q4_K_M) | `--engine llamacpp`   |

Both engines coexist; choose at deploy time via the `--engine` flag in `scripts/setup.sh` / `scripts/deploy.sh`, via the Makefile target suffix (`cloud-llm-deploy` vs `cloud-llm-deploy-llamacpp`), or via the docker-compose profile (`--profile llm` vs `--profile llm-llamacpp`).

Everything outside this directory — backend code, API contracts, env vars consumed by the backend — is **agnostic to the engine**. The backend only sees `POST /v1/chat/completions` and uses `LLM_MODEL_NAME` as a routing label.

---

## When to use each engine

### vLLM (default)
- Fastest inference on NVIDIA GPU (~40–60 tok/s on A100 for ALIA-40b GPTQ)
- Production-proven, extensive quantization support (GPTQ, AWQ, bitsandbytes)
- Current production deployment — **do not change unless you have a reason**

### llama.cpp (alternative)
- Consumes pre-quantized GGUF files directly (no on-the-fly quantization at startup)
- Much faster cold start on baked image (~30–60s vs ~5 min for vLLM with bitsandbytes)
- `/health` endpoint correctly reports 503 while loading and 200 when ready (vLLM returns 200 prematurely)
- Smaller Docker image (~28 GB baked vs ~100 GB for vLLM + original weights)
- Expected ~25–35 tok/s on A100 — slower than vLLM but acceptable for current token caps (512 for RAG, 2048 for route narratives)

---

## Files

| File                                   | Engine   | Purpose |
|----------------------------------------|----------|---------|
| `Dockerfile`                           | vLLM     | Base image (vLLM + bitsandbytes) |
| `Dockerfile.baked`                     | vLLM     | Base + model weights baked in |
| `Dockerfile.llamacpp`                  | llama.cpp | Base image (llama.cpp server CUDA) |
| `Dockerfile.llamacpp.baked`            | llama.cpp | Base + GGUF baked in |
| `cloudbuild-baked.yaml`                | vLLM     | Cloud Build pipeline for baked vLLM image |
| `cloudbuild-llamacpp.yaml`             | llama.cpp | Cloud Build pipeline for base llama.cpp image |
| `cloudbuild-baked-llamacpp.yaml`       | llama.cpp | Cloud Build pipeline for baked llama.cpp image |
| `scripts/setup.sh`                     | both     | First-time Cloud Run setup (takes `--engine`) |
| `scripts/deploy.sh`                    | both     | Rebuild + redeploy (takes `--engine`) |

---

## Cloud Run deployment

### vLLM (existing, unchanged)
```bash
make cloud-llm-setup                  # first-time setup (GCS FUSE)
make cloud-llm-setup-baked            # first-time setup + bake model
make cloud-llm-deploy                 # day-to-day redeploy (GCS FUSE)
make cloud-llm-deploy-baked           # day-to-day redeploy (baked)
```

Service name: `uja-llm` · Image: `.../iaph-rag/llm`

### llama.cpp (new alternative)
```bash
# One-off: download GGUF locally, then upload to GCS
cd backend && make download-alia-gguf && cd ..
make cloud-llm-setup-llamacpp-model   # setup + upload GGUF to GCS

# Deploy baked image (recommended)
make cloud-llm-setup-llamacpp-baked   # first-time setup + bake GGUF
make cloud-llm-deploy-llamacpp-baked  # day-to-day redeploy (baked)

# Or deploy with GCS FUSE (model streamed at runtime)
make cloud-llm-setup-llamacpp
make cloud-llm-deploy-llamacpp
```

Service name: `uja-llm-llamacpp` · Image: `.../iaph-rag/llm-llamacpp`

Both services run in the same project / region (`europe-west4`) and share the same IAM service account (`llm-invoker`) and GCS bucket (`innovasur-uja-alia-iaph-models`).

---

## Local development (docker compose)

Only one LLM profile can run at a time on a single-GPU host.

```bash
# Option A — vLLM (existing default)
docker compose --profile llm up -d postgres embedding-service llm-service

# Option B — llama.cpp (requires GGUF at backend/models/<DIR>/<FILE>.gguf)
cd backend && make download-alia-gguf && cd ..
docker compose --profile llm-llamacpp up -d postgres embedding-service llm-service-llamacpp
```

Both services expose the same OpenAI-compatible API; the backend points at whichever is running via `LLM_SERVICE_URL`.

---

## llama-server key flags (Cloud Run args)

When running llama.cpp, the Cloud Run service receives these args (configured in `scripts/deploy.sh`):

| Flag                 | Default                                         | Purpose |
|----------------------|-------------------------------------------------|---------|
| `--model`            | `/app/model/<FILE>.gguf` (baked) or `/gcs-models/<DIR>/<FILE>.gguf` (FUSE) | Absolute path to GGUF |
| `--alias`            | `ALIA-40b-instruct-2601`                        | Reported model name in `/v1/models`; must match backend `LLM_MODEL_NAME` |
| `--ctx-size`         | `8192`                                          | Context window (tokens). Larger = more KV-cache VRAM. |
| `--n-gpu-layers`     | `999`                                           | Layers offloaded to GPU (999 = all layers) |
| `--parallel`         | `1`                                             | Concurrent request slots (match Cloud Run `max-instances=1`) |
| `--threads-http`     | `8`                                             | HTTP worker threads |
| `--no-warmup`        | *(set)*                                         | Skip built-in warmup (startup probe + backend keepalive cover this) |
| `--jinja`            | *(set)*                                         | Honor Jinja chat template embedded in GGUF (ALIA uses ChatML) |

---

## Switching GGUF quantizations

To try a different quant level (e.g. Q5_K_M for better quality):

1. Override the filename when downloading:
   ```bash
   cd backend
   GGUF_FILE=ALIA-40b-instruct-2601.Q5_K_M.gguf bash scripts/download_alia_gguf.sh
   ```
2. Export the matching env var:
   ```bash
   export LLM_GGUF_FILE=ALIA-40b-instruct-2601.Q5_K_M.gguf
   ```
3. Re-upload + redeploy:
   ```bash
   make cloud-llm-setup-llamacpp-model
   make cloud-llm-deploy-llamacpp-baked
   ```

Available quants in `mradermacher/ALIA-40b-instruct-2601-GGUF` (approximate sizes):

| Quant    | File size | Notes |
|----------|-----------|-------|
| Q2_K     | 15.8 GB   | Very lossy |
| Q3_K_M   | 20.1 GB   | |
| Q4_K_S   | 23.5 GB   | |
| **Q4_K_M** | **24.7 GB** | **Default — good quality/size trade-off** |
| Q5_K_M   | 28.9 GB   | Better quality; still fits A100 40 GB at ctx=8192 |
| Q6_K     | 33.3 GB   | |
| Q8_0     | 43.1 GB   | Barely fits A100 40 GB; use 48 GB GPUs |

---

## Health / readiness probes

- **llama.cpp `/health`**: returns HTTP 503 while loading the model, HTTP 200 with `{"status":"ok"}` once ready. Cloud Run startup probe relies on this directly (no buffering issue).
- **vLLM `/health`**: returns HTTP 200 as soon as the HTTP server starts, *before* the engine finishes loading weights. Cloud Run startup probe keeps retrying; the backend-side inference probe (`/v1/chat/completions` with `max_tokens=1`) is the only reliable readiness signal.

The backend's `health_check_adapter.py` inference probe works identically with both engines because both expose the same `/v1/chat/completions` endpoint.
