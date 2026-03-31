# Guia de cuantizacion, ejecucion y despliegue de ALIA-40b

## Estrategia: salamandra local, ALIA-40b en Cloud Run

ALIA-40b (40.4B params) no cabe en la RTX 5090 (32GB) con vLLM:
- GPTQ: Marlin desempaqueta a 25.27GB + KV cache = no cabe
- bitsandbytes: 26.86GB + KV cache = no cabe

| Entorno | Modelo | VRAM | Contexto | Cold start |
|---|---|---|---|---|
| **Local** (RTX 5090) | salamandra-7b | ~14 GB | 4096 | ~30s |
| **Cloud Run** (A100 40GB) | ALIA-40b GPTQ | ~25 GB | 8192 | ~1 min (baked) |

## Requisitos previos

- GPU NVIDIA con >= 16GB VRAM (local)
- ~30GB de espacio en disco (modelo GPTQ para Cloud Run)
- Python 3.11+, `pip install huggingface_hub vllm`
- Docker con soporte NVIDIA (nvidia-container-toolkit)
- `gcloud` CLI configurado con proyecto `innovasur-uja-alia`

## Versiones cuantizadas disponibles

Cuantizaciones existentes en HuggingFace para `BSC-LT/ALIA-40b-instruct-2601`:

### Compatibles con vLLM (safetensors)

| Modelo | Metodo | Bits | Tamano | Autor |
|---|---|---|---|---|
| **`agustim/ALIA-40b-GPTQ-INT4`** | AutoRound (GPTQ) | **4-bit** | **27.2 GB** | **Comunidad (recomendado)** |
| `agustim/ALIA-40b-GPTQ-INT4_3b` | AutoRound (GPTQ) | 3-bit | 22.7 GB | Comunidad |
| `agustim/ALIA-40b-AutoRound-INT4_3b` | AutoRound | 3-bit | 22.7 GB | Comunidad |

### GGUF (llama.cpp, no compatible con vLLM)

| Modelo | Quants | Tamano | Autor |
|---|---|---|---|
| `BSC-LT/ALIA-40b-instruct-2601-GGUF` | Q8_0 | 43 GB | Oficial BSC-LT |
| `mradermacher/...-i1-GGUF` | IQ1_S a Q6_K | 9.8–33 GB | Comunidad (imatrix) |
| `mradermacher/...-GGUF` | Q2_K a Q8_0 | 15.8–43 GB | Comunidad |

### No disponible

No existe AWQ ni EXL2 de este modelo. Si se necesitase AWQ, habria que cuantizarlo
manualmente (ver seccion al final).

---

## Local: salamandra-7b (RTX 5090 / cualquier GPU)

Salamandra-7b cabe holgadamente en cualquier GPU moderna (~14GB VRAM).

### Paso 1 — Configurar .env raiz

```env
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
LLM_QUANTIZATION_ARGS=--dtype bfloat16
LLM_MAX_MODEL_LEN=4096
```

### Paso 2 — Arrancar con Docker Compose

```bash
make infra-llm
# Primera vez descarga ~14GB de HuggingFace (cacheado en volumen hf_cache)
# Siguientes veces arranca en ~30s
```

### Paso 3 — Verificar

```bash
curl http://localhost:18000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BSC-LT/salamandra-7b-instruct",
    "messages": [{"role": "user", "content": "Describe brevemente la Alhambra de Granada."}],
    "max_tokens": 256,
    "temperature": 0.3
  }'
```

### Paso 4 — Configurar backend

En `backend/config/.env`:

```env
LLM_PROVIDER=vllm
LLM_SERVICE_URL=http://localhost:18000/v1
LLM_MODEL_NAME=BSC-LT/salamandra-7b-instruct
LLM_TEMPERATURE=0.3
```

---

## Cloud Run: GPTQ (A100 40GB)

Usa `agustim/ALIA-40b-GPTQ-INT4`: modelo pre-cuantizado a 4-bit GPTQ, 27GB.
El kernel Marlin desempaqueta a 25.27GB en VRAM — cabe en A100 40GB con margen para
KV cache de 8192 tokens. Carga directa sin cuantizar, cold start rapido (~1 min baked).

Los scripts `setup.sh` y `deploy.sh` ya estan configurados para usar GPTQ automaticamente.

### Paso 1 — Descargar y subir modelo GPTQ a GCS

```bash
pip install huggingface_hub

huggingface-cli download agustim/ALIA-40b-GPTQ-INT4 \
  --local-dir ~/models/ALIA-40b-GPTQ-INT4

gcloud storage cp -r ~/models/ALIA-40b-GPTQ-INT4 \
  gs://innovasur-uja-alia-iaph-models/
```

O directamente con el script (descarga + sube):

```bash
make cloud-llm-setup-model
```

### Paso 2 — Desplegar

```bash
# Modelo bakeado en imagen (recomendado, cold start ~1 min)
make cloud-llm-setup-baked

# O modo GCS FUSE (cold start mas lento ~3-5 min, imagen mas pequena)
make cloud-llm-setup
```

### Paso 3 — Configurar backend para usar Cloud Run

En `backend/config/.env`:

```env
LLM_PROVIDER=vllm
LLM_SERVICE_URL=https://uja-llm-XXXXXXXXXX.europe-west1.run.app/v1
LLM_MODEL_NAME=agustim/ALIA-40b-GPTQ-INT4
LLM_TEMPERATURE=0.1
```

(La URL exacta la muestra el script de deploy al terminar.)

---

## Alternativa: crear AWQ propio (maxima optimizacion)

AWQ tiene mejor rendimiento que GPTQ en vLLM pero no existe version publica para
ALIA-40b. Requiere una maquina con >= 80GB RAM para cuantizar.

```bash
pip install autoawq transformers

python3 << 'EOF'
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model_path = "BSC-LT/ALIA-40b-instruct-2601"
quant_path = "./ALIA-40b-instruct-2601-AWQ"

model = AutoAWQForCausalLM.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",
}

model.quantize(tokenizer, quant_config=quant_config)
model.save_quantized(quant_path)
tokenizer.save_pretrained(quant_path)
EOF
```

Tiempo: 1-3 horas. Resultado: ~22GB. Configuracion:

```env
LLM_MODEL_NAME=./ALIA-40b-instruct-2601-AWQ
LLM_QUANTIZATION_ARGS=--quantization awq
LLM_MAX_MODEL_LEN=8192
```

---

## Troubleshooting

### Error: CUDA out of memory
- Reducir `--max-model-len` (ej: 4096 en vez de 8192)
- Reducir `--gpu-memory-utilization` (ej: 0.85)
- Verificar que no hay otros procesos usando la GPU: `nvidia-smi`

### El modelo tarda mucho en arrancar
- Primera ejecucion descarga el modelo — es normal
- Verificar cache: `ls ~/.cache/huggingface/hub/`
- En Docker, el volumen `hf_cache` persiste entre reinicios

### vLLM no reconoce el modelo
- Verificar version de vLLM: `pip show vllm` (necesita >= 0.6.0)
- ALIA-40b usa arquitectura custom — versiones antiguas pueden no soportarla
- Actualizar: `pip install -U vllm`

### Respuestas de baja calidad
- Usar temperatura 0.0-0.2 (recomendacion de BSC-LT)
- No usar repetition penalty (el modelo ya esta entrenado sin ella)
- Verificar que el chat template ChatML se aplica correctamente (vLLM lo hace automaticamente)
