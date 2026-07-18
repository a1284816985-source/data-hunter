"""图片代理服务 — 后端中转绕过防盗链，不落盘"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import unquote

router = APIRouter()

# 各平台需要的 Referer
PLATFORM_REFERERS = {
    "xhscdn.com": "https://www.xiaohongshu.com/",
    "xiaohongshu.com": "https://www.xiaohongshu.com/",
    "douyin.com": "https://www.douyin.com/",
    "douyinstatic.com": "https://www.douyin.com/",
    "taobao.com": "https://www.taobao.com/",
    "alicdn.com": "https://www.taobao.com/",
    "tbcdn.com": "https://www.taobao.com/",
    "meituan.com": "https://www.meituan.com/",
    "amazon.com": "https://www.amazon.com/",
    "media-amazon.com": "https://www.amazon.com/",
}


def _guess_referer(url: str) -> str:
    for domain, ref in PLATFORM_REFERERS.items():
        if domain in url:
            return ref
    return ""


async def _fetch_image(url: str):
    """流式获取远程图片"""
    referer = _guess_referer(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(404, "图片获取失败")
        return resp.content, resp.headers.get("content-type", "image/jpeg")


@router.get("/image-proxy")
async def proxy_image(url: str = Query(..., description="原始图片 URL")):
    """代理远程图片，绕过防盗链"""
    decoded = unquote(url)
    if not decoded.startswith("http"):
        raise HTTPException(400, "仅支持 http/https URL")

    try:
        content, content_type = await _fetch_image(decoded)
        return StreamingResponse(
            iter([content]),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"代理失败: {e}")
