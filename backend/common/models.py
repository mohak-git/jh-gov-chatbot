from pydantic import BaseModel, EmailStr, Field, BeforeValidator
from typing import Optional, Annotated

# Helper to handle ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str
    email: EmailStr
    password: str
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
