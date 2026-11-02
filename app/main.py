from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth as auth_routes
from app.api.routes import documents as documents_routes
from app.api.routes import gmail as gmail_routes
from app.api.routes import health as health_routes
from app.api.routes import jobs as jobs_routes
from app.api.routes import tickets as tickets_routes
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.modules.auth.service import seed_users
from app.modules.gmail.oauth import seed_from_env as seed_gmail
from app.modules.knowledge_base.service import seed_knowledge_docs

log = structlog.get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    log.info("app.startup", env=settings.app_env)
    with SessionLocal() as db:
        seed_users(db)
        seed_gmail(db)
        seed_knowledge_docs(db)
    yield
    log.info("app.shutdown")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Customer Automation API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        session_cookie="ca_session",
        same_site="lax",
        https_only=settings.is_production,
        max_age=60 * 60 * 24 * 7,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(health_routes.router)
    application.include_router(health_routes.router, prefix="/api/v1")
    for prefix in ("/api", "/api/v1"):
        application.include_router(auth_routes.router, prefix=prefix)
        application.include_router(jobs_routes.router, prefix=prefix)
        application.include_router(gmail_routes.router, prefix=prefix)
        application.include_router(documents_routes.router, prefix=prefix)
        application.include_router(tickets_routes.router, prefix=prefix)
        application.include_router(tickets_routes.stats_router, prefix=prefix)
    return application


app = create_app()
