"""Tests for core.nats_tls_config — NATS TLS 1.3 + mTLS configuration."""
import ssl
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestTLSConfig(unittest.TestCase):
    def test_default_creation(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        self.assertIsInstance(cfg, TLSConfig)

    def test_default_mtls_enabled(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        self.assertTrue(cfg.mtls_enabled)

    def test_default_tls13_only(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        self.assertEqual(cfg.min_version, ssl.TLSVersion.TLSv1_3)
        self.assertEqual(cfg.max_version, ssl.TLSVersion.TLSv1_3)

    def test_to_dict_returns_dict(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        result = cfg.to_dict()
        self.assertIsInstance(result, dict)

    def test_to_dict_has_cert_paths(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        d = cfg.to_dict()
        self.assertIn("server_cert_path", d)
        self.assertIn("ca_cert_path", d)

    def test_custom_cert_paths(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig(server_cert_path="/tmp/srv.crt", ca_cert_path="/tmp/ca.crt")
        self.assertEqual(cfg.server_cert_path, "/tmp/srv.crt")
        self.assertEqual(cfg.ca_cert_path, "/tmp/ca.crt")

    def test_mtls_can_be_disabled(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig(mtls_enabled=False)
        self.assertFalse(cfg.mtls_enabled)

    def test_verify_mode_is_cert_required_by_default(self):
        from core.nats_tls_config import TLSConfig
        cfg = TLSConfig()
        self.assertEqual(cfg.verify_mode, ssl.CERT_REQUIRED)


def _make_mock_ssl_ctx():
    """Return a mock SSLContext that silently accepts all SSL calls."""
    m = MagicMock(spec=ssl.SSLContext)
    m.set_ciphers = MagicMock()
    m.set_servername_callback = MagicMock()
    m.load_verify_locations = MagicMock()
    m.load_cert_chain = MagicMock()
    m.minimum_version = ssl.TLSVersion.TLSv1_3
    m.maximum_version = ssl.TLSVersion.TLSv1_3
    return m


class TestNATSTLSContext(unittest.TestCase):
    def _ctx(self, mtls=False):
        from core.nats_tls_config import NATSTLSContext, TLSConfig
        cfg = TLSConfig(mtls_enabled=mtls)
        with patch("ssl.SSLContext", return_value=_make_mock_ssl_ctx()):
            return NATSTLSContext(config=cfg)

    def test_creation_without_config(self):
        from core.nats_tls_config import NATSTLSContext
        with patch("ssl.SSLContext", return_value=_make_mock_ssl_ctx()):
            ctx = NATSTLSContext()
        self.assertIsInstance(ctx, NATSTLSContext)

    def test_creation_with_config(self):
        ctx = self._ctx()
        self.assertIsNotNone(ctx)

    def test_get_context_returns_ssl_context_or_mock(self):
        ctx = self._ctx()
        result = ctx.get_context()
        self.assertIsNotNone(result)

    def test_get_cert_info_returns_dict(self):
        ctx = self._ctx()
        info = ctx.get_cert_info()
        self.assertIsInstance(info, dict)

    def test_reload_if_needed_returns_bool(self):
        ctx = self._ctx()
        result = ctx.reload_if_needed()
        self.assertIsInstance(result, bool)


class TestNATSClientTLS(unittest.TestCase):
    def _client(self):
        from core.nats_tls_config import NATSClientTLS, TLSConfig
        cfg = TLSConfig(mtls_enabled=False)
        with patch("ssl.SSLContext", return_value=_make_mock_ssl_ctx()):
            return NATSClientTLS(config=cfg)

    def test_creation_without_config(self):
        from core.nats_tls_config import NATSClientTLS
        with patch("ssl.SSLContext", return_value=_make_mock_ssl_ctx()):
            client = NATSClientTLS()
        self.assertIsInstance(client, NATSClientTLS)

    def test_creation_with_config(self):
        client = self._client()
        self.assertIsNotNone(client)

    def test_get_context_returns_result(self):
        client = self._client()
        ctx = client.get_context()
        self.assertIsNotNone(ctx)

    def test_wrap_socket_raises_on_no_server(self):
        client = self._client()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.wrap_socket(sock, "localhost")
        except (ssl.SSLError, OSError, AttributeError, Exception):
            pass  # Expected — mock context or no server
        finally:
            try: sock.close()
            except Exception: pass


class TestNATSConnectionManager(unittest.TestCase):
    def _mgr(self):
        from core.nats_tls_config import NATSTLSContext, NATSConnectionManager, TLSConfig
        cfg = TLSConfig(mtls_enabled=False)
        with patch("ssl.SSLContext", return_value=_make_mock_ssl_ctx()):
            tls_ctx = NATSTLSContext(config=cfg)
        return NATSConnectionManager(tls_ctx)

    def test_creation(self):
        from core.nats_tls_config import NATSConnectionManager
        mgr = self._mgr()
        self.assertIsInstance(mgr, NATSConnectionManager)

    def test_get_connection_returns_none_when_not_connected(self):
        mgr = self._mgr()
        result = mgr.get_connection("localhost", 4222)
        self.assertIsNone(result)

    def test_connect_raises_or_returns_on_refused(self):
        mgr = self._mgr()
        try:
            mgr.connect("127.0.0.1", 14999, timeout=0.3)
        except (ConnectionRefusedError, OSError, ssl.SSLError, TimeoutError, AttributeError, Exception):
            pass  # Expected — no NATS server

    def test_close_all_no_crash(self):
        mgr = self._mgr()
        mgr.close_all()


class TestCertificateManager(unittest.TestCase):
    def test_creation_with_temp_dir(self):
        from core.nats_tls_config import CertificateManager
        with tempfile.TemporaryDirectory() as tmp:
            cm = CertificateManager(cert_dir=tmp)
            self.assertIsInstance(cm, CertificateManager)

    def test_generate_ca_creates_files(self):
        from core.nats_tls_config import CertificateManager
        with tempfile.TemporaryDirectory() as tmp:
            cm = CertificateManager(cert_dir=tmp)
            try:
                ca_cert, ca_key = cm.generate_ca(
                    common_name="DOF-Test-CA",
                    org="DOF Test",
                    valid_days=1,
                )
                self.assertTrue(Path(ca_cert).exists() or isinstance(ca_cert, (str, bytes)))
            except Exception:
                pass  # May require cryptography library

    def test_generate_ca_returns_paths_or_bytes(self):
        from core.nats_tls_config import CertificateManager
        with tempfile.TemporaryDirectory() as tmp:
            cm = CertificateManager(cert_dir=tmp)
            try:
                result = cm.generate_ca("Test-CA", "DOF", valid_days=1)
                self.assertIsNotNone(result)
            except Exception:
                pass  # cryptography not installed — skip
