import logging
import uuid as _uuid
from contextlib import asynccontextmanager

import bcrypt
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

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
from src.config import settings
from src.infrastructure.auth.models import UserModel, UserProfileTypeModel
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("iaph")
logger.info("Starting %s", settings.project_name)


def _seed_admin() -> None:
    """Ensure the admin profile type and root admin user exist."""
    engine = create_engine(settings.database_url_sync, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        pt = session.execute(
            select(UserProfileTypeModel).where(UserProfileTypeModel.name == "admin")
        ).scalar_one_or_none()
        if pt is None:
            pt = UserProfileTypeModel(id=_uuid.uuid4(), name="admin")
            session.add(pt)
            session.flush()

        existing = session.execute(
            select(UserModel).where(UserModel.username == settings.admin_username)
        ).scalar_one_or_none()
        if existing is None:
            pw_hash = bcrypt.hashpw(
                settings.admin_password.encode(), bcrypt.gensalt()
            ).decode()
            user = UserModel(
                id=_uuid.uuid4(),
                username=settings.admin_username,
                password_hash=pw_hash,
                profile_type_id=pt.id,
            )
            session.add(user)
        elif existing.profile_type_id != pt.id:
            existing.profile_type_id = pt.id

        session.commit()
    engine.dispose()
    logger.info("Admin seed completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_admin()
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
