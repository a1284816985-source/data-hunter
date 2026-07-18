"""
平台账号管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Union
from database import get_db
from models import PlatformAccount

router = APIRouter()


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
        }
        for a in accounts
    ]


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
