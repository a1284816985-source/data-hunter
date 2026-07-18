"""
采集任务 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import Task, TaskStatus, TaskType, Platform
from scrapers.scheduler import scheduler

router = APIRouter()


# ── Schema ──
class TaskCreate(BaseModel):
    keyword: str
    platforms: List[str]  # ["taobao", "xiaohongshu", ...]
    task_type: str  # "product_group" | "article_video"
    count_per_platform: int = 20


class TaskOut(BaseModel):
    id: int
    keyword: str
    platforms: list
    task_type: str
    count_per_platform: int
    status: str
    total_items: int
    error_message: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


# ── 平台类型映射 ──
# 商品/团购模式支持的平台
PRODUCT_PLATFORMS = [
    Platform.TAOBAO.value,
    Platform.XIAOHONGSHU.value,
    Platform.DOUYIN.value,
    Platform.MEITUAN.value,
    Platform.AMAZON.value,
]
# 图文/视频模式支持的平台
ARTICLE_PLATFORMS = [
    Platform.XIAOHONGSHU.value,
    Platform.DOUYIN.value,
]


@router.get("/platforms", summary="获取可用平台列表")
async def get_platforms(task_type: Optional[str] = None):
    """根据任务类型返回可选平台"""
    if task_type == TaskType.ARTICLE_VIDEO.value:
        platforms = ARTICLE_PLATFORMS
    else:
        platforms = PRODUCT_PLATFORMS
    return {
        "platforms": [
            {"value": p, "label": _platform_label(p)}
            for p in platforms
        ]
    }


@router.post("/", response_model=TaskOut, summary="创建采集任务")
async def create_task(req: TaskCreate, db: Session = Depends(get_db)):
    # 验证平台
    valid_platforms = [p.value for p in Platform]
    for p in req.platforms:
        if p not in valid_platforms:
            raise HTTPException(400, f"无效平台: {p}")

    # 验证类型
    if req.task_type == TaskType.ARTICLE_VIDEO.value:
        for p in req.platforms:
            if p not in ARTICLE_PLATFORMS:
                raise HTTPException(400, f"平台 {_platform_label(p)} 不支持图文/视频采集")

    task = Task(
        keyword=req.keyword,
        platforms=req.platforms,
        task_type=req.task_type,
        count_per_platform=req.count_per_platform,
        status=TaskStatus.QUEUED.value,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 确保调度器在运行
    scheduler.start()

    return task


@router.get("/", response_model=List[TaskOut], summary="获取任务列表")
async def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return tasks


@router.get("/{task_id}", response_model=TaskOut, summary="获取任务详情")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == TaskStatus.RUNNING.value:
        raise HTTPException(400, "正在运行的任务无法取消")
    task.status = TaskStatus.CANCELLED.value
    db.commit()
    return {"message": "已取消"}


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == TaskStatus.RUNNING.value:
        raise HTTPException(400, "任务正在运行中，无法删除")
    # 删除关联数据
    from models import ScrapedItem, Report
    db.query(ScrapedItem).filter(ScrapedItem.task_id == task_id).delete()
    db.query(Report).filter(Report.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": "已删除"}


def _platform_label(p: str) -> str:
    labels = {
        "taobao": "淘宝", "xiaohongshu": "小红书",
        "douyin": "抖音", "meituan": "美团", "amazon": "亚马逊",
    }
    return labels.get(p, p)
