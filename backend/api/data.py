"""
数据浏览 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import ScrapedItem, Task

router = APIRouter()


@router.get("/tasks/{task_id}/items", summary="获取任务采集结果")
async def get_task_items(
    task_id: int,
    platform: Optional[str] = None,
    item_type: Optional[str] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """获取某任务的采集数据，支持筛选和排序"""
    query = db.query(ScrapedItem).filter(ScrapedItem.task_id == task_id)

    if platform:
        query = query.filter(ScrapedItem.platform == platform)
    if item_type:
        query = query.filter(ScrapedItem.item_type == item_type)

    # 排序
    if sort_by == "price_asc":
        query = query.order_by(ScrapedItem.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(ScrapedItem.price.desc())
    elif sort_by == "likes":
        query = query.order_by(ScrapedItem.likes.desc())
    elif sort_by == "sales":
        query = query.order_by(ScrapedItem.sales.desc())
    else:
        query = query.order_by(ScrapedItem.id.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_item_to_dict(item) for item in items],
    }


@router.get("/tasks/{task_id}/stats", summary="获取任务统计概览")
async def get_task_stats(task_id: int, db: Session = Depends(get_db)):
    """按平台统计采集结果"""
    items = db.query(ScrapedItem).filter(ScrapedItem.task_id == task_id).all()

    platforms = {}
    total_price = 0
    price_count = 0

    for item in items:
        p = item.platform
        if p not in platforms:
            platforms[p] = {"count": 0, "platform": p}
        platforms[p]["count"] += 1

        if item.price and item.price > 0:
            total_price += item.price
            price_count += 1

    return {
        "total_items": len(items),
        "by_platform": list(platforms.values()),
        "avg_price": round(total_price / price_count, 2) if price_count > 0 else 0,
    }


@router.get("/items/{item_id}", summary="获取单条数据详情")
async def get_item_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ScrapedItem).filter(ScrapedItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "数据不存在")
    return _item_to_dict(item)


@router.post("/tasks/{task_id}/export", summary="导出为 Excel")
async def export_excel(task_id: int, db: Session = Depends(get_db)):
    """生成 Excel 文件并返回下载 URL"""
    import openpyxl
    from io import BytesIO
    import os

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    items = db.query(ScrapedItem).filter(ScrapedItem.task_id == task_id).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "采集数据"

    if task.task_type == "product_group":
        headers = ["平台", "标题", "价格", "原价", "销量", "店铺", "评分", "链接"]
        ws.append(headers)
        for item in items:
            ws.append([
                item.platform, item.title, item.price, item.original_price,
                item.sales, item.shop_name, item.rating, item.source_url,
            ])
    else:
        headers = ["平台", "标题", "文案", "点赞", "评论", "收藏", "作者", "发布时间", "链接"]
        ws.append(headers)
        for item in items:
            ws.append([
                item.platform, item.title, item.content_text,
                item.likes, item.comments_count, item.favorites,
                item.author_name, item.publish_time, item.source_url,
            ])

    # 保存文件
    export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"task_{task_id}_{task.keyword}.xlsx"
    filepath = os.path.join(export_dir, filename)
    wb.save(filepath)

    return {"filename": filename, "download_url": f"/api/data/download/{filename}"}


def _item_to_dict(item: ScrapedItem) -> dict:
    return {
        "id": item.id,
        "task_id": item.task_id,
        "platform": item.platform,
        "item_type": item.item_type,
        "title": item.title,
        "price": item.price,
        "original_price": item.original_price,
        "sales": item.sales,
        "main_image": item.main_image,
        "detail_images": item.detail_images,
        "shop_name": item.shop_name,
        "specs": item.specs,
        "rating": item.rating,
        "content_text": item.content_text,
        "cover_image": item.cover_image,
        "likes": item.likes,
        "comments_count": item.comments_count,
        "favorites": item.favorites,
        "publish_time": item.publish_time,
        "author_name": item.author_name,
        "tags": item.tags,
        "comments": item.comments,
        "source_url": item.source_url,
        "created_at": str(item.created_at) if item.created_at else None,
    }
