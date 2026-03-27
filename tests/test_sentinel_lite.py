"""
Tests unitarios para Sentinel Lite — NO requieren red.
Usa unittest.mock.patch sobre urllib.request.urlopen para simular HTTP.
"""

import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

from core.sentinel_lite import SentinelLite, CheckResult, SentinelResult


class _MockResponse:
    """Mock para urllib response."""

    def __init__(self, body: bytes = b"", code: int = 200):
        self._body = body
        self._code = code

    def getcode(self):
        return self._code

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestIdentityCheck(unittest.TestCase):
    """Tests para check_erc8004_identity."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    def test_valid_address_format(self):
        """Address 0x válido → score 80."""
        result = self.sentinel.check_erc8004_identity(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        )
        self.assertEqual(result.score, 80)
        self.assertIn("Valid", result.details)
        self.assertIn("identity_hash", result.details)

    def test_invalid_address_format(self):
        """Address sin 0x o corto → score 0."""
        # Sin 0x
        result = self.sentinel.check_erc8004_identity("cd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 0)
        self.assertIn("Invalid", result.details)

        # Muy corto
        result = self.sentinel.check_erc8004_identity("0x1234")
        self.assertEqual(result.score, 0)

        # Vacío
        result = self.sentinel.check_erc8004_identity("")
        self.assertEqual(result.score, 0)

        # Caracteres inválidos
        result = self.sentinel.check_erc8004_identity("0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")
        self.assertEqual(result.score, 0)


class TestMetadataCheck(unittest.TestCase):
    """Tests para check_metadata_dict (sin red)."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    def test_metadata_complete(self):
        """Metadata con todos los campos → 100."""
        meta = {"name": "Apex", "description": "Agent", "version": "1.0"}
        result = self.sentinel.check_metadata_dict(meta)
        self.assertEqual(result.score, 100)
        self.assertIn("All required", result.details)

    def test_metadata_partial(self):
        """Metadata con campos faltantes → 50."""
        meta = {"name": "Apex"}
        result = self.sentinel.check_metadata_dict(meta)
        self.assertEqual(result.score, 50)
        self.assertIn("Partial", result.details)

    def test_metadata_empty(self):
        """Metadata vacío → 0."""
        result = self.sentinel.check_metadata_dict({})
        self.assertEqual(result.score, 0)
        self.assertIn("No required", result.details)


class TestMcpToolsCheck(unittest.TestCase):
    """Tests para check_mcp_tools."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    def test_mcp_tools_many(self):
        """>10 tools → 100."""
        meta = {"tools": [f"tool_{i}" for i in range(15)]}
        result = self.sentinel.check_mcp_tools(meta)
        self.assertEqual(result.score, 100)
        self.assertIn("15 tools", result.details)

    def test_mcp_tools_some(self):
        """6 tools → 80 (>5)."""
        meta = {"tools": [f"tool_{i}" for i in range(6)]}
        result = self.sentinel.check_mcp_tools(meta)
        self.assertEqual(result.score, 80)

    def test_mcp_tools_few(self):
        """3 tools → 60 (>0)."""
        meta = {"tools": [f"tool_{i}" for i in range(3)]}
        result = self.sentinel.check_mcp_tools(meta)
        self.assertEqual(result.score, 60)

    def test_mcp_tools_none(self):
        """0 tools → 30."""
        meta = {"tools": []}
        result = self.sentinel.check_mcp_tools(meta)
        self.assertEqual(result.score, 30)
        self.assertIn("0 tools", result.details)

    def test_mcp_tools_mcptools_field(self):
        """Usa campo 'mcpTools' si 'tools' no existe."""
        meta = {"mcpTools": ["a", "b", "c"]}
        result = self.sentinel.check_mcp_tools(meta)
        self.assertEqual(result.score, 60)


class TestValidateOffline(unittest.TestCase):
    """Tests para validate_offline."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    def test_validate_offline(self):
        """Validación sin red — solo identity + metadata + mcp_tools + x402."""
        meta = {
            "name": "Test Agent",
            "description": "A test",
            "version": "1.0",
            "tools": [f"t{i}" for i in range(12)],
        }
        result = self.sentinel.validate_offline(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            metadata=meta,
        )
        self.assertIsInstance(result, SentinelResult)
        self.assertGreater(result.checks_run, 1)
        self.assertIn("identity", result.checks)
        self.assertIn("mcp_tools", result.checks)
        self.assertIn("metadata", result.checks)
        # No checks de red
        self.assertNotIn("health", result.checks)
        self.assertNotIn("a2a", result.checks)
        self.assertNotIn("response_time", result.checks)

    def test_validate_offline_no_metadata(self):
        """Offline sin metadata — solo identity."""
        result = self.sentinel.validate_offline(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
        )
        self.assertEqual(result.checks_run, 1)
        self.assertIn("identity", result.checks)


