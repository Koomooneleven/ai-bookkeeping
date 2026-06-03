from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionCreate(BaseModel):
    text: str = Field(..., description="消费描述文本，AI 自动解析")


class TransactionDirectCreate(BaseModel):
    amount: float
    currency: str = "CNY"
    item_name: str
    category: str = "其他"
    trans_date: str  # "YYYY-MM-DD HH:MM" 格式
    notes: str = ""


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    trans_date: Optional[datetime] = None
    notes: Optional[str] = None


class ParsedResult(BaseModel):
    amount: float
    currency: str = "CNY"
    item_name: str
    category: str = "其他"
    date: str  # "YYYY-MM-DD HH:MM" 格式
    notes: str


class TransactionOut(BaseModel):
    id: int
    amount: float
    currency: str
    item_name: str
    category: Optional[str]
    trans_date: str  # "YYYY-MM-DD HH:MM"
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


class CategoryCreate(BaseModel):
    name: str
    icon: str = "📌"
    color: str = "#CCCCCC"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: Optional[str]
    color: Optional[str]


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    api_key: str
    is_admin: bool = False
    created_at: Optional[str] = None
