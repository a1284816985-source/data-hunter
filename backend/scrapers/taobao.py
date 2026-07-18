"""
淘宝爬虫 v2 — 已验证 Cookie + 精准选择器
"""
import asyncio
import json
import sqlite3
from typing import Optional
from playwright.async_api import async_playwright


def _load_cookies(platform: str = "taobao") -> Optional[list]:
    try:
        db = sqlite3.connect('/Users/l./data_hunter/backend/data_hunter.db')
        row = db.execute(
            "SELECT cookies FROM platform_accounts WHERE platform=? AND status='active'",
            (platform,)
        ).fetchone()
        db.close()
        if not row or not row[0]:
            return None
        return json.loads(row[0])
    except Exception:
        return None


class TaobaoScraper:

    def __init__(self, cookies=None):
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None

    def supports_article(self) -> bool:
        return False

    def supports_group_buy(self) -> bool:
        return False

    async def launch(self, headless: bool = True) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self._ctx = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        cookies = _load_cookies()
        if cookies:
            await self._ctx.add_cookies(cookies)
        self._page = await self._ctx.new_page()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def search_products(self, keyword: str, count: int = 20) -> list:
        results = []
        try:
            url = f"https://s.taobao.com/search?q={keyword}"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)
            await self._page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(4)

            # Extract using product card containers
            data = await self._page.evaluate("""
                () => {
                    const results = [];
                    // Find product card containers: class contains mainPicAndDesc or similar
                    const allDivs = document.querySelectorAll('div');
                    const seen = new Set();

                    for (const div of allDivs) {
                        if (results.length >= 30) break;
                        const cls = (div.className || '');
                        const txt = (div.innerText || '').trim();

                        // Product cards: have ¥ AND 人付款, and are reasonable size
                        if (!txt.includes('¥') || !txt.includes('人付款')) continue;
                        if (txt.length < 30 || txt.length > 2000) continue;
                        // Avoid huge containers
                        if (div.children.length > 10) continue;

                        let parent = div;
                        for (let i = 0; i < 3 && parent; i++) {
                            const pCls = (parent.className || '');
                            if (pCls.includes('mainPicAndDesc') || pCls.includes('Card') || pCls.includes('double')) {
                                if (!seen.has(parent)) {
                                    seen.add(parent);
                                    const pTxt = (parent.innerText || '').trim();
                                    const lines = pTxt.split('\\n').filter(l => l.trim());
                                    const imgs = Array.from(parent.querySelectorAll('img')).slice(0, 2)
                                        .map(img => img.src || img.getAttribute('data-src') || '');
                                    results.push({
                                        text: pTxt.substring(0, 300),
                                        lines: lines.slice(0, 10),
                                        imgs: imgs.filter(i => i),
                                    });
                                }
                                break;
                            }
                            parent = parent.parentElement;
                        }
                    }
                    return results;
                }
            """)

            for item in data[:count]:
                text = item.get('text', '')
                lines = item.get('lines', [])
                imgs = item.get('imgs', [])

                # Parse fields from lines
                title = lines[0] if lines else ""
                price = 0.0
                sales = ""
                shop = ""

                for line in lines:
                    if ('¥' in line or '￥' in line) and '万' not in line:
                        cleaned = ''.join(c for c in line if c.isdigit() or c == '.')
                        try:
                            p = float(cleaned)
                            if 0.01 < p < 999999:
                                price = p
                        except ValueError:
                            pass
                    if '人付款' in line or '人收货' in line:
                        sales = line.strip()
                    if '店' in line and len(line) < 20 and '旗舰' in line:
                        shop = line.strip()

                # Price fallback: combine consecutive digit-only lines after ¥
                if price == 0.0:
                    in_price = False
                    price_parts = []
                    for line in lines:
                        if '¥' in line or '￥' in line:
                            in_price = True
                            price_parts.append(''.join(c for c in line if c.isdigit() or c == '.'))
                            continue
                        if in_price and line.replace('.', '').replace(' ', '').isdigit():
                            price_parts.append(line.strip())
                        elif in_price and price_parts:
                            break
                    if price_parts:
                        try:
                            price = float(''.join(price_parts))
                        except ValueError:
                            pass

                results.append({
                    "title": title,
                    "price": price,
                    "sales": sales,
                    "shop_name": shop or "淘宝商家",
                    "main_image": imgs[0] if imgs else "",
                    "source_url": f"https://s.taobao.com/search?q={keyword}",
                    "original_price": None,
                    "detail_images": imgs,
                    "specs": None,
                    "rating": None,
                })

        except Exception as e:
            print(f"[淘宝] 搜索异常: {e}")
        return results

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        return []

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        return []
