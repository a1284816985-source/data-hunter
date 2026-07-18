"""
平台账号管理 API — 一键登录 + Cookie 检测
"""
import json
import threading
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Union
from database import get_db
from models import PlatformAccount
import httpx

router = APIRouter()

# 登录任务状态（内存中）
_login_tasks: dict = {}


class AccountUpdate(BaseModel):
    cookies: Optional[Union[dict, list]] = None
    account_name: Optional[str] = None


@router.get("/", summary="获取所有平台账号")
async def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(PlatformAccount).all()
    return [
        {
            "id": a.id, "platform": a.platform, "account_name": a.account_name,
            "status": a.status, "has_cookies": bool(a.cookies),
            "last_verified": str(a.last_verified) if a.last_verified else None,
            "updated_at": str(a.updated_at),
            "logging_in": a.platform in _login_tasks,
        }
        for a in accounts
    ]


@router.post("/{platform}/login", summary="一键登录（打开浏览器窗口）")
async def login_platform(platform: str, db: Session = Depends(get_db)):
    """打开可见浏览器，用户扫码登录后自动捕获 Cookie"""
    valid_platforms = ["xiaohongshu", "taobao", "douyin", "meituan", "amazon"]
    if platform not in valid_platforms:
        raise HTTPException(400, f"不支持的平台: {platform}")

    if platform in _login_tasks:
        raise HTTPException(400, "该平台正在登录中，请先完成或取消")

    # 在后台线程运行登录流程
    _login_tasks[platform] = "pending"

    def _run_login():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from services.platform_login import do_login
            result = loop.run_until_complete(do_login(platform))

            if result["success"]:
                # 保存 Cookie 到数据库
                sync_db = next(get_db())
                try:
                    account = sync_db.query(PlatformAccount).filter(
                        PlatformAccount.platform == platform
                    ).first()
                    cookies_json = json.dumps(result["cookies"])
                    if account:
                        account.cookies = result["cookies"]
                        account.status = "active"
                        account.last_verified = datetime.now()
                    else:
                        account = PlatformAccount(
                            platform=platform,
                            account_name=platform,
                            cookies=result["cookies"],
                            status="active",
                            last_verified=datetime.now(),
                        )
                        sync_db.add(account)
                    sync_db.commit()
                finally:
                    sync_db.close()

            _login_tasks[platform] = "done" if result["success"] else "failed"
        except Exception as e:
            _login_tasks[platform] = f"error: {e}"
        finally:
            loop.close()

    threading.Thread(target=_run_login, daemon=True).start()

    return {"message": "浏览器已打开，请在窗口中扫码登录", "platform": platform}


@router.get("/{platform}/login-status", summary="查询登录状态")
async def login_status(platform: str):
    return {"platform": platform, "status": _login_tasks.get(platform, "idle")}


@router.post("/{platform}/verify", summary="检测 Cookie 是否有效")
async def verify_cookies(platform: str, db: Session = Depends(get_db)):
    """通过访问平台页面检测 Cookie 是否仍有效"""
    account = db.query(PlatformAccount).filter(
        PlatformAccount.platform == platform
    ).first()
    if not account or not account.cookies:
        return {"valid": False, "reason": "无 Cookie"}

    # 各平台检测 URL 和有效标志
    checks = {
        "xiaohongshu": ("https://www.xiaohongshu.com", ["创作中心", "发布"]),
        "taobao": ("https://www.taobao.com", ["我的淘宝", "购物车"]),
        "douyin": ("https://www.douyin.com", ["投稿", "消息"]),
        "meituan": ("https://www.meituan.com", ["我的", "订单"]),
        "amazon": ("https://www.amazon.com", ["Hello", "Account"]),
    }

    check = checks.get(platform)
    if not check:
        return {"valid": False, "reason": "不支持的平台"}

    url, indicators = check
    cookies = account.cookies
    if isinstance(cookies, str):
        cookies = json.loads(cookies)

    # 构造 Cookie header
    cookie_str = "; ".join(
        f"{c['name']}={c['value']}" for c in cookies[:30]
        if isinstance(c, dict)
    )

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Cookie": cookie_str,
                }
            )
            text = resp.text[:3000]
            hits = sum(1 for ind in indicators if ind in text)
            valid = hits >= 2

            # 更新状态
            account.status = "active" if valid else "expired"
            account.last_verified = datetime.now()
            db.commit()

            return {
                "valid": valid,
                "status": account.status,
                "indicators_found": hits,
                "checked_at": str(account.last_verified),
            }
    except Exception as e:
        account.status = "error"
        account.last_verified = datetime.now()
        db.commit()
        return {"valid": False, "reason": str(e)}


@router.post("/verify-all", summary="检测所有平台 Cookie 有效性")
async def verify_all(db: Session = Depends(get_db)):
    accounts = db.query(PlatformAccount).filter(
        PlatformAccount.cookies.isnot(None)
    ).all()

    results = {}
    for acc in accounts:
        try:
            result = await verify_cookies(acc.platform, db)
            results[acc.platform] = result["valid"]
        except Exception:
            results[acc.platform] = False

    return {"results": results, "checked_at": str(datetime.now())}


@router.post("/{platform}", summary="添加/更新平台账号")
async def upsert_account(
    platform: str,
    req: AccountUpdate,
    db: Session = Depends(get_db),
):
    account = db.query(PlatformAccount).filter(
        PlatformAccount.platform == platform
    ).first()

    if account:
        if req.cookies is not None:
            account.cookies = req.cookies
        if req.account_name is not None:
            account.account_name = req.account_name
        account.status = "active"
    else:
        account = PlatformAccount(
            platform=platform,
            cookies=req.cookies or {},
            account_name=req.account_name or platform,
        )
        db.add(account)

    db.commit()
    db.refresh(account)
    return {"message": "保存成功", "id": account.id}


@router.delete("/{account_id}", summary="删除平台账号")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(PlatformAccount).filter(PlatformAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "账号不存在")
    db.delete(account)
    db.commit()
    return {"message": "已删除"}
