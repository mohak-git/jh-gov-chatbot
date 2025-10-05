from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from typing import List
from orchestrator.agent import run_query
from orchestrator.utils import save_uploaded_pdfs
import logging
import requests
import orchestrator.config as config
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

app = FastAPI(title="Multi-Level RAG Orchestrator Agent", version="1.0.0")


@app.get("/health")
def healthcheck():
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


@app.post("/ingest")
async def ingest(files: List[UploadFile] = File(...)):
    try:
        pdf_paths = save_uploaded_pdfs(files, dest_dir=PDF_DIR)
        result = run_query(pdf_paths, action="ingest")
        return {"message": "Ingestion completed via agent", "result": result}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query(question: str, level: int = Query(None)):
    try:
        response = run_query(question, level=level)
        return {"answer": response}
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
