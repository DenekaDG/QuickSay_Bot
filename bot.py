import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, BotCommandScopeChat
from psycopg2.pool import ThreadedConnectionPool

from config import BOT_TOKEN, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, ADMIN_ID
from tasks import process_audio_task
from payment_service import generate_payment_link

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DB_PARAMS = {
    "dbname": DB_NAME, "user": DB_USER, "password": DB_PASSWORD, "host": DB_HOST, "port": DB_PORT
}

# Объявляем переменную пула глобально, инициализировать будем в main()
db_pool = None

# ==========================================
# РАСШИРЕННЫЙ СЛОВАРЬ МУЛЬТИЯЗЫЧНОЙ ЛОКАЛИЗАЦИИ
# ==========================================
LOCALIZATION = {
    "en": {
        "welcome": "👋 <b>Hello, {name}! I am your AI Assistant QuickSay.</b>\n\nI turn voice messages and video notes into text, summaries, protocols, and translations.\n\n👇 <b>Choose processing mode:</b>",
        "settings_title": "⚙️ <b>Choose audio/video processing mode:</b>",
        "choose_lang": "🌐 <b>Choose translation language:</b>",
        "btn_summary": "📝 Summary", "btn_creative": "🎨 Creative",
        "btn_meeting": "💼 Minutes", "btn_insider": "⚡ Insight", "btn_editor": "✍️ Editor",
        "btn_opponent": "🧠 Opponent", "btn_diary": "🌱 Diary",
        "btn_translate": "🌐 Translation", "btn_back": "⬅️ Back",
        "menu_desc_start": "Instruction", "menu_desc_settings": "Change mode",
        "status_changed": "🎯 <b>Done!</b> Current mode: <b>{style}</b>.",
        "file_received": "📥 File received. Downloading to server...",
        "processing": "⏳ Processing audio in background. Expect the result shortly!",
        "download_error": "❌ Failed to download the file.", "db_error": "❌ Database error.",
        "style_summary": "📝 Summary", "style_creative": "🎨 Creative",
        "style_meeting": "💼 Meeting Minutes Protocol", "style_insider": "⚡ One-Sentence Insight", "style_editor": "✍️ Smart Text Editor",
        "style_opponent": "🧠 Brainstorm Opponent", "style_diary": "🌱 Personal Diary",
        "style_lang_ua": "🇺🇦 Translation to Ukrainian", "style_lang_en": "🇬🇧 Translation to English",
        "style_lang_de": "🇩🇪 Translation to German", "style_lang_fr": "🇫🇷 Translation to French",
        "style_lang_es": "🇪🇸 Translation to Spanish", "style_lang_it": "🇮🇹 Translation to Italian",
        
        "balance_msg": "💳 <b>Your current balance:</b> <code>{minutes} minutes</code>.\n\nNeed more time? Choose a top-up package below:",
        "btn_buy_minutes": "💎 Top up balance",
        "btn_pack_100": "📦 Package: 100 min ($2.00)",
        "btn_pack_300": "🚀 Package: 300 min ($5.00)",
        "invoice_created": "✨ <b>Invoice created successfully!</b>\n\nTo pay with your credit card or crypto, click the button below and open Telegram Wallet.",
        "btn_pay_now": "💳 Pay via CryptoBot",
        "menu_desc_balance": "Check balance"
    },
    "ru": {
        "welcome": "👋 <b>Привет, {name}! Я твой ИИ-ассистент QuickSay.</b>\n\nПревращаю аудиосообщения и кружочки в текст, выжимки, протоколы и переводы.\n\n👇 <b>Выбери режим обработки:</b>",
        "settings_title": "⚙️ <b>Выбери режим обработки аудио/видео:</b>",
        "choose_lang": "🌐 <b>Выбери язык перевода:</b>",
        "btn_summary": "📝 Суть", "btn_creative": "🎨 Креатив",
        "btn_meeting": "💼 Протокол", "btn_insider": "⚡ Инсайт", "btn_editor": "✍️ Редактор",
        "btn_opponent": "🧠 Оппонент", "btn_diary": "🌱 Дневник",
        "btn_translate": "🌐 Перевод", "btn_back": "⬅️ Назад",
        "menu_desc_start": "Инструкция", "menu_desc_settings": "Выбор режима",
        "status_changed": "🎯 <b>Готово!</b> Текущий режим: <b>{style}</b>.",
        "file_received": "📥 Файл получен. Начинаю скачивание...",
        "processing": "⏳ Обрабатываю аудио в фоне. Скоро прилетит ответ!",
        "download_error": "❌ Не удалось получить файл.", "db_error": "❌ Ошибка базы данных.",
        "style_summary": "📝 Суть", "style_creative": "🎨 Креатив",
        "style_meeting": "💼 Протокол встречи", "style_insider": "⚡ Инсайт в одну строку", "style_editor": "✍️ Умный текстовый редактор",
        "style_opponent": "🧠 Критический оппонент", "style_diary": "🌱 Анализ личного дневника",
        "style_lang_ua": "🇺🇦 Перевод на украинский", "style_lang_en": "🇬🇧 Перевод на английский",
        "style_lang_de": "🇩🇪 Перевод на немецкий", "style_lang_fr": "🇫🇷 Перевод на французский",
        "style_lang_es": "🇪🇸 Перевод на испанский", "style_lang_it": "🇮🇹 Перевод на итальянский",
        
        "balance_msg": "💳 <b>Твой текущий баланс:</b> <code>{minutes} мин.</code>\n\nЗаканчивается время? Ты можешь пополнить баланс, выбрав пакет ниже:",
        "btn_buy_minutes": "💎 Пополнить баланс",
        "btn_pack_100": "📦 Пакет: 100 мин ($2.00)",
        "btn_pack_300": "🚀 Пакет: 300 мин ($5.00)",
        "invoice_created": "✨ <b>Счет успешно сгенерирован!</b>\n\nДля оплаты обычной банковской картой или криптой нажмите кнопку ниже и перейдите в кошелек Telegram Wallet.",
        "btn_pay_now": "💳 Оплатить через CryptoBot",
        "menu_desc_balance": "Баланс"
    },
    "uk": {
        "welcome": "👋 <b>Привіт, {name}! Я твій ІІ-асистент QuickSay.</b>\n\nПеретворюю аудіоповідомлення та кружечки на текст, вижимки, протоколі та переклади.\n\n👇 <b>Вибери режим обробки:</b>",
        "settings_title": "⚙️ <b>Вибери режим обробки аудіо/відео:</b>",
        "choose_lang": "🌐 <b>Вибери мову перекладу:</b>",
        "btn_summary": "📝 Суть", "btn_creative": "🎨 Креатив",
        "btn_meeting": "💼 Протокол", "btn_insider": "⚡ Інсайт", "btn_editor": "✍️ Редактор",
        "btn_opponent": "🧠 Опонент", "btn_diary": "🌱 Щоденник",
        "btn_translate": "🌐 Переклад", "btn_back": "⬅️ Назад",
        "menu_desc_start": "Інструкція", "menu_desc_settings": "Вибір режиму",
        "status_changed": "🎯 <b>Готово!</b> Поточний режим: <b>{style}</b>.",
        "file_received": "📥 Файл отримано. Починаю завантаження...",
        "processing": "⏳ Обробляю аудіо у фоні. Скоро прилетить відповідь!",
        "download_error": "❌ Не вдалося отримати файл.", "db_error": "❌ Помилка бази даних.",
        "style_summary": "📝 Суть", "style_creative": "🎨 Креатив",
        "style_meeting": "💼 Протокол зустрічі", "style_insider": "⚡ Інсайт в один рядок", "style_editor": "✍️ Розумний текстовий редактор",
        "style_opponent": "🧠 Критичний опонент", "style_diary": "🌱 Аналіз особистого щоденника",
        "style_lang_ua": "🇺🇦 Переклад на українську", "style_lang_en": "🇬🇧 Переклад на англійську",
        "style_lang_de": "🇩🇪 Переклад на німецьку", "style_lang_fr": "🇫🇷 Переклад на французьку",
        "style_lang_es": "🇪🇸 Переклад на іспанську", "style_lang_it": "🇮🇹 Переклад на італійську",
        
        "balance_msg": "💳 <b>Твій поточний баланс:</b> <code>{minutes} хв.</code>\n\nЗакінчується час? Ти можеш поповнить баланс, обравши пакет нижче:",
        "btn_buy_minutes": "💎 Поповнити баланс",
        "btn_pack_100": "📦 Пакет: 100 хв ($2.00)",
        "btn_pack_300": "🚀 Пакет: 300 хв ($5.00)",
        "invoice_created": "✨ <b>Рахунок успішно згенеровано!</b>\n\nДля оплати звичайною банківською картою або криптою натисніть кнопку нижче та перейдіть у гаманець Telegram Wallet.",
        "btn_pay_now": "💳 Оплатити через CryptoBot",
        "menu_desc_balance": "Баланс"
    }
}

