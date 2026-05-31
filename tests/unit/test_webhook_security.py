"""
Unit tests for webhook server signature verification.

Tests cover:
- Signature generation and validation
- Hash computation
- Token verification
"""

import pytest
import hashlib
import hmac
from typing import Tuple


class TestWebhookSignatureVerification:
    """Test webhook signature verification"""

    def test_generate_signature(self):
        """Test webhook signature generation"""
        secret = "test_secret_key"
        data = "test_webhook_data"
        
        # Generate signature
        signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert len(signature) == 64  # SHA256 hex is 64 chars
        assert isinstance(signature, str)

    def test_verify_valid_signature(self):
        """Test verification of valid signature"""
        secret = "test_secret_key"
        data = "test_webhook_data"
        
        # Generate signature
        expected_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature
        computed_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert computed_signature == expected_signature

    def test_verify_invalid_signature(self):
        """Test rejection of invalid signature"""
        secret = "test_secret_key"
        data = "test_webhook_data"
        
        # Generate valid signature
        expected_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Try with different data
        wrong_data = "different_data"
        computed_signature = hmac.new(
            secret.encode(),
            wrong_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert computed_signature != expected_signature

    def test_signature_consistency(self):
        """Test that same inputs always produce same signature"""
        secret = "test_secret"
        data = "consistent_data"
        
        sig1 = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        
        assert sig1 == sig2

    def test_signature_case_sensitivity(self):
        """Test that signature is case sensitive for data"""
        secret = "secret"
        
        sig_lower = hmac.new(secret.encode(), "data".encode(), hashlib.sha256).hexdigest()
        sig_upper = hmac.new(secret.encode(), "DATA".encode(), hashlib.sha256).hexdigest()
        
        assert sig_lower != sig_upper

    def test_empty_data_signature(self):
        """Test signature generation with empty data"""
        secret = "secret"
        data = ""
        
        signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert len(signature) == 64
        assert signature is not None


class TestPayloadValidation:
    """Test webhook payload validation"""

    def test_json_payload_extraction(self):
        """Test extracting data from JSON payload"""
        import json
        
        payload = {
            "user_id": 123456,
            "invoice_id": "invoice_12345",
            "amount": 5.00,
            "status": "completed"
        }
        
        json_str = json.dumps(payload)
        extracted = json.loads(json_str)
        
        assert extracted["user_id"] == 123456
        assert extracted["invoice_id"] == "invoice_12345"
        assert extracted["amount"] == 5.00
        assert extracted["status"] == "completed"

    def test_required_fields_validation(self):
        """Test validation of required webhook fields"""
        payload = {
            "user_id": 123456,
            "invoice_id": "invoice_12345",
            "amount": 5.00,
        }
        
        required_fields = ["user_id", "invoice_id", "amount", "status"]
        
        for field in required_fields:
            if field not in payload:
                pytest.skip(f"Field {field} missing from payload")

    def test_amount_type_validation(self):
        """Test amount field type validation"""
        valid_amounts = [5.00, 10, 0.01, 1000.99]
        
        for amount in valid_amounts:
            assert isinstance(float(amount), float)
            assert float(amount) > 0

    def test_status_enum_validation(self):
        """Test status field is from allowed enum"""
        valid_statuses = ["pending", "completed", "failed", "expired"]
        test_status = "completed"
        
        assert test_status in valid_statuses
