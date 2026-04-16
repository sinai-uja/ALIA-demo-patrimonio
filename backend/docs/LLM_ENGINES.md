# LLM Engines — vLLM vs llama.cpp

The IAPH RAG backend can consume LLM inference from two interchangeable self-hosted engines, both exposing the same OpenAI-compatible API. You can switch between them without backend code changes — just point `LLM_SERVICE_URL` + `LLM_MODEL_NAME` at the running service.

## Decision matrix

| Criterion                 | vLLM (default)                  | llama.cpp                          |
|---------------------------|---------------------------------|------------------------------------|
| Model format              | HF safetensors + GPTQ/bitsandbytes | Single-file GGUF                 |
| Current production model  | `agustim/ALIA-40b-GPTQ-INT4`    | `mradermacher/ALIA-40b-instruct-2601-GGUF` (Q4_K_M) |
| Inference speed (A100)    | ~40–60 tok/s                    | ~25–35 tok/s                       |
| Cold start (baked image)  | ~5 min (bitsandbytes quantization at load) | ~30–60 s (weights ready on disk) |
| Baked image size          | ~100 GB (original weights)      | ~28 GB (pre-quantized GGUF)        |
| `/health` reliability     | 200 prematurely during cold start | 503 while loading, 200 when ready |
| Streaming SSE             | Yes                             | Yes                                |
| Chat template support     | Auto (from HF tokenizer config) | Via `--jinja` flag                 |

## When to choose each

### Use **vLLM** when
- You want maximum generation throughput (narratives with `max_tokens=2048` feel snappier)
- You already have the GPTQ weights in GCS and want zero-effort continuity
- The frozen production model version is what you need (`agustim/ALIA-40b-GPTQ-INT4`)

### Use **llama.cpp** when
- You want to evaluate the newer ALIA release (`ALIA-40b-instruct-2601`) for which only GGUF is published
- Cold start matters (first request after scale-to-zero tolerates <1 min vs 5 min)
- You want a smaller Docker image for faster deploys
- You want `/health` to accurately signal readiness (useful for custom monitoring)

## Switching engines

Both engines deploy to **separate Cloud Run services** under the same project:

| Engine     | Service name          | Env var needed in backend `.env`                      |
|------------|-----------------------|-------------------------------------------------------|
| vLLM       | `uja-llm`             | `LLM_SERVICE_URL=https://uja-llm-<hash>.run.app/v1`<br>`LLM_MODEL_NAME=agustim/ALIA-40b-GPTQ-INT4` |
| llama.cpp  | `uja-llm-llamacpp`    | `LLM_SERVICE_URL=https://uja-llm-llamacpp-<hash>.run.app/v1`<br>`LLM_MODEL_NAME=ALIA-40b-instruct-2601` |

You can keep both services deployed simultaneously and switch the backend between them by editing `LLM_SERVICE_URL` + `LLM_MODEL_NAME` (and restarting the backend). The IAM auth flow is identical — both use the `llm-invoker` service account.

## Deploying

### vLLM (existing)
```bash
make cloud-llm-setup-baked      # first time
make cloud-llm-deploy-baked     # redeploy
```

### llama.cpp (new)
```bash
cd backend && make download-alia-gguf && cd ..   # fetch GGUF locally
make cloud-llm-setup-llamacpp-model               # upload GGUF to GCS
make cloud-llm-setup-llamacpp-baked               # first time (builds + deploys)
make cloud-llm-deploy-llamacpp-baked              # redeploy
```

See [`llm/README.md`](../../llm/README.md) for the full flag reference and GGUF quantization options.

## Architecture notes

The `RAGPort`/`LLMPort` abstractions in the domain layer know nothing about the engine. The only backend file that contains engine-specific knowledge is the keepalive probe:

- [`backend/src/infrastructure/shared/adapters/health_check_adapter.py`](../src/infrastructure/shared/adapters/health_check_adapter.py) — sends a `POST /v1/chat/completions` with `max_tokens=1` to verify readiness. The hardcoded model name in the probe payload is ignored by llama.cpp (it serves a single model regardless), so no change is required there.

If an operator wants to distinguish engines in logs or metrics, that is a future refactor to expose `settings.llm_engine` (currently not implemented).
