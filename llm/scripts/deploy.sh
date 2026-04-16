#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Rebuild and redeploy the LLM service on Cloud Run.
#
# For day-to-day updates when code changes. Assumes infrastructure already
# exists (run setup.sh first).
#
# Usage:
#   ./llm/scripts/deploy.sh                         # vLLM (default)
#   ./llm/scripts/deploy.sh --engine llamacpp        # llama.cpp + GGUF
#   ./llm/scripts/deploy.sh --bake-model             # bake model into image
#   ./llm/scripts/deploy.sh --skip-build             # deploy only (reuse image)
#   make cloud-llm-deploy                            # vLLM via Makefile
#   make cloud-llm-deploy-baked                      # vLLM baked via Makefile
#   make cloud-llm-deploy-llamacpp                   # llama.cpp via Makefile
#   make cloud-llm-deploy-llamacpp-baked             # llama.cpp baked
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Flags (engine first)
# ---------------------------------------------------------------------------
ENGINE="vllm"
SKIP_BUILD=false
BAKE_MODEL=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine)       ENGINE="$2"; shift 2 ;;
    --engine=*)     ENGINE="${1#*=}"; shift ;;
    --skip-build)   SKIP_BUILD=true; shift ;;
    --bake-model)   BAKE_MODEL=true; shift ;;
    *)              shift ;;
  esac
done

if [[ "${ENGINE}" != "vllm" && "${ENGINE}" != "llamacpp" ]]; then
  echo "Unknown --engine: ${ENGINE}. Expected: vllm | llamacpp" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Shared configuration (both engines)
# ---------------------------------------------------------------------------
PROJECT_ID="innovasur-uja-alia"
REGION="europe-west4"
AR_REGION="europe-west1"
REPO_NAME="iaph-rag"
BUCKET_NAME="${PROJECT_ID}-iaph-models"

# Cloud Run service settings
CPU=20
MEMORY="80Gi"
GPU_TYPE="nvidia-rtx-pro-6000"
MAX_INSTANCES=1
MIN_INSTANCES=0
PORT=8000

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLM_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Engine-specific configuration
# ---------------------------------------------------------------------------
if [[ "${ENGINE}" == "vllm" ]]; then
  SERVICE_NAME="uja-llm"
  IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm"
  CLOUDBUILD_BAKED_CFG="${LLM_DIR}/cloudbuild-baked.yaml"
  MODEL_NAME="agustim/ALIA-40b-GPTQ-INT4"
  MODEL_DIR_NAME="ALIA-40b-GPTQ-INT4"
  MAX_MODEL_LEN=32768
  QUANTIZATION_ARGS="--quantization,gptq,--dtype,float16"
else
  SERVICE_NAME="uja-llm-llamacpp"
  IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm-llamacpp"
  CLOUDBUILD_BAKED_CFG="${LLM_DIR}/cloudbuild-baked-llamacpp.yaml"
  CLOUDBUILD_BASE_CFG="${LLM_DIR}/cloudbuild-llamacpp.yaml"
  GGUF_FILE="${LLM_GGUF_FILE:-ALIA-40b-instruct-2601.Q4_K_M.gguf}"
  MODEL_DIR_NAME="${LLM_GGUF_MODEL_DIR:-ALIA-40b-instruct-2601-GGUF}"
  SERVED_ALIAS="${LLM_GGUF_ALIAS:-ALIA-40b-instruct-2601}"
  CTX_SIZE="${LLM_CTX_SIZE:-8192}"
  N_GPU_LAYERS="${LLM_N_GPU_LAYERS:-999}"
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
skip()  { echo -e "${YELLOW}[SKIP]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()  { echo -e "\n${GREEN}━━━ $* ━━━${NC}"; }

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
IMAGE_TAG="latest"
if [[ "${BAKE_MODEL}" == "true" ]]; then
  IMAGE_TAG="baked"
fi

if [[ "${SKIP_BUILD}" == "true" ]]; then
  step "1/3 Build (skipped)"
  skip "Using existing image ${IMAGE}:${IMAGE_TAG}"
elif [[ "${BAKE_MODEL}" == "true" ]]; then
  step "1/3 Building BAKED image (Cloud Build)"
  info "Engine: ${ENGINE} — building base + baking model from GCS..."
  gcloud builds submit "${LLM_DIR}" \
    --config="${CLOUDBUILD_BAKED_CFG}" \
    --timeout=3600 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes model)"
elif [[ "${ENGINE}" == "llamacpp" ]]; then
  step "1/3 Building container image (llama.cpp, Cloud Build)"
  info "Submitting build from ${LLM_DIR}/ using Dockerfile.llamacpp..."
  gcloud builds submit "${LLM_DIR}" \
    --config="${CLOUDBUILD_BASE_CFG}" \
    --timeout=1800 \
    --quiet
  ok "Image built: ${IMAGE}:latest"
else
  step "1/3 Building container image (Cloud Build)"
  info "Submitting build from ${LLM_DIR}/ ..."
  gcloud builds submit "${LLM_DIR}" \
    --tag="${IMAGE}:latest" \
    --timeout=1800 \
    --quiet
  ok "Image built: ${IMAGE}:latest"
fi

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
step "2/3 Deploying to Cloud Run"

info "Deploying ${SERVICE_NAME}..."

DEPLOY_ARGS=(
  --image="${IMAGE}:${IMAGE_TAG}"
  --region="${REGION}"
  --port="${PORT}"
  --cpu="${CPU}"
  --memory="${MEMORY}"
  --gpu=1
  --gpu-type="${GPU_TYPE}"
  --max-instances="${MAX_INSTANCES}"
  --min-instances="${MIN_INSTANCES}"
  --no-cpu-throttling
  --cpu-boost
  --execution-environment=gen2
  --update-annotations=run.googleapis.com/launch-stage=BETA
  --no-allow-unauthenticated
  --no-gpu-zonal-redundancy
  --quiet
)

