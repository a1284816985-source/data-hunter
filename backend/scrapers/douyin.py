"""
抖音爬虫 v3 — persistent context + 精准解析
"""
import asyncio
import re
from playwright.async_api import async_playwright

PROFILE_DIR = '/tmp/douyin_profile'


class DouyinScraper:

    def __init__(self, cookies=None):
        self._pw = None
        self._ctx = None
        self._page = None

    def supports_article(self) -> bool:
        return True

    def supports_group_buy(self) -> bool:
        return False

    async def launch(self, headless: bool = False) -> None:
        self._pw = await async_playwright().start()
        self._ctx = await self._pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=headless,
            args=["--no-sandbox"],
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()

    async def close(self) -> None:
        if self._ctx:
            await self._ctx.close()
        if self._pw:
            await self._pw.stop()

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        results = []
        try:
            url = f"https://www.douyin.com/search/{keyword}"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(6)

            # Scroll to load more
            for _ in range(4):
                await self._page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(2)

            # Extract full page text
            text = await self._page.evaluate(
                "() => (document.body?.innerText || '')"
            )
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Parse: each video is: duration, likes, title, @author, ·date
            i = 0
            while i < len(lines) and len(results) < count:
                line = lines[i]

                # Detect start of video block: duration pattern (mm:ss) or like count
                is_duration = bool(re.match(r'^\d{1,2}:\d{2}$', line))
                is_likes = bool(re.match(r'^[\d.]+万?$', line))

                if is_duration or is_likes:
                    duration = line if is_duration else ""
                    likes = ""

                    if is_duration and i + 1 < len(lines):
                        # Next line should be likes
                        if re.match(r'^[\d.]+万?$', lines[i + 1]):
                            likes = lines[i + 1]
                            i += 1
                    elif is_likes:
                        likes = line

                    # Next lines: title, author, date
                    title = ""
                    author = ""
                    date = ""

                    if i + 1 < len(lines):
                        candidate = lines[i + 1]
                        # Title: has content but not @author or ·date pattern
                        if not candidate.startswith("@") and not candidate.startswith("·"):
                            title = candidate
                            i += 1

                    if i + 1 < len(lines) and lines[i + 1].startswith("@"):
                        author = lines[i + 1]
                        i += 1

                    if i + 1 < len(lines) and lines[i + 1].startswith("·"):
                        date = lines[i + 1]
                        i += 1

                    if title and len(title) > 3:
                        # Extract hashtags from title
                        tags = re.findall(r'#(\w+)', title)

                        results.append({
                            "title": title,
                            "author_name": author.lstrip("@"),
                            "likes": likes,
                            "cover_image": "",
                            "source_url": url,
                            "content_text": title,
                            "comments_count": "",
                            "favorites": "",
                            "publish_time": date.lstrip("· "),
                            "tags": tags,
                            "comments": [],
                        })

                i += 1

        except Exception as e:
            print(f"[抖音] 搜索异常: {e}")
        return results

    async def search_products(self, keyword: str, count: int = 20) -> list:
        return []

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        return []
