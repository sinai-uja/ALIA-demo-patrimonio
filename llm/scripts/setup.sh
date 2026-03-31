#!/usr/bin/env bash
# =============================================================================
# setup.sh — First-time infrastructure setup for the LLM service
#             on Google Cloud Run with GPU.
#
# Idempotent: safe to re-run. Skips resources that already exist.
# Reuses shared infrastructure (Artifact Registry, GCS bucket) created by
# the embedding service setup.
#
# Usage:
#   ./llm/scripts/setup.sh                          # from monorepo root
#   ./llm/scripts/setup.sh --upload-model            # also upload model to GCS
#   ./llm/scripts/setup.sh --bake-model              # bake model into image (faster cold start)
#   ./llm/scripts/setup.sh --generate-sa-key         # generate service account key
#   make cloud-llm-setup                             # via Makefile
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ID="innovasur-uja-alia"
REGION="europe-west1"
SERVICE_NAME="uja-llm"
REPO_NAME="iaph-rag"                        # shared with embedding service
BUCKET_NAME="${PROJECT_ID}-iaph-models"      # shared with embedding service
SA_NAME="llm-invoker"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm"

# Cloud Run service settings — A100 40GB for 4-bit quantized ALIA-40b
CPU=8
MEMORY="32Gi"
GPU_TYPE="nvidia-a100-40gb"
MAX_INSTANCES=1
MIN_INSTANCES=0
PORT=8000

# Model configuration
MODEL_NAME="BSC-LT/ALIA-40b-instruct-2601"
MODEL_DIR_NAME="ALIA-40b-instruct-2601"
MAX_MODEL_LEN=8192

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLM_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONOREPO_ROOT="$(cd "${LLM_DIR}/.." && pwd)"

# Flags
UPLOAD_MODEL=false
BAKE_MODEL=false
GENERATE_SA_KEY=false
for arg in "$@"; do
  case "$arg" in
    --upload-model)     UPLOAD_MODEL=true ;;
    --bake-model)       BAKE_MODEL=true ;;
    --generate-sa-key)  GENERATE_SA_KEY=true ;;
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
step "1/9 Preflight checks"

if ! command -v gcloud &>/dev/null; then
  err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [[ "${CURRENT_PROJECT}" != "${PROJECT_ID}" ]]; then
  info "Setting project to ${PROJECT_ID}"
  gcloud config set project "${PROJECT_ID}" --quiet
fi

if [[ "${BAKE_MODEL}" == "true" ]]; then
  info "Mode: BAKED (model in image, fast cold start)"
else
  info "Mode: GCS FUSE (model mounted from bucket)"
fi
ok "Project: ${PROJECT_ID}"

# ---------------------------------------------------------------------------
# Enable APIs
# ---------------------------------------------------------------------------
step "2/9 Enabling APIs"

