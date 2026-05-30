from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Startup: later phases will initialize DB engine, Redis pool,
    # queue client, and OpenTelemetry exporters here.
    app.state.settings = settings
    yield
    # Shutdown: later phases will close pools and flush tracers here.


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    return app


app = create_app()
