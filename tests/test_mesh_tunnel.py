"""Tests for core/mesh_tunnel.py — Phase 7 encrypted tunnel."""
import secrets
import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mesh_tunnel import TunnelSession, TunnelManager, get_tunnel_manager


# ─────────────────────────────────────
# TunnelSession Tests
# ─────────────────────────────────────

class TestTunnelSession(unittest.TestCase):

    def _make_session(self, session_id=None, host="127.0.0.1", port=9999, key=None):
        if session_id is None:
            session_id = "sess-001"
        if key is None:
            key = secrets.token_bytes(32)
        return TunnelSession(session_id, host, port, key)

    def test_session_stores_id(self):
        s = self._make_session(session_id="test-id")
        self.assertEqual(s.session_id, "test-id")

    def test_session_stores_host(self):
        s = self._make_session(host="10.0.0.1")
        self.assertEqual(s.peer_host, "10.0.0.1")

    def test_session_stores_port(self):
        s = self._make_session(port=8888)
        self.assertEqual(s.peer_port, 8888)

    def test_session_stores_key(self):
        key = secrets.token_bytes(32)
        s = self._make_session(key=key)
        self.assertEqual(s._key, key)

    def test_encrypt_returns_bytes(self):
        s = self._make_session()
        ct = s.encrypt(b"hello")
        self.assertIsInstance(ct, bytes)

    def test_encrypt_changes_data(self):
        s = self._make_session()
        plaintext = b"hello mesh"
        self.assertNotEqual(s.encrypt(plaintext), plaintext)

    def test_encrypt_decrypt_roundtrip(self):
        s = self._make_session()
        plaintext = b"Hello, DOF Mesh!"
        ct = s.encrypt(plaintext)
        self.assertEqual(s.decrypt(ct), plaintext)

    def test_encrypt_decrypt_empty(self):
        s = self._make_session()
        ct = s.encrypt(b"")
        self.assertEqual(s.decrypt(ct), b"")

    def test_encrypt_decrypt_large(self):
        s = self._make_session()
        big = secrets.token_bytes(64 * 1024)
        self.assertEqual(s.decrypt(s.encrypt(big)), big)

    def test_wrong_key_raises(self):
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        s1 = self._make_session(key=key1)
        s2 = self._make_session(key=key2)
        ct = s1.encrypt(b"secret")
        with self.assertRaises(Exception):
            s2.decrypt(ct)

    def test_tampered_ciphertext_raises(self):
        s = self._make_session()
        ct = bytearray(s.encrypt(b"data"))
        ct[-1] ^= 0xFF  # flip last byte
        with self.assertRaises(Exception):
            s.decrypt(bytes(ct))

    def test_encrypt_produces_different_ciphertexts(self):
        s = self._make_session()
        pt = b"same plaintext"
        ct1 = s.encrypt(pt)
        ct2 = s.encrypt(pt)
        # Different nonces → different ciphertexts
        self.assertNotEqual(ct1, ct2)

    def test_different_sessions_isolated(self):
        k1, k2 = secrets.token_bytes(32), secrets.token_bytes(32)
        s1 = self._make_session(session_id="s1", key=k1)
        s2 = self._make_session(session_id="s2", key=k2)
        ct = s1.encrypt(b"private")
        with self.assertRaises(Exception):
            s2.decrypt(ct)


# ─────────────────────────────────────
# TunnelManager Tests
# ─────────────────────────────────────

class TestTunnelManager(unittest.TestCase):

    def setUp(self):
        TunnelManager._instance = None
        self.mgr = TunnelManager()

    def test_initial_sessions_empty(self):
        self.assertEqual(len(self.mgr.get_sessions()), 0)

    def test_open_tunnel_returns_session(self):
        s = self.mgr.open_tunnel("127.0.0.1", 9999, "shared-secret")
        self.assertIsInstance(s, TunnelSession)

    def test_open_tunnel_stores_session(self):
        self.mgr.open_tunnel("127.0.0.1", 9999, "secret")
        self.assertEqual(len(self.mgr.get_sessions()), 1)

    def test_open_tunnel_session_id_unique(self):
        s1 = self.mgr.open_tunnel("127.0.0.1", 9999, "sec")
        s2 = self.mgr.open_tunnel("127.0.0.1", 9998, "sec")
        self.assertNotEqual(s1.session_id, s2.session_id)

    def test_open_tunnel_stores_correct_host(self):
        s = self.mgr.open_tunnel("192.168.1.50", 9999, "sec")
        self.assertEqual(s.peer_host, "192.168.1.50")

    def test_open_tunnel_stores_correct_port(self):
        s = self.mgr.open_tunnel("127.0.0.1", 7777, "sec")
        self.assertEqual(s.peer_port, 7777)

    def test_same_secret_same_key(self):
        s1 = self.mgr.open_tunnel("127.0.0.1", 9999, "same-secret")
        TunnelManager._instance = None
        mgr2 = TunnelManager()
        s2 = mgr2.open_tunnel("127.0.0.1", 9999, "same-secret")
        # HKDF is deterministic — same secret + host → same key
        self.assertEqual(s1._key, s2._key)

    def test_close_tunnel_removes_session(self):
        s = self.mgr.open_tunnel("127.0.0.1", 9999, "sec")
        self.mgr.close_tunnel(s.session_id)
        self.assertEqual(len(self.mgr.get_sessions()), 0)

    def test_close_nonexistent_returns_false(self):
        result = self.mgr.close_tunnel("nonexistent-id")
        self.assertFalse(result)

    def test_multiple_sessions_tracked(self):
        self.mgr.open_tunnel("10.0.0.1", 9001, "s1")
        self.mgr.open_tunnel("10.0.0.2", 9002, "s2")
        self.mgr.open_tunnel("10.0.0.3", 9003, "s3")
        self.assertEqual(len(self.mgr.get_sessions()), 3)

    def test_get_sessions_returns_list(self):
        self.assertIsInstance(self.mgr.get_sessions(), list)


# ─────────────────────────────────────
# Singleton Tests
# ─────────────────────────────────────

class TestGetTunnelManager(unittest.TestCase):

    def setUp(self):
        TunnelManager._instance = None

    def test_same_instance(self):
        m1 = get_tunnel_manager()
        m2 = get_tunnel_manager()
        self.assertIs(m1, m2)

    def test_is_tunnel_manager(self):
        self.assertIsInstance(get_tunnel_manager(), TunnelManager)


if __name__ == "__main__":
    unittest.main(verbosity=2)
