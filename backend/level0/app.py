from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import logging
from fastapi.concurrency import run_in_threadpool
import os
import shutil
from typing import List

import level0.config as config
from level0.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    HealthResponse,
)
from level0.vectorstore import FaissStore
from level0.ingest import ingest_pdfs
from level0.rag import RAGPipeline, EmbeddingsClient, GeminiClient


# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# App Initialization
# -------------------------------------------------------------------
app = FastAPI(
    title="Jharkhand Policies RAG Backend",
    version="1.0.0",
    description="Backend service for PDF ingestion and RAG-based querying.",
)

# Configure CORS
allowed_origins = getattr(config, "ALLOWED_ORIGINS", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Core Components
# -------------------------------------------------------------------
store = FaissStore(config.INDEX_FILE, config.META_FILE)
store.load()

embedder = EmbeddingsClient(config.EMBEDDING_MODEL, config.GOOGLE_API_KEY)
llm = GeminiClient(config.GEMINI_MODEL, config.GOOGLE_API_KEY)
rag = RAGPipeline(store, embedder, llm)


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------
def reset_store():
    """Safely reset the FAISS index and metadata."""
    try:
        store.reset()
        logger.info("Vector store reset successfully.")
    except Exception as e:
        logger.error(f"Failed to reset store: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset store")


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    stats = store.stats()
    return HealthResponse(status="ok", stats=StatsResponse(**stats))


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Return vector store statistics."""
    return StatsResponse(**store.stats())


@app.post("/ingest", response_model=IngestResponse)
# async def ingest(req: IngestRequest):
async def ingest(files: List[UploadFile] = File(...), force_rebuild: bool = False):
    """Ingest PDFs into the vector store."""
    logger.info(
        f"Ingest request received with {len(files)} file(s), force_rebuild={force_rebuild}"
    )

    # Save uploaded files to PDFS_DIR
    os.makedirs(config.PDFS_DIR, exist_ok=True)
    saved_paths = []
    for f in files:
        dest = os.path.join(config.PDFS_DIR, f.filename)
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        saved_paths.append(dest)

    if force_rebuild:
        logger.info("Force rebuild requested, resetting store...")
        reset_store()

    try:
        # Process PDFs in background thread to avoid blocking event loop
        chunks = await run_in_threadpool(ingest_pdfs, config.PDFS_DIR)
        logger.info(f"PDF ingestion completed:\n" f"  chunks = {len(chunks)}")

        await run_in_threadpool(rag.build_index, chunks)
        num_files = len({c["source_file"] for c in chunks})
        logger.info(
            f"Index build completed:\n"
            f"  files = {num_files}\n"
            f"  total_chunks = {len(chunks)}"
        )

        stats = store.stats()
        logger.info(f"Ingestion finished:\n" f"  vectors = {stats['vectors']}")

        return IngestResponse(
            files_processed=len({c["source_file"] for c in chunks}),
            chunks_added=len(chunks),
            vectors=stats["vectors"],
            message="Ingestion complete",
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Query the RAG pipeline with a question."""
    top_k = req.top_k if req.top_k is not None else config.TOP_K_DEFAULT
    max_tokens = req.max_output_tokens if req.max_output_tokens is not None else 512

    logger.info(
        f"Query request received:\n"
        f"  question = {req.question}\n"
        f"  top_k = {top_k}\n"
        f"  max_tokens = {max_tokens}"
    )

    try:
        result = await run_in_threadpool(
            rag.answer, req.question, top_k=top_k, max_output_tokens=max_tokens
        )
        logger.info(
            f"Query answered:\n"
            f"  top_k = {top_k}\n"
            f"  citations_count = {len(result['citations'])}"
        )

        return QueryResponse(
            answer=result["answer"],
            citations=result["citations"],
            used_top_k=top_k,
            prompt=result.get("prompt"),
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query failed")
