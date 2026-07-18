"""
简易登录 API（内部使用，无需复杂权限）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import secrets
from database import get_db
from models import User

router = APIRouter()

# 简单的内存 session（生产环境应改用 Redis）
_sessions: dict = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_session(token: str) -> bool:
    return token in _sessions


@router.post("/register", summary="注册（首次使用）")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    return {"message": "注册成功"}


@router.post("/login", summary="登录")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password_hash != hash_password(req.password):
        raise HTTPException(401, "用户名或密码错误")

    token = secrets.token_hex(32)
    _sessions[token] = user.id
    return {"token": token, "username": user.username, "role": user.role}


@router.post("/logout", summary="登出")
async def logout(token: str = ""):
    _sessions.pop(token, None)
    return {"message": "已登出"}


@router.get("/me", summary="当前用户")
async def me(token: str = ""):
    user_id = _sessions.get(token)
    if not user_id:
        raise HTTPException(401, "未登录")
    return {"user_id": user_id}
