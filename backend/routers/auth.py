import bcrypt
import secrets
from fastapi import APIRouter, Depends, HTTPException, Header
from database import get_db
from models import UserLogin, UserCreate, UserOut, APIResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def verify_admin(x_api_key: str = Header(...)):
    """管理员验证：用全局 API_KEY 或 admin 用户的 api_key"""
    from config import API_KEY
    from database import DB_PATH
    import aiosqlite

    if x_api_key == API_KEY:
        return True

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    row = await db.execute_fetchall(
        "SELECT id FROM users WHERE api_key = ? AND is_admin = 1", [x_api_key]
    )
    await db.close()
    if row:
        return True
    raise HTTPException(status_code=403, detail="需要管理员权限")


@router.post("/login", response_model=APIResponse)
async def login(body: UserLogin, db=Depends(get_db)):
    row = await db.execute_fetchall(
        "SELECT id, username, password_hash, api_key, is_admin FROM users WHERE username = ?",
        [body.username],
    )
    if not row:
        return APIResponse(success=False, error="用户名或密码错误")

    user = row[0]
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        return APIResponse(success=False, error="用户名或密码错误")

    return APIResponse(
        success=True,
        data={
            "id": user["id"],
            "username": user["username"],
            "api_key": user["api_key"],
            "is_admin": bool(user["is_admin"]),
        },
    )


@router.post("/register", response_model=APIResponse)
async def register(
    body: UserCreate,
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    """管理员创建新用户"""
    existing = await db.execute_fetchall(
        "SELECT id FROM users WHERE username = ?", [body.username]
    )
    if existing:
        return APIResponse(success=False, error="用户名已存在")

    pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    api_key = secrets.token_urlsafe(16)

    await db.execute(
        "INSERT INTO users (username, password_hash, api_key) VALUES (?, ?, ?)",
        (body.username, pwd_hash, api_key),
    )
    await db.commit()

    row = await db.execute_fetchall("SELECT id FROM users WHERE username = ?", [body.username])
    user_id = row[0]["id"]

    # 为新用户创建默认分类
    for cat in [
        ('餐饮', '🍽️', '#FF6B6B'),
        ('交通', '🚗', '#4ECDC4'),
        ('购物', '🛒', '#45B7D1'),
        ('娱乐', '🎮', '#96CEB4'),
        ('居住', '🏠', '#FFEAA7'),
        ('医疗', '💊', '#DDA0DD'),
        ('教育', '📚', '#98D8C8'),
        ('其他', '📌', '#CCCCCC'),
    ]:
        await db.execute(
            "INSERT OR IGNORE INTO categories (name, icon, color, user_id) VALUES (?, ?, ?, ?)",
            (cat[0], cat[1], cat[2], user_id),
        )
    await db.commit()

    return APIResponse(
        success=True,
        data={"username": body.username, "api_key": api_key},
    )


@router.get("/users", response_model=APIResponse)
async def list_users(
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    rows = await db.execute_fetchall(
        "SELECT id, username, api_key, is_admin, created_at FROM users ORDER BY id"
    )
    return APIResponse(
        success=True,
        data={"users": [dict(r) for r in rows]},
    )


@router.put("/users/{user_id}/reset-key", response_model=APIResponse)
async def reset_api_key(
    user_id: int,
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    """管理员重置用户 API Key"""
    row = await db.execute_fetchall("SELECT username FROM users WHERE id = ?", [user_id])
    if not row:
        return APIResponse(success=False, error="用户不存在")

    new_key = secrets.token_urlsafe(16)
    await db.execute("UPDATE users SET api_key = ? WHERE id = ?", (new_key, user_id))
    await db.commit()

    return APIResponse(
        success=True,
        data={"user_id": user_id, "username": row[0]["username"], "api_key": new_key},
    )


@router.put("/users/{user_id}", response_model=APIResponse)
async def update_user(
    user_id: int,
    body: UserCreate,
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    """管理员修改用户：用户名 和/或 密码"""
    row = await db.execute_fetchall("SELECT id FROM users WHERE id = ?", [user_id])
    if not row:
        return APIResponse(success=False, error="用户不存在")

    # 检查新用户名是否已被占用
    existing = await db.execute_fetchall(
        "SELECT id FROM users WHERE username = ? AND id != ?", [body.username, user_id]
    )
    if existing:
        return APIResponse(success=False, error="用户名已存在")

    pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    await db.execute(
        "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
        (body.username, pwd_hash, user_id),
    )
    await db.commit()
    return APIResponse(success=True, data={"user_id": user_id, "username": body.username})


@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: int,
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    """管理员删除用户"""
    row = await db.execute_fetchall("SELECT username, is_admin FROM users WHERE id = ?", [user_id])
    if not row:
        return APIResponse(success=False, error="用户不存在")
    if row[0]["is_admin"]:
        return APIResponse(success=False, error="不能删除管理员")

    await db.execute("DELETE FROM transactions WHERE user_id = ?", [user_id])
    await db.execute("DELETE FROM categories WHERE user_id = ?", [user_id])
    await db.execute("DELETE FROM users WHERE id = ?", [user_id])
    await db.commit()
    return APIResponse(success=True, data={"user_id": user_id, "username": row[0]["username"], "deleted": True})
