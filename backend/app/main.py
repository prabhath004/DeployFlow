from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, deployments, health, logs, projects
from app.core.config import get_settings
from app.db.database import dispose_engine, init_engine
from app.db.redis import dispose_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_engine(settings)
    init_redis(settings)
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
        version="0.5.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(deployments.project_router)
    app.include_router(deployments.deployment_router)
    app.include_router(logs.router)
    return app


app = create_app()
