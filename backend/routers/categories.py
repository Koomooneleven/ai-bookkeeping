from fastapi import APIRouter, Depends
from database import get_db
from models import CategoryCreate, CategoryUpdate, APIResponse
from routers.transactions import verify_api_key

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    rows = await db.execute_fetchall(
        "SELECT * FROM categories WHERE user_id = ? ORDER BY id", [auth["user_id"]]
    )
    return {"success": True, "data": [dict(r) for r in rows]}


@router.post("", response_model=APIResponse)
async def create_category(
    body: CategoryCreate,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    try:
        cursor = await db.execute(
            "INSERT INTO categories (name, icon, color, user_id) VALUES (?, ?, ?, ?)",
            (body.name, body.icon, body.color, auth["user_id"]),
        )
        await db.commit()
        return APIResponse(success=True, data={"id": cursor.lastrowid, "name": body.name})
    except Exception as e:
        return APIResponse(success=False, error=f"添加失败: {str(e)}")


@router.put("/{cat_id}", response_model=APIResponse)
async def update_category(
    cat_id: int,
    body: CategoryUpdate,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return APIResponse(success=False, error="没有需要更新的字段")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [cat_id, auth["user_id"]]
    await db.execute(f"UPDATE categories SET {set_clause} WHERE id = ? AND user_id = ?", values)
    await db.commit()
    return APIResponse(success=True, data={"id": cat_id, "updated": True})


@router.delete("/{cat_id}", response_model=APIResponse)
async def delete_category(
    cat_id: int,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    row = await db.execute_fetchall(
        "SELECT name FROM categories WHERE id = ? AND user_id = ?", [cat_id, auth["user_id"]]
    )
    if not row:
        return APIResponse(success=False, error="分类不存在")
    name = row[0]["name"]
    await db.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", [cat_id, auth["user_id"]])
    await db.commit()
    return APIResponse(success=True, data={"id": cat_id, "name": name, "deleted": True})
