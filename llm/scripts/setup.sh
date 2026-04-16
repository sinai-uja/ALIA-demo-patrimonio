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
#   ./llm/scripts/setup.sh                          # vLLM (default, backward-compat)
#   ./llm/scripts/setup.sh --engine vllm             # explicit vLLM
#   ./llm/scripts/setup.sh --engine llamacpp         # llama.cpp + GGUF
#   ./llm/scripts/setup.sh --upload-model            # also upload model to GCS
#   ./llm/scripts/setup.sh --bake-model              # bake model into image
#   ./llm/scripts/setup.sh --generate-sa-key         # generate service account key
#   make cloud-llm-setup                             # via Makefile (vLLM)
#   make cloud-llm-setup-llamacpp                    # via Makefile (llama.cpp)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Flags (engine selection first — must precede config so we branch correctly)
# ---------------------------------------------------------------------------
ENGINE="vllm"   # default: backward-compatible, unchanged behavior
UPLOAD_MODEL=false
BAKE_MODEL=false
GENERATE_SA_KEY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine)           ENGINE="$2"; shift 2 ;;
    --engine=*)         ENGINE="${1#*=}"; shift ;;
    --upload-model)     UPLOAD_MODEL=true; shift ;;
    --bake-model)       BAKE_MODEL=true; shift ;;
    --generate-sa-key)  GENERATE_SA_KEY=true; shift ;;
    *)                  shift ;;
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
AR_REGION="europe-west1"                     # Artifact Registry region
REPO_NAME="iaph-rag"                        # shared with embedding service
BUCKET_NAME="${PROJECT_ID}-iaph-models"      # shared with embedding service
SA_NAME="llm-invoker"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run service settings — RTX PRO 6000 48GB for quantized ALIA-40b
CPU=20
MEMORY="80Gi"
GPU_TYPE="nvidia-rtx-pro-6000"
MAX_INSTANCES=1
MIN_INSTANCES=0
PORT=8000

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLM_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONOREPO_ROOT="$(cd "${LLM_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Engine-specific configuration
# ---------------------------------------------------------------------------
if [[ "${ENGINE}" == "vllm" ]]; then
  # Existing vLLM + GPTQ setup (unchanged).
  SERVICE_NAME="uja-llm"
  IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm"
  DOCKERFILE="Dockerfile"
  CLOUDBUILD_BAKED_CFG="${LLM_DIR}/cloudbuild-baked.yaml"
  MODEL_NAME="agustim/ALIA-40b-GPTQ-INT4"
  MODEL_DIR_NAME="ALIA-40b-GPTQ-INT4"
  MAX_MODEL_LEN=32768
  QUANTIZATION_ARGS="--quantization,gptq,--dtype,float16"
else
  # llama.cpp + GGUF (new, opt-in via --engine llamacpp).
  SERVICE_NAME="uja-llm-llamacpp"
  IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/llm-llamacpp"
  DOCKERFILE="Dockerfile.llamacpp"
  CLOUDBUILD_BAKED_CFG="${LLM_DIR}/cloudbuild-baked-llamacpp.yaml"
  HF_REPO="mradermacher/ALIA-40b-instruct-2601-GGUF"
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
info "Engine: ${ENGINE}"
info "Service: ${SERVICE_NAME}"
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

LOCAL_MODEL_DIR="${MONOREPO_ROOT}/backend/models/${MODEL_DIR_NAME}"

if [[ "${UPLOAD_MODEL}" == "true" || "${BAKE_MODEL}" == "true" ]]; then
  if [[ "${ENGINE}" == "vllm" ]]; then
    # vLLM: multi-file HF model directory (config.json + safetensors shards).
    if gcloud storage ls "gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/config.json" &>/dev/null; then
      skip "${MODEL_DIR_NAME} already in GCS"
    else
      # Prefer local model from backend/models/ (downloaded via make download-alia-gptq)
      if [[ -d "${LOCAL_MODEL_DIR}" && -f "${LOCAL_MODEL_DIR}/config.json" ]]; then
        info "Uploading ${MODEL_DIR_NAME} from local backend/models/ to GCS (~27GB)..."
        gcloud storage cp -r "${LOCAL_MODEL_DIR}" "gs://${BUCKET_NAME}/" --quiet
        ok "Uploaded ${MODEL_DIR_NAME} to GCS"
      else
        info "Local model not found at ${LOCAL_MODEL_DIR}"
        info "Download it first:  cd backend && make download-alia-gptq"
        info "Falling back to HuggingFace download..."

        TEMP_DIR=$(mktemp -d)
        if command -v huggingface-cli &>/dev/null; then
          huggingface-cli download "${MODEL_NAME}" --local-dir "${TEMP_DIR}/${MODEL_DIR_NAME}"
          gcloud storage cp -r "${TEMP_DIR}/${MODEL_DIR_NAME}" "gs://${BUCKET_NAME}/" --quiet
          rm -rf "${TEMP_DIR}"
          ok "Uploaded ${MODEL_DIR_NAME} to GCS"
        else
          err "huggingface-cli not found. Install with: pip install huggingface_hub"
          err "Or download the model first:  cd backend && make download-alia-gptq"
          rm -rf "${TEMP_DIR}"
          exit 1
        fi
      fi
    fi
  else
    # llama.cpp: single GGUF file.
    LOCAL_GGUF="${LOCAL_MODEL_DIR}/${GGUF_FILE}"
    GCS_GGUF="gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/${GGUF_FILE}"
    if gcloud storage ls "${GCS_GGUF}" &>/dev/null; then
      skip "${GGUF_FILE} already in GCS"
    else
      if [[ -f "${LOCAL_GGUF}" ]]; then
        info "Uploading ${GGUF_FILE} from local backend/models/ to GCS (~24.7GB)..."
        gcloud storage cp "${LOCAL_GGUF}" "${GCS_GGUF}" --quiet
        ok "Uploaded ${GGUF_FILE} to GCS"
      else
        info "Local GGUF not found at ${LOCAL_GGUF}"
        info "Download it first:  cd backend && make download-alia-gguf"
        info "Falling back to HuggingFace download..."

        TEMP_DIR=$(mktemp -d)
        if command -v hf &>/dev/null; then
          hf download "${HF_REPO}" "${GGUF_FILE}" --local-dir "${TEMP_DIR}"
        elif command -v huggingface-cli &>/dev/null; then
          huggingface-cli download "${HF_REPO}" "${GGUF_FILE}" --local-dir "${TEMP_DIR}"
        else
          err "Neither 'hf' nor 'huggingface-cli' found. Install with: pip install huggingface_hub"
          err "Or download the model first:  cd backend && make download-alia-gguf"
          rm -rf "${TEMP_DIR}"
          exit 1
        fi
        gcloud storage cp "${TEMP_DIR}/${GGUF_FILE}" "${GCS_GGUF}" --quiet
        rm -rf "${TEMP_DIR}"
        ok "Uploaded ${GGUF_FILE} to GCS"
      fi
    fi
  fi
else
  skip "Model upload skipped (use --upload-model or --bake-model)"
  if [[ "${ENGINE}" == "vllm" ]]; then
    info "Ensure model is already in gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/"
    info "Or download locally first:  cd backend && make download-alia-gptq"
  else
    info "Ensure GGUF is already in gs://${BUCKET_NAME}/${MODEL_DIR_NAME}/${GGUF_FILE}"
    info "Or download locally first:  cd backend && make download-alia-gguf"
  fi
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
    --config="${CLOUDBUILD_BAKED_CFG}" \
    --timeout=3600 \
    --quiet
  ok "Baked image built: ${IMAGE}:latest (includes model)"
elif [[ "${ENGINE}" == "llamacpp" ]]; then
  # Non-default Dockerfile requires a cloudbuild config YAML.
  info "Building base image (llama.cpp, model loaded at runtime via GCS FUSE)..."
  gcloud builds submit "${LLM_DIR}" \
    --config="${LLM_DIR}/cloudbuild-llamacpp.yaml" \
    --timeout=1800 \
    --quiet
  ok "Image built: ${IMAGE}:latest"
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
  --update-annotations=run.googleapis.com/launch-stage=BETA
  --no-allow-unauthenticated
  --no-gpu-zonal-redundancy
  --quiet
)

if [[ "${ENGINE}" == "vllm" ]]; then
  # ─── vLLM engine (existing behavior, unchanged) ──────────────────────────
  if [[ "${BAKE_MODEL}" == "true" ]]; then
    # Baked: model inside image at /app/model, pass as local path
    DEPLOY_ARGS+=(
      --startup-probe="httpGet.path=/health,httpGet.port=${PORT},initialDelaySeconds=60,timeoutSeconds=10,periodSeconds=15,failureThreshold=80"
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
  # ─── llama.cpp engine (new, opt-in via --engine llamacpp) ────────────────
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
ok "Setup complete! Service: ${SERVICE_URL}"
