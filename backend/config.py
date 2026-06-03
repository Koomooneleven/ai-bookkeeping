import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
API_KEY = os.getenv("API_KEY", "change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Railway 持久化卷路径（优先），否则用项目目录
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or os.environ.get("DATA_DIR") or BASE_DIR
DB_PATH = os.path.join(DATA_DIR, "accounting.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
