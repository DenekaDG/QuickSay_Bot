import os
import asyncio
from typing import Optional, Dict, Tuple
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, BotCommandScopeChat
from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import Error as PostgresError

from config import BOT_TOKEN, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, ADMIN_ID
from tasks import process_audio_task
from payment_service import generate_payment_link
from logging_config import get_bot_logger

# Initialize logger with file rotation
logger = get_bot_logger()

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

def get_lang(lang_code: Optional[str]) -> Dict[str, str]:
    """
    Get localization dictionary for given language code.
    
    Args:
        lang_code: Language code (en, ru, uk)
        
    Returns:
        Dictionary with localized strings
    """
    if lang_code and lang_code in LOCALIZATION:
        return LOCALIZATION[lang_code]
    return LOCALIZATION["en"]

def get_main_keyboard(current_style: str = "summary", lang: str = "en") -> InlineKeyboardMarkup:
    """
    Create main menu keyboard with processing modes.
    
    Args:
        current_style: Currently selected processing style
        lang: Language code for localization
        
    Returns:
        InlineKeyboardMarkup with mode selection buttons
    """
    try:
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
    except Exception as e:
        logger.error(f"Error creating main keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Back", callback_data="back_to_styles")]])

def get_languages_keyboard(current_style: str = "summary", lang: str = "en") -> InlineKeyboardMarkup:
    """
    Create languages selection keyboard.
    
    Args:
        current_style: Currently selected language style
        lang: Interface language code
        
    Returns:
        InlineKeyboardMarkup with language selection buttons
    """
    try:
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
    except Exception as e:
        logger.error(f"Error creating languages keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Back", callback_data="back_to_styles")]])

def get_billing_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """
    Create billing menu keyboard.
    
    Args:
        lang: Language code for localization
        
    Returns:
        InlineKeyboardMarkup with payment package buttons
    """
    try:
        lang_dict = get_lang(lang)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=lang_dict["btn_pack_100"], callback_data="buy_pack:100")],
            [InlineKeyboardButton(text=lang_dict["btn_pack_300"], callback_data="buy_pack:300")],
            [InlineKeyboardButton(text=lang_dict["btn_back"], callback_data="back_to_styles")]
        ])
    except Exception as e:
        logger.error(f"Error creating billing keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Back", callback_data="back_to_styles")]])

