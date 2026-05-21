import os
import hmac
import hashlib
import logging
from aiohttp import web
from aiogram import Bot

from config import BOT_TOKEN, CRYPTO_BOT_TOKEN, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from psycopg2.pool import ThreadedConnectionPool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализируем бота для отправки уведомлений об успешной оплате
bot = Bot(token=BOT_TOKEN)

DB_PARAMS = {
    "dbname": DB_NAME, "user": DB_USER, "password": DB_PASSWORD, "host": DB_HOST, "port": DB_PORT
}

# Поднимаем отдельный пул для вебхук-сервера, так как он работает в параллельном процессе
db_pool = ThreadedConnectionPool(minconn=1, maxconn=5, **DB_PARAMS)

# Текст уведомлений на разных языках
NOTIFICATIONS = {
    "ru": "🎉 <b>Оплата получена!</b>\nНа ваш баланс зачислено: <b>+{minutes} мин.</b>\nСпасибо за поддержку проекта! 🙌",
    "uk": "🎉 <b>Оплату отримано!</b>\nНа ваш баланс зараховано: <b>+{minutes} хв.</b>\nДякуємо за підтримку проєкту! 🙌",
    "en": "🎉 <b>Payment received!</b>\n<b>+{minutes} min.</b> have been credited to your balance.\nThank you for supporting the project! 🙌"
}

def verify_signature(body_bytes: bytes, header_signature: str) -> bool:
    """Проверка подписи CryptoBot для защиты от фейковых запросов"""
    if not header_signature:
        return False
    # Создаем секрет на основе крипто-токена
    secret = hashlib.sha256(CRYPTO_BOT_TOKEN.encode('utf-8')).digest()
    # Вычисляем HMAC-SHA256 от тела запроса
    computed_sig = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_sig, header_signature)

async def crypto_bot_webhook(request: web.Request):
    # 1. Читаем сырые байты для валидации подписи
    body_bytes = await request.read()
    signature = request.headers.get("crypto-pay-api-signature", "")
    
    if not verify_signature(body_bytes, signature):
        logger.warning("🚨 Получен запрос с невалидной подписью!")
        return web.Response(text="Forbidden", status=403)
    
    # 2. Если подпись верна, парсим JSON
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return web.Response(text="Bad Request", status=400)
    
    # Проверяем тип события. Нас интересует только успешная оплата инвойса
    if data.get("update_type") != "invoice_paid":
        return web.Response(text="OK", status=200)
    
    payload = data.get("payload", {})
    invoice_id = payload.get("invoice_id")
    status = payload.get("status")
    
    # Защитный барьер на статус
    if status != "paid":
        return web.Response(text="OK", status=200)
    
    # Извлекаем кастомные метаданные (Ожидается строка формата "user_id:minutes")
    description = payload.get("description", "")
    try:
        custom_payload = payload.get("payload", "")
        if not custom_payload and ":" in description:
            custom_payload = description 
            
        tg_user_id, minutes_to_add = map(int, custom_payload.split(":"))
    except Exception as e:
        logger.error(f"Не удалось распарсить метаданные счета ({description} / {payload.get('payload')}): {e}")
        return web.Response(text="Metadata error", status=200)

    # 3. Начисляем минуты в базу данных
    conn = None
    user_lang = "ru"  # Дефолтный язык, если в базе пусто или произойдет сбой
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        
        # Исправленный SQL-запрос обновления баланса с возвратом language_code
        cur.execute("""
            UPDATE users 
            SET balance_minutes = balance_minutes + %s 
            WHERE telegram_id = %s 
            RETURNING language_code;
        """, (minutes_to_add, tg_user_id))
        
        res = cur.fetchone()
        if res and res[0]:
            user_lang = res[0]
            
        conn.commit()
        cur.close()
        logger.info(f"💰 Баланс пользователя {tg_user_id} успешно пополнен на +{minutes_to_add} мин. (Счет #{invoice_id})")
        
    except Exception as db_err:
        logger.error(f"Ошибка БД при обработке платежа #{invoice_id}: {db_err}")
        if conn:
            conn.rollback()
        return web.Response(text="Database Error", status=500)
    finally:
        if conn:
            db_pool.putconn(conn)

    # 4. Отправляем юзеру пуш-уведомление в Telegram
    try:
        msg_text = NOTIFICATIONS.get(user_lang, NOTIFICATIONS["ru"]).format(minutes=minutes_to_add)
        await bot.send_message(chat_id=tg_user_id, text=msg_text, parse_mode="HTML")
    except Exception as tg_err:
        logger.warning(f"Не удалось отправить уведомление пользователю {tg_user_id}: {tg_err}")

    return web.Response(text="OK", status=200)

async def app_factory():
    app = web.Application()
    app.router.add_post("/crypto-webhook", crypto_bot_webhook)
    return app

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/crypto-webhook", crypto_bot_webhook)
    
    # Слушаем на 0.0.0.0, чтобы Docker наружу прокидывал порт
    logger.info("🚀 Запуск вебхук-сервера CryptoBot на порту 8081...")
    web.run_app(app, host="0.0.0.0", port=8081)