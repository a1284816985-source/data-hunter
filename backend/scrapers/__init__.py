"""
通用爬虫基类 — 所有平台爬虫的父类
"""
from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import json
import os


class BaseScraper(ABC):
    """爬虫基类"""

    def __init__(self, platform_name: str, cookies: Optional[dict] = None):
        self.platform_name = platform_name
        self.cookies = cookies
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def launch(self, headless: bool = True) -> Page:
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        """)

        if self.cookies:
            await self.context.add_cookies(self.cookies)

        self.page = await self.context.new_page()
        return self.page

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    @abstractmethod
    async def search_products(self, keyword: str, count: int = 20) -> list:
        """搜索商品，返回商品列表 [{title, price, ...}]"""
        pass

    @abstractmethod
    async def search_articles(self, keyword: str, count: int = 20) -> list:
        """搜索图文/视频，返回内容列表 [{title, content_text, likes, ...}]"""
        pass

    @abstractmethod
    async def search_group_buys(self, keyword: str, count: int = 20) -> list:
        """搜索团购，返回团购列表"""
        pass

    def supports_product(self) -> bool:
        return True

    def supports_article(self) -> bool:
        return False

    def supports_group_buy(self) -> bool:
        return False