def get_lang(lang_code):
    if lang_code in LOCALIZATION:
        return LOCALIZATION[lang_code]
    return LOCALIZATION["en"]

# ==========================================
# СЕТКА КНОПОК ИНТЕРФЕЙСА
# ==========================================

def get_main_keyboard(current_style="summary", lang="en"):
    lang_dict = get_lang(lang)
    is_translation = str(current_style).startswith("lang_")
    
    t_summary = f"{lang_dict['btn_summary']} ✅" if current_style == "summary" else lang_dict['btn_summary']
    t_creative = f"{lang_dict['btn_creative']} ✅" if current_style == "creative" else lang_dict['btn_creative']
    t_meeting = f"{lang_dict['btn_meeting']} ✅" if current_style == "meeting" else lang_dict['btn_meeting']
    t_insider = f"{lang_dict['btn_insider']} ✅" if current_style == "insider" else lang_dict['btn_insider']
    t_editor = f"{lang_dict['btn_editor']} ✅" if current_style == "editor" else lang_dict['btn_editor']
    t_opponent = f"{lang_dict['btn_opponent']} ✅" if current_style == "opponent" else lang_dict['btn_opponent']
    t_diary = f"{lang_dict['btn_diary']} ✅" if current_style == "diary" else lang_dict['btn_diary']
    t_translate = f"{lang_dict['btn_translate']} ✅" if is_translation else lang_dict['btn_translate']

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_summary, callback_data="set_style:summary"),
         InlineKeyboardButton(text=t_creative, callback_data="set_style:creative")],
        [InlineKeyboardButton(text=t_meeting, callback_data="set_style:meeting"),
         InlineKeyboardButton(text=t_insider, callback_data="set_style:insider"),
         InlineKeyboardButton(text=t_editor, callback_data="set_style:editor")],
        [InlineKeyboardButton(text=t_opponent, callback_data="set_style:opponent"),
         InlineKeyboardButton(text=t_diary, callback_data="set_style:diary")],
        [InlineKeyboardButton(text=t_translate, callback_data="open_languages")],
        [InlineKeyboardButton(text=lang_dict["btn_buy_minutes"], callback_data="open_billing")]
    ])

