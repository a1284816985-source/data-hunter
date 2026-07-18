"""平台一键登录服务 — Playwright 可见窗口 + 自动捕获 Cookie"""
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# 各平台配置
PLATFORM_CONFIG = {
    "xiaohongshu": {
        "name": "小红书",
        "login_url": "https://www.xiaohongshu.com",
        "login_indicators": ["创作中心", "发布", "通知", "我"],  # 登录后页面会出现这些
    },
    "taobao": {
        "name": "淘宝",
        "login_url": "https://login.taobao.com/",
        "login_indicators": ["已买到的宝贝", "我的淘宝", "购物车"],
    },
    "douyin": {
        "name": "抖音",
        "login_url": "https://www.douyin.com/",
        "login_indicators": ["投稿", "消息", "我"],
    },
    "meituan": {
        "name": "美团",
        "login_url": "https://passport.meituan.com/account/login",
        "login_indicators": ["我的", "订单", "收藏"],
    },
    "amazon": {
        "name": "亚马逊",
        "login_url": "https://www.amazon.com/ap/signin",
        "login_indicators": ["Hello", "Account", "Orders"],
    },
}


def _cookies_to_db_format(cookies: list) -> list:
    """Playwright cookies → data_hunter 存储格式"""
    result = []
    for c in cookies:
        result.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
        })
    return result


async def do_login(platform: str) -> dict:
    """
    打开可见浏览器 → 用户手动登录 → 检测登录成功 → 捕获 Cookie
    返回 {"success": True, "cookies": [...]} 或 {"success": False, "error": "..."}
    """
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        return {"success": False, "error": f"不支持的平台: {platform}"}

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--no-sandbox"],
            )
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="zh-CN",
            )
            page = await ctx.new_page()

            # 对小红书/抖音/美团加 stealth
            if platform in ("xiaohongshu", "douyin", "meituan"):
                try:
                    stealth = Stealth()
                    await stealth.apply_stealth_async(page)
                except Exception:
                    pass

            print(f"[Login] 打开 {config['name']} 登录页: {config['login_url']}")
            await page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)

            # 等待用户登录（最多 120 秒）
            logged_in = False
            for _ in range(60):  # 60 × 2s = 120s
                await asyncio.sleep(2)
                try:
                    page_text = await page.evaluate(
                        "() => (document.body?.innerText || '')"
                    )
                    # 检测登录成功标志
                    hits = sum(1 for ind in config["login_indicators"] if ind in page_text)
                    if hits >= 2:
                        logged_in = True
                        break
                except Exception:
                    pass

            if not logged_in:
                # 超时，但仍尝试捕获 Cookie（可能用户已登录但指示符不同）
                print(f"[Login] 超时，尝试捕获当前 Cookie...")

            # 捕获 Cookie
            cookies = await ctx.cookies()
            await browser.close()

            if not cookies:
                return {"success": False, "error": "未捕获到任何 Cookie"}

            db_cookies = _cookies_to_db_format(cookies)
            print(f"[Login] ✅ 捕获 {len(db_cookies)} 个 Cookie")

            return {
                "success": True,
                "cookies": db_cookies,
                "count": len(db_cookies),
                "logged_in": logged_in,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
