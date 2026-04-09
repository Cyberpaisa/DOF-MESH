
"""
Tests for core/sensitive_data_handler.py — PCI DSS compliant data protection.

Tests credit card handling, encryption, masking, and secure deletion.
All tests use mock/test data only.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sensitive_data_handler import (
    SensitiveDataHandler,
    DataType,
    SensitiveDataRecord,
    CRYPTO_AVAILABLE
)


class TestSensitiveDataHandler(unittest.TestCase):
    """Test sensitive data handler with isolated storage."""
    
    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_master_key = os.urandom(32)
        self.master_key_b64 = os.urandom(32).hex()  # Use hex for test
        
        # Patch environment variable
        self.env_patcher = patch.dict(os.environ, {
            'DOF_MASTER_KEY': self.master_key_b64
        })
        self.env_patcher.start()
        
        # Initialize handler
        self.handler = SensitiveDataHandler(
            storage_path=os.path.join(self.temp_dir, "sensitive"),
            master_key_env_var="DOF_MASTER_KEY"
        )
    
    def tearDown(self):
        """Clean up."""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_credit_card_storage_and_retrieval(self):
        """Test storing and retrieving credit card data."""
        if not CRYPTO_AVAILABLE:
            self.skipTest("cryptography library not available")
        
        # Test credit card data
        test_card = {
            "number": "4532123456789012",
            "expiry": "12/28",
            "holder_name": "Test User",
            "cvv": "123"
        }
        
        # Store credit card
        token = self.handler.store_credit_card(
            number=test_card["number"],
            expiry=test_card["expiry"],
            holder_name=test_card["holder_name"],
            cvv=test_card["cvv"]
        )
        
        self.assertIsNotNone(token)
        self.assertTrue(len(token) >= 16)
        
        # Retrieve credit card
        retrieved = self.handler.retrieve_credit_card(token)
        
        self.assertEqual(retrieved["number"], test_card["number"])
        self.assertEqual(retrieved["expiry"], test_card["expiry"])
        self.assertEqual(retrieved["holder_name"], test_card["holder_name"])
        self.assertEqual(retrieved["cvv"], test_card["cvv"])
    
    def test_credit_card_masking(self):
        """Test credit card number masking."""
        handler = SensitiveDataHandler()
        
        # Test 16-digit card
        masked = handler.mask_credit_card("4532-1234-5678-9012")
        self.assertEqual(masked, "4532-****-****-9012")
        
        # Test without dashes
        masked = handler.mask_credit_card("4532123456789012")
        self.assertEqual(masked, "4532-****-****-9012")
        
        # Test 15-digit card (Amex)
        masked = handler.mask_credit_card("3782-822463-10005")
        self.assertEqual(masked, "3782-******-10005")
        
        # Test generic masking
        masked = handler.mask_credit_card("123456789")
        self.assertEqual(masked, "1234*****")
    
    def test_data_expiration(self):
        """Test automatic data expiration."""
        if not CRYPTO_AVAILABLE:
            self.skipTest("cryptography library not available")
        
        # Store with short expiration
        token = self.handler.store_credit_card(
            number="4532123456789012",
            expiry="12/28",
            holder_name="Test User",
            expires_in=timedelta(seconds=1)  # Expire in 1 second
        )
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Try to retrieve - should raise exception
        with self.assertRaises(Exception):
            self.handler.retrieve_credit_card(token)
    
    def test_secure_deletion(self):
        """Test secure deletion of sensitive data."""
        if not CRYPTO_AVAILABLE:
            self.skipTest("cryptography library not available")
        
        # Store data
        token = self.handler.store_credit_card(
            number="4532123456789012",
            expiry="12/28",
            holder_name="Test User"
        )
        
        # Delete data
        result = self.handler.delete_sensitive_data(token)
        self.assertTrue(result)
        
        # Try to retrieve deleted data
        with self.assertRaises(Exception):
            self.handler.retrieve_credit_card(token)
        
        # Try to delete non-existent data
        result = self.handler.delete_sensitive_data("nonexistent")
        self.assertFalse(result)
    
    def test_validation(self):
        """Test credit card validation."""
        handler = SensitiveDataHandler()
        
        # Test valid Luhn algorithm (test card number)
        # 4532123456789012 is a valid test Visa number
        # Actually, let's use a known valid test number
        test_valid_numbers = [
            "4111111111111111",  # Visa test
            "5555555555554444",  # MasterCard test
            "378282246310005",   # Amex test
        ]
        
        for number in test_valid_numbers:
            # Just test that they don't raise validation errors
            try:
                handler.store_credit_card(
                    number=number,
                    expiry="12/28",
                    holder_name="Test User"
                )
            except Exception as e:
                if "invalid" in str(e).lower():
                    self.fail(f"Valid test card {number} failed validation")
    
    def test_audit_logging(self):
        """Test audit logging functionality."""
        if not CRYPTO_AVAILABLE:
            self.skipTest("cryptography library not available")
        
        audit_log = self.handler.audit_log_path
        
        # Store data
        token = self.handler.store_credit_card(
            number="4532123456789012",
            expiry="12/28",
            holder_name="Test User"
        )
        
        # Check audit log was created
        self.assertTrue(os.path.exists(audit_log))
        
        # Read audit log
        with open(audit_log, 'r') as f:
            lines = f.readlines()
        
        # Should have at least one audit entry
        self.assertGreater(len(lines), 0)
        
        # Check JSON format
        for line in lines:
            audit_entry = json.loads(line.strip())
            self.assertIn('action', audit_entry)
            self.assertIn('timestamp', audit_entry)
            self.assertIn('token', audit_entry)
            self.assertIn('data_type', audit_entry)
            self.assertIn('success', audit_entry)
    
    def test_token_uniqueness(self):
        """Test that tokens are unique."""
        if not CRYPTO_AVAILABLE:
            self.skipTest("cryptography library not available")
        
        tokens = set()
        
        for i in range(5):
            token = self.handler.store_credit_card(
                number=f"45321234567890{i:02d}",
                expiry="12/28",
                holder_name=f"User {i}"
            )
            tokens.add(token)
        
        # All tokens should be unique
        self.assertEqual(len(tokens), 5)


if __name__ == '__main__':
    unittest.main()
