from typing import List

from common.auth import get_current_user
from common.logging import setup_logging
from common.models import UserDB
from common.schemas import IngestResponse
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from orchestrator.agent import run_query
from orchestrator.utils import save_uploaded_pdfs
from orchestrator.config import PDFS_DIR
# Setup logging
logger = setup_logging(__name__)

# Initialize router
router = APIRouter(tags=["Gateway"])

# Query endpoint
@router.post("/query")
async def query_gateway(
    question: str,
    level: int = Query(0, description="RAG Level to query"),
    current_user: UserDB = Depends(get_current_user),
):
    try:
        response = run_query(question, level=level)
        return {"answer": response}
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Ingest endpoint
@router.post("/ingest", response_model=IngestResponse)
async def ingest_gateway(
    files: List[UploadFile] = File(...),
    current_user: UserDB = Depends(get_current_user),
):
    try:
        pdf_paths = save_uploaded_pdfs(files, dest_dir=PDFS_DIR)
        result = run_query(pdf_paths, action="ingest")
        return {"message": "Ingestion completed via agent", "result": result}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
