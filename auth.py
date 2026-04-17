import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_db
from models import UserLogin, UserPublic, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

JWT_SECRET = os.environ.get("JWT_SECRET", "lingodeck-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7


def _make_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db=Depends(get_db),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("user_id")
    async with db.execute("SELECT id, email, display_name, created_at FROM users WHERE id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


@router.post("/register")
async def register(body: UserRegister, db=Depends(get_db)):
    email = body.email.lower().strip()
    async with db.execute("SELECT id FROM users WHERE email = ?", (email,)) as cur:
        existing = await cur.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    async with db.execute(
        "INSERT INTO users (email, display_name, password_hash) VALUES (?, ?, ?)",
        (email, body.name, pw_hash),
    ) as cur:
        user_id = cur.lastrowid
    await db.commit()

    token = _make_token(user_id, email)
    return {"data": {"token": token}, "error": None}


@router.post("/login")
async def login(body: UserLogin, db=Depends(get_db)):
    email = body.email.lower().strip()
    async with db.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _make_token(row["id"], row["email"])
    return {"data": {"token": token}, "error": None}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "data": UserPublic(
            id=current_user["id"],
            email=current_user["email"],
            display_name=current_user["display_name"],
            created_at=current_user["created_at"],
        ).model_dump(),
        "error": None,
    }
