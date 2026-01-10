from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from common.logging import setup_logging
from fastapi.concurrency import run_in_threadpool
import os
import shutil
from typing import List

import level2.config as config
from common.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    HealthResponse,
)
from level2.vectorstore import FaissStore
from level2.ingest import ingest_pdfs
from level2.rag import RAGPipeline, EmbeddingsClient, GeminiClient

# Setup Logging
logger = setup_logging(__name__)

# App Init
app = FastAPI(
    title="Jharkhand Policies RAG Backend (Level 2)",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
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
        logger.info("Store reset successfully.")
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

    return HealthResponse(
        status="ok",
        stats=StatsResponse(
            vectors=stats.get("vectors", 0),
            files_indexed=stats.get("files_indexed", 0),
            index_path=stats.get("index_path"),
            metadata_path=stats.get("metadata_path"),
            index_exists=stats.get("index_exists"),
            last_modified=stats.get("last_modified"),
        ),
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: List[UploadFile] = File(...), force_rebuild: bool = False):
    """Ingest PDF files into the vector store."""
    logger.info(f"Ingest request: {len(files)} files, force={force_rebuild}")

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
        logger.info(f"Ingested {len(chunks)} chunks")

        await run_in_threadpool(rag.build_index, chunks)
        logger.info("Index built successfully: ", chunks)

        stats = store.stats()
        logger.info("Ingestion complete: ", stats)

        return IngestResponse(
            files_processed=len(files),
            chunks_added=len(chunks),
            vectors=stats.get("vectors", 0),
            message="Ingestion complete",
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Query the RAG pipeline with a question."""
    top_k = req.top_k or config.TOP_K_DEFAULT
    max_tokens = req.max_output_tokens or 512
    logger.info(
        f"Query request: {req.question}, top_k={top_k}, max_tokens={max_tokens}"
    )

    try:
        result = await run_in_threadpool(
            rag.answer, req.question, top_k=top_k, max_output_tokens=max_tokens
        )
        logger.info(f"Query result: {result}")
        
        return QueryResponse(
            answer=result["answer"],
            citations=result["citations"],
            used_top_k=top_k,
            prompt=result.get("prompt"),
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query failed")
