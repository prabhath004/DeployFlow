from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, deployments, health, logs, projects
from app.core.config import get_settings
from app.db.database import dispose_engine, get_engine, init_engine
from app.db.redis import dispose_redis, init_redis
from app.observability.logging import setup_logging
from app.observability.metrics import setup_metrics
from app.observability.tracing import instrument_app, setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    setup_tracing("deployflow-api")
    setup_metrics("deployflow-api")
    init_engine(settings)
    init_redis(settings)
    # Auto-instrument FastAPI + SQLAlchemy *after* the engine exists.
    instrument_app(app, engine=get_engine())
    app.state.settings = settings
    try:
        yield
    finally:
        await dispose_redis()
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.10.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(deployments.project_router)
    app.include_router(deployments.deployment_router)
    app.include_router(logs.router)
    return app


app = create_app()