if [[ "${ENGINE}" == "vllm" ]]; then
  # ─── vLLM engine (existing behavior, unchanged) ──────────────────────────
  if [[ "${BAKE_MODEL}" == "true" ]]; then
    # Baked: model inside image at /app/model
    DEPLOY_ARGS+=(
      --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=30,timeoutSeconds=10,periodSeconds=15,failureThreshold=40"
      --clear-volume-mounts
      --clear-volumes
      --command="python3"
      --args="-m,vllm.entrypoints.openai.api_server,--model,/app/model,--served-model-name,${MODEL_NAME},${QUANTIZATION_ARGS},--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--enforce-eager,--port,${PORT}"
    )
    info "Deploy mode: BAKED (model in image, no GCS volumes)"
  else
    # GCS FUSE: mount bucket, model loaded from GCS
    DEPLOY_ARGS+=(
      --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=60,timeoutSeconds=10,periodSeconds=15,failureThreshold=80"
      --add-volume="name=models,type=cloud-storage,bucket=${BUCKET_NAME}"
      --add-volume-mount="volume=models,mount-path=/gcs-models"
      --command="python3"
      --args="-m,vllm.entrypoints.openai.api_server,--model,/gcs-models/${MODEL_DIR_NAME},${QUANTIZATION_ARGS},--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--enforce-eager,--port,${PORT}"
    )
    info "Deploy mode: GCS FUSE (model mounted from gs://${BUCKET_NAME})"
  fi
else
  # ─── llama.cpp engine (new) ──────────────────────────────────────────────
  LLAMACPP_ARGS="--alias,${SERVED_ALIAS},--host,0.0.0.0,--port,${PORT},--ctx-size,${CTX_SIZE},--n-gpu-layers,${N_GPU_LAYERS},--parallel,1,--threads-http,8,--no-warmup,--jinja"
  if [[ "${BAKE_MODEL}" == "true" ]]; then
    # Baked: GGUF inside image at /app/model/<file>
    DEPLOY_ARGS+=(
      --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=30,timeoutSeconds=10,periodSeconds=10,failureThreshold=30"
      --clear-volume-mounts
      --clear-volumes
      --args="--model,/app/model/${GGUF_FILE},${LLAMACPP_ARGS}"
    )
    info "Deploy mode: BAKED llama.cpp (GGUF in image, no GCS volumes)"
  else
    # GCS FUSE: mount bucket, GGUF streamed from GCS
    DEPLOY_ARGS+=(
      --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=60,timeoutSeconds=10,periodSeconds=15,failureThreshold=60"
      --add-volume="name=models,type=cloud-storage,bucket=${BUCKET_NAME}"
      --add-volume-mount="volume=models,mount-path=/gcs-models"
      --args="--model,/gcs-models/${MODEL_DIR_NAME}/${GGUF_FILE},${LLAMACPP_ARGS}"
    )
    info "Deploy mode: GCS FUSE llama.cpp (GGUF from gs://${BUCKET_NAME})"
  fi
fi

gcloud run deploy "${SERVICE_NAME}" "${DEPLOY_ARGS[@]}"
ok "Deployed ${SERVICE_NAME}"

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
step "3/3 Verification"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

info "Service URL: ${SERVICE_URL}"

# Health check (retry up to 5 times for cold start — model loading is slow)
info "Testing /health (waiting for cold start if needed)..."
for attempt in 1 2 3 4 5; do
  HEALTH=$(curl -s -w "\n%{http_code}" --max-time 180 \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/health")
  HTTP_CODE=$(echo "${HEALTH}" | tail -1)
  BODY=$(echo "${HEALTH}" | sed '$d')

  if [[ "${HTTP_CODE}" == "200" ]]; then
    ok "Health check passed"
    echo "  ${BODY}" | python3 -m json.tool 2>/dev/null || echo "  ${BODY}"
    break
  fi

  if [[ "${attempt}" -lt 5 ]]; then
    info "Attempt ${attempt}/5 failed (HTTP ${HTTP_CODE}), retrying in 60s..."
    sleep 60
  else
    err "Health check failed after 5 attempts (HTTP ${HTTP_CODE})"
    echo "  ${BODY}"
    err "Check logs: gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit=50"
    exit 1
  fi
done

# Chat completion test — use engine-specific served-model name
if [[ "${ENGINE}" == "vllm" ]]; then
  TEST_MODEL="${MODEL_NAME}"
else
  TEST_MODEL="${SERVED_ALIAS}"
fi
info "Testing POST /v1/chat/completions ..."
CHAT_RESP=$(curl -s -w "\n%{http_code}" -X POST --max-time 120 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"${TEST_MODEL}"'",
    "messages": [{"role": "user", "content": "Describe brevemente la Alhambra de Granada."}],
    "max_tokens": 128,
    "temperature": 0.1
  }' \
  "${SERVICE_URL}/v1/chat/completions")
HTTP_CODE=$(echo "${CHAT_RESP}" | tail -1)
BODY=$(echo "${CHAT_RESP}" | sed '$d')

if [[ "${HTTP_CODE}" == "200" ]]; then
  CONTENT=$(echo "${BODY}" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'][:200])" 2>/dev/null || echo "?")
  ok "Chat completion OK"
  echo "  Response: ${CONTENT}..."
else
  err "Chat completion failed (HTTP ${HTTP_CODE}): ${BODY}"
fi

echo ""
ok "Deploy complete! Service: ${SERVICE_URL}"
