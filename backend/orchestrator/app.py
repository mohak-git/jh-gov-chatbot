from fastapi import FastAPI
from common.logging import setup_logging

import requests
import orchestrator.config as config
from fastapi.middleware.cors import CORSMiddleware
from common.config import settings
from common.db import db
from orchestrator.routers import auth, gateway

# Setup Logging
logger = setup_logging(__name__)

app = FastAPI(title="Jharkhand Chatbot Orchestrator", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close()

# Routers
app.include_router(auth.router)
app.include_router(gateway.router)

@app.get("/health")
def health():
    """Check orchestrator and Level servers health"""
    status = {"orchestrator": "ok", "levels": {}}

    for level_name, url in {
        "level0": config.LEVEL0_URL,
        "level1": config.LEVEL1_URL,
        "level2": config.LEVEL2_URL,
    }.items():
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                status["levels"][level_name] = {
                    "status": "ok",
                    "vectors": data.get("stats", {}).get("vectors", 0),
                }
            else:
                status["levels"][level_name] = {"status": f"error {resp.status_code}"}
        except Exception as e:
            logger.warning(f"{level_name} health check failed: {e}")
            status["levels"][level_name] = {"status": "down"}

    return status
