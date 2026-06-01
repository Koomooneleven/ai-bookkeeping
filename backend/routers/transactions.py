from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from database import get_db
from models import TransactionCreate, TransactionUpdate, TransactionOut, APIResponse
from ai_parser import parse_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def verify_api_key(x_api_key: str = Header(...)):
    from config import API_KEY

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="无效的 API Key")
    return x_api_key


@router.post("", response_model=APIResponse)
async def create_transaction(
    body: TransactionCreate,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    parsed = await parse_transaction(body.text)
    cursor = await db.execute(
        """INSERT INTO transactions (amount, currency, item_name, category, trans_date, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            parsed.amount,
            parsed.currency,
            parsed.item_name,
            parsed.category,
            parsed.date,
            parsed.notes,
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


@router.get("", response_model=dict)
async def list_transactions(
    page: int = 1,
    page_size: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    conditions = []
    params = []

    if date_from:
        conditions.append("trans_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("trans_date <= ?")
        params.append(date_to)
    if category:
        conditions.append("category = ?")
        params.append(category)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_row = await db.execute_fetchall(f"SELECT COUNT(*) as c FROM transactions {where}", params)
    total = count_row[0]["c"]

    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await db.execute_fetchall(
        f"""SELECT * FROM transactions {where}
            ORDER BY trans_date DESC, created_at DESC
            LIMIT ? OFFSET ?""",
        params,
    )

    items = [dict(r) for r in rows]
    return {"success": True, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/{trans_id}", response_model=APIResponse)
async def get_transaction(
    trans_id: int,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    row = await db.execute_fetchall("SELECT * FROM transactions WHERE id = ?", [trans_id])
    if not row:
        return APIResponse(success=False, error="账单不存在")
    return APIResponse(success=True, data=dict(row[0]))


@router.put("/{trans_id}", response_model=APIResponse)
async def update_transaction(
    trans_id: int,
    body: TransactionUpdate,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return APIResponse(success=False, error="没有需要更新的字段")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [trans_id]
    await db.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", values)
    await db.commit()

    row = await db.execute_fetchall("SELECT * FROM transactions WHERE id = ?", [trans_id])
    return APIResponse(success=True, data=dict(row[0]))


@router.delete("/{trans_id}", response_model=APIResponse)
async def delete_transaction(
    trans_id: int,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    await db.execute("DELETE FROM transactions WHERE id = ?", [trans_id])
    await db.commit()
    return APIResponse(success=True, data={"id": trans_id, "deleted": True})
