import logging
from aiocryptopay import AioCryptoPay, Networks
from config import CRYPTO_BOT_TOKEN  # Токен успешно импортируется!
from db.database import create_pending_payment

logger = logging.getLogger(__name__)

async def generate_payment_link(user_id: int, minutes_package: int) -> str:
    """
    Генерирует инвойс в CryptoBot и возвращает ссылку для пользователя.
    Сессия закрывается вручную в блоке finally, чтобы избежать ложных ошибок Pylance на "None".
    """
    # Определяем стоимость пакета
    if minutes_package == 100:
        amount = 2.00
    elif minutes_package == 300:
        amount = 5.00
    else:
        amount = 1.00  # На всякий случай дефолт
        
    # Инициализируем клиент напрямую без контекстного менеджера
    crypto = AioCryptoPay(token=CRYPTO_BOT_TOKEN, network=Networks.MAIN_NET)
    
    try:
        # Передаем параметры для фиатного чека
        invoice = await crypto.create_invoice(
            fiat='USD', 
            amount=amount,
            currency_type='fiat',
            description=f"Пополнение баланса QuickSay: {minutes_package} мин.",
            # Показываем пользователю только две самые популярные монеты:
            accepted_assets='USDT,TON',
            # КРИТИЧЕСКИ ВАЖНО: передаем данные для вебхука
            payload=f"{user_id}:{minutes_package}"
        )
        logger.info(f"💰 Инвойс создан для {user_id}: {invoice.bot_invoice_url}")
        
        # Сохраняем попытку платежа в БД со статусом pending
        try:
            create_pending_payment(
                user_id=user_id,
                invoice_id=str(invoice.invoice_id),
                amount_usd=amount,
                minutes=minutes_package
            )
        except Exception as db_err:
            logger.error(f"⚠️ Ошибка сохранения счета в БД: {db_err}")
            
        return invoice.bot_invoice_url
            
    except Exception as e:
        logger.error(f"❌ Ошибка Crypto Pay API для юзера {user_id}: {e}")
        raise e
    finally:
        # Гарантированно закрываем сессию после выполнения запроса
        await crypto.close()