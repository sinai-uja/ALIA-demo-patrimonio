# Despliegue del servicio de embeddings en Google Cloud Run

Guia para desplegar el servicio de embeddings (Qwen3-Embedding) + reranker (Qwen3-Reranker) en **Google Cloud Run con GPU**.

> **Region**: `europe-west1` (Belgica). Las GPU NVIDIA L4 en Cloud Run solo estan disponibles en: `asia-southeast1`, `europe-west1`, `europe-west4`, `us-central1`, `us-east4`. Se elige `europe-west1` por proximidad a Espana.

> **URL del servicio**: `https://uja-embedding-542619191440.europe-west1.run.app`

---

## Despliegue rapido (scripts automatizados)

Los scripts en `embedding/scripts/` automatizan todo el proceso. Tambien disponibles via `make`.

### Dos modos de despliegue

| Modo | Cold start | Imagen | Comando |
|------|-----------|--------|---------|
| **GCS FUSE** (por defecto) | ~3-4 min (lee modelos del bucket) | ~2 GB | `make cloud-deploy` |
| **Baked** (modelos en imagen) | ~10-20s (modelos ya en disco) | ~4-5 GB | `make cloud-deploy-baked` |

### Primera vez (setup completo)

```bash
make cloud-setup              # GCS FUSE (modelos ya en bucket)
make cloud-setup-models       # GCS FUSE + subir modelos a GCS
make cloud-setup-baked        # Baked (modelos en imagen, cold start rapido)
```

### Redeploy dia a dia

```bash
make cloud-deploy                  # rebuild + deploy (GCS FUSE)
make cloud-deploy-baked            # rebuild + deploy (modelos en imagen)
make cloud-deploy-skip-build       # solo redeploy GCS FUSE (misma imagen)
make cloud-deploy-baked-skip-build # solo redeploy baked (misma imagen)
```

Los scripts son idempotentes: se pueden re-ejecutar sin romper nada. Se puede cambiar de modo en cualquier momento.

---

## Indice (referencia manual)

