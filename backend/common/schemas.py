from typing import List, Optional
from pydantic import BaseModel, EmailStr


# Authentication Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# RAG Schemas
class IngestResponse(BaseModel):
    files_processed: int
    chunks_added: int
    vectors: int
    message: str


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    max_output_tokens: Optional[int] = None


class Citation(BaseModel):
    source_file: str
    page_start: int
    page_end: int
    score: float
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    used_top_k: int
    prompt: Optional[str] = None


# Health Schemas
class StatsResponse(BaseModel):
    vectors: int
    files_indexed: Optional[int] = None
    index_path: Optional[str] = None
    metadata_path: Optional[str] = None
    index_exists: Optional[bool] = None
    last_modified: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    stats: Optional[StatsResponse] = None
