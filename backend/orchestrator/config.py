import os
from common.config import settings

BASE_DIR = os.path.dirname(__file__)

# Level server URLs
LEVEL2_URL = settings.LEVEL2_URL
LEVEL1_URL = settings.LEVEL1_URL
LEVEL0_URL = settings.LEVEL0_URL

# Compression ratios
LEVEL2_TO_1_RATIO = float(settings.LEVEL2_TO_1_RATIO)
LEVEL1_TO_0_RATIO = float(settings.LEVEL1_TO_0_RATIO)

# Gemini API
GOOGLE_API_KEY = settings.GOOGLE_API_KEY
GEMINI_MODEL = settings.GEMINI_MODEL

# Temporary PDF storage
PDFS_DIR = os.path.join(BASE_DIR, "pdfs")
os.makedirs(PDFS_DIR, exist_ok=True)
