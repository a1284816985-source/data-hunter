"""
美团爬虫 — Playwright 浏览器自动化
"""
from scrapers import BaseScraper
from typing import Optional


class MeituanScraper(BaseScraper):

    def __init__(self, cookies: Optional[dict] = None):
        super().__init__("meituan", cookies)

    def supports_group_buy(self) -> bool:
        return True

    async def search_products(self, keyword: str, count: int = 20) -> list:
        """搜索美团外卖/电商商品"""
        await self.launch(headless=True)
        results = []
        try:
            search_url = f"https://www.meituan.com/s/?keyword={keyword}"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(4000)

            items = await self.page.query_selector_all('[class*="list-item"], [class*="card"], [class*="poi"]')
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
                        "shop_name": "美团商家",
                        "source_url": self.page.url,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[美团] 商品搜索失败: {e}")
        finally:
            await self.close()
        return results

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        """搜索美团团购"""
        await self.launch(headless=True)
        results = []
        try:
            # 美团团购一般在 dianping.com 或 meituan.com 团购频道
            search_url = f"https://www.meituan.com/s/?keyword={keyword}&type=group"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(4000)

            items = await self.page.query_selector_all('[class*="deal"], [class*="group"], [class*="card"]')
            for item in items[:count]:
                try:
                    title_el = await item.query_selector('[class*="title"]')
                    price_el = await item.query_selector('[class*="price"]')
                    original_el = await item.query_selector('[class*="original"]')
                    sales_el = await item.query_selector('[class*="sales"]')
                    img_el = await item.query_selector("img")

                    title = await title_el.inner_text() if title_el else ""
                    price_text = await price_el.inner_text() if price_el else "0"
                    original_text = await original_el.inner_text() if original_el else ""
                    sales = await sales_el.inner_text() if sales_el else ""
                    img_url = await img_el.get_attribute("src") if img_el else ""

                    price = float("".join(c for c in price_text if c.isdigit() or c == ".")) if price_text else 0
                    original_price = float("".join(c for c in original_text if c.isdigit() or c == ".")) if original_text else None

                    results.append({
                        "title": title.strip(),
                        "price": price,
                        "original_price": original_price,
                        "sales": sales.strip(),
                        "main_image": img_url,
                        "shop_name": "美团商家",
                        "source_url": self.page.url,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[美团] 团购搜索失败: {e}")
        finally:
            await self.close()
        return results

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        """美团不支持图文/视频"""
        return []
