import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints.accessibility.accessibility import router as accessibility_router
from src.api.v1.endpoints.admin.admin import router as admin_router
from src.api.v1.endpoints.auth.auth import router as auth_router
from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.chat.chat import router as chat_router
from src.api.v1.endpoints.documents.documents import router as documents_router
from src.api.v1.endpoints.feedback.feedback import router as feedback_router
from src.api.v1.endpoints.heritage.heritage import router as heritage_router
from src.api.v1.endpoints.rag.rag import router as rag_router
from src.api.v1.endpoints.routes.routes import router as routes_router
from src.api.v1.endpoints.search.search import router as search_router
from src.api.v1.exception_handlers import register_exception_handlers
from src.composition.auth_composition import build_auth_application_service
from src.config import settings
from src.infrastructure.shared.persistence.engine import AsyncSessionLocal
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("iaph")
logger.info("Starting %s", settings.project_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        auth_service = build_auth_application_service(session)
        await auth_service.ensure_root_admin(
            username=settings.admin_username,
            password=settings.admin_password,
        )
    logger.info("Root admin bootstrap completed")
    yield


app = FastAPI(
    title=settings.project_name,
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"]
)
app.include_router(
    admin_router,
    prefix=settings.api_v1_prefix,
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    documents_router,
    prefix=f"{settings.api_v1_prefix}/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    rag_router,
    prefix=f"{settings.api_v1_prefix}/rag",
    tags=["rag"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    chat_router,
    prefix=f"{settings.api_v1_prefix}/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    accessibility_router,
    prefix=f"{settings.api_v1_prefix}/accessibility",
    tags=["accessibility"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    routes_router,
    prefix=f"{settings.api_v1_prefix}/routes",
    tags=["routes"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    heritage_router,
    prefix=f"{settings.api_v1_prefix}/heritage",
    tags=["heritage"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    search_router,
    prefix=f"{settings.api_v1_prefix}/search",
    tags=["search"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    feedback_router,
    prefix=f"{settings.api_v1_prefix}/feedback",
    tags=["feedback"],
    dependencies=[Depends(get_current_user)],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.project_name}
