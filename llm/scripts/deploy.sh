#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Rebuild and redeploy the LLM service on Cloud Run.
#
# For day-to-day updates when code changes. Assumes infrastructure already
# exists (run setup.sh first).
#
# Usage:
#   ./llm/scripts/deploy.sh                # from monorepo root (GCS FUSE)
#   ./llm/scripts/deploy.sh --bake-model   # bake model into image
#   ./llm/scripts/deploy.sh --skip-build   # deploy only (reuse existing image)
#   make cloud-llm-deploy                  # via Makefile
#   make cloud-llm-deploy-baked            # via Makefile (baked)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (must match setup.sh)
# ---------------------------------------------------------------------------
PROJECT_ID="innovasur-uja-alia"
REGION="europe-west4"
AR_REGION="europe-west1"
SERVICE_NAME="uja-llm"
REPO_NAME="iaph-rag"
BUCKET_NAME="${PROJECT_ID}-iaph-models"
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm"

# Cloud Run service settings
CPU=20
MEMORY="80Gi"
GPU_TYPE="nvidia-rtx-pro-6000"
MAX_INSTANCES=1
MIN_INSTANCES=0
PORT=8000

# Model configuration (GPTQ for Cloud Run — fits on A100 40GB, fast cold start)
MODEL_NAME="agustim/ALIA-40b-GPTQ-INT4"
MODEL_DIR_NAME="ALIA-40b-GPTQ-INT4"
MAX_MODEL_LEN=32768
QUANTIZATION_ARGS="--quantization,gptq,--dtype,float16"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLM_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Flags
SKIP_BUILD=false
BAKE_MODEL=false
for arg in "$@"; do
  case "$arg" in
    --skip-build)  SKIP_BUILD=true ;;
    --bake-model)  BAKE_MODEL=true ;;
  esac
done

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
  info "Building base + baking model from GCS..."
  gcloud builds submit "${LLM_DIR}" \
    --config="${LLM_DIR}/cloudbuild-baked.yaml" \
    --timeout=3600 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes model)"
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

if [[ "${BAKE_MODEL}" == "true" ]]; then
  # Baked: model inside image at /app/model
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=30,timeoutSeconds=10,periodSeconds=15,failureThreshold=40"
    --clear-volume-mounts
    --clear-volumes
    --command="python3"
    --args="-m,vllm.entrypoints.openai.api_server,--model,/app/model,--served-model-name,${MODEL_NAME},${QUANTIZATION_ARGS},--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--port,${PORT}"
  )
  info "Deploy mode: BAKED (model in image, no GCS volumes)"
else
  # GCS FUSE: mount bucket, model loaded from GCS
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=60,timeoutSeconds=10,periodSeconds=15,failureThreshold=80"
    --add-volume="name=models,type=cloud-storage,bucket=${BUCKET_NAME}"
    --add-volume-mount="volume=models,mount-path=/gcs-models"
    --command="python3"
    --args="-m,vllm.entrypoints.openai.api_server,--model,/gcs-models/${MODEL_DIR_NAME},${QUANTIZATION_ARGS},--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--port,${PORT}"
  )
  info "Deploy mode: GCS FUSE (model mounted from gs://${BUCKET_NAME})"
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

# Chat completion test
info "Testing POST /v1/chat/completions ..."
CHAT_RESP=$(curl -s -w "\n%{http_code}" -X POST --max-time 120 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"${MODEL_NAME}"'",
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
