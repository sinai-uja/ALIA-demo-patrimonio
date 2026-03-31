# Servicio LLM — Despliegue de ALIA-40b

## Resumen

El servicio `llm/` en la raiz del monorepo proporciona un endpoint de inferencia LLM autoalojado usando **vLLM**. Expone una API compatible con OpenAI (chat/completions).

- **Local**: `BSC-LT/salamandra-7b-instruct` (14GB VRAM, cabe en cualquier GPU)
- **Cloud Run**: `agustim/ALIA-40b-GPTQ-INT4` (25GB VRAM, A100 40GB, GPTQ pre-cuantizado)

El sistema mantiene retrocompatibilidad con **Gemini** como alternativa sin GPU.

## Modelo de produccion: ALIA-40b

| Propiedad | Valor |
|---|---|
| HuggingFace ID | `BSC-LT/ALIA-40b-instruct-2601` |
| Parametros | 40.4B |
| Arquitectura | Transformer decoder-only (custom) |
| Ventana de contexto | 163,840 tokens |
| Plantilla de chat | ChatML (`<\|im_start\|>user`/`<\|im_start\|>assistant`) |
| Vocabulario | 256,000 tokens |
| Temperatura recomendada | 0.0–0.2 |

## Estrategia: salamandra local, ALIA-40b en Cloud Run

ALIA-40b no cabe en la RTX 5090 (32GB) con vLLM — ni GPTQ (25.27GB desempaquetados + KV cache) ni bitsandbytes (26.86GB + KV cache) dejan espacio suficiente. Por eso:

| Entorno | Modelo | VRAM | Contexto | Cold start |
|---|---|---|---|---|
| **Local** (RTX 5090) | salamandra-7b | ~14 GB | 4096 | ~30s |
| **Cloud Run** (A100 40GB) | ALIA-40b GPTQ | ~25 GB | 8192 | ~1 min (baked) |

## Estructura del servicio

```
llm/
├── Dockerfile              # vllm/vllm-openai + bitsandbytes
├── Dockerfile.baked        # Pesos GPTQ incluidos en la imagen
├── cloudbuild-baked.yaml   # Pipeline Cloud Build (3 pasos)
├── .dockerignore
└── scripts/
    ├── setup.sh            # Setup inicial Cloud Run (GPTQ automatico)
    └── deploy.sh           # Redespliegue Cloud Run (GPTQ automatico)
```

## Desarrollo local

### `.env` raiz

```env
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
LLM_QUANTIZATION_ARGS=--dtype bfloat16
LLM_MAX_MODEL_LEN=4096
```

### `backend/config/.env`

```env
LLM_PROVIDER=vllm
LLM_SERVICE_URL=http://localhost:18000/v1
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
LLM_TEMPERATURE=0.3
```

### Arrancar

```bash
make infra-llm    # solo el servicio LLM
make infra        # todo (postgres + embedding + LLM)
```

## Despliegue en Cloud Run

Los scripts usan automaticamente **GPTQ** (`agustim/ALIA-40b-GPTQ-INT4`).

### Setup inicial

```bash
make cloud-llm-setup              # GCS FUSE (modelo montado en runtime)
make cloud-llm-setup-model        # Tambien sube modelo GPTQ a GCS (~27GB)
make cloud-llm-setup-baked        # Modelo en imagen (cold start ~1 min)
```

### Redespliegue

```bash
make cloud-llm-deploy             # Reconstruir y redesplegar
make cloud-llm-deploy-baked       # Con modelo incluido
make cloud-llm-deploy-skip-build  # Redesplegar sin reconstruir
```

### Configuracion de Cloud Run

| Parametro | Valor |
|---|---|
| Servicio | `uja-llm` |
| Region | `europe-west1` |
| GPU | NVIDIA A100 40GB |
| CPU / Memoria | 8 / 32Gi |
| Instancias | 0–1 |
| Modelo | `agustim/ALIA-40b-GPTQ-INT4` |
| Cuantizacion | GPTQ 4-bit (Marlin kernel) |

## Cambio entre modelos

Solo cambios en `.env` — sin tocar codigo.

### Salamandra-7b (local, default)

```env
# .env raiz
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
LLM_QUANTIZATION_ARGS=--dtype bfloat16
LLM_MAX_MODEL_LEN=4096

# backend/config/.env
LLM_PROVIDER=vllm
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
```

### ALIA-40b Cloud Run (configurado automaticamente por scripts)

```env
# Los scripts usan internamente:
# MODEL_NAME=agustim/ALIA-40b-GPTQ-INT4
# QUANTIZATION_ARGS=--quantization,gptq,--dtype,float16
# MAX_MODEL_LEN=8192

# backend/config/.env (apuntar al servicio Cloud Run)
LLM_PROVIDER=vllm
LLM_SERVICE_URL=https://uja-llm-XXXXXXXXXX.europe-west1.run.app/v1
LLM_MODEL_NAME=agustim/ALIA-40b-GPTQ-INT4
LLM_TEMPERATURE=0.1
```

### Gemini (API de Google, sin GPU)

```env
# backend/config/.env
LLM_PROVIDER=gemini
GEMINI_API_KEY=<tu-clave>
GEMINI_MODEL_NAME=gemini-3.1-flash-lite-preview
```
