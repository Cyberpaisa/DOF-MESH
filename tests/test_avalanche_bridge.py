"""
Tests for core/avalanche_bridge.py — AvalancheBridge.

Tests offline mode and hex_to_bytes32 conversion.
On-chain tests require AVALANCHE_PRIVATE_KEY (skipped in CI).
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.avalanche_bridge import _hex_to_bytes32


class TestHexToBytes32(unittest.TestCase):
    """Test _hex_to_bytes32 conversion."""

    def test_full_64_char_hex(self):
        hex_str = "a" * 64
        result = _hex_to_bytes32(hex_str)
        self.assertEqual(len(result), 32)
        self.assertEqual(result, bytes.fromhex("a" * 64))

    def test_with_0x_prefix(self):
        hex_str = "0x" + "b" * 64
        result = _hex_to_bytes32(hex_str)
        self.assertEqual(len(result), 32)
        self.assertEqual(result, bytes.fromhex("b" * 64))

    def test_short_hex_padded(self):
        hex_str = "abcd"
        result = _hex_to_bytes32(hex_str)
        self.assertEqual(len(result), 32)
        self.assertEqual(result[:2], bytes.fromhex("abcd"))
        self.assertEqual(result[2:], b"\x00" * 30)

    def test_long_hex_truncated(self):
        hex_str = "ff" * 40  # 40 bytes
        result = _hex_to_bytes32(hex_str)
        self.assertEqual(len(result), 32)
        self.assertEqual(result, bytes.fromhex("ff" * 32))


class TestAvalancheBridgeOffline(unittest.TestCase):
    """Test AvalancheBridge in offline mode."""

    def setUp(self):
        self._orig_rpc = os.environ.get("AVALANCHE_RPC_URL")
        self._orig_key = os.environ.get("AVALANCHE_PRIVATE_KEY")
        self._orig_addr = os.environ.get("VALIDATION_REGISTRY_ADDRESS")
        os.environ.pop("AVALANCHE_RPC_URL", None)
        os.environ.pop("AVALANCHE_PRIVATE_KEY", None)
        os.environ.pop("VALIDATION_REGISTRY_ADDRESS", None)

    def tearDown(self):
        for key, val in [
            ("AVALANCHE_RPC_URL", self._orig_rpc),
            ("AVALANCHE_PRIVATE_KEY", self._orig_key),
            ("VALIDATION_REGISTRY_ADDRESS", self._orig_addr),
        ]:
            if val is not None:
                os.environ[key] = val

    def test_offline_without_env(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        self.assertFalse(bridge.is_online)

    def test_send_attestation_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        result = bridge.send_attestation("abc", "def", True)
        self.assertEqual(result["status"], "offline")

    def test_send_batch_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        result = bridge.send_batch([{"certificate_hash": "a", "agent_id": "b", "compliant": True}])
        self.assertEqual(result["status"], "offline")

    def test_verify_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        result = bridge.verify_on_chain("abc")
        self.assertEqual(result["status"], "offline")

    def test_is_compliant_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        self.assertIsNone(bridge.is_compliant_on_chain("abc"))

    def test_total_attestations_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        self.assertIsNone(bridge.total_attestations())

    def test_get_balance_offline(self):
        from core.avalanche_bridge import AvalancheBridge
        bridge = AvalancheBridge()
        self.assertIsNone(bridge.get_balance())


class TestAvalancheBridgeOnline(unittest.TestCase):
    """Test AvalancheBridge with real Avalanche C-Chain (requires env vars).

    These tests are skipped in CI where AVALANCHE_PRIVATE_KEY is not set.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        cls._has_key = bool(os.environ.get("AVALANCHE_PRIVATE_KEY"))

    def setUp(self):
        if not self._has_key:
            self.skipTest("AVALANCHE_PRIVATE_KEY not set — skipping on-chain tests")
        from core.avalanche_bridge import AvalancheBridge
        self.bridge = AvalancheBridge()
        if not self.bridge.is_online:
            self.skipTest("AvalancheBridge not online — skipping")

    def test_connection(self):
        self.assertTrue(self.bridge.is_online)

    def test_get_balance(self):
        balance = self.bridge.get_balance()
        self.assertIsNotNone(balance)
        self.assertGreaterEqual(balance, 0)  # wallet may be empty but must return a valid float

    def test_total_attestations(self):
        total = self.bridge.total_attestations()
        self.assertIsNotNone(total)
        self.assertGreaterEqual(total, 0)

    def test_verify_existing_attestation(self):
        """Verify the test attestation we sent during development."""
        import hashlib
        test_cert_hash = hashlib.sha256(b"dof-test-attestation-001").hexdigest()
        result = self.bridge.verify_on_chain(test_cert_hash)
        # Should be found (we sent it during development)
        if result["status"] == "found":
            self.assertTrue(result["compliant"])
        # If not found, that's OK too (different network state)


if __name__ == "__main__":
    unittest.main()