APIS=(
  run.googleapis.com
  artifactregistry.googleapis.com
  iam.googleapis.com
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
# Artifact Registry (shared — should already exist from embedding setup)
# ---------------------------------------------------------------------------
step "3/9 Artifact Registry repository"

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
# GCS bucket (shared — should already exist from embedding setup)
# ---------------------------------------------------------------------------
step "4/9 GCS bucket for models"

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
# Upload model (optional)
# ---------------------------------------------------------------------------
step "5/9 Upload model to GCS"

if [[ "${UPLOAD_MODEL}" == "true" || "${BAKE_MODEL}" == "true" ]]; then
  # Check if model already exists in GCS
  if gcloud storage ls "gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/config.json" &>/dev/null; then
    skip "${MODEL_DIR_NAME} already in GCS"
  else
    info "Downloading ${MODEL_NAME} from HuggingFace and uploading to GCS..."
    info "This may take a while (~80GB in bf16)..."

    # Download model using huggingface-cli if available, otherwise instruct user
    TEMP_DIR=$(mktemp -d)
    if command -v huggingface-cli &>/dev/null; then
      huggingface-cli download "${MODEL_NAME}" --local-dir "${TEMP_DIR}/${MODEL_DIR_NAME}"
      gcloud storage cp -r "${TEMP_DIR}/${MODEL_DIR_NAME}" "gs://${BUCKET_NAME}/" --quiet
      rm -rf "${TEMP_DIR}"
      ok "Uploaded ${MODEL_DIR_NAME} to GCS"
    else
      err "huggingface-cli not found. Install with: pip install huggingface_hub"
      err "Then download the model manually:"
      err "  huggingface-cli download ${MODEL_NAME} --local-dir /path/to/${MODEL_DIR_NAME}"
      err "  gcloud storage cp -r /path/to/${MODEL_DIR_NAME} gs://${BUCKET_NAME}/"
      rm -rf "${TEMP_DIR}"
      exit 1
    fi
  fi
else
  skip "Model upload skipped (use --upload-model or --bake-model)"
  info "Ensure model is already in gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/"
fi

# ---------------------------------------------------------------------------
# Service account
# ---------------------------------------------------------------------------
step "6/9 Service account (llm-invoker)"

if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
  skip "Service account ${SA_NAME} already exists"
else
  info "Creating service account ${SA_NAME}..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="LLM Service Invoker" \
    --description="Used by external backend servers to call the Cloud Run LLM service" \
    --quiet
  ok "Created ${SA_EMAIL}"
fi

# Ensure run.invoker role
info "Ensuring ${SA_NAME} has roles/run.invoker on ${SERVICE_NAME}..."
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --region="${REGION}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker" \
  --quiet &>/dev/null 2>&1 || skip "Service not yet deployed — will bind after deploy"
ok "${SA_NAME} has roles/run.invoker"

# Generate key if requested
if [[ "${GENERATE_SA_KEY}" == "true" ]]; then
  SA_KEY_FILE="${MONOREPO_ROOT}/llm-invoker-key.json"
  info "Generating service account key..."
  gcloud iam service-accounts keys create "${SA_KEY_FILE}" \
    --iam-account="${SA_EMAIL}" \
    --project="${PROJECT_ID}" \
    --quiet
  ok "Key saved to ${SA_KEY_FILE}"
  echo ""
  info "Add this to the backend .env on your external server:"
  echo -e "  ${CYAN}GCP_LLM_SERVICE_ACCOUNT_JSON=$(python3 -c "import json; print(json.dumps(json.load(open('${SA_KEY_FILE}'))))")${NC}"
  echo ""
fi

# ---------------------------------------------------------------------------
# Build image
# ---------------------------------------------------------------------------
step "7/9 Building container image (Cloud Build)"

if [[ "${BAKE_MODEL}" == "true" ]]; then
  info "Building BAKED image (base + model from GCS)..."
  gcloud builds submit "${LLM_DIR}" \
    --config="${LLM_DIR}/cloudbuild-baked.yaml" \
    --timeout=3600 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes model)"
else
  info "Building base image (model loaded at runtime via GCS FUSE or HF download)..."
  gcloud builds submit "${LLM_DIR}" \
    --tag="${IMAGE}:latest" \
    --timeout=1800 \
    --quiet
  ok "Image built: ${IMAGE}:latest"
fi

# ---------------------------------------------------------------------------
# Deploy to Cloud Run
# ---------------------------------------------------------------------------
step "8/9 Deploying to Cloud Run"

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
  --quiet
)

if [[ "${BAKE_MODEL}" == "true" ]]; then
  # Baked: model inside image at /app/model, pass as local path
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=30,timeoutSeconds=10,periodSeconds=15,failureThreshold=40"
    --clear-volume-mounts
    --clear-volumes
    --command="python3"
    --args="-m,vllm.entrypoints.openai.api_server,--model,/app/model,--quantization,bitsandbytes,--load-format,bitsandbytes,--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--dtype,bfloat16,--port,${PORT}"
  )
  info "Deploy mode: BAKED (model in image, no GCS volumes)"
else
  # GCS FUSE: mount bucket, model loaded from GCS
  DEPLOY_ARGS+=(
    --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=30,timeoutSeconds=10,periodSeconds=15,failureThreshold=40"
    --add-volume="name=models,type=cloud-storage,bucket=${BUCKET_NAME}"
    --add-volume-mount="volume=models,mount-path=/gcs-models"
    --command="python3"
    --args="-m,vllm.entrypoints.openai.api_server,--model,/gcs-models/${MODEL_DIR_NAME},--quantization,bitsandbytes,--load-format,bitsandbytes,--max-model-len,${MAX_MODEL_LEN},--gpu-memory-utilization,0.9,--dtype,bfloat16,--port,${PORT}"
  )
  info "Deploy mode: GCS FUSE (model mounted from gs://${BUCKET_NAME})"
fi

gcloud run deploy "${SERVICE_NAME}" "${DEPLOY_ARGS[@]}"
ok "Deployed ${SERVICE_NAME}"

# Re-bind IAM after deploy (in case service was just created)
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --region="${REGION}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker" \
  --quiet &>/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
step "9/9 Verification"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

info "Service URL: ${SERVICE_URL}"

# Health check (retry up to 5 times — model loading + quantization is slow)
info "Testing /health (waiting for cold start — model loading + quantization may take several minutes)..."
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
ok "Setup complete! Service: ${SERVICE_URL}"
