from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from database import get_db
from models import TransactionCreate, TransactionDirectCreate, TransactionUpdate, TransactionOut, APIResponse
from ai_parser import parse_transaction
import json

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def verify_api_key(x_api_key: str = Header(...), db=Depends(get_db)):
    from config import API_KEY

    # 查找用户
    row = await db.execute_fetchall(
        "SELECT id, is_admin FROM users WHERE api_key = ?", [x_api_key]
    )
    if row:
        return {"user_id": row[0]["id"], "is_admin": bool(row[0]["is_admin"])}

    # 兼容全局 API_KEY（管理操作用）
    if x_api_key == API_KEY:
        # 返回 admin 用户
        admin = await db.execute_fetchall(
            "SELECT id FROM users WHERE is_admin = 1 LIMIT 1"
        )
        if admin:
            return {"user_id": admin[0]["id"], "is_admin": True}
        return {"user_id": None, "is_admin": True}

    raise HTTPException(status_code=403, detail="无效的 API Key")


async def extract_text(request: Request) -> str:
    """从请求中提取text字段，兼容JSON和表单两种格式"""
    content_type = request.headers.get("content-type", "")
    raw = (await request.body()).decode("utf-8", errors="replace")

    if "application/json" in content_type or raw.strip().startswith("{"):
        try:
            data = json.loads(raw)
            return data.get("text", "")
        except json.JSONDecodeError:
            pass

    if "application/x-www-form-urlencoded" in content_type or "=" in raw:
        from urllib.parse import parse_qs
        try:
            parsed = parse_qs(raw)
            return parsed.get("text", [""])[0]
        except Exception:
            pass

    # 纯文本直接当作消费内容
    return raw.strip()


@router.post("", response_model=APIResponse)
async def create_transaction(
    request: Request,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    text = await extract_text(request)
    if not text:
        return APIResponse(success=False, error="未收到输入内容，请检查快捷指令中text字段是否正确绑定")

    try:
        parsed = await parse_transaction(text)
    except ValueError as e:
        return APIResponse(success=False, error=f"收到: [{text}] → {str(e)}")
    except Exception as e:
        return APIResponse(success=False, error=f"收到: [{text}] → AI错误: {str(e)}")

    cursor = await db.execute(
        """INSERT INTO transactions (amount, currency, item_name, category, trans_date, notes, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            parsed.amount,
            parsed.currency,
            parsed.item_name,
            parsed.category,
            parsed.date,
            parsed.notes,
            auth["user_id"],
        ),
    )
    await db.commit()
    return APIResponse(
        success=True,
        data={
            "id": cursor.lastrowid,
            "amount": parsed.amount,
            "currency": parsed.currency,
            "item_name": parsed.item_name,
            "category": parsed.category,
            "trans_date": parsed.date,
        },
    )


@router.post("/direct", response_model=APIResponse)
async def create_transaction_direct(
    body: TransactionDirectCreate,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    cursor = await db.execute(
        """INSERT INTO transactions (amount, currency, item_name, category, trans_date, notes, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (body.amount, body.currency, body.item_name, body.category, body.trans_date, body.notes, auth["user_id"]),
    )
    await db.commit()
    return APIResponse(
        success=True,
        data={"id": cursor.lastrowid, "amount": body.amount, "currency": body.currency,
              "item_name": body.item_name, "category": body.category, "trans_date": body.trans_date},
    )


@router.get("", response_model=dict)
async def list_transactions(
    page: int = 1,
    page_size: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = "date_desc",
    search: Optional[str] = None,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    conditions = ["transactions.user_id = ?"]
    params = [auth["user_id"]]

    if date_from:
        conditions.append("trans_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("trans_date <= ?")
        params.append(date_to)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if search:
        conditions.append("(item_name LIKE ? OR notes LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_row = await db.execute_fetchall(f"SELECT COUNT(*) as c FROM transactions {where}", params)
    total = count_row[0]["c"]

    sort_map = {
        "date_desc": "trans_date DESC, created_at DESC",
        "date_asc": "trans_date ASC, created_at ASC",
        "amount_desc": "amount DESC",
        "amount_asc": "amount ASC",
    }
    order = sort_map.get(sort, "trans_date DESC, created_at DESC")

    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await db.execute_fetchall(
        f"""SELECT * FROM transactions {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?""",
        params,
    )

    items = [dict(r) for r in rows]
    return {"success": True, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/{trans_id}", response_model=APIResponse)
async def get_transaction(
    trans_id: int,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    row = await db.execute_fetchall(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?", [trans_id, auth["user_id"]]
    )
    if not row:
        return APIResponse(success=False, error="账单不存在")
    return APIResponse(success=True, data=dict(row[0]))


@router.put("/{trans_id}", response_model=APIResponse)
async def update_transaction(
    trans_id: int,
    body: TransactionUpdate,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return APIResponse(success=False, error="没有需要更新的字段")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [trans_id, auth["user_id"]]
    await db.execute(f"UPDATE transactions SET {set_clause} WHERE id = ? AND user_id = ?", values)
    await db.commit()

    row = await db.execute_fetchall(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?", [trans_id, auth["user_id"]]
    )
    return APIResponse(success=True, data=dict(row[0]))


@router.delete("/{trans_id}", response_model=APIResponse)
async def delete_transaction(
    trans_id: int,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    await db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", [trans_id, auth["user_id"]])
    await db.commit()
    return APIResponse(success=True, data={"id": trans_id, "deleted": True})
