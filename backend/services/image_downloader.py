"""图片下载工具 — 爬虫抓取时同步下载到本地"""
import os
import httpx
import hashlib

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def image_path(task_id: int, item_id: int, ext: str = "jpg") -> str:
    """返回本地图片路径"""
    subdir = os.path.join(IMAGES_DIR, str(task_id))
    ensure_dir(subdir)
    return os.path.join(subdir, f"{item_id}.{ext}")


def local_url(task_id: int, item_id: int) -> str:
    """返回前端可用的本地图片 URL，自动探测扩展名"""
    subdir = os.path.join(IMAGES_DIR, str(task_id))
    ensure_dir(subdir)
    for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
        if os.path.exists(os.path.join(subdir, f"{item_id}.{ext}")):
            return f"/api/images/{task_id}/{item_id}.{ext}"
    return ""


def download_image(url: str, task_id: int, item_id: int) -> str:
    """下载图片到本地，返回本地 URL。失败返回空字符串"""
    if not url:
        return ""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        if resp.status_code != 200:
            return ""

        content_type = resp.headers.get("content-type", "")
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"

        path = image_path(task_id, item_id, ext)
        with open(path, "wb") as f:
            f.write(resp.content)
        return local_url(task_id, item_id)
    except Exception:
        return ""
