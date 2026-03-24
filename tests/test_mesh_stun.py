"""Tests for core/mesh_stun.py — Phase 7 NAT traversal."""
import socket
import struct
import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mesh_stun import STUNClient, NATType, get_stun_client


# ─────────────────────────────────────
# NATType Tests
# ─────────────────────────────────────

class TestNATType(unittest.TestCase):

    def test_open_value(self):
        self.assertEqual(NATType.OPEN.value, "OPEN")

    def test_restricted_value(self):
        self.assertEqual(NATType.RESTRICTED.value, "RESTRICTED")

    def test_symmetric_value(self):
        self.assertEqual(NATType.SYMMETRIC.value, "SYMMETRIC")

    def test_blocked_value(self):
        self.assertEqual(NATType.BLOCKED.value, "BLOCKED")

    def test_enum_has_four_members(self):
        self.assertEqual(len(NATType), 4)

    def test_enum_iterable(self):
        self.assertGreater(len(list(NATType)), 0)


# ─────────────────────────────────────
# STUNClient Init Tests
# ─────────────────────────────────────

class TestSTUNClientInit(unittest.TestCase):

    def setUp(self):
        STUNClient._instance = None

    def test_default_stun_server_tuple(self):
        c = STUNClient()
        host, port = c.DEFAULT_STUN_SERVER
        self.assertIsInstance(host, str)
        self.assertIsInstance(port, int)

    def test_cache_ttl_positive(self):
        self.assertGreater(STUNClient.CACHE_TTL, 0)

    def test_initial_endpoint_none(self):
        c = STUNClient()
        self.assertIsNone(c._public_endpoint)

    def test_initial_nat_type_none(self):
        c = STUNClient()
        self.assertIsNone(c._nat_type)

    def test_magic_cookie_correct(self):
        self.assertEqual(STUNClient.STUN_MAGIC_COOKIE, 0x2112A442)

    def test_binding_request_type(self):
        self.assertEqual(STUNClient.BINDING_REQUEST, 0x0001)

    def test_binding_response_type(self):
        self.assertEqual(STUNClient.BINDING_RESPONSE, 0x0101)


# ─────────────────────────────────────
# discover_public_endpoint Tests
# ─────────────────────────────────────

class TestDiscover(unittest.TestCase):

    def setUp(self):
        STUNClient._instance = None
        self.client = STUNClient()
        self.client._last_update = 0  # force cache miss

    @patch("core.mesh_stun.socket.socket")
    def test_returns_tuple_on_success(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        # Minimal response that passes 20-byte check with correct magic
        resp = struct.pack("!HHIIII", 0x0101, 0, 0x2112A442, 0, 0, 0)
        sock.recvfrom.return_value = (resp, ("stun.l.google.com", 19302))
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        result = self.client.discover_public_endpoint()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    @patch("core.mesh_stun.socket.socket")
    def test_returns_str_and_int(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        resp = struct.pack("!HHIIII", 0x0101, 0, 0x2112A442, 0, 0, 0)
        sock.recvfrom.return_value = (resp, ("stun.l.google.com", 19302))
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        ip, port = self.client.discover_public_endpoint()
        self.assertIsInstance(ip, str)
        self.assertIsInstance(port, int)

    @patch("core.mesh_stun.socket.socket")
    def test_socket_closed_after_call(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        resp = struct.pack("!HHIIII", 0x0101, 0, 0x2112A442, 0, 0, 0)
        sock.recvfrom.return_value = (resp, ("stun.l.google.com", 19302))
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        self.client.discover_public_endpoint()
        sock.close.assert_called()

    @patch("core.mesh_stun.socket.socket")
    def test_timeout_returns_fallback(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        sock.recvfrom.side_effect = socket.timeout
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        ip, port = self.client.discover_public_endpoint()
        self.assertIsInstance(ip, str)
        self.assertIsInstance(port, int)

    @patch("core.mesh_stun.socket.socket")
    def test_timeout_sets_blocked(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        sock.recvfrom.side_effect = socket.timeout
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        self.client.discover_public_endpoint()
        self.assertEqual(self.client._nat_type, NATType.BLOCKED)

    @patch("core.mesh_stun.socket.socket")
    def test_timeout_closes_socket(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        sock.recvfrom.side_effect = socket.timeout
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        self.client.discover_public_endpoint()
        sock.close.assert_called()

    @patch("core.mesh_stun.socket.socket")
    def test_os_error_handled_gracefully(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        sock.recvfrom.side_effect = OSError("network unreachable")
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        # Must not raise
        ip, port = self.client.discover_public_endpoint()
        self.assertIsInstance(ip, str)
        self.assertIsInstance(port, int)

    @patch("core.mesh_stun.socket.socket")
    def test_cache_prevents_second_socket_creation(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        resp = struct.pack("!HHIIII", 0x0101, 0, 0x2112A442, 0, 0, 0)
        sock.recvfrom.return_value = (resp, ("stun.l.google.com", 19302))
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        self.client.discover_public_endpoint()
        self.client.discover_public_endpoint()  # second call → cache hit
        self.assertEqual(mock_cls.call_count, 1)

    @patch("core.mesh_stun.socket.socket")
    def test_nat_type_set_after_success(self, mock_cls):
        sock = MagicMock()
        mock_cls.return_value = sock
        resp = struct.pack("!HHIIII", 0x0101, 0, 0x2112A442, 0, 0, 0)
        sock.recvfrom.return_value = (resp, ("stun.l.google.com", 19302))
        sock.getsockname.return_value = ("10.0.0.1", 5000)
        self.client.discover_public_endpoint()
        self.assertIsNotNone(self.client._nat_type)
        self.assertIsInstance(self.client._nat_type, NATType)


# ─────────────────────────────────────
# Singleton Tests
# ─────────────────────────────────────

class TestSingleton(unittest.TestCase):

    def setUp(self):
        STUNClient._instance = None

    def test_same_instance_twice(self):
        c1 = get_stun_client()
        c2 = get_stun_client()
        self.assertIs(c1, c2)

    def test_returns_stun_client(self):
        c = get_stun_client()
        self.assertIsInstance(c, STUNClient)

    def test_class_method_same_as_function(self):
        c1 = STUNClient.get_stun_client()
        c2 = get_stun_client()
        self.assertIs(c1, c2)

    def test_reset_creates_new(self):
        c1 = get_stun_client()
        STUNClient._instance = None
        c2 = get_stun_client()
        self.assertIsNot(c1, c2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
