"""
亚马逊爬虫 — 已验证版本（无需登录，Stealth 即可）
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re


class AmazonScraper:
    """亚马逊爬虫 — 兼容 scheduler 接口"""

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
            locale="en-US",
        )
        self._page = await self._ctx.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def search_products(self, keyword: str, count: int = 20) -> list:
        results = []
        try:
            url = f"https://www.amazon.com/s?k={keyword}"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            page_num = 0
            while len(results) < count and page_num < 5:  # 最多翻5页
                # 滚动当前页加载全部商品
                for _ in range(6):
                    await self._page.evaluate("window.scrollBy(0, 600)")
                    await asyncio.sleep(0.8)

                items = await self._page.query_selector_all(
                    '[data-component-type="s-search-result"]'
                )

                for item in items:
                    if len(results) >= count:
                        break
                    try:
                        # ... (extraction logic unchanged)
                        title_el = (await item.query_selector("h2 a span") or
                                    await item.query_selector("h2 span") or
                                    await item.query_selector("h2"))
                        title = await title_el.inner_text() if title_el else ""
                        # Price — 多策略提取
                        price = 0.0
                        offscreen_el = await item.query_selector(".a-price .a-offscreen")
                        if offscreen_el:
                            price_text = await offscreen_el.inner_text()
                            m = re.search(r"([\d,]+\.?\d*)", price_text.replace(",", ""))
                            if m:
                                try:
                                    price = float(m.group(1))
                                except ValueError:
                                    pass
                        # 兜底: 从整个 item 文本中提取价格
                        if price == 0.0:
                            item_text = await item.inner_text()
                            # 匹配 $XX.XX 或 HKD XX.XX
                            m = re.search(r"[\$HKD￥¥]\s*([\d,]+\.?\d*)", item_text)
                            if m:
                                try:
                                    price = float(m.group(1).replace(",", ""))
                                except ValueError:
                                    pass

                        rating = None
                        rating_el = await item.query_selector(".a-icon-star-small .a-icon-alt, .a-icon-alt")
                        if rating_el:
                            rating_text = await rating_el.inner_text()
                            m = re.search(r"(\d+\.?\d*)", rating_text)
                            if m:
                                rating = float(m.group(1))

                        sales = ""
                        star_el = await item.query_selector(".a-icon-star-small")
                        if star_el:
                            sales = (await star_el.inner_text()).strip()
                        if not sales or not sales.replace(",", "").replace(".", "").isdigit():
                            item_text = await item.inner_text()
                            m = re.search(r"([\d,]+)\s+ratings?", item_text, re.IGNORECASE)
                            if m:
                                sales = m.group(1)

                        # 抓取全部图片
                        img_el = await item.query_selector("img.s-image")
                        main_image = await img_el.get_attribute("src") if img_el else ""
                        
                        # 尝试抓取轮播图/缩略图
                        all_imgs = await item.query_selector_all("img")
                        detail_images = []
                        for img in all_imgs:
                            src = await img.get_attribute("src") or ""
                            data_src = await img.get_attribute("data-src") or ""
                            for s in [src, data_src]:
                                if s and s not in detail_images and s != main_image and "s-image" not in (await img.get_attribute("class") or ""):
                                    if "amazon" in s.lower() or "media-amazon" in s.lower() or "images" in s.lower():
                                        detail_images.append(s)
                        detail_images = detail_images[:10]  # 最多10张

                        # URL — 多策略提取
                        link_el = (await item.query_selector("h2 a") or
                                   await item.query_selector("a.a-link-normal[href]") or
                                   await item.query_selector(".s-product-image-container a") or
                                   await item.query_selector("a[href*='/dp/']"))
                        source_url = ""
                        if link_el:
                            href = await link_el.get_attribute("href") or ""
                            if href.startswith("/"):
                                source_url = f"https://www.amazon.com{href.split('?')[0]}"  # 去掉 query 参数
                            elif href.startswith("http"):
                                source_url = href.split("?")[0]

                        results.append({
                            "title": title.strip(),
                            "price": price,
                            "rating": rating,
                            "sales": sales,
                            "main_image": main_image,
                            "shop_name": "Amazon",
                            "source_url": source_url,
                            "original_price": None,
                            "detail_images": detail_images,
                            "specs": None,
                        })
                    except Exception:
                        continue

                if len(results) >= count:
                    break

                # 翻下一页
                page_num += 1
                try:
                    next_btn = await self._page.query_selector("a.s-pagination-next:not(.s-pagination-disabled)")
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(3)
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            print(f"[亚马逊] 搜索异常: {e}")

        # 访问前10个商品的详情页，提取规格参数
        if results:
            detail_count = min(10, len(results))
            for i in range(detail_count):
                try:
                    detail_url = results[i].get("source_url", "")
                    if detail_url:
                        specs = await self._scrape_detail(detail_url)
                        if specs:
                            results[i]["specs"] = specs
                except Exception:
                    continue

        return results

    async def _scrape_detail(self, url: str) -> dict:
        """访问商品详情页，提取规格参数"""
        try:
            page = await self._ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(4)

            specs = {}

            # 策略1: 找所有包含 ":" 的文本行
            all_text = await page.evaluate("() => (document.body?.innerText || '')")
            lines = all_text.split("\n")
            in_specs = False
            spec_keywords = ["technical details", "product information", "specifications",
                           "product details", "item specifics", "about this item",
                           "additional information", "product description"]
            for line in lines:
                line = line.strip()
                if not line:
                    if in_specs and len(specs) > 5:
                        break  # 空行表示规格区域结束
                    continue
                # 触发词
                if any(w in line.lower() for w in spec_keywords):
                    in_specs = True
                    continue
                if in_specs and (":" in line or "：" in line):
                    sep = ":" if ":" in line else "："
                    parts = line.split(sep, 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val and len(key) < 80 and len(val) > 1:
                        specs[key] = val
                elif in_specs and len(specs) > 10 and not any(c in line for c in [":", "：", "›"]):
                    break  # 规格区域结束

            # 策略2: 提取 feature bullets
            bullets_el = await page.query_selector("#feature-bullets, #featurebullets_feature_div, #feature-bullets ul")
            if bullets_el:
                bullet_items = await bullets_el.query_selector_all("li, span.a-list-item")
                for bi in bullet_items[:10]:
                    try:
                        text = (await bi.inner_text()).strip()
                        if text and len(text) > 5:
                            idx = len([k for k in specs if k.startswith("要点")])
                            specs[f"要点{idx+1}"] = text
                    except Exception:
                        continue

            # 策略3: 表格提取
            tech_tables = await page.query_selector_all(
                "#productDetails_techSpec_section_1 tr, "
                "#productDetails_detailBullets_sections tr, "
                "table.a-keyvalue tr, "
                "#technicalSpecifications_feature_div tr"
            )
            for row in tech_tables:
                try:
                    cells = await row.query_selector_all("th, td")
                    if len(cells) >= 2:
                        key = (await cells[0].inner_text()).strip()
                        val = (await cells[1].inner_text()).strip()
                        if key and val and len(key) < 60:
                            specs[key] = val
                except Exception:
                    continue

            await page.close()
            return specs if specs else None
        except Exception:
            return None

    async def search_articles(self, keyword: str, count: int = 20) -> list:
        return []

    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        return []
