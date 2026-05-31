"""
Unit tests for database operations.

Tests cover:
- User registration and creation
- Balance management
- Payment operations
- User profile retrieval
"""

import pytest
from typing import Optional
from psycopg2 import Error as PostgresError


class TestUserOperations:
    """Test user-related database operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        """Setup: Create tables before each test"""
        cur = db_conn.cursor()
        
        # Create users table
        cur.execute("""
            DROP TABLE IF EXISTS users CASCADE;
            CREATE TABLE users (
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
        db_conn.commit()
        yield
        
        # Cleanup
        cur.execute("DROP TABLE IF EXISTS users CASCADE;")
        db_conn.commit()
        cur.close()

    def test_insert_new_user(self, db_conn, sample_user_data: dict):
        """Test inserting a new user into the database"""
        cur = db_conn.cursor()
        
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name, ai_style, balance_minutes, is_premium)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            sample_user_data["telegram_id"],
            sample_user_data["username"],
            sample_user_data["first_name"],
            sample_user_data["last_name"],
            sample_user_data["ai_style"],
            sample_user_data["balance_minutes"],
            sample_user_data["is_premium"]
        ))
        db_conn.commit()
        
        # Verify insertion
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        user = cur.fetchone()
        cur.close()
        
        assert user is not None
        assert user[0] == sample_user_data["telegram_id"]
        assert user[1] == sample_user_data["username"]

    def test_get_user_profile(self, db_conn, sample_user_data: dict):
        """Test retrieving user profile"""
        cur = db_conn.cursor()
        
        # Insert test user
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name, ai_style, balance_minutes)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            sample_user_data["telegram_id"],
            sample_user_data["username"],
            sample_user_data["first_name"],
            sample_user_data["last_name"],
            sample_user_data["ai_style"],
            sample_user_data["balance_minutes"]
        ))
        db_conn.commit()
        
        # Retrieve user
        cur.execute(
            "SELECT ai_style, balance_minutes, is_premium FROM users WHERE telegram_id = %s",
            (sample_user_data["telegram_id"],)
        )
        result = cur.fetchone()
        cur.close()
        
        assert result is not None
        assert result[0] == "summary"  # ai_style
        assert result[1] == 100  # balance_minutes
        assert result[2] is False  # is_premium

    def test_update_user_style(self, db_conn, sample_user_data: dict):
        """Test updating user's AI style"""
        cur = db_conn.cursor()
        
        # Insert user
        cur.execute("""
            INSERT INTO users (telegram_id, ai_style)
            VALUES (%s, %s);
        """, (sample_user_data["telegram_id"], "summary"))
        db_conn.commit()
        
        # Update style
        new_style = "creative"
        cur.execute(
            "UPDATE users SET ai_style = %s WHERE telegram_id = %s",
            (new_style, sample_user_data["telegram_id"])
        )
        db_conn.commit()
        
        # Verify update
        cur.execute("SELECT ai_style FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        result = cur.fetchone()
        cur.close()
        
        assert result[0] == new_style

    def test_user_not_found(self, db_conn):
        """Test retrieving non-existent user"""
        cur = db_conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (999999999,))
        result = cur.fetchone()
        cur.close()
        
        assert result is None

    def test_duplicate_user_insert_conflict(self, db_conn, sample_user_data: dict):
        """Test handling duplicate user insertion"""
        cur = db_conn.cursor()
        
        # Insert first user
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s);
        """, (sample_user_data["telegram_id"], "user1", "Test"))
        db_conn.commit()
        
        # Try to insert same user ID again (should fail without ON CONFLICT)
        with pytest.raises(PostgresError):
            cur.execute("""
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (%s, %s, %s);
            """, (sample_user_data["telegram_id"], "user2", "Test2"))
            db_conn.commit()
        
        cur.close()
        db_conn.rollback()

    def test_on_conflict_update(self, db_conn, sample_user_data: dict):
        """Test ON CONFLICT DO UPDATE for user upsert"""
        cur = db_conn.cursor()
        
        # First insert
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name;
        """, (sample_user_data["telegram_id"], "user1", "Test"))
        db_conn.commit()
        
        # Second insert with same ID (should update)
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name;
        """, (sample_user_data["telegram_id"], "user_updated", "Updated"))
        db_conn.commit()
        
        # Verify update
        cur.execute("SELECT username, first_name FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        result = cur.fetchone()
        cur.close()
        
        assert result[0] == "user_updated"
        assert result[1] == "Updated"


class TestBalanceOperations:
    """Test balance-related database operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        """Setup: Create users table before each test"""
        cur = db_conn.cursor()
        cur.execute("""
            DROP TABLE IF EXISTS users CASCADE;
            CREATE TABLE users (
                telegram_id BIGINT PRIMARY KEY,
                balance_minutes INT DEFAULT 15,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db_conn.commit()
        yield
        
        cur.execute("DROP TABLE IF EXISTS users CASCADE;")
        db_conn.commit()
        cur.close()

    def test_get_balance(self, db_conn, sample_user_data: dict):
        """Test retrieving user balance"""
        cur = db_conn.cursor()
        
        # Insert user with balance
        cur.execute(
            "INSERT INTO users (telegram_id, balance_minutes) VALUES (%s, %s);",
            (sample_user_data["telegram_id"], sample_user_data["balance_minutes"])
        )
        db_conn.commit()
        
        # Get balance
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        balance = cur.fetchone()[0]
        cur.close()
        
        assert balance == 100

    def test_deduct_balance(self, db_conn, sample_user_data: dict):
        """Test deducting minutes from balance"""
        cur = db_conn.cursor()
        
        # Insert user
        cur.execute(
            "INSERT INTO users (telegram_id, balance_minutes) VALUES (%s, %s);",
            (sample_user_data["telegram_id"], 100)
        )
        db_conn.commit()
        
        # Deduct balance
        cur.execute(
            "UPDATE users SET balance_minutes = balance_minutes - %s WHERE telegram_id = %s;",
            (20, sample_user_data["telegram_id"])
        )
        db_conn.commit()
        
        # Verify deduction
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        new_balance = cur.fetchone()[0]
        cur.close()
        
        assert new_balance == 80

    def test_add_balance(self, db_conn, sample_user_data: dict):
        """Test adding minutes to balance"""
        cur = db_conn.cursor()
        
        # Insert user
        cur.execute(
            "INSERT INTO users (telegram_id, balance_minutes) VALUES (%s, %s);",
            (sample_user_data["telegram_id"], 50)
        )
        db_conn.commit()
        
        # Add balance
        cur.execute(
            "UPDATE users SET balance_minutes = balance_minutes + %s WHERE telegram_id = %s;",
            (30, sample_user_data["telegram_id"])
        )
        db_conn.commit()
        
        # Verify addition
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        new_balance = cur.fetchone()[0]
        cur.close()
        
        assert new_balance == 80

    def test_insufficient_balance(self, db_conn, sample_user_data: dict):
        """Test check for insufficient balance"""
        cur = db_conn.cursor()
        
        # Insert user with low balance
        cur.execute(
            "INSERT INTO users (telegram_id, balance_minutes) VALUES (%s, %s);",
            (sample_user_data["telegram_id"], 5)
        )
        db_conn.commit()
        
        # Check balance
        cur.execute("SELECT balance_minutes FROM users WHERE telegram_id = %s", (sample_user_data["telegram_id"],))
        balance = cur.fetchone()[0]
        cur.close()
        
        # Verify insufficient balance
        assert balance < 10


class TestPaymentOperations:
    """Test payment-related database operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        """Setup: Create tables before each test"""
        cur = db_conn.cursor()
        
        # Create users and payments tables
        cur.execute("""
            DROP TABLE IF EXISTS payments CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
            CREATE TABLE users (
                telegram_id BIGINT PRIMARY KEY,
                balance_minutes INT DEFAULT 15
            );
            CREATE TABLE payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                invoice_id VARCHAR(255) UNIQUE NOT NULL,
                amount_usd NUMERIC(10, 2) NOT NULL,
                minutes_to_add INT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db_conn.commit()
        yield
        
        cur.execute("DROP TABLE IF EXISTS payments CASCADE;")
        cur.execute("DROP TABLE IF EXISTS users CASCADE;")
        db_conn.commit()
        cur.close()

    def test_create_pending_payment(self, db_conn, sample_user_data: dict, sample_payment_data: dict):
        """Test creating a pending payment"""
        cur = db_conn.cursor()
        
        # Insert user first
        cur.execute("INSERT INTO users (telegram_id) VALUES (%s);", (sample_user_data["telegram_id"],))
        db_conn.commit()
        
        # Insert payment
        cur.execute("""
            INSERT INTO payments (user_id, invoice_id, amount_usd, minutes_to_add, status)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            sample_payment_data["user_id"],
            sample_payment_data["invoice_id"],
            sample_payment_data["amount_usd"],
            sample_payment_data["minutes_to_add"],
            sample_payment_data["status"]
        ))
        db_conn.commit()
        
        # Verify insertion
        cur.execute("SELECT * FROM payments WHERE invoice_id = %s", (sample_payment_data["invoice_id"],))
        payment = cur.fetchone()
        cur.close()
        
        assert payment is not None
        assert payment[2] == sample_payment_data["invoice_id"]
        assert payment[5] == "pending"

    def test_update_payment_status(self, db_conn, sample_user_data: dict, sample_payment_data: dict):
        """Test updating payment status"""
        cur = db_conn.cursor()
        
        # Insert user and payment
        cur.execute("INSERT INTO users (telegram_id) VALUES (%s);", (sample_user_data["telegram_id"],))
        cur.execute("""
            INSERT INTO payments (user_id, invoice_id, amount_usd, minutes_to_add, status)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            sample_payment_data["user_id"],
            sample_payment_data["invoice_id"],
            sample_payment_data["amount_usd"],
            sample_payment_data["minutes_to_add"],
            "pending"
        ))
        db_conn.commit()
        
        # Update status to completed
        cur.execute(
            "UPDATE payments SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE invoice_id = %s;",
            ("completed", sample_payment_data["invoice_id"])
        )
        db_conn.commit()
        
        # Verify update
        cur.execute("SELECT status FROM payments WHERE invoice_id = %s", (sample_payment_data["invoice_id"],))
        status = cur.fetchone()[0]
        cur.close()
        
        assert status == "completed"

    def test_get_payment_by_invoice_id(self, db_conn, sample_user_data: dict, sample_payment_data: dict):
        """Test retrieving payment by invoice ID"""
        cur = db_conn.cursor()
        
        # Setup
        cur.execute("INSERT INTO users (telegram_id) VALUES (%s);", (sample_user_data["telegram_id"],))
        cur.execute("""
            INSERT INTO payments (user_id, invoice_id, amount_usd, minutes_to_add, status)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            sample_payment_data["user_id"],
            sample_payment_data["invoice_id"],
            sample_payment_data["amount_usd"],
            sample_payment_data["minutes_to_add"],
            sample_payment_data["status"]
        ))
        db_conn.commit()
        
        # Retrieve
        cur.execute("SELECT * FROM payments WHERE invoice_id = %s", (sample_payment_data["invoice_id"],))
        payment = cur.fetchone()
        cur.close()
        
        assert payment is not None
        assert payment[3] == sample_payment_data["amount_usd"]
        assert payment[4] == sample_payment_data["minutes_to_add"]

    def test_list_pending_payments(self, db_conn, sample_user_data: dict):
        """Test listing pending payments"""
        cur = db_conn.cursor()
        
        # Insert user
        cur.execute("INSERT INTO users (telegram_id) VALUES (%s);", (sample_user_data["telegram_id"],))
        db_conn.commit()
        
        # Insert multiple payments
        for i in range(3):
            cur.execute("""
                INSERT INTO payments (user_id, invoice_id, amount_usd, minutes_to_add, status)
                VALUES (%s, %s, %s, %s, %s);
            """, (
                sample_user_data["telegram_id"],
                f"invoice_{i}",
                5.00 + i,
                100 + i*10,
                "pending" if i < 2 else "completed"
            ))
        db_conn.commit()
        
        # Get pending payments
        cur.execute("SELECT * FROM payments WHERE status = %s ORDER BY created_at DESC;", ("pending",))
        pending = cur.fetchall()
        cur.close()
        
        assert len(pending) == 2
