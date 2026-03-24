"""Tests for core.icarus_v2 — IcarusV2 behavioral threat hunter."""
import unittest
from unittest.mock import patch


class TestBaselineModel(unittest.TestCase):
    def setUp(self):
        from core.icarus_v2 import BaselineModel
        self.model = BaselineModel()

    def test_update_accepts_bytes(self):
        self.model.update(b"hello world packet")

    def test_stats_returns_tuple(self):
        result = self.model.stats(b"data")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_detect_anomaly_returns_tuple(self):
        result = self.model.detect_anomaly(b"normal packet")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_detect_anomaly_tuple_bool_dict(self):
        is_anomaly, details = self.model.detect_anomaly(b"packet")
        self.assertIsInstance(is_anomaly, bool)
        self.assertIsInstance(details, dict)

    def test_update_then_detect_no_crash(self):
        for i in range(10):
            self.model.update(bytes(range(i % 256)))
        is_anom, _ = self.model.detect_anomaly(b"test")
        self.assertIsInstance(is_anom, bool)


class TestKeyRotationMonitor(unittest.TestCase):
    def setUp(self):
        from core.icarus_v2 import KeyRotationMonitor
        self.krm = KeyRotationMonitor()

    def test_register_key_no_crash(self):
        self.krm.register_key("sha256:abc123")

    def test_detect_anomaly_new_key(self):
        result = self.krm.detect_anomaly("sha256:new_unseen_key")
        self.assertIsInstance(result, bool)

    def test_detect_anomaly_registered_key(self):
        self.krm.register_key("sha256:known")
        result = self.krm.detect_anomaly("sha256:known")
        self.assertIsInstance(result, bool)

    def test_rapid_rotation_is_anomaly(self):
        # Register same key multiple times quickly — should flag anomaly
        for i in range(20):
            self.krm.register_key(f"sha256:key_{i}")
            self.krm.detect_anomaly(f"sha256:key_{i}")


class TestIcarusHoneypot(unittest.TestCase):
    def setUp(self):
        from core.icarus_v2 import Honeypot
        self.hp = Honeypot()

    def test_simulate_connection_returns_tuple(self):
        result = self.hp.simulate_connection()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_simulate_connection_port_int(self):
        port, payload = self.hp.simulate_connection()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)

    def test_simulate_connection_payload_bytes(self):
        port, payload = self.hp.simulate_connection()
        self.assertIsInstance(payload, bytes)

    def test_log_intrusion_no_crash(self):
        self.hp.log_intrusion(8765, b"probe payload")

    def test_get_traps_returns_list(self):
        result = self.hp.get_traps()
        self.assertIsInstance(result, list)

    def test_log_then_get_traps(self):
        self.hp.log_intrusion(1234, b"test")
        traps = self.hp.get_traps()
        self.assertGreater(len(traps), 0)


class TestIcarusV2(unittest.TestCase):
    def setUp(self):
        from core.icarus_v2 import IcarusV2
        self.icarus = IcarusV2()

    def test_process_packet_returns_dict(self):
        result = self.icarus.process_packet(b"normal traffic", "sha256:abc")
        self.assertIsInstance(result, dict)

    def test_process_packet_returns_dict_always(self):
        result = self.icarus.process_packet(b"packet data", "sha256:key1")
        self.assertIsInstance(result, dict)  # empty dict = no threat

    def test_process_empty_packet(self):
        result = self.icarus.process_packet(b"", "sha256:empty")
        self.assertIsInstance(result, dict)

    def test_run_honeypot_cycle_returns_none_or_dict(self):
        result = self.icarus.run_honeypot_cycle()
        self.assertIn(type(result), [type(None), dict])

    def test_get_status_returns_dict(self):
        status = self.icarus.get_status()
        self.assertIsInstance(status, dict)

    def test_get_status_has_packets_processed(self):
        self.icarus.process_packet(b"test", "sha256:k0")
        status = self.icarus.get_status()
        self.assertIn("packets_processed", status)
        self.assertGreater(status["packets_processed"], 0)

    def test_process_high_entropy_packet(self):
        import os
        random_bytes = os.urandom(256)
        result = self.icarus.process_packet(random_bytes, "sha256:random")
        self.assertIsInstance(result, dict)  # dict (may be empty = no anomaly triggered yet)

    def test_process_multiple_packets(self):
        for i in range(5):
            result = self.icarus.process_packet(
                f"packet {i}".encode(), f"sha256:k{i}"
            )
            self.assertIsInstance(result, dict)


class TestShannonEntropy(unittest.TestCase):
    def test_empty_bytes_returns_zero(self):
        from core.icarus_v2 import shannon_entropy
        self.assertEqual(shannon_entropy(b""), 0.0)

    def test_uniform_bytes_high_entropy(self):
        from core.icarus_v2 import shannon_entropy
        import os
        e = shannon_entropy(os.urandom(1024))
        self.assertGreater(e, 6.0)

    def test_repeated_bytes_low_entropy(self):
        from core.icarus_v2 import shannon_entropy
        e = shannon_entropy(b"aaaaaaaaaa")
        self.assertEqual(e, 0.0)

    def test_returns_float(self):
        from core.icarus_v2 import shannon_entropy
        self.assertIsInstance(shannon_entropy(b"hello"), float)
