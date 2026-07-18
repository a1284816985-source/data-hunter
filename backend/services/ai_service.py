"""
AI 服务 — Grsai API 调用，生成分析报告 + 爆款仿写
"""
import httpx
import json
import os
from typing import List
from models import Task, ScrapedItem

# Grsai API 配置（从 Hermes 环境读取）
GRSAI_BASE_URL = "https://grsai.dakka.com.cn/v1"
GRSAI_MODEL = "gpt-5.5"

# API Key — 避免 f-string 被 Hermes 掩码破坏
def _get_api_key() -> str:
    # 尝试从环境变量 / Hermes config 读取
    key = os.environ.get("GRSAI_API_KEY", "")
    if not key:
        try:
            import yaml
            with open(os.path.expanduser("~/.hermes/config.yaml")) as f:
                config = yaml.safe_load(f)
            providers = config.get("providers", {})
            for name, cfg in providers.items():
                if "grsai" in name.lower():
                    key = cfg.get("api_key", "")
                    break
        except Exception:
            pass
    return key


def _build_payload(messages: list, temperature: float = 0.7) -> dict:
    return {
        "model": GRSAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }


def _build_headers() -> dict:
    key = _get_api_key()
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    }


async def _call_ai(messages: list, temperature: float = 0.7) -> str:
    """调用 Grsai API 并返回文本"""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            GRSAI_BASE_URL + "/chat/completions",
            json=_build_payload(messages, temperature),
            headers=_build_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def generate_analysis_report(task: Task, items: List[ScrapedItem]) -> dict:
    """根据任务类型生成分析报告"""

    # 整理数据
    items_data = _format_items_for_ai(items, task.task_type)

    if task.task_type == "product_group":
        system_prompt = """你是一位资深的市场分析师。请根据提供的商品/团购数据，生成一份专业的竞调分析报告。
报告必须包含以下四个部分，每部分用 markdown 格式，配上关键数据发现：

1. 价格对比分析：对比各平台价格分布，找出最低价/最高价/均价
2. 销量趋势判断：分析各平台销量表现，判断热销价格区间
3. 用户评价情感分析：基于评价内容判断用户口碑
4. 竞品策略建议：给出具体的差异化定价和选品建议

请以 JSON 格式输出：
{"sections": [{"title": "...", "content": "...", "chart_type": "bar|line|pie|none", "chart_data": {...}}], "summary": "..."}"""
    else:
        system_prompt = """你是一位资深的社交媒体内容分析师。请根据提供的图文/视频数据，生成一份专业的内容分析报告。
报告必须包含以下四个部分，每部分用 markdown 格式：

1. 内容策略分析：各平台内容形式分布、文案风格对比
2. 互动数据对比：点赞/评论/收藏排行分析
3. 爆款规律提炼：高互动内容的共性特征
4. 选题方向建议：热门话题推荐和内容创作策略

请以 JSON 格式输出：
{"sections": [{"title": "...", "content": "...", "chart_type": "bar|line|pie|none", "chart_data": {...}}], "summary": "..."}"""

    user_prompt = f"关键词：{task.keyword}\n\n采集数据：\n{items_data}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await _call_ai(messages, temperature=0.7)
        # 尝试解析 JSON
        # 处理可能的 markdown 包裹
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        # 解析失败时返回原始文本
        return {"sections": [{"title": "分析报告", "content": raw, "chart_type": "none", "chart_data": {}}], "summary": raw[:200]}


async def rewrite_viral_content(
    original_title: str,
    original_content: str,
    original_tags: list,
    own_topic: str,
    keep_structure: bool = True,
    keep_tone: bool = True,
    keep_hook: bool = True,
) -> dict:
    """爆款仿写"""

    system_prompt = """你是一位专业的社交媒体爆款文案写手。你的任务是根据参考爆款内容的结构和风格，围绕用户指定的主题创作一篇全新的文案。

要求：
1. 保留原文的结构框架和节奏
2. 保持原文的语气风格
3. 开头钩子要同样有吸引力
4. 内容100%原创，不抄袭原文
5. 适合在抖音/小红书等平台发布

请以 JSON 格式输出：
{"title": "建议标题", "content": "正文文案", "tags": ["话题1", "话题2", "话题3"]}"""

    user_prompt = f"""参考原文标题：{original_title}
参考原文内容：{original_content}
参考标签：{original_tags}

我的产品/主题：{own_topic}

保留元素：结构框架={'是' if keep_structure else '否'}，语气风格={'是' if keep_tone else '否'}，开头钩子={'是' if keep_hook else '否'}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await _call_ai(messages, temperature=0.8)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        return {"title": "", "content": raw, "tags": []}


def _format_items_for_ai(items: List[ScrapedItem], task_type: str) -> str:
    """将采集数据格式化为 AI 可读文本"""
    lines = []
    for i, item in enumerate(items[:50]):  # 限制 50 条避免超 token
        if task_type == "product_group":
            lines.append(
                f"{i+1}. [{item.platform}] {item.title} | "
                f"价格: ¥{item.price} | 原价: ¥{item.original_price or '无'} | "
                f"销量: {item.sales or '未知'} | 店铺: {item.shop_name or '未知'} | "
                f"评分: {item.rating or '无'}"
            )
        else:
            lines.append(
                f"{i+1}. [{item.platform}] {item.title} | "
                f"点赞: {item.likes or '无'} | 评论: {item.comments_count or '无'} | "
                f"收藏: {item.favorites or '无'} | 作者: {item.author_name or '未知'}"
            )
    return "\n".join(lines)


async def analyze_product_sentiment(
    title: str, price: float, rating, sales: str, shop: str, platform: str
) -> dict:
    """对单个商品做 AI 情感分析"""
    system_prompt = """你是一位资深电商分析师。请根据商品信息，分析该商品的市场情绪和消费者反馈趋势。
    
请以 JSON 格式输出：
{
    "sentiment": "positive/neutral/negative",
    "score": 0-100,
    "summary": "一句话总结市场情绪",
    "pros": ["优点1", "优点2"],
    "cons": ["缺点/风险1"],
    "buy_advice": "购买建议(20字内)",
    "target_users": "适合人群"
}"""

    user_prompt = f"""商品：{title}
价格：¥{price}
评分：{rating or '未知'}
销量：{sales or '未知'}
店铺：{shop}
平台：{platform}

请分析该商品的市场情绪和消费者反馈趋势。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await _call_ai(messages, temperature=0.6)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        return {
            "sentiment": "neutral",
            "score": 50,
            "summary": raw[:100] if raw else "暂无数据",
            "pros": [],
            "cons": [],
            "buy_advice": "",
            "target_users": "",
        }
