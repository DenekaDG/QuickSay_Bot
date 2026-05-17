import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from psycopg2.pool import ThreadedConnectionPool

# Импортируем параметры твоей базы данных напрямую
from config import BOT_TOKEN, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from tasks import process_audio_task

# 1. Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 2. Инициализация Бота, Диспетчера и папок
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 3. Упаковка параметров для psycopg2 в словарь
DB_PARAMS = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT
}

# 4. Инициализация пула соединений PostgreSQL
try:
    db_pool = ThreadedConnectionPool(minconn=1, maxconn=10, **DB_PARAMS)
    logger.info("✅ Пул соединений PostgreSQL успешно запущен.")
except Exception as e:
    logger.critical(f"❌ Не удалось запустить пул БД: {e}")
    raise e

# ==========================================
# ИНТЕРФЕЙС: КЛАВИАТУРЫ И ОНБОРДИНГ
# ==========================================

def get_main_keyboard():
    """Возвращает главное меню стилей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💼 Бизнес (Суть)", callback_data="set_style:business"),
            InlineKeyboardButton(text="📝 Конспект", callback_data="set_style:summary")
        ],
        [
            InlineKeyboardButton(text="🇺🇦 Перевод на UA", callback_data="set_style:translate_ua"),
            InlineKeyboardButton(text="🌐 Другие языки", callback_data="open_languages")
        ],
        [
            InlineKeyboardButton(text="🧘 Философия", callback_data="set_style:philosophy"),
            InlineKeyboardButton(text="🎭 Юмор", callback_data="set_style:humor")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.chat.id
    user_name = message.from_user.first_name or "Друг"
    
    # Автоматическая регистрация пользователя в БД
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (telegram_id, ai_style, balance_minutes)
            VALUES (%s, 'business', 15)
            ON CONFLICT (telegram_id) DO NOTHING;
        """, (user_id,))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

    welcome_text = (
        f"👋 <b>Привет, {user_name}! Я твой умный ИИ-помощник QuickSay.</b>\n\n"
        f"Я умею мгновенно превращать <b>голосовые сообщения, аудиофайлы и кружочки</b> "
        f"в структурированный текст, переводы и выжимки.\n\n"
        f"⚙️ <b>Как это работает?</b>\n"
        f"1. Выбери желаемый стиль обработки на кнопках ниже (по умолчанию стоит <i>Бизнес</i>).\n"
        f"2. Отправь мне любое аудио или видеосообщение.\n"
        f"3. Через пару секунд получи готовый идеальный результат!\n\n"
        f"👇 <b>Выбери стиль обработки прямо сейчас:</b>"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# Меню выбора языков перевода
@dp.callback_query(F.data == "open_languages")
async def open_languages_menu(callback: CallbackQuery):
    lang_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 Английский", callback_data="set_style:lang_en"),
            InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data="set_style:lang_de")
        ],
        [
            InlineKeyboardButton(text="🇵🇱 Польский", callback_data="set_style:lang_pl"),
            InlineKeyboardButton(text="🇪🇸 Испанский", callback_data="set_style:lang_es")
        ],
        [
            InlineKeyboardButton(text="🇫🇷 Французский", callback_data="set_style:lang_fr"),
            InlineKeyboardButton(text="🇮🇹 Итальянский", callback_data="set_style:lang_it")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к стилям", callback_data="back_to_styles")
        ]
    ])
    await callback.message.edit_text("🌐 <b>Выбери язык, на который перевести твоё аудио/видео:</b>", reply_markup=lang_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "back_to_styles")
async def back_to_styles(callback: CallbackQuery):
    await callback.message.edit_text("👇 <b>Выбери стиль обработки прямо сейчас:</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")
    await callback.answer()

# Универсальный обработчик переключения стилей и языков
@dp.callback_query(F.data.startswith("set_style:"))
async def process_style_callback(callback: CallbackQuery):
    style_name = callback.data.split(":")[1]
    user_id = callback.message.chat.id
    
    style_titles = {
        "business": "💼 Бизнес-ассистент",
        "summary": "📝 Подробный конспект",
        "translate_ua": "🇺🇦 Перевод на украинский",
        "philosophy": "🧘 Философский анализ",
        "humor": "🎭 Юмористический взгляд",
        "lang_en": "🇬🇧 Перевод на английский",
        "lang_de": "🇩🇪 Перевод на немецкий",
        "lang_pl": "🇵🇱 Перевод на польский",
        "lang_es": "🇪🇸 Перевод на испанский",
        "lang_fr": "🇫🇷 Перевод на французский",
        "lang_it": "🇮🇹 Перевод на итальянский"
    }
    
    selected_title = style_titles.get(style_name, "💼 Бизнес-ассистент")
    
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET ai_style = %s WHERE telegram_id = %s", (style_name, user_id))
        conn.commit()
        cur.close()
        
        await callback.answer(f"Выбран стиль: {selected_title}")
        await callback.message.answer(f"🎯 <b>Готово!</b> Теперь все файлы я обрабатываю в стиле: <b>{selected_title}</b>.")
    except Exception as e:
        logger.error(f"Ошибка смены стиля для {user_id}: {e}")
        await callback.answer("❌ Ошибка при смене стиля.")
    finally:
        if conn:
            db_pool.putconn(conn)

# ==========================================
# ОБРАБОТКА МЕДИАФАЙЛОВ
# ==========================================

@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(message: Message):
    user_id = message.chat.id
    conn = None
    user_style = "business"
    
    # Извлекаем текущий стиль из БД
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res:
            user_style = res[0]
    except Exception as e:
        logger.error(f"Ошибка получения профиля для {user_id}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)
            
    # Определяем тип файла и расширение
    if message.voice:
        file_id = message.voice.file_id
        file_ext = "ogg"
    elif message.audio:
        file_id = message.audio.file_id
        file_ext = "mp3"
    elif message.video:
        file_id = message.video.file_id
        file_ext = "mp4"
    elif message.video_note:
        file_id = message.video_note.file_id
        file_ext = "mp4"
    else:
        return

    await message.answer("📥 Файл получен. Начинаю скачивание на сервер...")

    # Скачиваем файл на сервер во временную папку
    try:
        file_info = await bot.get_file(file_id)
        file_path_on_server = os.path.join(DOWNLOAD_DIR, f"{file_id}.{file_ext}")
        await bot.download_file(file_info.file_path, file_path_on_server)
    except Exception as e:
        logger.error(f"Ошибка скачивания файла от {user_id}: {e}")
        return await message.answer("❌ Не удалось получить файл из Telegram. Попробуйте еще раз.")

    # Передаём задачу в фоновую очередь Celery
    process_audio_task.delay(file_path_on_server, user_id, user_style)
    await message.answer("⏳ Задача добавлена в очередь обработки. Скоро прилетит ответ!")

if __name__ == "__main__":
    logger.info("🚀 Бот QuickSay успешно запущен.")
    dp.run_polling(bot)