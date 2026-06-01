import aiosqlite
import os
from config import DB_PATH


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

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL        NOT NULL,
            currency    VARCHAR(10) NOT NULL DEFAULT 'CNY',
            item_name   VARCHAR(255) NOT NULL,
            category    VARCHAR(50),
            trans_date  TEXT        NOT NULL,  -- YYYY-MM-DD HH:MM 格式
            notes       TEXT,
            created_at  DATETIME    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  VARCHAR(50) UNIQUE NOT NULL,
            icon  VARCHAR(10),
            color VARCHAR(7)
        );

        INSERT OR IGNORE INTO categories (name, icon, color) VALUES
            ('餐饮', '🍽️', '#FF6B6B'),
            ('交通', '🚗', '#4ECDC4'),
            ('购物', '🛒', '#45B7D1'),
            ('娱乐', '🎮', '#96CEB4'),
            ('居住', '🏠', '#FFEAA7'),
            ('医疗', '💊', '#DDA0DD'),
            ('教育', '📚', '#98D8C8'),
            ('其他', '📌', '#CCCCCC');
    """)

    await db.commit()
    await db.close()
