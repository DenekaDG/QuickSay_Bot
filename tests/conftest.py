"""
Pytest configuration and shared fixtures for testing.
"""

import os
import sys
import pytest
from typing import Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def db_config() -> dict:
    """Database configuration for tests"""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "bot_admin"),
        "password": os.getenv("DB_PASSWORD", "password"),
        "database": os.getenv("DB_NAME", "test_ai_voice_bot"),
    }


@pytest.fixture(scope="session")
def db_pool(db_config: dict) -> Generator:
    """Create database connection pool for tests"""
    try:
        pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            **db_config
        )
        yield pool
        pool.closeall()
    except psycopg2.OperationalError as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
def db_conn(db_pool):
    """Get database connection from pool"""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        conn.rollback()  # Rollback any changes
        db_pool.putconn(conn)


@pytest.fixture(autouse=True)
def cleanup_db(db_conn):
    """Clean up test data after each test"""
    yield
    # Note: actual cleanup logic depends on test requirements
    # Usually done with explicit DELETE or transaction rollback


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing"""
    return {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "ai_style": "summary",
        "balance_minutes": 100,
        "is_premium": False,
    }


@pytest.fixture
def sample_payment_data() -> dict:
    """Sample payment data for testing"""
    return {
        "user_id": 123456789,
        "invoice_id": "test_invoice_12345",
        "amount_usd": 5.00,
        "minutes_to_add": 100,
        "status": "pending",
    }
