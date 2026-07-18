"""
小红书爬虫 — 已验证版本（Cookie + Stealth + 反爬对抗）
"""
import asyncio
import json
import sqlite3
from typing import Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


def _load_cookies_for_playwright(platform: str = "xiaohongshu") -> Optional[list]:
    """从 data_hunter 数据库加载 Playwright 格式的 Cookie"""
    try:
        db = sqlite3.connect('/Users/l./data_hunter/backend/data_hunter.db')
        row = db.execute(
            "SELECT cookies FROM platform_accounts WHERE platform=? AND status='active'",
            (platform,)
        ).fetchone()
        db.close()
        if not row or not row[0]:
            return None
        raw = json.loads(row[0])
        pw_cookies = []
        if isinstance(raw, dict):
            for name, value in raw.items():
                pw_cookies.append({
                    "name": name, "value": str(value),
                    "domain": ".xiaohongshu.com", "path": "/",
                })
        elif isinstance(raw, list):
            pw_cookies = raw
        return pw_cookies
    except Exception:
        return None


class XiaohongshuScraper:
    """小红书爬虫 — 兼容 scheduler 接口"""

    def __init__(self, cookies: Optional[dict] = None):
        self._cookies = cookies
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def supports_article(self) -> bool:
        return True

    def supports_group_buy(self) -> bool:
        return False

    async def launch(self, headless: bool = True) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 加载 Cookie
        db_cookies = _load_cookies_for_playwright()
        if db_cookies:
            await self._context.add_cookies(db_cookies)

        self._page = await self._context.new_page()

        # Stealth 反检测
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        """搜索小红书图文笔记"""
        results = []
        try:
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            # 滚动加载更多
            for _ in range(min(3, count // 10 + 1)):
                await self._page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(2)

            # 提取笔记
            items = await self._page.query_selector_all("section.note-item")
            if not items:
                items = await self._page.query_selector_all(".note-item")

            for item in items:
                if len(results) >= count:
                    break
                try:
                    text = await item.inner_text()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    title = lines[0] if len(lines) > 0 else ""
                    author = lines[1] if len(lines) > 1 else ""

                    likes = ""
                    for line in lines:
                        cleaned = line.replace("万", "").replace(",", "").replace(".", "")
                        if cleaned.isdigit() and len(cleaned) >= 2:
                            likes = line
                            break

                    img_el = await item.query_selector("img")
                    cover_image = await img_el.get_attribute("src") if img_el else ""

                    # 优先取带 xsec_token 的链接（/search_result/ 而非 /explore/）
                    link_els = await item.query_selector_all("a[href]")
                    source_url = ""
                    for link_el in link_els:
                        href = await link_el.get_attribute("href") or ""
                        if href.startswith("/"):
                            full = f"https://www.xiaohongshu.com{href}"
                        else:
                            full = href
                        if "xsec_token" in full:
                            source_url = full
                            break
                        if not source_url and "/explore/" not in href:
                            source_url = full
                    if not source_url and link_els:
                        href = await link_els[0].get_attribute("href") or ""
                        source_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href

                    results.append({
                        "title": title,
                        "author_name": author,
                        "likes": likes,
                        "cover_image": cover_image,
                        "source_url": source_url,
                        "content_text": "",
                        "comments_count": "",
                        "favorites": "",
                        "publish_time": "",
                        "tags": [],
                        "comments": [],
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[小红书] 图文搜索异常: {e}")
        return results

    async def search_products(self, keyword: str, count: int = 20) -> list:
        """搜索小红书商品"""
        results = []
        try:
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=goods"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)
            await self._page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

            selectors = [
                "[class*='goods'] [class*='card']",
                "[class*='product'] [class*='card']",
                "[class*='goods-item']",
            ]
            items = []
            for sel in selectors:
                items = await self._page.query_selector_all(sel)
                if items:
                    break

            for item in items:
                if len(results) >= count:
                    break
                try:
                    text = await item.inner_text()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    title = lines[0] if lines else ""
                    price = 0.0
                    sales = ""

                    for line in lines:
                        if "¥" in line or "￥" in line:
                            price_str = line.replace("¥", "").replace("￥", "").strip()
                            try:
                                price = float(price_str)
                            except Exception:
                                pass
                        if "已售" in line or "销量" in line:
                            sales = line

                    img_el = await item.query_selector("img")
                    main_image = await img_el.get_attribute("src") if img_el else ""

                    # 优先取带 xsec_token 的链接（/search_result/ 而非 /explore/）
                    link_els = await item.query_selector_all("a[href]")
                    source_url = ""
                    for link_el in link_els:
                        href = await link_el.get_attribute("href") or ""
                        if href.startswith("/"):
                            full = f"https://www.xiaohongshu.com{href}"
                        else:
                            full = href
                        if "xsec_token" in full:
                            source_url = full
                            break
                        if not source_url and "/explore/" not in href:
                            source_url = full
                    if not source_url and link_els:
                        href = await link_els[0].get_attribute("href") or ""
                        source_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href

                    results.append({
                        "title": title,
                        "price": price,
                        "sales": sales,
                        "shop_name": "小红书商家",
                        "main_image": main_image,
                        "source_url": source_url,
                        "original_price": None,
                        "detail_images": [],
                        "specs": None,
                        "rating": None,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[小红书] 商品搜索异常: {e}")
        return results

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        return []
