"""
采集调度器 — 管理任务队列和爬虫执行
"""
import asyncio
import threading
import traceback
from typing import Optional
from models import Task, TaskStatus, TaskType, ScrapedItem, Platform
from database import SessionLocal
from scrapers import BaseScraper


class ScraperScheduler:
    """采集调度器，在后台线程中运行"""

    def __init__(self):
        self._running = False
        self._current_task_id: Optional[int] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Scheduler] 采集调度器已启动")

    def stop(self):
        self._running = False

    def _run_loop(self):
        """主循环，轮询待处理任务"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._process_queue())
        finally:
            loop.close()

    async def _process_queue(self):
        while self._running:
            db = SessionLocal()
            try:
                # 取下一个排队中的任务
                task = db.query(Task).filter(
                    Task.status == TaskStatus.QUEUED.value
                ).order_by(Task.created_at).first()

                if task:
                    await self._execute_task(task.id)
                else:
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"[Scheduler] 调度错误: {e}")
                await asyncio.sleep(5)
            finally:
                db.close()

    async def _execute_task(self, task_id: int):
        """执行单个采集任务"""
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return

            task.status = TaskStatus.RUNNING.value
            db.commit()

            platforms = task.platforms  # JSON list
            total_items = 0

            for platform_name in platforms:
                try:
                    scraper = self._get_scraper(platform_name)
                    if not scraper:
                        continue

                    await scraper.launch(headless=True)

                    if task.task_type == TaskType.PRODUCT_GROUP.value:
                        # 商品/团购模式
                        if platform_name == Platform.MEITUAN.value and scraper.supports_group_buy():
                            items = await scraper.search_group_buys(task.keyword, task.count_per_platform)
                        else:
                            items = await scraper.search_products(task.keyword, task.count_per_platform)

                        item_type = "group_buy" if platform_name == Platform.MEITUAN.value else "product"
                    else:
                        # 图文/视频模式
                        items = await scraper.search_articles(task.keyword, task.count_per_platform)
                        item_type = "article"

                    # 保存采集结果
                    # 过滤无货 + 异常低价
                    items = self._filter_items(items, task.task_type)
                    
                    for item_data in items:
                        db_item = ScrapedItem(
                            task_id=task.id,
                            platform=platform_name,
                            item_type=item_type,
                            **self._map_item_fields(item_data, item_type),
                        )
                        db.add(db_item)
                        total_items += 1

                    await scraper.close()

                except Exception as e:
                    print(f"[Scheduler] 平台 {platform_name} 采集失败: {e}")
                    traceback.print_exc()
                    # 单个平台失败不中断其他平台
                    continue

            task.total_items = total_items
            task.status = TaskStatus.COMPLETED.value
            db.commit()

        except Exception as e:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                task.error_message = str(e)
                db.commit()
            traceback.print_exc()
        finally:
            db.close()

    def _filter_items(self, items: list, task_type: str) -> list:
        """过滤无货商品 + 异常低价"""
        if not items:
            return items

        filtered = []

        if task_type == TaskType.PRODUCT_GROUP.value:
            # 收集有效价格
            prices = []
            for item in items:
                p = item.get("price", 0)
                if p and p > 0.5:
                    prices.append(p)

            # 计算中位数，过滤低于中位数 15% 的异常低价
            if prices:
                prices.sort()
                median = prices[len(prices) // 2]
                min_price = max(0.5, median * 0.15)

                for item in items:
                    p = item.get("price", 0) or 0
                    title = item.get("title", "")
                    # 跳过无价格（无货/下架）
                    if p <= 0:
                        continue
                    # 跳过异常低价
                    if p < min_price:
                        continue
                    # 跳过明显的配件/补差价链接
                    skip_words = ["补差价", "补邮费", "配件", "专用", "仅", "定金"]
                    if any(w in title for w in skip_words) and p < 10:
                        continue
                    filtered.append(item)

                removed = len(items) - len(filtered)
                if removed > 0:
                    print(f"[过滤] {removed}/{len(items)} 条被过滤 (无货/异常低价/配件)")
            else:
                filtered = items
        else:
            # 图文/视频：不过滤
            filtered = items

        return filtered

    def _get_scraper(self, platform_name: str) -> Optional[BaseScraper]:
        """根据平台名获取爬虫实例"""
        if platform_name == Platform.XIAOHONGSHU.value:
            from scrapers.xiaohongshu import XiaohongshuScraper
            return XiaohongshuScraper()
        elif platform_name == Platform.TAOBAO.value:
            from scrapers.taobao import TaobaoScraper
            return TaobaoScraper()
        elif platform_name == Platform.DOUYIN.value:
            from scrapers.douyin import DouyinScraper
            return DouyinScraper()
        elif platform_name == Platform.MEITUAN.value:
            from scrapers.meituan import MeituanScraper
            return MeituanScraper()
        elif platform_name == Platform.AMAZON.value:
            from scrapers.amazon import AmazonScraper
            return AmazonScraper()
        return None

    def _map_item_fields(self, item_data: dict, item_type: str) -> dict:
        """映射采集字段到数据库字段"""
        mapped = {
            "title": item_data.get("title"),
            "content_text": item_data.get("content_text"),
            "likes": item_data.get("likes"),
            "comments_count": item_data.get("comments_count"),
            "favorites": item_data.get("favorites"),
            "publish_time": item_data.get("publish_time"),
            "author_name": item_data.get("author_name"),
            "tags": item_data.get("tags"),
            "cover_image": item_data.get("cover_image"),
            "source_url": item_data.get("source_url"),
            "comments": item_data.get("comments"),
            "raw_data": item_data,
        }

        if item_type in ("product", "group_buy"):
            mapped.update({
                "price": item_data.get("price"),
                "original_price": item_data.get("original_price"),
                "sales": item_data.get("sales"),
                "main_image": item_data.get("main_image"),
                "detail_images": item_data.get("detail_images"),
                "shop_name": item_data.get("shop_name"),
                "specs": item_data.get("specs"),
                "rating": item_data.get("rating"),
            })

        return mapped


# 全局单例
scheduler = ScraperScheduler()
