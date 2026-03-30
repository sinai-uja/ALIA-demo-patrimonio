#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Rebuild and redeploy the embedding+reranker service on Cloud Run.
#
# For day-to-day updates when code changes. Assumes infrastructure already
# exists (run setup.sh first).
#
# Usage:
#   ./embedding/scripts/deploy.sh                # from monorepo root (GCS FUSE)
#   ./embedding/scripts/deploy.sh --bake-models  # bake models into image
#   ./embedding/scripts/deploy.sh --skip-build   # deploy only (reuse existing image)
#   make cloud-deploy                            # via Makefile
#   make cloud-deploy-baked                      # via Makefile (baked)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (must match setup.sh)
# ---------------------------------------------------------------------------
PROJECT_ID="innovasur-uja-alia"
REGION="europe-west1"
SERVICE_NAME="uja-embedding"
REPO_NAME="iaph-rag"
BUCKET_NAME="${PROJECT_ID}-iaph-models"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/embedding"

# Cloud Run service settings
CPU=4
MEMORY="16Gi"
GPU_TYPE="nvidia-l4"
MAX_INSTANCES=1
MIN_INSTANCES=0
PORT=8001

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EMBEDDING_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Flags
SKIP_BUILD=false
BAKE_MODELS=false
for arg in "$@"; do
  case "$arg" in
    --skip-build)  SKIP_BUILD=true ;;
    --bake-models) BAKE_MODELS=true ;;
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
if [[ "${SKIP_BUILD}" == "true" ]]; then
  step "1/3 Build (skipped)"
  skip "Using existing image ${IMAGE}:latest"
elif [[ "${BAKE_MODELS}" == "true" ]]; then
  step "1/3 Building BAKED image (Cloud Build)"
  info "Building base + baking models from GCS..."
  gcloud builds submit "${EMBEDDING_DIR}" \
    --config="${EMBEDDING_DIR}/cloudbuild-baked.yaml" \
    --timeout=1800 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes models)"
else
  step "1/3 Building container image (Cloud Build)"
  info "Submitting build from ${EMBEDDING_DIR}/ ..."
  gcloud builds submit "${EMBEDDING_DIR}" \
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
  --image="${IMAGE}:latest"
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
  --no-allow-unauthenticated
  --set-env-vars="DEVICE=cuda,POOLING_STRATEGY=last_token,MAX_LENGTH=32768,RERANKER_MAX_LENGTH=8192,RERANKER_BATCH_SIZE=4"
  --quiet
)

if [[ "${BAKE_MODELS}" == "true" ]]; then
  # Baked: models inside image, no volume mounts, use default CMD
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=5,timeoutSeconds=5,periodSeconds=10,failureThreshold=12"
    --clear-volume-mounts
    --clear-volumes
    --command=""
    --args=""
  )
  info "Deploy mode: BAKED (models in image, no GCS volumes)"
else
  # GCS FUSE: mount bucket, symlink models at startup
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=10,timeoutSeconds=5,periodSeconds=15,failureThreshold=30"
    --add-volume="name=models,type=cloud-storage,bucket=${BUCKET_NAME}"
    --add-volume-mount="volume=models,mount-path=/gcs-models"
    --command="sh"
    --args="-c,ln -s /gcs-models/Qwen3-Embedding-0.6B /app/model && ln -s /gcs-models/Qwen3-Reranker-0.6B /app/reranker_model && uvicorn main:app --host 0.0.0.0 --port ${PORT}"
  )
  info "Deploy mode: GCS FUSE (models mounted from gs://${BUCKET_NAME})"
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

# Health check (retry up to 3 times for cold start)
info "Testing /health (waiting for cold start if needed)..."
for attempt in 1 2 3; do
  HEALTH=$(curl -s -w "\n%{http_code}" --max-time 120 \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/health")
  HTTP_CODE=$(echo "${HEALTH}" | tail -1)
  BODY=$(echo "${HEALTH}" | sed '$d')

  if [[ "${HTTP_CODE}" == "200" ]]; then
    ok "Health check passed"
    echo "  ${BODY}" | python -m json.tool 2>/dev/null || echo "  ${BODY}"
    break
  fi

  if [[ "${attempt}" -lt 3 ]]; then
    info "Attempt ${attempt}/3 failed (HTTP ${HTTP_CODE}), retrying in 30s..."
    sleep 30
  else
    err "Health check failed after 3 attempts (HTTP ${HTTP_CODE})"
    echo "  ${BODY}"
    err "Check logs: gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit=50"
    exit 1
  fi
done

# Embedding test
info "Testing POST /embed ..."
EMBED_RESP=$(curl -s -w "\n%{http_code}" -X POST --max-time 60 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["prueba de embedding"]}' \
  "${SERVICE_URL}/embed")
HTTP_CODE=$(echo "${EMBED_RESP}" | tail -1)
BODY=$(echo "${EMBED_RESP}" | sed '$d')

if [[ "${HTTP_CODE}" == "200" ]]; then
  DIM=$(echo "${BODY}" | python -c "import sys,json; print(len(json.load(sys.stdin)['embeddings'][0]))" 2>/dev/null || echo "?")
  ok "Embedding OK (dim=${DIM})"
else
  err "Embedding failed (HTTP ${HTTP_CODE}): ${BODY}"
fi

# Rerank test
info "Testing POST /rerank ..."
RERANK_RESP=$(curl -s -w "\n%{http_code}" -X POST --max-time 60 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"monumentos","documents":["La Alhambra de Granada","El olivo es un cultivo"],"top_n":2}' \
  "${SERVICE_URL}/rerank")
HTTP_CODE=$(echo "${RERANK_RESP}" | tail -1)
BODY=$(echo "${RERANK_RESP}" | sed '$d')

if [[ "${HTTP_CODE}" == "200" ]]; then
  ok "Rerank OK"
  echo "  ${BODY}" | python -m json.tool 2>/dev/null || echo "  ${BODY}"
else
  err "Rerank failed (HTTP ${HTTP_CODE}): ${BODY}"
fi

echo ""
ok "Deploy complete! Service: ${SERVICE_URL}"
