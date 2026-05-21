import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# ==========================================
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (из .env)
# ==========================================

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "bot_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ai_voice_bot_db")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Admin Settings
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ==========================================
# DERIVED CONFIGURATION
# ==========================================

# Database URL for SQLAlchemy/other tools
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Путь для временного сохранения аудио/видео из Telegram
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================================
# VALIDATION
# ==========================================

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен в .env файле")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY не установлен в .env файле")
if not DB_PASSWORD:
    raise ValueError("❌ DB_PASSWORD не установлен в .env файле")
