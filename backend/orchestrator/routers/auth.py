from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from common.db import get_database
from common.auth import get_password_hash, verify_password, create_access_token
from common.models import UserDB, UserCreate
from common.schemas import Token, UserResponse
from common.logging import setup_logging

# Setup logging
logger = setup_logging(__name__)

# Initialize router
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    db = get_database()
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    password = get_password_hash(user.password)
    user_in_db = UserDB(
        username=user.username,
        email=user.email,
        password=password
    )
    
    new_user = await db.users.insert_one(user_in_db.model_dump(by_alias=True, exclude=["id"]))
    created_user = await db.users.find_one({"_id": new_user.inserted_id})
    
    logger.info(f"User {created_user['username']} registered successfully")
    return UserDB(**created_user)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_database()
    user = await db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"username": user["username"], "email": user["email"]})
    logger.info(f"User {user['username']} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}
