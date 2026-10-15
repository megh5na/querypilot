import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.routes import schema, ask
from app.core.logging import configure_logging, request_id_var
from app.db.session import close_pools, get_pool, get_readonly_pool

configure_logging()  # do this before anything else can log (e.g. pool startup)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize both pools before the first request arrives
    # read only and read write pools, basically
    await get_pool()
    await get_readonly_pool()
    yield
    await close_pools()  # shutdown: release connections cleanly instead of leaving it to process exit


app = FastAPI(title="QueryPilot", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    # every request gets a short correlation id, stashed in a contextvar so
    # any logger.*() call made while handling this request — in this file,
    # in ask.py, wherever — picks it up automatically via JSONFormatter.
    request_id = uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    start = time.monotonic()
    try:
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        request_id_var.reset(token)  # scoped to this request only


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(schema.router)
app.include_router(ask.router)