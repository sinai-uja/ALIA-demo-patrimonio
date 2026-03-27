# Gestión de usuarios

El sistema utiliza autenticación basada en BD (tabla `users`) con contraseñas hasheadas con **bcrypt** y tokens **JWT**. Los usuarios se gestionan exclusivamente por línea de comandos.

## Requisitos previos

1. Infraestructura levantada (`make infra` desde la raíz)
2. Migraciones aplicadas (`make migrate`)

## Comandos

Todos los comandos se ejecutan desde `backend/`:

```bash
# Equivalente: make manage-users ARGS="<subcomando>"
```

### Crear usuario

```bash
make manage-users ARGS="create-user --username alice --password secret"

# Con perfil de usuario asignado:
make manage-users ARGS="create-user --username alice --password secret --profile-type investigador"
```

### Eliminar usuario

```bash
make manage-users ARGS="delete-user --username alice"
```

### Listar usuarios

```bash
make manage-users ARGS="list-users"
```

Salida:

```
Username             Profile Type         Created At                ID
------------------------------------------------------------------------------------------
admin                ciudadano            2026-03-27 21:30:00       ca010939-c4bc-...
alice                investigador         2026-03-27 22:00:00       b1234567-abcd-...
```

### Añadir tipo de perfil

Los tipos de perfil se almacenan en la tabla `user_profile_types`. Por defecto se crean `investigador` y `ciudadano` en la migración.

```bash
make manage-users ARGS="add-profile-type --name administrador"
```

### Listar tipos de perfil

```bash
make manage-users ARGS="list-profile-types"
```

## Tipos de perfil

Los tipos de perfil permiten categorizar a los usuarios para análisis y trazabilidad. Se almacenan en BD para poder añadir nuevos sin cambios de código.

| Tipo | Descripción |
|------|-------------|
| `investigador` | Investigador o académico del patrimonio |
| `ciudadano` | Ciudadano general interesado en el patrimonio |

El usuario puede cambiar su perfil desde el desplegable en la barra de navegación de la UI.

## Modelo de datos

```
user_profile_types
├── id (UUID PK)
├── name (unique)
└── created_at

users
├── id (UUID PK)
├── username (unique)
├── password_hash (bcrypt)
├── profile_type_id (FK → user_profile_types, nullable)
├── created_at
└── updated_at
```

## Scoping de datos

Cada usuario solo ve sus propios datos:

- **Sesiones de chat** — filtradas por `user_id`
- **Rutas virtuales** — filtradas por `user_id`
- **Feedback** — asociado al `username`

Los datos anteriores al sistema multi-usuario tienen `user_id = NULL`.

## Endpoints de autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/login` | Login con username/password → JWT tokens |
| `POST` | `/auth/refresh` | Refrescar access token |
| `GET` | `/auth/me` | Info del usuario autenticado |
| `PUT` | `/auth/profile-type` | Cambiar tipo de perfil |
| `GET` | `/auth/profile-types` | Listar tipos de perfil disponibles |

## Trazabilidad

El `username` y `profile_type` se incluyen en:

- Logs de búsqueda (`usecases/search.log`)
- Logs de generación de rutas (`usecases/routes.log`)
- Logs de feedback (`feedback.log`)
- CSVs de análisis (`all_searches_*.csv`, `all_routes_*.csv`, `search_feedback_*.csv`, `route_feedback_*.csv`)
