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

### Запуск всего стека

```bash
docker-compose up -d
```

Это запустит:

- **Redis** (6379) — брокер Celery
- **PostgreSQL** (5432) — база данных
- **Bot** — основной Telegram-бот
- **Worker** — фоновый обработчик (Celery)
- **pgAdmin** (8585) — управление БД

### Остановка

```bash
docker-compose down
```

### Просмотр логов

```bash
docker-compose logs -f bot
docker-compose logs -f worker
```

---

## 🎮 Использование

### Запуск локально (без Docker)

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

## � Статус функционала

### ✅ Полностью реализовано

- [x] Распознавание речи (Groq Whisper API)
- [x] 7 режимов обработки текста (Summary, Creative, Meeting, Insight, Editor, Opponent, Diary)
- [x] Перевод на 6 языков (UA, EN, DE, FR, ES, IT)
- [x] Интеграция платежей (CryptoBot)
- [x] Система баланса в минутах
- [x] Мультиязычный интерфейс (RU, UA, EN)
- [x] Docker контейнеризация
- [x] PostgreSQL база данных с пулом соединений
- [x] Celery для асинхронной обработки
- [x] Панель администратора

### 🔄 В разработке / Требуют улучшений

- [ ] Type safety и null-checks в обработчиках
- [ ] Логирование в файлы (Rotating File Handler)
- [ ] Unit и интеграционные тесты
- [ ] Мониторинг Celery (Flower)
- [ ] Документирование API
- [ ] CI/CD pipeline (GitHub Actions)

### 🚀 Планируется

- [ ] Web-интерфейс для управления аккаунтом
- [ ] Кэширование результатов обработки
- [ ] Статистика использования
- [ ] Интеграция с Stripe/PayPal
- [ ] Расширенные режимы анализа текста
- [ ] Синтез речи (Text-to-Speech)
- [ ] Мобильное приложение
- [ ] Multi-language support для более 10 языков

---

## 📈 План развития проекта (Roadmap)

### Phase 1: Стабилизация и качество кода (июнь 2026)

#### 1.1 Type Safety и Error Handling

```bash
# Приоритет: ВЫСОКИЙ
# Проблемы:
- Потенциальные None-errors в callback.message
- Небезопасное разделение callback.data
- Отсутствие валидации пользовательского ввода

# Решение:
- Добавить type hints (mypy)
- Обернуть опасные операции в try-except
- Добавить классы для валидации (Pydantic)
```

#### 1.2 Логирование и Мониторинг

```bash
# Приоритет: ВЫСОКИЙ
# Что сделать:
1. Настроить логирование в файлы (/app/logs)
2. Добавить ротацию логов (RotatingFileHandler)
3. Интегрировать Flower для мониторинга Celery
4. Настроить централизованное логирование (ELK stack опционально)

# Файлы для изменения:
- bot.py: добавить FileHandler
- tasks.py: улучшить logging для Celery
- docker-compose.yml: добавить Flower сервис
```

#### 1.3 Тестирование

```bash
# Приоритет: ВЫСОКИЙ
# Что добавить:
1. Unit-тесты для database.py (pytest)
2. Интеграционные тесты для bot handlers
3. Тесты для webhook подписей (webhook_server.py)
4. Mock-тесты для Groq API

# Структура:
tests/
  ├── unit/
  │   ├── test_database.py
  │   ├── test_config.py
  │   └── test_payment_service.py
  ├── integration/
  │   ├── test_bot_handlers.py
  │   └── test_celery_tasks.py
  └── conftest.py
```

### Phase 2: Функциональность и UX (июль-август 2026)

#### 2.1 Web-интерфейс

```bash
# Приоритет: СРЕДНИЙ
# Компоненты:
1. Личный кабинет пользователя
   - История обработок
   - Управление балансом
   - Скачивание результатов
2. Admin Dashboard
   - Статистика пользователей
   - Управление платежами
   - Просмотр логов

# Стек:
- Frontend: React + Tailwind CSS
- Backend: FastAPI/Django REST
- Интеграция с существующей БД PostgreSQL
```

#### 2.2 Расширенные AI-режимы

```bash
# Приоритет: СРЕДНИЙ
# Новые режимы:
1. Email Draft - сформировать письмо из речи
2. Social Post - подготовить пост для соцсетей
3. Hashtag Generator - генерация хэштегов
4. Code Documenter - документирование кода
5. Language Tutor - корректировка грамматики

# API: Groq Llama с улучшенными промптами
```

#### 2.3 Кэширование результатов

```bash
# Приоритет: СРЕДНИЙ
# Что сделать:
1. Redis кэш для результатов обработки
   - Время жизни: 7 дней
   - Ключ: hash(user_id + file_id + mode)
2. Оптимизация БД запросов
3. Мониторинг cache hit rate

# Код:
from tasks import cache_result
@cache_result(ttl=7*24*3600)
def process_audio_task(...):
    ...
```

### Phase 3: Интеграции и расширение (сентябрь-октябрь 2026)

#### 3.1 Платежные системы