class TestVerdicts(unittest.TestCase):
    """Tests para los tres verdicts."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    def test_verdict_pass(self):
        """Score >=60 → PASS."""
        # identity=80, metadata=100, mcp=100 → promedio ponderado alto
        meta = {
            "name": "Agent",
            "description": "Desc",
            "version": "1.0",
            "tools": [f"t{i}" for i in range(15)],
        }
        result = self.sentinel.validate_offline(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            metadata=meta,
        )
        self.assertEqual(result.verdict, "PASS")
        self.assertGreaterEqual(result.total_score, 60)

    def test_verdict_warn(self):
        """Score >=40 y <60 → WARN."""
        # identity=0 (bad address), metadata=100, mcp=30 → mixed
        meta = {
            "name": "Agent",
            "description": "Desc",
            "version": "1.0",
            "tools": [],
        }
        result = self.sentinel.validate_offline("invalid_addr", metadata=meta)
        # identity=0(w=0.20), metadata=100(w=0.15), mcp=30(w=0.10), x402=0(w=0.05)
        # weighted = (0*0.20 + 100*0.15 + 30*0.10 + 0*0.05) / (0.20+0.15+0.10+0.05)
        # = (0 + 15 + 3 + 0) / 0.50 = 36 → FAIL
        # Ajustemos para WARN: identity=0, metadata=100, mcp=60 (>0 tools)
        meta2 = {
            "name": "Agent",
            "description": "Desc",
            "version": "1.0",
            "tools": ["a", "b"],
        }
        result = self.sentinel.validate_offline("invalid_addr", metadata=meta2)
        # identity=0(0.20), metadata=100(0.15), mcp=60(0.10), x402=0(0.05)
        # = (0 + 15 + 6 + 0) / 0.50 = 42 → WARN
        self.assertEqual(result.verdict, "WARN")
        self.assertGreaterEqual(result.total_score, 40)
        self.assertLess(result.total_score, 60)

    def test_verdict_fail(self):
        """Score <40 → FAIL."""
        result = self.sentinel.validate_offline("bad_address")
        # Solo identity=0 → total=0
        self.assertEqual(result.verdict, "FAIL")
        self.assertLess(result.total_score, 40)


class TestHealthCheckMock(unittest.TestCase):
    """Tests para check_health con mock de urllib."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_health_check_mock(self, mock_urlopen):
        """Mock urllib para simular health OK rápido."""
        mock_urlopen.return_value = _MockResponse(b'{"status":"ok"}', 200)
        result = self.sentinel.check_health("http://example.com")
        self.assertEqual(result.score, 100)
        self.assertEqual(result.name, "health")

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_health_check_timeout_mock(self, mock_urlopen):
        """Mock urllib para simular timeout."""
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        result = self.sentinel.check_health("http://example.com")
        self.assertEqual(result.score, 0)
        self.assertIn("unreachable", result.details)


