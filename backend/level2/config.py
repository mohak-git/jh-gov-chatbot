import os
from common.config import settings

# Directories
INDEX_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "index"))
PDFS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "pdfs"))

# Models
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
GEMINI_MODEL = settings.GEMINI_MODEL

# Chunking
CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP

# Retrieval
TOP_K_DEFAULT = settings.TOP_K_DEFAULT

# API Keys
GOOGLE_API_KEY = settings.GOOGLE_API_KEY
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS

# Filenames for persistence
INDEX_FILE = os.path.join(INDEX_DIR, "jharkhand_faiss.index")
META_FILE = os.path.join(INDEX_DIR, "jharkhand_metadata.json")

os.makedirs(INDEX_DIR, exist_ok=True)
