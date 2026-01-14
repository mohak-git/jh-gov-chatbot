from typing import List

from common.auth import get_current_user
from common.logging import setup_logging
from common.models import UserDB
from common.schemas import Citation, IngestResponse, QueryResponse
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from orchestrator.agent import run_query
from orchestrator.config import PDFS_DIR
from orchestrator.graph import chatbot_graph
from orchestrator.utils import save_uploaded_pdfs

# Setup logging
logger = setup_logging(__name__)

# Initialize router
router = APIRouter(tags=["Gateway"])


# Chat endpoint with memory
@router.post("/chat", response_model=QueryResponse)
async def chat_gateway(
    message: str,
    thread_id: str = Query(None, description="Thread ID for conversation memory"),
    level: int = Query(0, description="RAG Level to query"),
    current_user: UserDB = Depends(get_current_user),
):
    """
    Chat endpoint with conversation memory.
    Uses LangGraph with MongoDB checkpointer for persistent state.

    - thread_id: Optional. If not provided, uses user_id for single-thread per user.
    - message: The user's question or message.
    """
    try:
        # Use provided thread_id or default to user_id
        user_id = str(current_user.id)
        threadId = str(thread_id) or user_id

        logger.info(f"[CHAT] User {current_user.username} | Thread: {user_id}")

        result = chatbot_graph.invoke(
            message=message, thread_id=threadId, user_id=user_id
        )

        # Convert citations to the expected format
        citations = [
            Citation(
                source_file=c.get("source_file", ""),
                page_start=c.get("page_start", 0),
                page_end=c.get("page_end", 0),
                score=c.get("score", 0.0),
                snippet=c.get("snippet", ""),
            )
            for c in result.get("citations", [])
        ]

        return QueryResponse(
            answer=result["answer"],
            citations=citations,
            prompt=result.get("prompt", None),
            used_top_k=result.get("used_top_k", 0),
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Query endpoint (without memory)
@router.post("/query", response_model=QueryResponse)
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
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to ingest files")
    try:
        pdf_paths = save_uploaded_pdfs(files, dest_dir=PDFS_DIR)
        result = run_query(pdf_paths, action="ingest")
        return {"message": "Ingestion completed via agent", "result": result}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
