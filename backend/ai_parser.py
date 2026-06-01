import json
import httpx
from datetime import date

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from models import ParsedResult

SYSTEM_PROMPT = """你是一个记账文本解析助手。用户会输入一段消费描述文本，你需要提取结构化信息并返回 JSON。

规则：
1. amount: 数字金额，如 35.5。必须提取到金额数字
2. currency: 货币代码，默认 "CNY"。根据上下文识别：$→USD, HK$→HKD, ¥/元/块→CNY, €→EUR, £→GBP, JP¥/円→JPY
3. item_name: 商品或商家名称，简短概括，不要超过20个字
4. category: 从 [餐饮, 交通, 购物, 娱乐, 居住, 医疗, 教育, 其他] 中选择最合适的
5. date: 日期，格式 YYYY-MM-DD。如果用户提到了"昨天/前天/上周/3天前"等，请计算具体日期
6. notes: 保留用户原始输入文本

返回格式（严格 JSON，不要包含 markdown 标记）：
{"amount": 35.5, "currency": "CNY", "item_name": "麦当劳", "category": "餐饮", "date": "2026-05-30", "notes": "原文本"}

如果用户输入无法解析出金额和商品信息，返回：
{"amount": 0, "currency": "CNY", "item_name": "", "category": "其他", "date": "2026-05-30", "notes": "无法解析", "error": "请说明金额和买了什么，例如「午餐麦当劳35元」"}

今天的日期是 {today}。"""


async def parse_transaction(text: str) -> ParsedResult:
    """调用 DeepSeek API 解析消费文本"""
    today = date.today().isoformat()
    prompt = SYSTEM_PROMPT.replace("{today}", today)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    result = json.loads(content)

    if result.get("amount", 0) <= 0:
        raise ValueError(result.get("error", "未识别到有效金额，请重试"))

    return ParsedResult(**result)