# ==========================================
# COMMAND HANDLERS
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Start command handler - registers user and shows main menu.
    
    Args:
        message: Incoming message from user
    """
    try:
        # Safety checks
        if not message.from_user:
            logger.warning("Received /start from anonymous user")
            return
        
        user_id: int = message.chat.id
        user_name: str = message.from_user.first_name or "Friend"
        user_lang: str = message.from_user.language_code or "en"
        
        username: Optional[str] = message.from_user.username
        first_name: Optional[str] = message.from_user.first_name
        last_name: Optional[str] = message.from_user.last_name
        
        lang_dict = get_lang(user_lang)
        
        # Register user in database
        conn = None
        try:
            if db_pool is None:
                logger.error(f"Database pool not initialized for user {user_id}")
                return
            
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
            logger.info(f"User {user_id} ({username}) registered/updated successfully")
        except PostgresError as e:
            logger.error(f"Database error registering user {user_id}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)

        # Set bot commands
        try:
            commands = [
                BotCommand(command="/start", description=lang_dict.get("menu_desc_start", "Start")),
                BotCommand(command="/balance", description=lang_dict.get("menu_desc_balance", "Balance")),
                BotCommand(command="/settings", description=f"[{lang_dict.get('btn_summary', 'Mode')}] {lang_dict.get('menu_desc_settings', 'Settings')} ⚙️")
            ]
            await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
        except Exception as e:
            logger.warning(f"Failed to set commands for user {user_id}: {e}")

        # Send welcome message
        await message.answer(
            lang_dict.get("welcome", "Welcome!").format(name=user_name), 
            reply_markup=get_main_keyboard("summary", user_lang), 
            parse_mode="HTML"
        )
        logger.info(f"Sent welcome message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in /start command: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred. Please try again later.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

@dp.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """
    Settings command - show processing mode selection.
    
    Args:
        message: Incoming message from user
    """
    try:
        if not message.from_user:
            logger.warning("Received /settings from anonymous user")
            return
        
        user_id: int = message.chat.id
        user_lang: str = message.from_user.language_code or "en"
        lang_dict = get_lang(user_lang)
        current_style: str = "summary"
        
        # Get user's current style from database
        conn = None
        try:
            if db_pool is None:
                logger.error(f"Database pool not initialized for user {user_id}")
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res:
                current_style = res[0]
                logger.debug(f"Retrieved style '{current_style}' for user {user_id}")
        except PostgresError as e:
            logger.error(f"Database error getting style for user {user_id}: {e}")
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)

        await message.answer(
            lang_dict.get("settings_title", "Choose mode:"), 
            reply_markup=get_main_keyboard(current_style, user_lang), 
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in /settings command: {e}", exc_info=True)
        try:
            await message.answer("❌ Error loading settings.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

@dp.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    """
    Balance command - show user's current balance.
    
    Args:
        message: Incoming message from user
    """
    try:
        if not message.from_user:
            logger.warning("Received /balance from anonymous user")
            return
        
        user_id: int = message.chat.id
        user_lang: str = message.from_user.language_code or "en"
        lang_dict = get_lang(user_lang)
        balance_minutes: int = 0
        
        # Get balance from database
        conn = None
        try:
            if db_pool is None:
                logger.error(f"Database pool not initialized for user {user_id}")
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res:
                balance_minutes = res[0]
                logger.debug(f"Retrieved balance {balance_minutes} minutes for user {user_id}")
        except PostgresError as e:
            logger.error(f"Database error getting balance for user {user_id}: {e}")
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)
                
        await message.answer(
            lang_dict.get("balance_msg", "Balance: {minutes} min.").format(minutes=balance_minutes),
            reply_markup=get_billing_keyboard(user_lang),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in /balance command: {e}", exc_info=True)
        try:
            await message.answer("❌ Error loading balance.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

# ==========================================
# CALLBACK QUERY HANDLERS
# ==========================================

def _get_user_id_and_lang_from_callback(callback: CallbackQuery) -> Tuple[Optional[int], str]:
    """
    Safely extract user ID and language from callback query.
    
    Args:
        callback: CallbackQuery object
        
    Returns:
        Tuple of (user_id, language_code) or (None, "en") if extraction fails
    """
    if not callback.message or not callback.message.chat:
        logger.warning("Callback has no message or chat info")
        return None, "en"
    
    if not callback.from_user:
        logger.warning("Callback has no from_user info")
        return None, "en"
    
    user_id = callback.message.chat.id
    user_lang = callback.from_user.language_code or "en"
    
    return user_id, user_lang

@dp.callback_query(F.data == "open_billing")
async def open_billing_menu(callback: CallbackQuery) -> None:
    """
    Handle billing menu open callback.
    
    Args:
        callback: CallbackQuery object
    """
    try:
        # Safe callback message check
        if not callback.message:
            logger.warning(f"open_billing callback has no message")
            await callback.answer("❌ Error: No message", show_alert=True)
            return
        
        user_id, user_lang = _get_user_id_and_lang_from_callback(callback)
        if user_id is None:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        lang_dict = get_lang(user_lang)
        balance_minutes: int = 0
        
        # Get balance from database
        conn = None
        try:
            if db_pool is None:
                await callback.answer("❌ Database error", show_alert=True)
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res: 
                balance_minutes = res[0]
        except PostgresError as e:
            logger.error(f"Database error getting balance: {e}")
            await callback.answer("❌ Database error", show_alert=True)
            return
        finally:
            if conn and db_pool: 
                db_pool.putconn(conn)

        await callback.message.edit_text(
            lang_dict.get("balance_msg", "Balance: {minutes} min.").format(minutes=balance_minutes),
            reply_markup=get_billing_keyboard(user_lang),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in open_billing_menu: {e}", exc_info=True)
        try:
            await callback.answer("❌ An error occurred", show_alert=True)
        except Exception as answer_err:
            logger.error(f"Failed to send answer: {answer_err}")

@dp.callback_query(lambda c: c.data and c.data.startswith("buy_pack:"))
async def process_buy_package(callback: CallbackQuery) -> None:
    """
    Handle buy package callback.
    
    Args:
        callback: CallbackQuery object
    """
    try:
        # Safe callback message check
        if not callback.message:
            logger.warning("buy_pack callback has no message")
            await callback.answer("❌ Error: No message", show_alert=True)
            return
        
        # Safe callback data check
        if not callback.data or ":" not in callback.data:
            logger.warning(f"Invalid buy_pack callback data: {callback.data}")
            await callback.answer("❌ Invalid action", show_alert=True)
            return
        
        user_id, user_lang = _get_user_id_and_lang_from_callback(callback)
        if user_id is None:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        lang_dict = get_lang(user_lang)
        
        # Parse minutes from callback data
        try:
            minutes_pack = int(callback.data.split(":")[1])
        except (IndexError, ValueError) as e:
            logger.warning(f"Failed to parse minutes from callback data '{callback.data}': {e}")
            await callback.answer("❌ Invalid data format", show_alert=True)
            return
        
        await callback.answer("⏳ Processing...")
        
        # Generate payment link
        try:
            pay_url = await generate_payment_link(user_id=user_id, minutes_package=minutes_pack)
            
            pay_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=lang_dict.get("btn_pay_now", "Pay Now"), url=pay_url)],
                [InlineKeyboardButton(text=lang_dict.get("btn_back", "Back"), callback_data="open_billing")]
            ])
            
            await callback.message.edit_text(
                lang_dict.get("invoice_created", "Invoice created!"),
                reply_markup=pay_kb,
                parse_mode="HTML"
            )
            logger.info(f"Payment link created for user {user_id}, {minutes_pack} min")
        except Exception as e:
            logger.error(f"Error creating payment link for user {user_id}: {e}", exc_info=True)
            try:
                await callback.message.answer(lang_dict.get("db_error", "❌ Database error"))
            except Exception as send_err:
                logger.error(f"Failed to send error message: {send_err}")
                
    except Exception as e:
        logger.error(f"Error in process_buy_package: {e}", exc_info=True)
        try:
            await callback.answer("❌ An error occurred", show_alert=True)
        except Exception as answer_err:
            logger.error(f"Failed to send answer: {answer_err}")

@dp.callback_query(F.data == "open_languages")
async def open_languages_menu(callback: CallbackQuery) -> None:
    """
    Handle languages menu open callback.
    
    Args:
        callback: CallbackQuery object
    """
    try:
        # Safe callback message check
        if not callback.message:
            logger.warning("open_languages callback has no message")
            await callback.answer("❌ Error: No message", show_alert=True)
            return
        
        user_id, user_lang = _get_user_id_and_lang_from_callback(callback)
        if user_id is None:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        lang_dict = get_lang(user_lang)
        current_style: str = "summary"
        
        # Get current style from database
        conn = None
        try:
            if db_pool is None:
                await callback.answer("❌ Database error", show_alert=True)
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res:
                current_style = res[0]
        except PostgresError as e:
            logger.error(f"Database error getting style: {e}")
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)

        await callback.message.edit_text(
            lang_dict.get("choose_lang", "Choose language:"), 
            reply_markup=get_languages_keyboard(current_style, user_lang), 
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in open_languages_menu: {e}", exc_info=True)
        try:
            await callback.answer("❌ An error occurred", show_alert=True)
        except Exception as answer_err:
            logger.error(f"Failed to send answer: {answer_err}")

@dp.callback_query(F.data == "back_to_styles")
async def back_to_styles(callback: CallbackQuery) -> None:
    """
    Handle back to styles button callback.
    
    Args:
        callback: CallbackQuery object
    """
    try:
        # Safe callback message check
        if not callback.message:
            logger.warning("back_to_styles callback has no message")
            await callback.answer("❌ Error: No message", show_alert=True)
            return
        
        user_id, user_lang = _get_user_id_and_lang_from_callback(callback)
        if user_id is None:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        if not callback.from_user:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        lang_dict = get_lang(user_lang)
        current_style: str = "summary"
        
        # Get current style from database
        conn = None
        try:
            if db_pool is None:
                await callback.answer("❌ Database error", show_alert=True)
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res:
                current_style = res[0]
        except PostgresError as e:
            logger.error(f"Database error getting style: {e}")
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)

        user_name = callback.from_user.first_name or "Friend"
        await callback.message.edit_text(
            lang_dict.get("welcome", "Welcome!").format(name=user_name), 
            reply_markup=get_main_keyboard(current_style, user_lang), 
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in back_to_styles: {e}", exc_info=True)
        try:
            await callback.answer("❌ An error occurred", show_alert=True)
        except Exception as answer_err:
            logger.error(f"Failed to send answer: {answer_err}")

@dp.callback_query(F.data.startswith("set_style:"))
async def process_style_callback(callback: CallbackQuery) -> None:
    """
    Handle style selection callback.
    
    Args:
        callback: CallbackQuery object
    """
    try:
        # Safe callback data and message check
        if not callback.data or ":" not in callback.data:
            logger.warning(f"Invalid set_style callback data: {callback.data}")
            await callback.answer("❌ Invalid action", show_alert=True)
            return
        
        if not callback.message:
            logger.warning("set_style callback has no message")
            await callback.answer("❌ Error: No message", show_alert=True)
            return
        
        style_name: str = callback.data.split(":")[1]
        user_id, user_lang = _get_user_id_and_lang_from_callback(callback)
        if user_id is None:
            await callback.answer("❌ Error: Cannot identify user", show_alert=True)
            return
        
        lang_dict = get_lang(user_lang)
        
        style_titles_short = {
            "summary": lang_dict.get("btn_summary", "📝"), 
            "creative": lang_dict.get("btn_creative", "🎨"),
            "meeting": lang_dict.get("btn_meeting", "💼"), 
            "insider": lang_dict.get("btn_insider", "⚡"),
            "editor": lang_dict.get("btn_editor", "✍️"),
            "opponent": lang_dict.get("btn_opponent", "🧠"), 
            "diary": lang_dict.get("btn_diary", "🌱"),
            "lang_ua": "🇺🇦 UA", "lang_en": "🇬🇧 EN", "lang_de": "🇩🇪 DE",
            "lang_fr": "🇫🇷 FR", "lang_es": "🇪🇸 ES", "lang_it": "🇮🇹 IT"
        }
        
        selected_short = style_titles_short.get(style_name, "📝")
        selected_full = lang_dict.get(f"style_{style_name}", lang_dict.get("style_summary", "Summary"))
        
        # Update style in database
        conn = None
        try:
            if db_pool is None:
                await callback.answer("❌ Database error", show_alert=True)
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("UPDATE users SET ai_style = %s WHERE telegram_id = %s", (style_name, user_id))
            conn.commit()
            cur.close()
            logger.info(f"User {user_id} changed style to '{style_name}'")
            
            # Update bot commands
            try:
                commands = [
                    BotCommand(command="/start", description=lang_dict.get("menu_desc_start", "Start")),
                    BotCommand(command="/balance", description=lang_dict.get("menu_desc_balance", "Balance")),
                    BotCommand(command="/settings", description=f"[{selected_short}] {lang_dict.get('menu_desc_settings', 'Settings')} ⚙️")
                ]
                await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
            except Exception as cmd_err:
                logger.warning(f"Failed to update commands for user {user_id}: {cmd_err}")
            
            await callback.answer(f"{selected_short}")
            await callback.message.answer(
                lang_dict.get("status_changed", "Done!").format(style=selected_full), 
                parse_mode="HTML"
            )
            
            # Update keyboard
            if style_name.startswith("lang_"):
                await callback.message.edit_reply_markup(
                    reply_markup=get_languages_keyboard(style_name, user_lang)
                )
            else:
                await callback.message.edit_reply_markup(
                    reply_markup=get_main_keyboard(style_name, user_lang)
                )
                
        except PostgresError as e:
            logger.error(f"Database error changing style for user {user_id}: {e}")
            await callback.answer("❌ Database error", show_alert=True)
        finally:
            if conn and db_pool:
                db_pool.putconn(conn)
                
    except Exception as e:
        logger.error(f"Error in process_style_callback: {e}", exc_info=True)
        try:
            await callback.answer("❌ An error occurred", show_alert=True)
        except Exception as answer_err:
            logger.error(f"Failed to send answer: {answer_err}")

# ==========================================
# ADMIN PANEL
# ==========================================

@dp.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message) -> None:
    """
    Admin stats command - show bot statistics.
    
    Args:
        message: Incoming message from user
    """
    try:
        if not message.from_user or message.from_user.id != ADMIN_ID:
            logger.warning(f"Unauthorized admin access attempt from user {message.from_user.id if message.from_user else 'unknown'}")
            return
        
        conn = None
        try:
            if db_pool is None:
                await message.answer("❌ Database error")
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users;")
            total_users = cur.fetchone()[0]
            cur.execute("SELECT SUM(balance_minutes) FROM users;")
            total_minutes = cur.fetchone()[0] or 0
            cur.close()
            
            logger.info(f"Admin stats requested: {total_users} users, {total_minutes} total minutes")
            await message.answer(
                f"📊 <b>QuickSay Bot Statistics</b>\n\n"
                f"👥 Total users: <code>{total_users}</code>\n"
                f"⏳ Total balance: <code>{total_minutes} min.</code>", 
                parse_mode="HTML"
            )
        except PostgresError as e:
            logger.error(f"Database error getting stats: {e}")
            await message.answer("❌ Database error.")
        finally:
            if conn and db_pool: 
                db_pool.putconn(conn)
                
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

@dp.message(Command("add_minutes"))
async def cmd_add_minutes(message: Message) -> None:
    """
    Admin command to add minutes to user's balance.
    Usage: /add_minutes <user_id> <minutes>
    
    Args:
        message: Incoming message from user
    """
    try:
        if not message.from_user or message.from_user.id != ADMIN_ID:
            logger.warning(f"Unauthorized add_minutes attempt from user {message.from_user.id if message.from_user else 'unknown'}")
            return
        
        args = (message.text or "").split()
        if len(args) != 3:
            await message.answer("⚠️ Format: <code>/add_minutes [ID] [Minutes]</code>", parse_mode="HTML")
            return
            
        try: 
            target_user_id = int(args[1])
            minutes_to_add = int(args[2])
        except ValueError:
            await message.answer("⚠️ User ID and minutes must be integers!")
            return

        if minutes_to_add <= 0:
            await message.answer("⚠️ Minutes must be a positive number!")
            return

        conn = None
        try:
            if db_pool is None:
                await message.answer("❌ Database error")
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s;", (target_user_id,))
            if not cur.fetchone():
                await message.answer("❌ User not found in database.")
                cur.close()
                return
                
            # Add minutes
            cur.execute(
                "UPDATE users SET balance_minutes = balance_minutes + %s WHERE telegram_id = %s;", 
                (minutes_to_add, target_user_id)
            )
            conn.commit()
            cur.close()
            
            logger.info(f"Admin {message.from_user.id} added {minutes_to_add} minutes to user {target_user_id}")
            await message.answer(
                f"✅ User <code>{target_user_id}</code> received: <b>+{minutes_to_add} min.</b>", 
                parse_mode="HTML"
            )
            
            # Notify user
            try: 
                await bot.send_message(
                    chat_id=target_user_id, 
                    text=f"🎁 <b>You received bonus minutes!</b>\n"
                         f"Balance increased by: <b>+{minutes_to_add} min.</b>", 
                    parse_mode="HTML"
                )
            except Exception as msg_err:
                logger.warning(f"Failed to notify user {target_user_id}: {msg_err}")
                
        except PostgresError as e:
            logger.error(f"Database error adding minutes: {e}")
            await message.answer("❌ Database error while executing operation.")
        finally:
            if conn and db_pool: 
                db_pool.putconn(conn)
                
    except Exception as e:
        logger.error(f"Error in add_minutes: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

# ==========================================
# MEDIA HANDLING
# ==========================================

@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(message: Message) -> None:
    """
    Handle voice messages, audio files, and video notes.
    Validates balance, downloads media, and delegates to Celery task.
    
    Args:
        message: Incoming message with media
    """
    try:
        if not message.from_user:
            logger.warning("Received media from anonymous user")
            return
        
        user_id: int = message.chat.id
        user_lang: str = message.from_user.language_code or "en"
        lang_dict = get_lang(user_lang)
        conn = None
        user_style: str = "summary"
        balance_minutes: int = 0
        
        # Get user profile
        try:
            if db_pool is None:
                await message.answer("❌ Database error")
                return
            
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT ai_style, balance_minutes FROM users WHERE telegram_id = %s", (user_id,))
            res = cur.fetchone()
            cur.close()
            if res: 
                user_style = res[0]
                balance_minutes = res[1]
                logger.debug(f"Retrieved profile for user {user_id}: style={user_style}, balance={balance_minutes}")
        except PostgresError as e:
            logger.error(f"Database error getting user profile: {e}")
        finally:
            if conn and db_pool: 
                db_pool.putconn(conn)
            
        # Check balance
        if balance_minutes < 1:
            logger.info(f"User {user_id} has insufficient balance: {balance_minutes}")
            await message.answer(
                lang_dict.get("balance_msg", "Balance: {minutes} min.").format(minutes=balance_minutes),
                reply_markup=get_billing_keyboard(user_lang),
                parse_mode="HTML"
            )
            return

        # Determine file type and get file ID
        file_id: Optional[str] = None
        file_ext: str = "ogg"
        
        if message.voice: 
            file_id, file_ext = message.voice.file_id, "ogg"
        elif message.audio: 
            file_id, file_ext = message.audio.file_id, "mp3"
        elif message.video: 
            file_id, file_ext = message.video.file_id, "mp4"
        elif message.video_note: 
            file_id, file_ext = message.video_note.file_id, "mp4"
        
        if not file_id:
            logger.warning(f"No file ID extracted for user {user_id}")
            return

        # Send confirmation message
        await message.answer(lang_dict.get("file_received", "File received..."))
        
        # Download file
        try:
            file_info = await bot.get_file(file_id)
            if not file_info.file_path:
                logger.error(f"No file path returned for file {file_id}")
                await message.answer(lang_dict.get("download_error", "❌ Download failed"))
                return
            
            file_path_on_server = os.path.join(DOWNLOAD_DIR, f"{file_id}.{file_ext}")
            await bot.download_file(file_info.file_path, file_path_on_server)
            logger.info(f"File {file_id} downloaded successfully for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id} for user {user_id}: {e}", exc_info=True)
            await message.answer(lang_dict.get("download_error", "❌ Download failed"))
            return

        # Delegate to Celery worker
        try:
            process_audio_task.delay(file_path_on_server, user_id, user_style)
            logger.info(f"Processing task queued for user {user_id}, style={user_style}")
            await message.answer(lang_dict.get("processing", "⏳ Processing..."))
        except Exception as e:
            logger.error(f"Error queuing Celery task for user {user_id}: {e}", exc_info=True)
            await message.answer(lang_dict.get("db_error", "❌ Error"))
            
    except Exception as e:
        logger.error(f"Error in handle_media: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred while processing your media.")
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}")

async def set_main_menu(bot_instance: Bot) -> None:
    """
    Set default bot commands in menu.
    
    Args:
        bot_instance: Bot instance to set commands for
    """
    try:
        commands = [
            BotCommand(command="/start", description="Instruction / Інструкція"),
            BotCommand(command="/balance", description="Balance / Баланс 💳"),
            BotCommand(command="/settings", description="Change mode / Настройки ⚙️")
        ]
        await bot_instance.set_my_commands(commands)
        logger.info("Main menu commands set successfully")
    except Exception as e:
        logger.warning(f"Failed to set main menu: {e}")

# ==========================================
# BOT INITIALIZATION AND STARTUP
# ==========================================

async def main() -> None:
    """
    Main async function - initializes bot and starts polling.
    """
    global db_pool
    logger.info("🚀 Starting QuickSay Bot...")
    
    # Initialize database connection pool with retries
    max_retries: int = 5
    retry_delay: int = 5
    for attempt in range(1, max_retries + 1):
        try:
            db_pool = ThreadedConnectionPool(minconn=1, maxconn=10, **DB_PARAMS)
            logger.info("✅ PostgreSQL connection pool initialized successfully")
            break
        except PostgresError as err:
            if attempt == max_retries:
                logger.critical(f"❌ Failed to initialize DB pool after {max_retries} attempts: {err}")
                raise err
            logger.info(f"🔄 Retrying DB connection {attempt}/{max_retries} in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

    # Initialize database tables
    try:
        from db.database import init_db
        init_db()
        logger.info("✅ Database tables initialized/verified")
    except Exception as e:
        logger.warning(f"⚠️ Warning during database initialization: {e}")

    # Set bot menu and start polling
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🤖 Bot started polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (KeyboardInterrupt)")
    except SystemExit:
        logger.info("🛑 Bot stopped (SystemExit)")
    except Exception as e:
        logger.critical(f"💥 Critical error: {e}", exc_info=True)