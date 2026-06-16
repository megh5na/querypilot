from fastapi import FastAPI
from app.api.routes import schema
from app.api.routes import ask

app = FastAPI(title="QueryPilot")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(schema.router) # adds the schema router to the app

app.include_router(ask.router)
