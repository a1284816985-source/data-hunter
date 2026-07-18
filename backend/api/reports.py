"""
AI 分析报告 + 爆款仿写 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Task, ScrapedItem, Report

router = APIRouter()


# ── Schema ──
class GenerateReportRequest(BaseModel):
    task_id: int


class RewriteRequest(BaseModel):
    item_id: int
    own_product_topic: str  # 用户自己的产品/主题
    keep_structure: bool = True
    keep_tone: bool = True
    keep_hook: bool = True


# ── 路由 ──
@router.post("/generate", summary="生成 AI 分析报告")
async def generate_report(req: GenerateReportRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != "completed":
        raise HTTPException(400, "任务尚未完成，无法生成报告")

    items = db.query(ScrapedItem).filter(ScrapedItem.task_id == req.task_id).all()
    if not items:
        raise HTTPException(400, "无采集数据，无法生成报告")

    # 调用 AI 生成报告
    from services.ai_service import generate_analysis_report
    report_content = await generate_analysis_report(task, items)

    # 保存报告
    report = Report(
        task_id=task.id,
        report_type=task.task_type,
        title=f"{task.keyword} - 竞调分析报告",
        content=report_content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "task_id": report.task_id,
        "report_type": report.report_type,
        "title": report.title,
        "content": report.content,
        "created_at": str(report.created_at),
    }


@router.get("/list", summary="获取报告列表")
async def list_reports(task_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Report)
    if task_id:
        query = query.filter(Report.task_id == task_id)
    reports = query.order_by(Report.created_at.desc()).all()
    return [
        {
            "id": r.id, "task_id": r.task_id, "report_type": r.report_type,
            "title": r.title, "created_at": str(r.created_at),
        }
        for r in reports
    ]


@router.get("/{report_id}", summary="获取报告详情")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    return {
        "id": report.id, "task_id": report.task_id,
        "report_type": report.report_type, "title": report.title,
        "content": report.content, "created_at": str(report.created_at),
    }


@router.delete("/{report_id}", summary="删除报告")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    db.delete(report)
    db.commit()
    return {"message": "已删除"}


@router.post("/rewrite", summary="爆款仿写")
async def rewrite_viral(req: RewriteRequest, db: Session = Depends(get_db)):
    """基于采集到的爆款内容，AI 仿写新文案"""
    item = db.query(ScrapedItem).filter(ScrapedItem.id == req.item_id).first()
    if not item:
        raise HTTPException(404, "内容不存在")

    from services.ai_service import rewrite_viral_content

    result = await rewrite_viral_content(
        original_title=item.title or "",
        original_content=item.content_text or "",
        original_tags=item.tags or [],
        own_topic=req.own_product_topic,
        keep_structure=req.keep_structure,
        keep_tone=req.keep_tone,
        keep_hook=req.keep_hook,
    )

    return {
        "item_id": item.id,
        "original_title": item.title,
        **result,
    }
