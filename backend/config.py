import os
from dotenv import load_dotenv

load_dotenv()

# Directories
INDEX_DIR = os.getenv("INDEX_DIR", os.path.normpath(os.path.join(os.getcwd(), "experiment")))
PDFS_DIR = os.getenv("PDFS_DIR", os.path.normpath(os.path.join(os.getcwd(), "backend", "pdfs")))

# Models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval
TOP_K_DEFAULT = int(os.getenv("TOP_K", "6"))

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Filenames for persistence
INDEX_FILE = os.path.join(INDEX_DIR, "jharkhand_faiss.index")
META_FILE = os.path.join(INDEX_DIR, "jharkhand_metadata.json")

os.makedirs(INDEX_DIR, exist_ok=True)
