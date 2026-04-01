#!/usr/bin/env bash
# =============================================================================
# Database export/import utility for IAPH RAG
#
# Usage:
#   ./scripts/db_backup.sh export [--docker]    Export all data to a dump file
#   ./scripts/db_backup.sh import [--docker] <file>   Import from a dump file
#
# Modes:
#   (default)   Local — connects via localhost:15432 (host-mapped port)
#   --docker    Docker — runs pg_dump/pg_restore inside the uja-postgres container
#
# Output:
#   backups/uja_iaph_YYYYMMDD_HHMMSS.dump  (custom pg_dump format)
# =============================================================================
set -euo pipefail

# ── Config (from root .env defaults) ─────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$BACKEND_DIR")"
BACKUP_DIR="${BACKEND_DIR}/backups"

DB_NAME="${POSTGRES_DB:-uja_iaph}"
DB_USER="${POSTGRES_USER:-uja}"
DB_PASS="${POSTGRES_PASSWORD:-uja}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-15432}"
CONTAINER="${POSTGRES_CONTAINER:-uja-postgres}"

# ── Parse arguments ──────────────────────────────────────────────────────────
ACTION="${1:-}"
shift || true

DOCKER_MODE=false
IMPORT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docker) DOCKER_MODE=true; shift ;;
    *) IMPORT_FILE="$1"; shift ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
usage() {
  echo "Usage:"
  echo "  $0 export [--docker]              Export database"
  echo "  $0 import [--docker] <file.dump>   Import database from dump"
  exit 1
}

check_container() {
  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "Error: container '${CONTAINER}' is not running."
    echo "Start it with: make infra"
    exit 1
  fi
}

# Auto-detect: if pg_dump is not installed locally, fall back to Docker mode
auto_docker_fallback() {
  if ! $DOCKER_MODE && ! command -v pg_dump &>/dev/null; then
    echo "pg_dump not found locally, falling back to Docker mode..."
    DOCKER_MODE=true
  fi
}

timestamp() {
  date +%Y%m%d_%H%M%S
}

# ── Export ────────────────────────────────────────────────────────────────────
do_export() {
  auto_docker_fallback
  mkdir -p "$BACKUP_DIR"
  local outfile="${BACKUP_DIR}/uja_iaph_$(timestamp).dump"

  echo "Exporting database '${DB_NAME}'..."

  if $DOCKER_MODE; then
    check_container
    docker exec -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc --no-owner --no-acl \
      > "$outfile"
  else
    PGPASSWORD="$DB_PASS" pg_dump \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      -Fc --no-owner --no-acl \
      > "$outfile"
  fi

  local size
  size=$(du -h "$outfile" | cut -f1)
  echo "Done: ${outfile} (${size})"
}

# ── Import ───────────────────────────────────────────────────────────────────
do_import() {
  auto_docker_fallback
  if [[ -z "$IMPORT_FILE" ]]; then
    echo "Error: no dump file specified."
    usage
  fi

  if [[ ! -f "$IMPORT_FILE" ]]; then
    echo "Error: file not found: ${IMPORT_FILE}"
    exit 1
  fi

  echo "Importing '${IMPORT_FILE}' into database '${DB_NAME}'..."
  echo "WARNING: this will DROP and recreate all tables in '${DB_NAME}'."
  read -rp "Continue? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi

  if $DOCKER_MODE; then
    check_container

    # Drop and recreate the database
    docker exec -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      psql -U "$DB_USER" -d postgres -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
      2>/dev/null || true

    docker exec -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      dropdb -U "$DB_USER" --if-exists "$DB_NAME"

    docker exec -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      createdb -U "$DB_USER" "$DB_NAME"

    # Ensure pgvector extension exists
    docker exec -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

    # Restore
    cat "$IMPORT_FILE" | docker exec -i -e PGPASSWORD="$DB_PASS" "$CONTAINER" \
      pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl --single-transaction \
      2>&1 || true
  else
    # Drop and recreate the database
    PGPASSWORD="$DB_PASS" psql \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
      2>/dev/null || true

    PGPASSWORD="$DB_PASS" dropdb \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"

    PGPASSWORD="$DB_PASS" createdb \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

    # Ensure pgvector extension exists
    PGPASSWORD="$DB_PASS" psql \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      -c "CREATE EXTENSION IF NOT EXISTS vector;"

    # Restore
    PGPASSWORD="$DB_PASS" pg_restore \
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      --no-owner --no-acl --single-transaction \
      "$IMPORT_FILE" 2>&1 || true
  fi

  echo "Done. Database '${DB_NAME}' restored from '${IMPORT_FILE}'."
  echo "Note: Alembic version table was restored. Run 'make migrate' if needed."
}

# ── Main ─────────────────────────────────────────────────────────────────────
case "$ACTION" in
  export) do_export ;;
  import) do_import ;;
  *) usage ;;
esac
