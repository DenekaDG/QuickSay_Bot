import psycopg2
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

def get_db_connection():
    """Функция для быстрого подключения к PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Таблица пользователей (уже существующая)
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
    
    # 2. Новая таблица для фиксации крипто-платежей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
            invoice_id VARCHAR(255) UNIQUE NOT NULL, -- ID счета из CryptoBot
            amount_usd NUMERIC(10, 2) NOT NULL,       -- Сумма в долларах (например, 5.00)
            minutes_to_add INT NOT NULL,              -- Сколько минут начислим после оплаты
            status VARCHAR(50) DEFAULT 'pending',     -- Статусы: pending, completed, expired
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ База данных успешно инициализирована (таблицы пользователей и платежей проверены).")


# === Функции для работы с финансами ===

def create_pending_payment(user_id: int, invoice_id: str, amount_usd: float, minutes: int):
    """Записывает новую попытку оплаты в базу со статусом pending"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO payments (user_id, invoice_id, amount_usd, minutes_to_add, status)
            VALUES (%s, %s, %s, %s, 'pending');
        """, (user_id, invoice_id, amount_usd, minutes))
        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при создании платежа в БД: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()