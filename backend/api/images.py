"""图片服务 — 提供本地存储的图片"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

router = APIRouter()


@router.get("/images/{task_id}/{filename}")
async def serve_image(task_id: int, filename: str):
    path = os.path.join(IMAGES_DIR, str(task_id), filename)
    if not os.path.exists(path):
        raise HTTPException(404, "图片不存在")
    return FileResponse(path)