def get_languages_keyboard(current_style="summary", lang="en"):
    lang_dict = get_lang(lang)
    text_ua = "🇺🇦 UA ✅" if current_style == "lang_ua" else "🇺🇦 UA"
    text_en = "🇬🇧 EN ✅" if current_style == "lang_en" else "🇬🇧 EN"
    text_de = "🇩🇪 DE ✅" if current_style == "lang_de" else "🇩🇪 DE"
    text_fr = "🇫🇷 FR ✅" if current_style == "lang_fr" else "🇫🇷 FR"
    text_es = "🇪🇸 ES ✅" if current_style == "lang_es" else "🇪🇸 ES"
    text_it = "🇮🇹 IT ✅" if current_style == "lang_it" else "🇮🇹 IT"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text_ua, callback_data="set_style:lang_ua"),
         InlineKeyboardButton(text=text_en, callback_data="set_style:lang_en"),
         InlineKeyboardButton(text=text_de, callback_data="set_style:lang_de")],
        [InlineKeyboardButton(text=text_fr, callback_data="set_style:lang_fr"),
         InlineKeyboardButton(text=text_es, callback_data="set_style:lang_es"),
         InlineKeyboardButton(text=text_it, callback_data="set_style:lang_it")],
        [InlineKeyboardButton(text=lang_dict["btn_back"], callback_data="back_to_styles")]
    ])

def get_billing_keyboard(lang="en"):
    lang_dict = get_lang(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lang_dict["btn_pack_100"], callback_data="buy_pack:100")],
        [InlineKeyboardButton(text=lang_dict["btn_pack_300"], callback_data="buy_pack:300")],
        [InlineKeyboardButton(text=lang_dict["btn_back"], callback_data="back_to_styles")]
    ])

