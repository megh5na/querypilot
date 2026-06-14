from fastapi import FastAPI

app = FastAPI(title="QueryPilot")

@app.get("/health")
def health():
    return {"status": "ok"}
