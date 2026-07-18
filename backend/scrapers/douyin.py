"""
抖音爬虫 — Playwright 浏览器自动化
"""
from scrapers import BaseScraper
from typing import Optional


class DouyinScraper(BaseScraper):

    def __init__(self, cookies: Optional[dict] = None):
        super().__init__("douyin", cookies)

    def supports_article(self) -> bool:
        return True

    async def search_products(self, keyword: str, count: int = 20) -> list:
        """搜索抖音电商商品"""
        await self.launch(headless=True)
        results = []
        try:
            search_url = f"https://www.douyin.com/search/{keyword}?type=product"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(4000)

            items = await self.page.query_selector_all('[class*="product"], [class*="shop"], [class*="card"]')
            for item in items[:count]:
                try:
                    title_el = await item.query_selector('[class*="title"], [class*="name"]')
                    price_el = await item.query_selector('[class*="price"]')
                    sales_el = await item.query_selector('[class*="sales"], [class*="sold"]')
                    img_el = await item.query_selector("img")

                    title = await title_el.inner_text() if title_el else ""
                    price_text = await price_el.inner_text() if price_el else "0"
                    sales = await sales_el.inner_text() if sales_el else ""
                    img_url = await img_el.get_attribute("src") if img_el else ""

                    price = float("".join(c for c in price_text if c.isdigit() or c == ".")) if price_text else 0

                    results.append({
                        "title": title.strip(),
                        "price": price,
                        "sales": sales.strip(),
                        "main_image": img_url,
                        "shop_name": "抖音小店",
                        "source_url": self.page.url,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[抖音] 商品搜索失败: {e}")
        finally:
            await self.close()
        return results

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        """搜索抖音短视频"""
        await self.launch(headless=True)
        results = []
        try:
            search_url = f"https://www.douyin.com/search/{keyword}"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(4000)

            items = await self.page.query_selector_all('[class*="search-result"], [class*="video"], [class*="card"]')
            for item in items[:count]:
                try:
                    title_el = await item.query_selector('[class*="title"], [class*="desc"]')
                    author_el = await item.query_selector('[class*="author"], [class*="nickname"]')
                    likes_el = await item.query_selector('[class*="like"], [class*="digg"]')
                    cover_el = await item.query_selector("img")

                    title = await title_el.inner_text() if title_el else ""
                    author = await author_el.inner_text() if author_el else ""
                    likes = await likes_el.inner_text() if likes_el else ""
                    cover = await cover_el.get_attribute("src") if cover_el else ""

                    results.append({
                        "title": title.strip(),
                        "author_name": author.strip(),
                        "likes": likes.strip(),
                        "cover_image": cover,
                        "source_url": self.page.url,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[抖音] 视频搜索失败: {e}")
        finally:
            await self.close()
        return results

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        """抖音有团购（抖音生活服务）"""
        await self.launch(headless=True)
        results = []
        try:
            search_url = f"https://www.douyin.com/search/{keyword}?type=general"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(4000)
            # 抖音团购在生活服务 tab 下，实际 URL 可能不同
            results = await self.search_products(keyword, count)
        except Exception as e:
            print(f"[抖音] 团购搜索失败: {e}")
        finally:
            await self.close()
        return results
