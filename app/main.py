import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import engine
from app.services.tasks import TaskNotFound

configure_logging(get_settings().log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    try:
        yield
    finally:
        if app.state.redis is not None:
            await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(title="Task Management API", lifespan=lifespan)
app.include_router(tasks_router, prefix="/api/v1")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.exception_handler(TaskNotFound)
async def not_found_handler(request: Request, exc: TaskNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Task not found"})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled request error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

