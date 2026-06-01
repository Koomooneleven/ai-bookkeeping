from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class TransactionCreate(BaseModel):
    text: str = Field(..., description="消费描述文本，AI 自动解析")


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    trans_date: Optional[date] = None
    notes: Optional[str] = None


class ParsedResult(BaseModel):
    amount: float
    currency: str = "CNY"
    item_name: str
    category: str = "其他"
    date: str
    notes: str


class TransactionOut(BaseModel):
    id: int
    amount: float
    currency: str
    item_name: str
    category: Optional[str]
    trans_date: str
    notes: Optional[str]
    created_at: Optional[str]


class APIResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class StatsMonthly(BaseModel):
    month: str
    total: float
    count: int


class StatsCategory(BaseModel):
    category: str
    total: float
    percentage: float
    color: Optional[str] = None
    icon: Optional[str] = None
