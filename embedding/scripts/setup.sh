#!/usr/bin/env bash
# =============================================================================
# setup.sh — First-time infrastructure setup for the embedding+reranker service
#             on Google Cloud Run with GPU.
#
# Idempotent: safe to re-run. Skips resources that already exist.
#
# Usage:
#   ./embedding/scripts/setup.sh                          # from monorepo root
#   ./embedding/scripts/setup.sh --upload-models          # also upload models
#   ./embedding/scripts/setup.sh --bake-models            # bake models into image (faster cold start)
#   make cloud-setup                                      # via Makefile
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
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

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EMBEDDING_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONOREPO_ROOT="$(cd "${EMBEDDING_DIR}/.." && pwd)"
EMBEDDING_MODEL_DIR="${MONOREPO_ROOT}/backend/models/Qwen3-Embedding-0.6B"
RERANKER_MODEL_DIR="${MONOREPO_ROOT}/backend/models/Qwen3-Reranker-0.6B"

# Flags
UPLOAD_MODELS=false
BAKE_MODELS=false
for arg in "$@"; do
  case "$arg" in
    --upload-models) UPLOAD_MODELS=true ;;
    --bake-models)   BAKE_MODELS=true ;;
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
# Preflight
# ---------------------------------------------------------------------------
step "1/8 Preflight checks"

if ! command -v gcloud &>/dev/null; then
  err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [[ "${CURRENT_PROJECT}" != "${PROJECT_ID}" ]]; then
  info "Setting project to ${PROJECT_ID}"
  gcloud config set project "${PROJECT_ID}" --quiet
fi

if [[ "${BAKE_MODELS}" == "true" ]]; then
  info "Mode: BAKED (models in image, fast cold start)"
else
  info "Mode: GCS FUSE (models mounted from bucket)"
fi
ok "Project: ${PROJECT_ID}"

# ---------------------------------------------------------------------------
# Enable APIs
# ---------------------------------------------------------------------------
step "2/8 Enabling APIs"

APIS=(
  run.googleapis.com
  artifactregistry.googleapis.com
  secretmanager.googleapis.com
  cloudbuild.googleapis.com
  compute.googleapis.com
)

for api in "${APIS[@]}"; do
  if gcloud services list --enabled --filter="name:${api}" --format="value(name)" 2>/dev/null | grep -q "${api}"; then
    skip "${api} (already enabled)"
  else
    info "Enabling ${api}..."
    gcloud services enable "${api}" --quiet
    ok "${api}"
  fi
done

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------
step "3/8 Artifact Registry repository"

if gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" &>/dev/null; then
  skip "Repository ${REPO_NAME} already exists"
else
  info "Creating repository ${REPO_NAME}..."
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="IAPH RAG container images" \
    --quiet
  ok "Created ${REPO_NAME}"
fi

# ---------------------------------------------------------------------------
# GCS bucket for models
# ---------------------------------------------------------------------------
step "4/8 GCS bucket for models"

if gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
  skip "Bucket ${BUCKET_NAME} already exists"
else
  info "Creating bucket ${BUCKET_NAME}..."
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --quiet
  ok "Created ${BUCKET_NAME}"
fi

# ---------------------------------------------------------------------------
# Upload models (optional / required for --bake-models)
# ---------------------------------------------------------------------------
step "5/8 Upload models to GCS"

if [[ "${UPLOAD_MODELS}" == "true" || "${BAKE_MODELS}" == "true" ]]; then
  for model_dir in "${EMBEDDING_MODEL_DIR}" "${RERANKER_MODEL_DIR}"; do
    model_name="$(basename "${model_dir}")"
    # Check if config.json exists in GCS (indicates model already uploaded)
    if gcloud storage ls "gs://${BUCKET_NAME}/${model_name}/config.json" &>/dev/null; then
      skip "${model_name} already in GCS"
    else
      if [[ ! -d "${model_dir}" ]]; then
        err "Model directory not found: ${model_dir}"
        err "Download it first (see backend/Makefile)"
        exit 1
      fi
      info "Uploading ${model_name} to GCS (this may take a few minutes)..."
      gcloud storage cp -r "${model_dir}" "gs://${BUCKET_NAME}/" --quiet
      ok "Uploaded ${model_name}"
    fi
  done
else
  skip "Model upload skipped (use --upload-models or --bake-models)"
  info "Ensure models are already in gs://${BUCKET_NAME}/"
fi

# ---------------------------------------------------------------------------
# Build image
# ---------------------------------------------------------------------------
step "6/8 Building container image (Cloud Build)"

if [[ "${BAKE_MODELS}" == "true" ]]; then
  info "Building BAKED image (base + models from GCS)..."
  gcloud builds submit "${EMBEDDING_DIR}" \
    --config="${EMBEDDING_DIR}/cloudbuild-baked.yaml" \
    --timeout=1800 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes models)"
else
  info "Building base image (models loaded at runtime via GCS FUSE)..."
  gcloud builds submit "${EMBEDDING_DIR}" \
    --tag="${IMAGE}:latest" \
    --timeout=1800 \
    --quiet
  ok "Image built: ${IMAGE}:latest"
fi

# ---------------------------------------------------------------------------
# Deploy to Cloud Run
# ---------------------------------------------------------------------------
step "7/8 Deploying to Cloud Run"

info "Deploying ${SERVICE_NAME} with GPU (${GPU_TYPE})..."

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
step "8/8 Verification"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

info "Service URL: ${SERVICE_URL}"

# Health check
info "Testing /health ..."
HEALTH=$(curl -s -w "\n%{http_code}" --max-time 120 \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/health")
HTTP_CODE=$(echo "${HEALTH}" | tail -1)
BODY=$(echo "${HEALTH}" | sed '$d')

if [[ "${HTTP_CODE}" == "200" ]]; then
  ok "Health check passed"
  echo "  ${BODY}" | python -m json.tool 2>/dev/null || echo "  ${BODY}"
else
  err "Health check failed (HTTP ${HTTP_CODE})"
  echo "  ${BODY}"
  exit 1
fi

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
ok "Setup complete! Service: ${SERVICE_URL}"
