# Database Backup & Restore

Utilidad para exportar e importar todos los datos de la base de datos PostgreSQL del proyecto, incluyendo tablas con pgvector, tsvector, JSONB y todos los datos de negocio.

## Requisitos

- **Local**: `pg_dump`, `pg_restore`, `psql`, `createdb`, `dropdb` (paquete `postgresql-client`)
- **Docker**: solo `docker` (las herramientas PG están dentro del contenedor)

## Uso rápido

### Exportar

```bash
# Desde la raíz del monorepo
make db-export              # Local (localhost:15432)
make db-export-docker       # Docker (contenedor uja-postgres)

# Desde backend/
make db-export
make db-export-docker
```

Los dumps se guardan en `backend/backups/uja_iaph_YYYYMMDD_HHMMSS.dump` (formato custom de pg_dump, comprimido).

### Importar

```bash
# Desde la raíz del monorepo
make db-import FILE=backend/backups/uja_iaph_20260330_143000.dump
make db-import-docker FILE=backend/backups/uja_iaph_20260330_143000.dump

# Desde backend/
make db-import FILE=backups/uja_iaph_20260330_143000.dump
make db-import-docker FILE=backups/uja_iaph_20260330_143000.dump
```

> **Cuidado**: la importación hace DROP de la base de datos y la recrea. Pide confirmación antes de proceder.

### Uso directo del script

```bash
cd backend

# Exportar
./scripts/db_backup.sh export              # local
./scripts/db_backup.sh export --docker     # docker

# Importar
./scripts/db_backup.sh import backups/dump.dump           # local
./scripts/db_backup.sh import --docker backups/dump.dump  # docker
```

## Variables de entorno

El script usa las siguientes variables con valores por defecto:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `POSTGRES_DB` | `uja_iaph` | Nombre de la base de datos |
| `POSTGRES_USER` | `uja` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `uja` | Contraseña |
| `DB_HOST` | `localhost` | Host (solo modo local) |
| `DB_PORT` | `15432` | Puerto (solo modo local) |
| `POSTGRES_CONTAINER` | `uja-postgres` | Nombre del contenedor Docker |

## Tablas incluidas

El dump incluye **todas** las tablas de la base de datos:

| Tabla | Contenido | Tipos especiales |
|-------|-----------|-----------------|
| `document_chunks_v1` - `v4` | Chunks de documentos con embeddings | pgvector, tsvector, JSONB |
| `heritage_assets` | Catálogo de bienes patrimoniales | JSONB, ARRAY |
| `chat_sessions` | Sesiones de conversación | UUID |
| `chat_messages` | Mensajes del chat | JSON |
| `virtual_routes` | Rutas virtuales generadas | JSON |
| `users` | Usuarios registrados | UUID |
| `user_profile_types` | Tipos de perfil (admin, investigador, ciudadano) | - |
| `user_feedback` | Valoraciones de usuarios | JSONB |
| `alembic_version` | Estado de migraciones | - |

También se exportan triggers (tsvector auto-update), índices (HNSW, GIN, B-tree) y la extensión pgvector.

## Flujos típicos

### Migrar datos de local a producción (Docker)

```bash
# 1. Exportar desde local
make db-export
# → backend/backups/uja_iaph_20260330_143000.dump

# 2. Copiar el dump al servidor de producción
scp backend/backups/uja_iaph_20260330_143000.dump user@server:~/iaph-rag-monorepo/backend/backups/

# 3. En el servidor, importar en Docker
make db-import-docker FILE=backend/backups/uja_iaph_20260330_143000.dump
```

### Migrar datos de producción (Docker) a local

```bash
# 1. En el servidor, exportar desde Docker
make db-export-docker
# → backend/backups/uja_iaph_20260330_150000.dump

# 2. Copiar a local
scp user@server:~/iaph-rag-monorepo/backend/backups/uja_iaph_20260330_150000.dump backend/backups/

# 3. Importar en local
make db-import FILE=backend/backups/uja_iaph_20260330_150000.dump
```

### Backup periódico en producción

```bash
# Añadir al crontab del servidor
0 3 * * * cd /path/to/iaph-rag-monorepo && make db-export-docker
```

## Notas

- El formato custom de pg_dump (`-Fc`) es comprimido y permite restauración selectiva de tablas si fuera necesario
- Los dumps incluyen la tabla `alembic_version`, por lo que tras restaurar no es necesario re-ejecutar migraciones (salvo que haya nuevas)
- Los flags `--no-owner --no-acl` evitan problemas de permisos al restaurar en un entorno con distinto usuario
- Los embeddings vectoriales (pgvector) se exportan e importan correctamente en formato binario