class TestA2ACheckMock(unittest.TestCase):
    """Tests para check_a2a_capability con mock."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_a2a_check_mock(self, mock_urlopen):
        """Mock urllib para simular agent.json disponible."""
        agent_json = json.dumps({"name": "TestAgent", "skills": []}).encode()
        mock_urlopen.return_value = _MockResponse(agent_json, 200)
        result = self.sentinel.check_a2a_capability("http://example.com")
        self.assertEqual(result.score, 100)
        self.assertIn("A2A endpoint found", result.details)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_a2a_check_not_found(self, mock_urlopen):
        """Sin agent.json → 0."""
        mock_urlopen.side_effect = urllib.error.URLError("404")
        result = self.sentinel.check_a2a_capability("http://example.com")
        self.assertEqual(result.score, 0)


class TestX402CheckMock(unittest.TestCase):
    """Tests para x402 con mock."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_x402_check_mock(self, mock_urlopen):
        """Mock para x402 — agent.json con campo x402."""
        body = json.dumps({"name": "Agent", "x402": {"price": 0.05}}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        result = self.sentinel.check_x402_capability("http://example.com")
        self.assertEqual(result.score, 100)
        self.assertIn("x402", result.details)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_x402_check_none(self, mock_urlopen):
        """Sin x402 → 0."""
        body = json.dumps({"name": "Agent"}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        result = self.sentinel.check_x402_capability("http://example.com")
        self.assertEqual(result.score, 0)

    def test_x402_from_metadata_present(self):
        """x402 en metadata dict → 100."""
        meta = {"name": "Agent", "x402": {"endpoint": "/pay"}}
        result = self.sentinel.check_x402_from_metadata(meta)
        self.assertEqual(result.score, 100)

    def test_x402_from_metadata_absent(self):
        """Sin x402 en metadata dict → 0."""
        meta = {"name": "Agent"}
        result = self.sentinel.check_x402_from_metadata(meta)
        self.assertEqual(result.score, 0)


class TestResponseTimeMock(unittest.TestCase):
    """Tests para check_response_time con mock."""

    def setUp(self):
        self.sentinel = SentinelLite(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_response_time_fast(self, mock_urlopen):
        """Respuesta rápida (<200ms simulado) → 100."""
        mock_urlopen.return_value = _MockResponse(b'ok', 200)
        result = self.sentinel.check_response_time("http://example.com")
        # Mock es instantáneo → <200ms → 100
        self.assertIn(result.score, [100, 80, 60])  # depende del sistema
        self.assertEqual(result.name, "response_time")

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_response_time_fail(self, mock_urlopen):
        """Fallo → 0."""
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        result = self.sentinel.check_response_time("http://example.com")
        self.assertEqual(result.score, 0)


class TestResultStorage(unittest.TestCase):
    """Tests para persistencia en JSONL."""

    def test_result_storage(self):
        """Verifica que se guarda en JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "sentinel", "validations.jsonl")
            sentinel = SentinelLite(log_path=log_path)
            result = sentinel.validate_offline(
                "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
            )
            # Verificar archivo existe
            self.assertTrue(os.path.exists(log_path))
            # Leer y parsear
            with open(log_path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["agent_address"], "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
            self.assertIn("verdict", data)
            self.assertIn("timestamp", data)


class TestDeterminism(unittest.TestCase):
    """Test de determinismo — mismo input → mismo score."""

    def test_score_deterministic(self):
        """Mismo input → mismo score, dos ejecuciones."""
        sentinel = SentinelLite(log_path=os.devnull)
        meta = {
            "name": "Agent",
            "description": "Test",
            "version": "1.0",
            "tools": ["a", "b", "c"],
        }
        addr = "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        r1 = sentinel.validate_offline(addr, metadata=meta)
        r2 = sentinel.validate_offline(addr, metadata=meta)
        self.assertEqual(r1.total_score, r2.total_score)
        self.assertEqual(r1.verdict, r2.verdict)
        self.assertEqual(r1.checks_run, r2.checks_run)
        self.assertEqual(r1.checks_passed, r2.checks_passed)


class TestMetadataFetchMock(unittest.TestCase):
    """Test para check_metadata con HTTP mock."""

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_metadata_fetch_complete(self, mock_urlopen):
        """Metadata URL con campos completos → 100."""
        body = json.dumps({
            "name": "Apex", "description": "Arbitrage Agent", "version": "2.0"
        }).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        sentinel = SentinelLite(log_path=os.devnull)
        result = sentinel.check_metadata("http://example.com/agent.json")
        self.assertEqual(result.score, 100)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_metadata_fetch_fail(self, mock_urlopen):
        """Metadata URL falla → 0."""
        mock_urlopen.side_effect = urllib.error.URLError("not found")
        sentinel = SentinelLite(log_path=os.devnull)
        result = sentinel.check_metadata("http://example.com/agent.json")
        self.assertEqual(result.score, 0)


class TestFullValidateMock(unittest.TestCase):
    """Test para validate() completo con mocks."""

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_validate_full_mock(self, mock_urlopen):
        """Validate con todos los endpoints disponibles."""
        # Mock responde OK para todo
        body = json.dumps({
            "name": "Agent", "x402": True, "skills": ["a"]
        }).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)

        sentinel = SentinelLite(log_path=os.devnull)
        result = sentinel.validate(
            agent_address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            endpoint_url="http://example.com",
            metadata_url="http://example.com/agent.json",
        )
        self.assertIsInstance(result, SentinelResult)
        self.assertGreater(result.checks_run, 3)
        self.assertIn("identity", result.checks)
        self.assertIn("health", result.checks)


if __name__ == "__main__":
    unittest.main()