# ==========================================
# ОБРАБОТЧИКИ КОМАНД
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.chat.id
    user_name = message.from_user.first_name or "Friend" if message.from_user else "Friend"
    user_lang = message.from_user.language_code or "en" if message.from_user else "en"
    lang_dict = get_lang(user_lang)
    
    username = message.from_user.username if message.from_user else None
    first_name = message.from_user.first_name if message.from_user else None
    last_name = message.from_user.last_name if message.from_user else None
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (telegram_id, ai_style, balance_minutes, username, first_name, last_name)
            VALUES (%s, 'summary', 15, %s, %s, %s) 
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = EXCLUDED.username, 
                first_name = EXCLUDED.first_name, 
                last_name = EXCLUDED.last_name;
        """, (user_id, username, first_name, last_name))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Ошибка регистрации {user_id}: {e}")
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)

    try:
        commands = [
            BotCommand(command="/start", description=lang_dict["menu_desc_start"]),
            BotCommand(command="/balance", description=lang_dict["menu_desc_balance"]),
            BotCommand(command="/settings", description=f"[{lang_dict['btn_summary']}] {lang_dict['menu_desc_settings']} ⚙️")
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
    except Exception as e:
        logger.error(f"Ошибка установки меню для {user_id}: {e}")

    await message.answer(
        lang_dict["welcome"].format(name=user_name), 
        reply_markup=get_main_keyboard("summary", user_lang), parse_mode="HTML"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.chat.id
    user_lang = message.from_user.language_code or "en" if message.from_user else "en"
    lang_dict = get_lang(user_lang)
    current_style = "summary"
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res:
            current_style = res[0]
    except Exception as e:
        logger.error(f"Ошибка получения стиля: {e}")
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)

    await message.answer(lang_dict["settings_title"], reply_markup=get_main_keyboard(current_style, user_lang), parse_mode="HTML")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.chat.id
    user_lang = message.from_user.language_code or "en" if message.from_user else "en"
    lang_dict = get_lang(user_lang)
    balance_minutes = 0
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res:
            balance_minutes = res[0]
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)
            
    await message.answer(
        lang_dict["balance_msg"].format(minutes=balance_minutes),
        reply_markup=get_billing_keyboard(user_lang),
        parse_mode="HTML"
    )

# ==========================================
# ОБРАБОТКА CALLBACK-ЗАПРОСОВ
# ==========================================

@dp.callback_query(F.data == "open_billing")
async def open_billing_menu(callback: CallbackQuery):
    if not callback.message or not isinstance(callback.message, Message) or not callback.message.chat:
        return
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    balance_minutes = 0
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res: 
            balance_minutes = res[0]
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if conn and db_pool: 
            db_pool.putconn(conn)

    await callback.message.edit_text(
        lang_dict["balance_msg"].format(minutes=balance_minutes),
        reply_markup=get_billing_keyboard(user_lang),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("buy_pack:"))
async def process_buy_package(callback: CallbackQuery):
    if not callback.message or not isinstance(callback.message, Message) or not callback.message.chat:
        return
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    
    try:
        minutes_pack = int((callback.data or "").split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return
    
    await callback.answer("⏳ ...")
    
    try:
        pay_url = await generate_payment_link(user_id=user_id, minutes_package=minutes_pack)
        
        pay_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=lang_dict["btn_pay_now"], url=pay_url)],
            [InlineKeyboardButton(text=lang_dict["btn_back"], callback_data="open_billing")]
        ])
        
        await callback.message.edit_text(
            lang_dict["invoice_created"],
            reply_markup=pay_kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка создания инвойса для {user_id}: {e}")
        await callback.message.answer(lang_dict["db_error"])

@dp.callback_query(F.data == "open_languages")
async def open_languages_menu(callback: CallbackQuery):
    if not callback.message or not isinstance(callback.message, Message) or not callback.message.chat:
        await callback.answer("❌ Error", show_alert=True)
        return
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    current_style = "summary"
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res:
            current_style = res[0]
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)

    await callback.message.edit_text(lang_dict["choose_lang"], reply_markup=get_languages_keyboard(current_style, user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "back_to_styles")
async def back_to_styles(callback: CallbackQuery):
    if not callback.message or not isinstance(callback.message, Message) or not callback.message.chat:
        await callback.answer("❌ Error", show_alert=True)
        return
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    current_style = "summary"
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res:
            current_style = res[0]
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)

    await callback.message.edit_text(
        lang_dict["welcome"].format(name=callback.from_user.first_name or "Friend"), 
        reply_markup=get_main_keyboard(current_style, user_lang), parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("set_style:"))
async def process_style_callback(callback: CallbackQuery):
    if not callback.data or not callback.message or not isinstance(callback.message, Message) or not callback.message.chat:
        await callback.answer("❌ Error", show_alert=True)
        return
    style_name = callback.data.split(":")[1]
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    
    style_titles_short = {
        "summary": lang_dict["btn_summary"], "creative": lang_dict["btn_creative"],
        "meeting": lang_dict["btn_meeting"], "insider": lang_dict["btn_insider"], "editor": lang_dict["btn_editor"],
        "opponent": lang_dict["btn_opponent"], "diary": lang_dict["btn_diary"],
        "lang_ua": "🇺🇦 UA", "lang_en": "🇬🇧 EN", "lang_de": "🇩🇪 DE",
        "lang_fr": "🇫🇷 FR", "lang_es": "🇪🇸 ES", "lang_it": "🇮🇹 IT"
    }
    
    selected_short = style_titles_short.get(style_name, lang_dict["btn_summary"])
    selected_full = lang_dict.get(f"style_{style_name}", lang_dict["style_summary"])
    
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET ai_style = %s WHERE telegram_id = %s", (style_name, user_id))
        conn.commit()
        cur.close()
        
        commands = [
            BotCommand(command="/start", description=lang_dict["menu_desc_start"]),
            BotCommand(command="/balance", description=lang_dict["menu_desc_balance"]),
            BotCommand(command="/settings", description=f"[{selected_short}] {lang_dict['menu_desc_settings']} ⚙️")
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
        
        await callback.answer(f"{selected_short}")
        await callback.message.answer(lang_dict["status_changed"].format(style=selected_full), parse_mode="HTML")
        
        if style_name.startswith("lang_"):
            await callback.message.edit_reply_markup(reply_markup=get_languages_keyboard(style_name, user_lang))
        else:
            await callback.message.edit_reply_markup(reply_markup=get_main_keyboard(style_name, user_lang))
            
    except Exception as e:
        logger.error(f"Ошибка смены стиля: {e}")
        await callback.answer(lang_dict["db_error"])
    finally:
        if conn and db_pool:
            db_pool.putconn(conn)

# ==========================================
# ПАНЕЛЬ АДМИНИСТРАТОРА
# ==========================================

@dp.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    if not message.from_user or message.from_user.id != ADMIN_ID: 
        return
    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users;")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT SUM(balance_minutes) FROM users;")
        total_minutes = cur.fetchone()[0] or 0
        cur.close()
        
        await message.answer(f"📊 <b>Статистика QuickSay Bot</b>\n\n👥 Всего в БД: <code>{total_users}</code>\n⏳ Общий баланс: <code>{total_minutes} мин.</code>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка админ-статистики: {e}")
        await message.answer("❌ Ошибка статистики.")
    finally:
        if conn and db_pool: 
            db_pool.putconn(conn)

@dp.message(Command("add_minutes"))
async def cmd_add_minutes(message: Message):
    if not message.from_user or message.from_user.id != ADMIN_ID: 
        return
    
    args = (message.text or "").split()
    if len(args) != 3:
        await message.answer("⚠️ Формат: <code>/add_minutes [ID] [Минуты]</code>", parse_mode="HTML")
        return
        
    try: 
        target_user_id = int(args[1])
        minutes_to_add = int(args[2])
    except ValueError:
        await message.answer("⚠️ ID пользователя и минуты должны быть целыми числами!")
        return

    conn = None
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s;", (target_user_id,))
        if not cur.fetchone():
            await message.answer("❌ Нет такого юзера в БД.")
            cur.close()
            return
            
        cur.execute("UPDATE users SET balance_minutes = balance_minutes + %s WHERE telegram_id = %s;", (minutes_to_add, target_user_id))
        conn.commit()
        cur.close()
        
        await message.answer(f"✅ Пользователю <code>{target_user_id}</code> начислено: <b>+{minutes_to_add} мин.</b>", parse_mode="HTML")
        
        try: 
            await bot.send_message(
                chat_id=target_user_id, 
                text=f"🎁 <b>Вам начислены бонусные минуты!</b>\nБаланс увеличен на: <b>+{minutes_to_add} мин.</b>", 
                parse_mode="HTML"
            )
        except Exception as msg_err:
            logger.warning(f"Не удалось отправить сообщение пользователю {target_user_id}: {msg_err}")
            
    except Exception as e:
        logger.error(f"Ошибка SQL при добавлении минут: {e}")
        await message.answer("❌ Ошибка SQL при выполнении операции.")
    finally:
        if conn and db_pool: 
            db_pool.putconn(conn)

# ==========================================
# ОБРАБОТКА МЕДИАФАЙЛОВ
# ==========================================

@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(message: Message):
    user_id = message.chat.id
    if not message.from_user:
        return
    
    user_lang = message.from_user.language_code or "en"
    lang_dict = get_lang(user_lang)
    conn = None
    user_style = "summary"
    balance_minutes = 0
    
    # 1. Запрашиваем стиль и текущий баланс за один SQL-запрос
    try:
        assert db_pool is not None
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT ai_style, balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        if res: 
            user_style = res[0]
            balance_minutes = res[1]
    except Exception as e:
        logger.error(f"Ошибка получения профиля: {e}")
    finally:
        if conn and db_pool: 
            db_pool.putconn(conn)
            
    # 2. КРИТИЧЕСКИЙ БАРЬЕР: Блокируем обработку, если баланс на нуле
    if balance_minutes < 1:
        await message.answer(
            lang_dict["balance_msg"].format(minutes=balance_minutes),
            reply_markup=get_billing_keyboard(user_lang),
            parse_mode="HTML"
        )
        return

    # 3. Валидация медиа-типа
    if message.voice: file_id, file_ext = message.voice.file_id, "ogg"
    elif message.audio: file_id, file_ext = message.audio.file_id, "mp3"
    elif message.video: file_id, file_ext = message.video.file_id, "mp4"
    elif message.video_note: file_id, file_ext = message.video_note.file_id, "mp4"
    else: return

    # 4. Если баланс ОК — скачиваем файл
    await message.answer(lang_dict["file_received"])
    try:
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            return await message.answer(lang_dict["download_error"])
        file_path_on_server = os.path.join(DOWNLOAD_DIR, f"{file_id}.{file_ext}")
        await bot.download_file(file_info.file_path, file_path_on_server)
    except Exception as e:
        logger.error(f"Ошибка скачивания файла {file_id}: {e}")
        return await message.answer(lang_dict["download_error"])

    # 5. Делегируем тяжелую работу Celery воркеру
    process_audio_task.delay(file_path_on_server, user_id, user_style)
    await message.answer(lang_dict["processing"])

async def set_main_menu(bot_instance: Bot):
    commands = [
        BotCommand(command="/start", description="Instruction / Инструкция"),
        BotCommand(command="/balance", description="Balance / Баланс 💳"),
        BotCommand(command="/settings", description="Change mode / Настройки ⚙️")
    ]
    await bot_instance.set_my_commands(commands)

# ==========================================
# ИНИЦИАЛИЗАЦИЯ И ЗАПУСК
# ==========================================

async def main():
    global db_pool
    logger.info("🚀 Запуск супер-комбайна QuickSay...")
    
    # Безопасное асинхронное подключение к пулу БД с повторными попытками
    max_retries = 5
    retry_delay = 5
    for attempt in range(1, max_retries + 1):
        try:
            db_pool = ThreadedConnectionPool(minconn=1, maxconn=10, **DB_PARAMS)
            logger.info("✅ Пул соединений PostgreSQL успешно запущен.")
            break
        except Exception as err:
            if attempt == max_retries:
                logger.critical(f"❌ Сбой запуска пула БД после {max_retries} попыток: {err}")
                raise err
            logger.info(f"🔄 Попытка переподключения к БД {attempt}/{max_retries} через {retry_delay} сек...")
            await asyncio.sleep(retry_delay)

    # Импортируем функцию создания таблиц из твоего db/database.py прямо здесь
    try:
        from db.database import init_db
        init_db()
        logger.info("✅ База данных и таблицы проверены/инициализированы.")
    except Exception as e:
        logger.error(f"⚠️ Предупреждение при инициализации таблиц: {e}")

    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен.")