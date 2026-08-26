from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import schema, ask
from app.db.session import get_pool, get_readonly_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize both pools before the first request arrives
    # read only and read write pools, basically
    await get_pool()
    await get_readonly_pool()
    yield
    # shutdown: nothing to explicitly close for now
    # asyncpg pools are closed by the OS on process exit
    # explicit pool.close() can be added here later


app = FastAPI(title="QueryPilot", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(schema.router)
app.include_router(ask.router)