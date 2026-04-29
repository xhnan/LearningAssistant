from datetime import datetime, timezone
import hmac

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from sqlalchemy import select


from core.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    create_access_token,
    hash_password,
    is_valid_bcrypt_password,
    verify_password,
)
router = APIRouter()
from db.session import get_db


def normalize_login_identifier(value: str) -> str:
    return value.strip()


def is_bcrypt_hash(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$"))


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


@router.post("/api/auth/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    username = normalize_login_identifier(req.username)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required",
        )

    if not is_valid_bcrypt_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password cannot be longer than {BCRYPT_MAX_PASSWORD_BYTES} bytes",
        )

    # Check if username already taken
    result = await db.execute(
        select(User).where(User.username == username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    user = User(
        username=username,
        email=f"{username}@placeholder.local",
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.commit()

    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/api/auth/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    username = normalize_login_identifier(req.username)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not is_valid_bcrypt_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()

    password_matches = bool(user and verify_password(req.password, user.password_hash))

    if user and not password_matches and not is_bcrypt_hash(user.password_hash):
        password_matches = hmac.compare_digest(req.password, user.password_hash)
        if password_matches:
            user.password_hash = hash_password(req.password)

    if not user or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
    )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
