import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.schemas import IngestRequest, IngestResponse, QueryRequest, QueryResponse, StatsResponse, HealthResponse
from backend.vectorstore import FaissStore
from backend.ingest import ingest_pdfs
from backend.rag import RAGPipeline, EmbeddingsClient, GeminiClient

app = FastAPI(title="Jharkhand Policies RAG Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = FaissStore(config.INDEX_FILE, config.META_FILE)
store.load()

embedder = EmbeddingsClient(config.EMBEDDING_MODEL, config.GOOGLE_API_KEY)
llm = GeminiClient(config.GEMINI_MODEL, config.GOOGLE_API_KEY)
rag = RAGPipeline(store, embedder, llm)


@app.get("/health", response_model=HealthResponse)
async def health():
    st = store.stats()
    return HealthResponse(status="ok", stats=StatsResponse(**st))


@app.get("/stats", response_model=StatsResponse)
async def stats():
    return StatsResponse(**store.stats())


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    if req.force_rebuild:
        # Reset index and metadata
        if os.path.exists(config.INDEX_FILE):
            try:
                os.remove(config.INDEX_FILE)
            except Exception:
                pass
        if os.path.exists(config.META_FILE):
            try:
                os.remove(config.META_FILE)
            except Exception:
                pass
        store.index = None
        store.id_to_meta = {}
        store._next_id = 0

    chunks = ingest_pdfs(config.PDFS_DIR)
    added = rag.build_index(chunks)
    st = store.stats()
    return IngestResponse(files_processed=len({c['source_file'] for c in chunks}), chunks_added=len(chunks), vectors=st["vectors"], message="Ingestion complete")


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    top_k = req.top_k or config.TOP_K_DEFAULT
    result = rag.answer(req.question, top_k=top_k, max_output_tokens=req.max_output_tokens or 512)
    return QueryResponse(answer=result["answer"], citations=result["citations"], used_top_k=top_k)


# For local dev: uvicorn backend.app:app --reload