1. [Prerequisitos](#1-prerequisitos)
2. [Preparar modelos en GCS](#2-preparar-modelos-en-gcs)
3. [Build y push de la imagen](#3-build-y-push-de-la-imagen)
4. [Desplegar en Cloud Run con GPU](#4-desplegar-en-cloud-run-con-gpu)
5. [Verificacion](#5-verificacion)
6. [Autenticacion](#6-autenticacion)
7. [Parametros criticos](#7-parametros-criticos)
8. [Estimacion de costes](#8-estimacion-de-costes)

---

## 1. Prerequisitos

### 1.1 Variables de entorno

```bash
export PROJECT_ID="innovasur-uja-alia"
export REGION="europe-west1"
```

### 1.2 Instalar y autenticar gcloud

```bash
# Instalar Google Cloud SDK (si no esta instalado)
sudo snap install google-cloud-cli --classic

# Autenticarse
gcloud auth login

# Configurar proyecto
gcloud config set project $PROJECT_ID
```

### 1.3 Activar APIs necesarias

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com
```

### 1.4 Crear repositorio en Artifact Registry

```bash
gcloud artifacts repositories create iaph-rag \
  --repository-format=docker \
  --location=$REGION \
  --description="IAPH RAG container images"
```

La URL del registro sera:
```
europe-west1-docker.pkg.dev/innovasur-uja-alia/iaph-rag
```

### 1.5 Verificar cuota de GPU

```bash
gcloud compute regions describe $REGION \
  --format="table(quotas.filter(metric='NVIDIA_L4_GPUS'))"
```

Si no tienes cuota, solicitarla en: **IAM & Admin > Quotas** buscando `NVIDIA L4 GPUs` para el servicio `Cloud Run`.

### 1.6 Crear bucket de GCS para modelos

```bash
gcloud storage buckets create gs://${PROJECT_ID}-iaph-models \
  --location=$REGION \
  --uniform-bucket-level-access
```

---

## 2. Preparar modelos en GCS

Los modelos se almacenan en GCS. En modo GCS FUSE se montan como volumen en el contenedor. En modo baked se descargan durante el build de la imagen.

```bash
# Subir Qwen3-Embedding
gcloud storage cp -r backend/models/Qwen3-Embedding-0.6B gs://${PROJECT_ID}-iaph-models/

# Subir Qwen3-Reranker
gcloud storage cp -r backend/models/Qwen3-Reranker-0.6B gs://${PROJECT_ID}-iaph-models/
```

---

## 3. Build y push de la imagen

### Modo GCS FUSE (imagen ligera, modelos en runtime)

```bash
IMAGE_EMBEDDING="${REGION}-docker.pkg.dev/${PROJECT_ID}/iaph-rag/embedding"

gcloud builds submit ./embedding \
  --tag=${IMAGE_EMBEDDING}:latest \
  --timeout=1800
```

### Modo Baked (imagen con modelos, cold start rapido)

```bash
gcloud builds submit ./embedding \
  --config=embedding/cloudbuild-baked.yaml \
  --timeout=1800
```

Esto ejecuta dos pasos: build de la imagen base, luego descarga los modelos de GCS y los copia dentro de la imagen.

> El primer build tarda ~10-15 min. Cloud Build no mantiene cache entre builds.

---

## 4. Desplegar en Cloud Run con GPU

### Modo GCS FUSE

```bash
IMAGE_EMBEDDING="${REGION}-docker.pkg.dev/${PROJECT_ID}/iaph-rag/embedding"

gcloud run deploy uja-embedding \
  --image=${IMAGE_EMBEDDING}:latest \
  --region=$REGION \
  --port=8001 \
  --cpu=4 \
  --memory=16Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --max-instances=1 \
  --min-instances=0 \
  --no-cpu-throttling \
  --cpu-boost \
  --execution-environment=gen2 \
  --no-allow-unauthenticated \
  --startup-probe=httpGet.path=/health,httpGet.port=8001,initialDelaySeconds=10,timeoutSeconds=5,periodSeconds=15,failureThreshold=30 \
  --set-env-vars="DEVICE=cuda,POOLING_STRATEGY=last_token,MAX_LENGTH=32768,RERANKER_MAX_LENGTH=8192,RERANKER_BATCH_SIZE=4" \
  --add-volume=name=models,type=cloud-storage,bucket=${PROJECT_ID}-iaph-models \
  --add-volume-mount=volume=models,mount-path=/gcs-models \
  --command="sh" \
  --args="-c,ln -s /gcs-models/Qwen3-Embedding-0.6B /app/model && ln -s /gcs-models/Qwen3-Reranker-0.6B /app/reranker_model && uvicorn main:app --host 0.0.0.0 --port 8001"
```

### Modo Baked

```bash
gcloud run deploy uja-embedding \
  --image=${IMAGE_EMBEDDING}:latest \
  --region=$REGION \
  --port=8001 \
  --cpu=4 \
  --memory=16Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --max-instances=1 \
  --min-instances=0 \
  --no-cpu-throttling \
  --cpu-boost \
  --execution-environment=gen2 \
  --no-allow-unauthenticated \
  --startup-probe=httpGet.path=/health,httpGet.port=8001,initialDelaySeconds=5,timeoutSeconds=5,periodSeconds=10,failureThreshold=12 \
  --set-env-vars="DEVICE=cuda,POOLING_STRATEGY=last_token,MAX_LENGTH=32768,RERANKER_MAX_LENGTH=8192,RERANKER_BATCH_SIZE=4" \
  --clear-volume-mounts \
  --clear-volumes \
  --command="" \
  --args=""
```

> En modo baked no se montan volumenes GCS. Los modelos ya estan en `/app/model` y `/app/reranker_model` dentro de la imagen. El startup probe es mas corto (~2 min vs ~7.5 min).

---

## 5. Verificacion

```bash
SERVICE_URL=https://uja-embedding-542619191440.europe-west1.run.app
TOKEN=$(gcloud auth print-identity-token)

# Health check
curl -s -H "Authorization: Bearer ${TOKEN}" ${SERVICE_URL}/health | python -m json.tool

# Test de embedding
curl -s -X POST ${SERVICE_URL}/embed \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["prueba de embedding"]}'

# Test de reranking
curl -s -X POST ${SERVICE_URL}/rerank \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"monumentos","documents":["La Alhambra de Granada","El olivo de Jaén"],"top_n":2}'
```

Ver logs del servicio:

```bash
gcloud run services logs read uja-embedding --region=$REGION --limit=50
```

---

## 6. Autenticacion

La autenticacion se gestiona exclusivamente a nivel de **Cloud Run IAM** (`--no-allow-unauthenticated`). Sin credenciales IAM validas, Cloud Run devuelve 403 sin arrancar ninguna instancia (ahorro de GPU).

### Desde servidores no-GCP

Para que el backend pueda llamar al servicio de embedding desde un servidor externo a GCP, se usa una **service account key** dedicada:

1. Se ha creado la service account `embedding-invoker@innovasur-uja-alia.iam.gserviceaccount.com` con el rol `roles/run.invoker`.
2. En el `.env` del backend se configura `GCP_SERVICE_ACCOUNT_JSON` con el JSON compacto de la key.
3. El backend obtiene automaticamente un identity token y lo envia como `Authorization: Bearer <token>`.

### Desde GCP (Cloud Run, GCE)

No se necesita configuracion adicional. El backend usa el metadata server automaticamente.

### Local (desarrollo)

Cuando la URL del embedding es `localhost`, no se envia ningun token de autenticacion (el servicio local no lo requiere).

---

## 7. Parametros criticos

| Parametro | Valor | Motivo |
|-----------|-------|--------|
| `--min-instances=0` | Sin instancias permanentes | Ahorra coste cuando no hay trafico |
| `--no-cpu-throttling` | CPU siempre activa | El modelo necesita CPU activa mientras la GPU procesa |
| `--cpu-boost` | CPU extra durante arranque | Acelera la carga de modelos en cold start |
| `--startup-probe` | HTTP probe en `/health` | GCS FUSE: 30x15s (~7.5 min), Baked: 12x10s (~2 min) |
| `--gpu=1, --gpu-type=nvidia-l4` | GPU dedicada | Los modelos necesitan CUDA |
| `--memory=16Gi` | Suficiente para modelos en RAM | Qwen3 + Reranker + overhead PyTorch |
| `--execution-environment=gen2` | Requerido para GPU | Solo gen2 soporta GPU en Cloud Run |
| `--no-allow-unauthenticated` | Servicio privado | Solo accesible con token IAM valido |

---

## 8. Estimacion de costes

| Recurso | Detalle | Coste mensual (est.) |
|---------|---------|---:|
| Cloud Run (GPU) | 4 vCPU, 16 GB, 1x L4, min 0 instancias | ~$0-400 (segun trafico) |
| GCS (modelos) | ~5 GB almacenamiento | ~$1 |
| Cloud Build | Builds esporadicos | ~$1-5 |
| **Total** | | **~$0-410/mes** |

### Optimizaciones de coste

1. **Committed use discounts** para GPU si es uso 24/7
3. **Subir `--min-instances=1`** si necesitas eliminar cold starts a cambio de coste fijo 24/7