```bash
# Приоритет: ВЫСОКИЙ
# Текущая интеграция:
- CryptoBot (Crypto платежи)

# Планируется добавить:
1. Stripe (Credit/Debit карты)
2. PayPal
3. Яндекс.Касса
4. Wise (для международных переводов)

# Структура:
payment_service.py
├── BasePaymentProvider (ABC)
├── CryptoBotProvider
├── StripeProvider
├── PayPalProvider
└── YandexKassaProvider
```

#### 3.2 Интеграция с месенджерами

```bash
# Приоритет: СРЕДНИЙ
# Добавить поддержку:
1. WhatsApp Bot
2. Discord Bot
3. Slack Bot
4. Viber Bot

# Использовать queueing system для unified backend
```

#### 3.3 Text-to-Speech (TTS)

```bash
# Приоритет: НИЗКИЙ
# Функциональность:
- Озвучка результатов обработки
- Выбор голоса и языка
- Сохранение аудиофайла

# API: Google Cloud TTS / ElevenLabs / Groq (если будет)
```

### Phase 4: Оптимизация и масштабирование (ноябрь-декабрь 2026)

#### 4.1 Производительность

```bash
# Приоритет: ВЫСОКИЙ
# Оптимизировать:
1. Обработку больших видеофайлов (>100MB)
2. Параллельную обработку (шеринг воркеров)
3. Кэширование моделей Whisper локально
4. Использование GPU для обработки (если доступно)

# Метрики:
- Время обработки: < 30 сек для 5-min audio
- Throughput: > 100 запросов/минуту
- Memory usage: < 500MB на воркер
```

#### 4.2 Масштабирование архитектуры

```bash
# Приоритет: СРЕДНИЙ
# Изменения:
1. Kubernetes deployment вместо Docker Compose
2. Load balancer (nginx)
3. Auto-scaling Celery workers
4. Message queue redundancy (RabbitMQ backup)
5. Database replication (PostgreSQL HA)

# Структура:
k8s/
├── bot-deployment.yaml
├── worker-deployment.yaml
├── webhook-deployment.yaml
├── postgres-statefulset.yaml
├── redis-statefulset.yaml
└── service.yaml
```

#### 4.3 Безопасность

```bash
# Приоритет: ВЫСОКИЙ
# Улучшить:
1. Rate limiting для API
2. CAPTCHA для защиты от ботов
3. Encryption for sensitive data
4. Audit logging для всех операций
5. 2FA для админ панели
6. DDoS protection

# Инструменты:
- slowapi для rate limiting
- Redis для сессий
- bcrypt для паролей
```

---

## 🛠️ Техстек и зависимости

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Bot Framework | aiogram | 3.28.2 |
| Async Queue | Celery | 5.6.3 |
| Message Broker | Redis | Latest |
| Database | PostgreSQL | 15+ |
| Speech Recognition | Groq Whisper | API v1 |
| LLM | Groq Llama 3.1 | API v1 |
| Payment | CryptoBot | API v1 |
| Web Server | aiohttp | 3.13.5 |
| ORM | psycopg2 | 2.9.12 |

---

## 💡 Советы для разработчиков

### Локальная разработка

```bash
# 1. Запустить зависимости в Docker
docker-compose -f docker-compose.dev.yml up -d

# 2. Установить зависимости
pip install -r requirements-dev.txt

# 3. Запустить тесты
pytest tests/ -v

# 4. Запустить в режиме разработки
python bot.py  # в отдельном терминале
celery -A tasks.celery_app worker --loglevel=debug  # в другом терминале
```

### Обновление зависимостей

```bash
# Проверить outdated пакеты
pip list --outdated

# Обновить все
pip install --upgrade -r requirements.txt

# Пересоздать requirements.txt
pip freeze > requirements.txt
```

### Добавление новой AI-режимности

```python
# 1. Добавить в PROCESSING_MODES в constants.py
PROCESSING_MODES = {
    "my_new_mode": {
        "emoji": "🆕",
        "system_prompt": "...",
        "description": "..."
    }
}

# 2. Добавить кнопку в bot.py
keyboard = [
    [InlineKeyboardButton(text="🆕 My New Mode", callback_data="mode:my_new_mode")]
]

# 3. Обновить БД для новых пользователей (в database.py)
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте `.env` файл на правильность значений
2. Убедитесь что Docker запущен: `docker ps`
3. Посмотрите логи: `docker-compose logs -f bot`
4. Переинициализируйте БД: `python db/database.py`
5. Проверьте наличие требуемых папок: `mkdir -p downloads logs`

### Часто возникающие ошибки

| Ошибка | Решение |
|--------|---------|
| `Connection refused on Redis` | Убедитесь что Redis запущен: `docker-compose ps redis` |
| `Database password authentication failed` | Проверьте DB_PASSWORD в `.env` |
| `No such module: 'aiogram'` | Запустите `pip install -r requirements.txt` |
| `Groq API key invalid` | Проверьте GROQ_API_KEY в `.env` |

---

## 📄 Лицензия

MIT License - см. LICENSE файл

---

**Последнее обновление:** май 2026  
**Статус:** ✅ Стабильный, активно разрабатывается  
**Создано с ❤️ для QuickSay Bot**
