from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, health
from app.core.config import get_settings
from app.db.database import dispose_engine, init_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_engine(settings)
    app.state.settings = settings
    # Later phases will also start: Redis pool, queue client, OTel exporters.
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
