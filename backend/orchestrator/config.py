import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Level server URLs
LEVEL2_URL = os.getenv("LEVEL2_URL", "http://localhost:8002")
LEVEL1_URL = os.getenv("LEVEL1_URL", "http://localhost:8001")
LEVEL0_URL = os.getenv("LEVEL0_URL", "http://localhost:8000")

# Compression ratios
LEVEL2_TO_1_RATIO = float(os.getenv("LEVEL2_TO_1_RATIO", 0.2))  # 1/5
LEVEL1_TO_0_RATIO = float(os.getenv("LEVEL1_TO_0_RATIO", 0.5))  # 1/2

# Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite")

# Temporary PDF storage
PDFS_DIR = os.path.join(BASE_DIR, "pdfs")
os.makedirs(PDFS_DIR, exist_ok=True)
