import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Project Info
    PROJECT_NAME: str = "Jharkhand Government Policies Chatbot"
    VERSION: str = "1.0.0"
    
    # Server Config
    PYTHON_ENV: str = os.getenv("PYTHON_ENV")
    HOST: str = os.getenv("HOST")
    ORCHESTRATOR_PORT: int = int(os.getenv("ORCHESTRATOR_PORT"))
    LEVEL0_PORT: int = int(os.getenv("LEVEL0_PORT"))
    LEVEL1_PORT: int = int(os.getenv("LEVEL1_PORT"))
    LEVEL2_PORT: int = int(os.getenv("LEVEL2_PORT"))
    
    # URLs
    ORCHESTRATOR_URL: str = f"{PYTHON_ENV}://{HOST}:{ORCHESTRATOR_PORT}"
    LEVEL0_URL: str = f"{PYTHON_ENV}://{HOST}:{LEVEL0_PORT}"
    LEVEL1_URL: str = f"{PYTHON_ENV}://{HOST}:{LEVEL1_PORT}"
    LEVEL2_URL: str = f"{PYTHON_ENV}://{HOST}:{LEVEL2_PORT}"
    
    ALLOWED_ORIGINS: list = ["*"]
    
    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL")

    # RAG Config
    MAX_CHUNKS_PER_FILE: int = int(os.getenv("MAX_CHUNKS_PER_FILE"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP"))
    TOP_K_DEFAULT: int = int(os.getenv("TOP_K_DEFAULT"))
    
    # Compression ratios
    LEVEL2_TO_1_RATIO: float = float(os.getenv("LEVEL2_TO_1_RATIO", 0.2))  # 1/5
    LEVEL1_TO_0_RATIO: float = float(os.getenv("LEVEL1_TO_0_RATIO", 0.5))  # 1/2
    
    # Auth & Database
    MONGO_URI: str = os.getenv("MONGO_URI")
    DB_NAME: str = os.getenv("DB_NAME")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

settings = Settings()