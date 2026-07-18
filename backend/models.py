from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from database import Base
import enum


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, enum.Enum):
    PRODUCT_GROUP = "product_group"      # 商品/团购
    ARTICLE_VIDEO = "article_video"      # 图文/视频


class Platform(str, enum.Enum):
    TAOBAO = "taobao"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    MEITUAN = "meituan"
    AMAZON = "amazon"


class ItemType(str, enum.Enum):
    PRODUCT = "product"       # 商品
    GROUP_BUY = "group_buy"   # 团购
    ARTICLE = "article"       # 图文
    VIDEO = "video"           # 视频


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(500), nullable=False, comment="搜索关键词")
    platforms = Column(JSON, nullable=False, comment="平台列表 JSON")
    task_type = Column(String(50), nullable=False, comment="任务类型: product_group/article_video")
    count_per_platform = Column(Integer, default=20, comment="每平台采集数量")
    status = Column(String(50), default=TaskStatus.QUEUED.value, comment="状态")
    total_items = Column(Integer, default=0, comment="采集结果总数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScrapedItem(Base):
    __tablename__ = "scraped_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, comment="关联任务ID")
    platform = Column(String(50), nullable=False, comment="平台")
    item_type = Column(String(50), nullable=False, comment="类型: product/group_buy/article/video")

    # 商品/团购字段
    title = Column(String(1000), nullable=True, comment="标题")
    price = Column(Float, nullable=True, comment="价格")
    original_price = Column(Float, nullable=True, comment="原价")
    sales = Column(String(100), nullable=True, comment="销量（可能含文字如'1万+'）")
    main_image = Column(String(2000), nullable=True, comment="主图URL")
    detail_images = Column(JSON, nullable=True, comment="详情图URL列表")
    shop_name = Column(String(500), nullable=True, comment="店铺名")
    specs = Column(JSON, nullable=True, comment="规格信息")
    rating = Column(Float, nullable=True, comment="评分")

    # 图文/视频字段
    content_text = Column(Text, nullable=True, comment="正文/文案")
    cover_image = Column(String(2000), nullable=True, comment="封面图URL")
    likes = Column(String(100), nullable=True, comment="点赞数")
    comments_count = Column(String(100), nullable=True, comment="评论数")
    favorites = Column(String(100), nullable=True, comment="收藏数")
    publish_time = Column(String(100), nullable=True, comment="发布时间")
    author_name = Column(String(500), nullable=True, comment="作者名")
    tags = Column(JSON, nullable=True, comment="标签/话题")

    # 评论内容
    comments = Column(JSON, nullable=True, comment="评论列表")

    # 元数据
    source_url = Column(String(2000), nullable=True, comment="原始链接")
    raw_data = Column(JSON, nullable=True, comment="原始数据")
    created_at = Column(DateTime, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, comment="关联任务ID")
    report_type = Column(String(50), nullable=False, comment="报告类型: product_group/article_video")
    title = Column(String(500), nullable=True, comment="报告标题")
    content = Column(JSON, nullable=False, comment="报告内容 JSON（含各维度分析+图表数据）")
    created_at = Column(DateTime, server_default=func.now())


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, comment="平台名")
    account_name = Column(String(200), nullable=True, comment="账号名/备注")
    cookies = Column(JSON, nullable=True, comment="Cookie数据")
    status = Column(String(50), default="active", comment="状态: active/expired/error")
    last_verified = Column(DateTime, nullable=True, comment="最后验证时间")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(50), default="user", comment="admin/user")
    created_at = Column(DateTime, server_default=func.now())
