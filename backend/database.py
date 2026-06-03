import aiosqlite
import bcrypt
import secrets
import os
from config import DB_PATH, API_KEY


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    # --- 基础表 ---
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL        NOT NULL,
            currency    VARCHAR(10) NOT NULL DEFAULT 'CNY',
            item_name   VARCHAR(255) NOT NULL,
            category    VARCHAR(50),
            trans_date  TEXT        NOT NULL,
            notes       TEXT,
            created_at  DATETIME    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  VARCHAR(50) NOT NULL,
            icon  VARCHAR(10),
            color VARCHAR(7)
        );
    """)

    # --- 用户表 ---
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key       VARCHAR(64) UNIQUE NOT NULL,
            is_admin      BOOLEAN DEFAULT 0,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- 迁移：给 transactions 加 user_id ---
    cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(transactions)")]
    if 'user_id' not in cols:
        await db.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)")

    # --- 迁移：给 categories 加 user_id ---
    cat_cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(categories)")]
    if 'user_id' not in cat_cols:
        await db.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER REFERENCES users(id)")

    # --- 创建复合唯一索引（允许不同用户有同名分类）---
    await db.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_user
        ON categories(name, user_id)
    """)

    # --- 创建默认管理员 ---
    existing = await db.execute_fetchall("SELECT id FROM users WHERE username = 'admin'")
    if not existing:
        pwd_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        admin_key = API_KEY if API_KEY != "change-me" else "jizhang2026"
        await db.execute(
            "INSERT INTO users (username, password_hash, api_key, is_admin) VALUES (?, ?, ?, 1)",
            ("admin", pwd_hash, admin_key),
        )
        admin_id = 1
    else:
        admin_id = existing[0]["id"]

    # --- 迁移现有数据 ---
    # transactions 中 user_id 为 NULL 的归给 admin
    orphan_tx = await db.execute_fetchall("SELECT COUNT(*) as c FROM transactions WHERE user_id IS NULL")
    if orphan_tx[0]["c"] > 0:
        await db.execute("UPDATE transactions SET user_id = ? WHERE user_id IS NULL", [admin_id])

    # categories 中 user_id 为 NULL 的归给 admin
    orphan_cat = await db.execute_fetchall("SELECT COUNT(*) as c FROM categories WHERE user_id IS NULL")
    if orphan_cat[0]["c"] > 0:
        await db.execute("UPDATE categories SET user_id = ? WHERE user_id IS NULL", [admin_id])

    # --- 确保 admin 有默认分类 ---
    admin_cats = await db.execute_fetchall("SELECT COUNT(*) as c FROM categories WHERE user_id = ?", [admin_id])
    if admin_cats[0]["c"] == 0:
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
                (cat[0], cat[1], cat[2], admin_id),
            )

    await db.commit()
    await db.close()
