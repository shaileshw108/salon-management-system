from fastapi import FastAPI
from .config import get_settings

settings = get_settings()
app = FastAPI(title="Shiva's Salon API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}
