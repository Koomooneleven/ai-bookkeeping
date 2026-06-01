import json
import httpx
from datetime import datetime

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from models import ParsedResult

SYSTEM_PROMPT = """你是一个记账文本解析助手。用户会输入消费描述文本（可能是手动输入的自然语言，也可能是支付页面截屏OCR提取的文本）。你需要提取结构化信息并返回 JSON。

规则：
1. amount: 数字金额。优先查找 ¥/$ 符号后的数字，或"元/块"前的数字。OCR文本中可能有多个金额，选实际支付的那个
2. currency: 货币代码，默认 "CNY"。¥/元/块→CNY, $→USD, €→EUR, £→GBP, JP¥/円→JPY
3. item_name: 商家或商品名称，简短概括不超过20字。优先从OCR文本中的品牌名/商家名提取
4. category: 从 [餐饮, 交通, 购物, 娱乐, 居住, 医疗, 教育, 其他] 中选择
5. datetime: 交易时间，格式 YYYY-MM-DD HH:MM。用户说"下午3点"→15:00，"刚刚/刚才"→当前时间。OCR文本中可能有完整时间戳，优先使用。如果未提及，默认当前时间
6. notes: 保留原始文本前200字

返回格式（严格JSON）：
{"amount": 35.5, "currency": "CNY", "item_name": "麦当劳", "category": "餐饮", "datetime": "2026-06-01 14:30", "notes": "..."}

OCR 文本示例："微信支付\n支付成功\n¥35.00\n麦当劳\n2026-06-01 14:30" → 金额35、麦当劳、餐饮、2026-06-01 14:30

无法解析时返回：
{"amount": 0, "currency": "CNY", "item_name": "", "category": "其他", "datetime": "{now}", "notes": "", "error": "请说明金额和买了什么，例如「午餐麦当劳35元」"}

当前时间 {now}。"""


async def parse_transaction(text: str) -> ParsedResult:
    """调用 DeepSeek API 解析消费文本"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = SYSTEM_PROMPT.replace("{now}", now)

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
        "max_tokens": 400,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    result = json.loads(content)

    if result.get("amount", 0) <= 0:
        raise ValueError(result.get("error", "未识别到有效金额，请重试"))

    # AI might return "date" or "datetime" key, normalize
    if "datetime" in result:
        result["date"] = result["datetime"]

    return ParsedResult(**result)
