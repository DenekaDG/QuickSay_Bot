# 🎙️ QuickSay - AI Voice Bot

**Telegram-бот для обработки голосовых сообщений и видео с ИИ**

---

## 📋 Содержание
1. [Описание](#описание)
2. [Установка](#установка)
3. [Конфигурация](#конфигурация)
4. [Использование](#использование)
5. [Архитектура](#архитектура)
6. [Исправленные ошибки](#исправленные-ошибки)

---

## 📖 Описание

**QuickSay** — интеллектуальный Telegram-бот, который:
- ✅ Преобразует голосовые сообщения в текст (через GROQ Whisper)
- ✅ Обрабатывает текст с ИИ в 7 режимах:
  - 📝 **Summary** — конспект
  - 🎨 **Creative** — творческий пересказ  
  - 💼 **Meeting** — протокол встречи
  - ⚡ **Insight** — инсайт в одну строку
  - ✍️ **Editor** — улучшение текста
  - 🧠 **Opponent** — критический анализ
  - 🌱 **Diary** — анализ дневника
- 🌐 Переводит на 6 языков (UA, EN, DE, FR, ES, IT)
- 💳 Система учета баланса в минутах
- 👨‍💼 Панель администратора для управления пользователями

---

## 🚀 Установка

### Требования
- Python 3.10+
- Docker & Docker Compose
- FFmpeg и FFprobe

### Шаг 1: Клонирование репозитория
```bash
git clone <repo_url>
cd ai_voice_bot
```

### Шаг 2: Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### Шаг 3: Установка зависимостей
```bash
pip install -r requirements.txt
```

### Шаг 4: Инициализация БД
```bash
python db/database.py
```

---

## ⚙️ Конфигурация

### 1. Создание `.env` файла

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_from_botfather

# API Keys
GROQ_API_KEY=your_groq_api_key

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_USER=bot_admin
DB_PASSWORD=your_secure_password
DB_NAME=ai_voice_bot_db

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Admin Settings
ADMIN_ID=your_telegram_id

# Environment
ENVIRONMENT=production
```

### 2. Получение токенов

**Telegram Bot Token:**
- Напишите [@BotFather](https://t.me/botfather) в Telegram
- Команда `/newbot` и следуйте инструкциям
- Скопируйте токен в `BOT_TOKEN`

**GROQ API Key:**
- Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
- Создайте API ключ
- Скопируйте в `GROQ_API_KEY`

---

## 🐳 Использование с Docker

### Запуск всего стека:
```bash
docker-compose up -d
```

Это запустит:
- **Redis** (6379) — брокер Celery
- **PostgreSQL** (5432) — база данных
- **Bot** — основной Telegram-бот
- **Worker** — фоновый обработчик (Celery)
- **pgAdmin** (8585) — управление БД

### Остановка:
```bash
docker-compose down
```

### Просмотр логов:
```bash
docker-compose logs -f bot
docker-compose logs -f worker
```

---

## 🎮 Использование

### Запуск локально (без Docker):

```bash
# Убедитесь что Redis и PostgreSQL запущены локально

# Терминал 1: Запуск бота
python bot.py

# Терминал 2: Запуск worker
celery -A tasks.celery_app worker --loglevel=info --pool=solo
```

### Команды бота

| Команда | Описание |
|---------|---------|
| `/start` | Запуск бота, регистрация пользователя |
| `/settings` | Выбор режима обработки |
| `/admin_stats` | Статистика (только админ) |
| `/add_minutes [ID] [Минуты]` | Начислить минуты (только админ) |

### Использование в чате

1. Отправьте голосовое сообщение, аудио или видео
2. Выберите режим обработки в меню или командой `/settings`
3. Бот автоматически обработает и вернет результат

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────┐
│   Telegram User Interface          │
│   (aiogram 3.28)                   │
└────────────────┬────────────────────┘
                 │
        ┌────────▼────────┐
        │   bot.py        │
        │  (Main Handler) │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
  Redis     PostgreSQL    Celery
(Queue)     (User Data)   (Tasks)
    │            │            │
    │            ▼            │
    │         📊 Schema:       │
    │         - users table    │
    │         - balance        │
    │         - styles         │
    │                          │
    └──────────┬───────────────┘
               │
        ┌──────▼──────┐
        │  tasks.py   │
        │  (Worker)   │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
  GROQ     FFmpeg    Whisper
 (Chat)    (Video→  (Speech→
           Audio)    Text)
```

### Компоненты

| Файл | Назначение |
|------|-----------|
| `bot.py` | Основной Telegram-бот (handlers, UI) |
| `tasks.py` | Celery tasks для обработки медиа |
| `config.py` | Конфигурация из `.env` |
| `constants.py` | Локализация и промпты ИИ |
| `db/database.py` | Schema БД и инициализация |
| `docker-compose.yml` | Docker stack конфигурация |

---

## 🔒 Безопасность

### ✅ Исправленные проблемы

1. **Открытые секреты** ❌ → ✅
   - **Было:** Hardcoded токены в `config.py`
   - **Исправлено:** Переход на `.env` файл с `python-dotenv`

2. **Дублированная конфигурация** ❌ → ✅
   - **Было:** Противоречивые настройки (localhost vs docker-hosts)
   - **Исправлено:** Единая конфигурация через переменные окружения

3. **Hardcoded ADMIN_ID** ❌ → ✅
   - **Было:** `ADMIN_ID = 276695292` в `bot.py`
   - **Исправлено:** Импорт из `config.py` (из `.env`)

4. **Inconsistent Redis URL** ❌ → ✅
   - **Было:** Hardcoded в `tasks.py`
   - **Исправлено:** Использование `REDIS_URL` из `config.py`

5. **Missing database columns** ❌ → ✅
   - **Было:** Schema БД не совпадала с использованием в коде
   - **Исправлено:** Добавлены поля `ai_style`, `first_name`, `last_name`

### 📋 Рекомендации

- ✅ Никогда не коммитьте `.env` файл (добавлен в `.gitignore`)
- ✅ Используйте `.env.example` как шаблон для новых разработчиков
- ✅ Используйте переменные окружения для всех секретов
- ✅ Регулярно ротируйте API ключи
- ✅ Используйте Docker для изоляции окружения

---

## 🐛 Исправленные ошибки

### 1. Import Error: Missing ADMIN_ID
```python
# ❌ Было
ADMIN_ID = 276695292

# ✅ Стало
from config import ADMIN_ID
```

### 2. Hardcoded Redis URL
```python
# ❌ Было
celery_app = Celery("audio_tasks", 
    broker="redis://redis:6379/0", 
    backend="redis://redis:6379/0")

# ✅ Стало
from config import REDIS_URL
celery_app = Celery("audio_tasks", 
    broker=REDIS_URL, 
    backend=REDIS_URL)
```

### 3. Missing Database Schema
```python
# ❌ Было - таблица без полей ai_style, first_name, last_name

# ✅ Стало
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id BIGINT PRIMARY KEY,
        username VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        ai_style VARCHAR(50) DEFAULT 'summary',
        balance_minutes INT DEFAULT 15,
        is_premium BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
```

### 4. Secrets in Source Code
```bash
# ❌ Было
git add config.py  # with tokens!

# ✅ Стало
# .gitignore
config.py
.env
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте `.env` файл
2. Убедитесь что Docker запущен: `docker ps`
3. Проверьте логи: `docker-compose logs -f`
4. Инициализируйте БД: `python db/database.py`

---

## 📄 Лицензия

MIT License - см. LICENSE файл

---

**Создано с ❤️ для QuickSay Bot**
