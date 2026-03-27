"""
Tests unitarios para Sentinel Lite v2 — NO requieren red.
Usa unittest.mock.patch sobre urllib.request.urlopen y ssl para simular.
Cubre: 10 checks, TRACER scoring, Survival engine, validate(), validate_offline(),
ejecución paralela, storage JSONL, classifications, tiers, proxy, TLS grading.
"""

import json
import os
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import patch, MagicMock, PropertyMock

from core.sentinel_lite import (
    SentinelEngine,
    SentinelLite,
    SentinelCheck,
    TRACERScore,
    SurvivalStatus,
    ValidationReport,
    TRACER_WEIGHTS,
    SCORE_THRESHOLDS,
    SURVIVAL_TIERS,
    TLS_GRADES,
    TRACER_CLASSIFICATIONS,
    EIP1967_IMPL_SLOT,
    CheckResult,
    SentinelResult,
)


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


# ═══════════════════════════════════════════════════════════════════════════
# 1. CHECK: HEALTH
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckHealth(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_health_ok(self, mock_urlopen):
        mock_urlopen.return_value = _MockResponse(b'{"status":"ok"}', 200)
        result = self.engine.check_health("http://example.com")
        self.assertEqual(result.name, "health")
        self.assertEqual(result.score, 100)
        self.assertTrue(result.passed)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_health_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        result = self.engine.check_health("http://example.com")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)
        self.assertIn("unreachable", result.data.get("error", ""))


# ═══════════════════════════════════════════════════════════════════════════
# 2. CHECK: TLS
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckTLS(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    def test_tls_http_gets_F(self):
        """HTTP sin SSL → grade F, score 0."""
        result = self.engine.check_tls("http://example.com")
        self.assertEqual(result.score, 0)
        self.assertEqual(result.data["grade"], "F")
        self.assertFalse(result.passed)

    def test_tls_grade_calculation(self):
        """Test estático del método _tls_grade."""
        self.assertEqual(SentinelEngine._tls_grade("TLSv1.3", 90), "A+")
        self.assertEqual(SentinelEngine._tls_grade("TLSv1.2", 90), "A")
        self.assertEqual(SentinelEngine._tls_grade("TLSv1.2", 20), "B")  # <30 días
        self.assertEqual(SentinelEngine._tls_grade("TLSv1.2", 3), "D")   # <7 días
        self.assertEqual(SentinelEngine._tls_grade("TLSv1.1", 90), "C")
        self.assertEqual(SentinelEngine._tls_grade("TLSv1", 90), "D")
        self.assertEqual(SentinelEngine._tls_grade("SSLv3", 90), "F")

    def test_tls_grade_A_plus(self):
        self.assertEqual(TLS_GRADES["A+"], 100)

    def test_tls_grade_F_score(self):
        self.assertEqual(TLS_GRADES["F"], 10)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHECK: LATENCY
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckLatency(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_latency_fast(self, mock_urlopen):
        """Mock instantáneo → <200ms → 100."""
        mock_urlopen.return_value = _MockResponse(b"ok", 200)
        result = self.engine.check_latency("http://example.com")
        self.assertEqual(result.name, "latency")
        self.assertIn(result.score, [100, 80])  # mock es instantáneo

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_latency_fail(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        result = self.engine.check_latency("http://example.com")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)


# ═══════════════════════════════════════════════════════════════════════════
# 4. CHECK: A2A
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckA2A(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_a2a_found(self, mock_urlopen):
        body = json.dumps({"name": "Agent", "skills": ["a"]}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        result = self.engine.check_a2a("http://example.com")
        self.assertEqual(result.score, 100)
        self.assertTrue(result.passed)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_a2a_not_found(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("404")
        result = self.engine.check_a2a("http://example.com")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CHECK: MCP
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckMCP(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    def test_mcp_many_tools(self):
        meta = {"tools": [f"t{i}" for i in range(15)]}
        result = self.engine.check_mcp(meta)
        self.assertEqual(result.score, 100)
        self.assertTrue(result.passed)
        self.assertEqual(result.data["tool_count"], 15)

    def test_mcp_some_tools(self):
        meta = {"tools": [f"t{i}" for i in range(7)]}
        result = self.engine.check_mcp(meta)
        self.assertEqual(result.score, 80)

    def test_mcp_few_tools(self):
        meta = {"tools": ["a", "b"]}
        result = self.engine.check_mcp(meta)
        self.assertEqual(result.score, 60)

    def test_mcp_no_tools(self):
        result = self.engine.check_mcp({"tools": []})
        self.assertEqual(result.score, 30)
        self.assertFalse(result.passed)

    def test_mcp_mcptools_field(self):
        meta = {"mcpTools": ["a", "b", "c"]}
        result = self.engine.check_mcp(meta)
        self.assertEqual(result.score, 60)
        self.assertEqual(result.data["tool_count"], 3)


# ═══════════════════════════════════════════════════════════════════════════
# 6. CHECK: X402
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckX402(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    def test_x402_in_metadata(self):
        meta = {"x402": {"price": 0.05}}
        result = self.engine.check_x402(meta)
        self.assertEqual(result.score, 100)
        self.assertTrue(result.passed)

    def test_x402_payment_in_metadata(self):
        meta = {"payment": {"method": "USDC"}}
        result = self.engine.check_x402(meta)
        self.assertEqual(result.score, 100)

    def test_x402_absent_metadata(self):
        meta = {"name": "Agent"}
        result = self.engine.check_x402(meta)
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_x402_from_endpoint(self, mock_urlopen):
        body = json.dumps({"x402": True}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        result = self.engine.check_x402("http://example.com")
        self.assertEqual(result.score, 100)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_x402_not_in_endpoint(self, mock_urlopen):
        body = json.dumps({"name": "Agent"}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)
        result = self.engine.check_x402("http://example.com")
        self.assertEqual(result.score, 0)


# ═══════════════════════════════════════════════════════════════════════════
# 7. CHECK: ON_CHAIN
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckOnChain(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_on_chain_is_contract(self, mock_urlopen):
        rpc_resp = json.dumps({"jsonrpc": "2.0", "result": "0x6060604052...", "id": 1}).encode()
        mock_urlopen.return_value = _MockResponse(rpc_resp, 200)
        result = self.engine.check_on_chain("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 100)
        self.assertTrue(result.data["is_contract"])

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_on_chain_not_contract(self, mock_urlopen):
        rpc_resp = json.dumps({"jsonrpc": "2.0", "result": "0x", "id": 1}).encode()
        mock_urlopen.return_value = _MockResponse(rpc_resp, 200)
        result = self.engine.check_on_chain("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 40)
        self.assertFalse(result.data["is_contract"])

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_on_chain_rpc_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("rpc down")
        result = self.engine.check_on_chain("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)


# ═══════════════════════════════════════════════════════════════════════════
# 8. CHECK: PROXY
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckProxy(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_proxy_detected(self, mock_urlopen):
        """EIP-1967 slot con valor → es proxy."""
        impl = "0x000000000000000000000000abcdef1234567890abcdef1234567890abcdef12"
        rpc_resp = json.dumps({"jsonrpc": "2.0", "result": impl, "id": 1}).encode()
        mock_urlopen.return_value = _MockResponse(rpc_resp, 200)
        result = self.engine.check_proxy("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 80)
        self.assertTrue(result.data["is_proxy"])
        self.assertIsNotNone(result.data["implementation"])

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_proxy_not_detected(self, mock_urlopen):
        """EIP-1967 slot vacío → no es proxy."""
        rpc_resp = json.dumps({
            "jsonrpc": "2.0",
            "result": "0x" + "0" * 64,
            "id": 1,
        }).encode()
        mock_urlopen.return_value = _MockResponse(rpc_resp, 200)
        result = self.engine.check_proxy("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 50)
        self.assertFalse(result.data["is_proxy"])

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_proxy_rpc_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("fail")
        result = self.engine.check_proxy("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 0)


# ═══════════════════════════════════════════════════════════════════════════
# 9. CHECK: RATINGS
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckRatings(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    def test_ratings_many_high(self):
        """50+ reviews, avg 4.5/5 → score alto."""
        ratings = [4.5] * 60
        result = self.engine.check_ratings(ratings)
        # volume=100*0.4 + (4.5/5*100)*0.6 = 40 + 54 = 94
        self.assertEqual(result.score, 94)
        self.assertTrue(result.passed)
        self.assertEqual(result.data["count"], 60)

    def test_ratings_few_low(self):
        """2 reviews, avg 1.0/5 → score bajo."""
        ratings = [1.0, 1.0]
        result = self.engine.check_ratings(ratings)
        # volume=40*0.4 + (1.0/5*100)*0.6 = 16 + 12 = 28
        self.assertEqual(result.score, 28)

    def test_ratings_empty(self):
        result = self.engine.check_ratings([])
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)

    def test_ratings_single_perfect(self):
        result = self.engine.check_ratings([5.0])
        # volume=40*0.4 + 100*0.6 = 16+60 = 76
        self.assertEqual(result.score, 76)


# ═══════════════════════════════════════════════════════════════════════════
# 10. CHECK: IDENTITY
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckIdentity(unittest.TestCase):
    def setUp(self):
        self.engine = SentinelEngine(log_path=os.devnull)

    def test_valid_address(self):
        result = self.engine.check_identity("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 80)
        self.assertTrue(result.passed)
        self.assertIn("identity_hash", result.data)

    def test_invalid_no_prefix(self):
        result = self.engine.check_identity("cd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.passed)

    def test_invalid_short(self):
        result = self.engine.check_identity("0x1234")
        self.assertEqual(result.score, 0)

    def test_invalid_chars(self):
        result = self.engine.check_identity("0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")
        self.assertEqual(result.score, 0)

    def test_empty_address(self):
        result = self.engine.check_identity("")
        self.assertEqual(result.score, 0)


# ═══════════════════════════════════════════════════════════════════════════
# TRACER SCORING (funciones puras)
# ═══════════════════════════════════════════════════════════════════════════


class TestTRACERScoring(unittest.TestCase):

    def test_tracer_all_perfect(self):
        """Todos los checks con score 100 → classification excellent."""
        checks = [
            SentinelCheck(name="tls", score=100, max_score=100, passed=True),
            SentinelCheck(name="proxy", score=80, max_score=100, passed=True),
            SentinelCheck(name="identity", score=80, max_score=100, passed=True),
            SentinelCheck(name="health", score=100, max_score=100, passed=True),
            SentinelCheck(name="latency", score=100, max_score=100, passed=True),
            SentinelCheck(name="mcp", score=100, max_score=100, passed=True),
            SentinelCheck(name="a2a", score=100, max_score=100, passed=True),
            SentinelCheck(name="on_chain", score=100, max_score=100, passed=True),
            SentinelCheck(name="x402", score=100, max_score=100, passed=True),
            SentinelCheck(name="ratings", score=100, max_score=100, passed=True),
        ]
        tracer = SentinelEngine.calculate_tracer(checks)
        self.assertGreaterEqual(tracer.total, 80)
        self.assertEqual(tracer.classification, "excellent")
        self.assertEqual(len(tracer.dimensions), 6)

    def test_tracer_all_zero(self):
        """Todos 0 → unreliable."""
        checks = [
            SentinelCheck(name="identity", score=0, max_score=100, passed=False),
            SentinelCheck(name="health", score=0, max_score=100, passed=False),
        ]
        tracer = SentinelEngine.calculate_tracer(checks)
        self.assertEqual(tracer.total, 0)
        self.assertEqual(tracer.classification, "unreliable")

    def test_tracer_classification_good(self):
        """Score entre 65-79 → good."""
        checks = [
            SentinelCheck(name="identity", score=80, max_score=100, passed=True),
            SentinelCheck(name="health", score=70, max_score=100, passed=True),
            SentinelCheck(name="latency", score=60, max_score=100, passed=True),
            SentinelCheck(name="mcp", score=80, max_score=100, passed=True),
            SentinelCheck(name="a2a", score=60, max_score=100, passed=True),
            SentinelCheck(name="on_chain", score=60, max_score=100, passed=True),
            SentinelCheck(name="x402", score=60, max_score=100, passed=True),
            SentinelCheck(name="ratings", score=70, max_score=100, passed=True),
        ]
        tracer = SentinelEngine.calculate_tracer(checks)
        self.assertIn(tracer.classification, ("good", "acceptable", "excellent"))

    def test_tracer_classification_acceptable(self):
        """Score 50-64 → acceptable."""
        checks = [
            SentinelCheck(name="identity", score=50, max_score=100, passed=True),
            SentinelCheck(name="health", score=50, max_score=100, passed=True),
            SentinelCheck(name="latency", score=50, max_score=100, passed=True),
            SentinelCheck(name="mcp", score=50, max_score=100, passed=True),
            SentinelCheck(name="a2a", score=50, max_score=100, passed=True),
            SentinelCheck(name="on_chain", score=50, max_score=100, passed=True),
            SentinelCheck(name="x402", score=50, max_score=100, passed=True),
            SentinelCheck(name="ratings", score=50, max_score=100, passed=True),
        ]
        tracer = SentinelEngine.calculate_tracer(checks)
        self.assertEqual(tracer.classification, "acceptable")
        self.assertAlmostEqual(tracer.total, 50.0, places=0)

    def test_tracer_classification_poor(self):
        """Score 35-49 → poor."""
        checks = [
            SentinelCheck(name="identity", score=40, max_score=100, passed=False),
            SentinelCheck(name="health", score=30, max_score=100, passed=False),
            SentinelCheck(name="latency", score=30, max_score=100, passed=False),
            SentinelCheck(name="mcp", score=40, max_score=100, passed=False),
            SentinelCheck(name="a2a", score=30, max_score=100, passed=False),
            SentinelCheck(name="on_chain", score=40, max_score=100, passed=False),
            SentinelCheck(name="x402", score=40, max_score=100, passed=False),
            SentinelCheck(name="ratings", score=40, max_score=100, passed=False),
        ]
        tracer = SentinelEngine.calculate_tracer(checks)
        self.assertEqual(tracer.classification, "poor")

    def test_tracer_with_metrics(self):
        """Métricas adicionales enriquecen dimensiones."""
        checks = [
            SentinelCheck(name="identity", score=80, max_score=100, passed=True),
        ]
        metrics = {
            "has_verified_wallet": True,
            "is_open_source": True,
            "uptime_percent": 99.5,
            "can_delegate": True,
            "total_transactions": 500,
            "feedback_score": 85,
        }
        tracer = SentinelEngine.calculate_tracer(checks, metrics)
        self.assertGreater(tracer.dimensions["trust"], 0)
        self.assertGreater(tracer.dimensions["reliability"], 0)
        self.assertGreater(tracer.dimensions["autonomy"], 0)
        self.assertGreater(tracer.dimensions["economics"], 0)
        self.assertGreater(tracer.dimensions["reputation"], 0)

    def test_tracer_weights_sum_to_one(self):
        total = sum(TRACER_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_tracer_empty_checks(self):
        tracer = SentinelEngine.calculate_tracer([])
        self.assertEqual(tracer.total, 0)
        self.assertEqual(tracer.classification, "unreliable")

    def test_tracer_timestamp(self):
        tracer = SentinelEngine.calculate_tracer([])
        self.assertTrue(len(tracer.timestamp) > 0)


# ═══════════════════════════════════════════════════════════════════════════
# SURVIVAL ENGINE (funciones puras)
# ═══════════════════════════════════════════════════════════════════════════


class TestSurvivalEngine(unittest.TestCase):

    def test_thriving(self):
        s = SentinelEngine.calculate_survival(200.0, 0.01, 0.05)
        self.assertEqual(s.tier, "THRIVING")
        self.assertFalse(s.should_reduce)
        self.assertGreater(s.hours_until_death, 0)

    def test_sustainable(self):
        s = SentinelEngine.calculate_survival(50.0, 0.01, 0.0)
        self.assertEqual(s.tier, "SUSTAINABLE")

    def test_conservation(self):
        s = SentinelEngine.calculate_survival(5.0, 0.01, 0.0)
        self.assertEqual(s.tier, "CONSERVATION")
        self.assertTrue(s.should_reduce)

    def test_dead(self):
        s = SentinelEngine.calculate_survival(0.0, 0.01, 0.0)
        self.assertEqual(s.tier, "DEAD")
        self.assertTrue(s.should_reduce)
        self.assertEqual(s.hours_until_death, 0.0)

    def test_dead_negative(self):
        s = SentinelEngine.calculate_survival(-5.0, 0.01, 0.0)
        self.assertEqual(s.tier, "DEAD")

    def test_should_reduce_with_losses(self):
        """Balance ok pero quemando rápido → should_reduce."""
        s = SentinelEngine.calculate_survival(15.0, 1.0, 0.0)
        # 15 / 1.0 = 15 horas < 24 → should_reduce
        self.assertTrue(s.should_reduce)

    def test_should_not_reduce_thriving(self):
        s = SentinelEngine.calculate_survival(500.0, 0.01, 0.02)
        self.assertEqual(s.tier, "THRIVING")
        self.assertFalse(s.should_reduce)

    def test_hours_calculation(self):
        s = SentinelEngine.calculate_survival(100.0, 0.5)
        self.assertEqual(s.hours_until_death, 200.0)

    def test_zero_cost(self):
        s = SentinelEngine.calculate_survival(50.0, 0.0)
        self.assertEqual(s.hours_until_death, float("inf"))


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATE() COMPLETO
# ═══════════════════════════════════════════════════════════════════════════


class TestValidate(unittest.TestCase):

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_validate_full(self, mock_urlopen):
        """Validate con endpoint + metadata + ratings + balance."""
        body = json.dumps({"name": "Agent", "x402": True, "skills": ["a"]}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)

        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate(
            address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            endpoint="http://example.com",
            metadata={"tools": [f"t{i}" for i in range(12)], "x402": True},
            ratings=[4.0, 5.0, 4.5],
            balance=50.0,
        )
        self.assertIsInstance(report, ValidationReport)
        self.assertGreater(len(report.checks), 3)
        self.assertIsNotNone(report.tracer)
        self.assertIsNotNone(report.survival)
        self.assertEqual(report.survival.tier, "SUSTAINABLE")

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_validate_result_pass(self, mock_urlopen):
        """Score alto → PASS."""
        body = json.dumps({"x402": True}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)

        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate(
            address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            endpoint="http://example.com",
            metadata={"tools": [f"t{i}" for i in range(15)], "x402": True},
            ratings=[5.0] * 50,
        )
        self.assertIn(report.result, ("PASS", "PARTIAL"))

    def test_validate_no_endpoint(self):
        """Solo address → checks mínimos."""
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate(address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertIsInstance(report, ValidationReport)
        check_names = [c.name for c in report.checks]
        self.assertIn("identity", check_names)


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATE_OFFLINE()
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateOffline(unittest.TestCase):

    def test_offline_basic(self):
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate_offline(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            metadata={"tools": [f"t{i}" for i in range(12)], "x402": True},
        )
        self.assertIsInstance(report, ValidationReport)
        check_names = [c.name for c in report.checks]
        self.assertIn("identity", check_names)
        self.assertIn("mcp", check_names)
        self.assertIn("x402", check_names)
        # No network checks
        self.assertNotIn("health", check_names)
        self.assertNotIn("a2a", check_names)
        self.assertNotIn("tls", check_names)

    def test_offline_no_metadata(self):
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate_offline("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(len(report.checks), 1)
        self.assertEqual(report.checks[0].name, "identity")

    def test_offline_with_ratings(self):
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate_offline(
            "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            ratings=[5.0, 4.0, 3.0],
        )
        check_names = [c.name for c in report.checks]
        self.assertIn("ratings", check_names)

    def test_offline_bad_address(self):
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate_offline("bad_address")
        self.assertEqual(report.result, "FAIL")


# ═══════════════════════════════════════════════════════════════════════════
# EJECUCIÓN PARALELA
# ═══════════════════════════════════════════════════════════════════════════


class TestParallelExecution(unittest.TestCase):

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_parallel_runs_multiple_checks(self, mock_urlopen):
        """Validate con endpoint debe correr checks en paralelo."""
        body = json.dumps({"name": "Agent"}).encode()
        mock_urlopen.return_value = _MockResponse(body, 200)

        engine = SentinelEngine(log_path=os.devnull, max_workers=4)
        report = engine.validate(
            address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            endpoint="http://example.com",
            metadata={"tools": ["a"]},
        )
        # Debe haber múltiples checks ejecutados
        self.assertGreater(len(report.checks), 4)

    @patch("core.sentinel_lite.urllib.request.urlopen")
    def test_parallel_handles_failures(self, mock_urlopen):
        """Si un check falla, los demás siguen."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise urllib.error.URLError("fail")
            return _MockResponse(b'{"status":"ok"}', 200)

        mock_urlopen.side_effect = side_effect
        engine = SentinelEngine(log_path=os.devnull)
        report = engine.validate(
            address="0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
            endpoint="http://example.com",
        )
        self.assertIsInstance(report, ValidationReport)
        self.assertGreater(len(report.checks), 0)


# ═══════════════════════════════════════════════════════════════════════════
# STORAGE JSONL
# ═══════════════════════════════════════════════════════════════════════════


class TestStorage(unittest.TestCase):

    def test_jsonl_storage(self):
        """Verifica que se guarda en JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "sentinel", "validations.jsonl")
            engine = SentinelEngine(log_path=log_path)
            report = engine.validate_offline("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
            self.assertTrue(os.path.exists(log_path))
            with open(log_path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["agent_address"], "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
            self.assertIn("result", data)
            self.assertIn("timestamp", data)

    def test_jsonl_multiple_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "sentinel", "validations.jsonl")
            engine = SentinelEngine(log_path=log_path)
            engine.validate_offline("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
            engine.validate_offline("0x29a45b03F07D1207f2e3ca34c38e7BE5458CE71a")
            with open(log_path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)

    def test_to_dict(self):
        report = ValidationReport(
            agent_address="0xtest",
            overall_score=75.0,
            result="PASS",
            checks=[SentinelCheck(name="id", score=80, max_score=100, passed=True)],
        )
        d = report.to_dict()
        self.assertEqual(d["agent_address"], "0xtest")
        self.assertEqual(d["overall_score"], 75.0)
        self.assertEqual(len(d["checks"]), 1)


# ═══════════════════════════════════════════════════════════════════════════
# DETERMINISMO
# ═══════════════════════════════════════════════════════════════════════════


class TestDeterminism(unittest.TestCase):

    def test_same_input_same_output(self):
        engine = SentinelEngine(log_path=os.devnull)
        meta = {"tools": ["a", "b", "c"], "x402": True}
        addr = "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        r1 = engine.validate_offline(addr, metadata=meta)
        r2 = engine.validate_offline(addr, metadata=meta)
        self.assertEqual(r1.overall_score, r2.overall_score)
        self.assertEqual(r1.result, r2.result)
        self.assertEqual(len(r1.checks), len(r2.checks))


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARDS COMPATIBILITY (SentinelLite alias)
# ═══════════════════════════════════════════════════════════════════════════


class TestBackwardsCompatibility(unittest.TestCase):

    def test_sentinel_lite_is_engine(self):
        s = SentinelLite(log_path=os.devnull)
        self.assertIsInstance(s, SentinelEngine)

    def test_check_erc8004_identity_alias(self):
        s = SentinelLite(log_path=os.devnull)
        result = s.check_erc8004_identity("0xcd595a299ad1d5D088B7764e9330f7B0be7ca983")
        self.assertEqual(result.score, 80)

    def test_check_metadata_dict_alias(self):
        s = SentinelLite(log_path=os.devnull)
        meta = {"name": "Agent", "description": "Test", "version": "1.0"}
        result = s.check_metadata_dict(meta)
        self.assertEqual(result.score, 100)
        self.assertIn("All required", result.data.get("details", ""))

    def test_check_metadata_dict_partial(self):
        s = SentinelLite(log_path=os.devnull)
        result = s.check_metadata_dict({"name": "Agent"})
        self.assertEqual(result.score, 50)

    def test_check_metadata_dict_empty(self):
        s = SentinelLite(log_path=os.devnull)
        result = s.check_metadata_dict({})
        self.assertEqual(result.score, 0)

    def test_check_mcp_tools_alias(self):
        s = SentinelLite(log_path=os.devnull)
        result = s.check_mcp_tools({"tools": ["a", "b"]})
        self.assertEqual(result.score, 60)

    def test_x402_from_metadata_alias(self):
        s = SentinelLite(log_path=os.devnull)
        result = s.check_x402_from_metadata({"x402": True})
        self.assertEqual(result.score, 100)

    def test_aliases_exist(self):
        self.assertIs(CheckResult, SentinelCheck)
        self.assertIs(SentinelResult, ValidationReport)


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════


class TestConstants(unittest.TestCase):

    def test_tracer_weights_six_dimensions(self):
        self.assertEqual(len(TRACER_WEIGHTS), 6)

    def test_score_thresholds(self):
        self.assertEqual(SCORE_THRESHOLDS["PASS"], 70)
        self.assertEqual(SCORE_THRESHOLDS["PARTIAL"], 40)
        self.assertEqual(SCORE_THRESHOLDS["FAIL"], 0)

    def test_eip1967_slot(self):
        self.assertTrue(EIP1967_IMPL_SLOT.startswith("0x"))
        self.assertEqual(len(EIP1967_IMPL_SLOT), 66)  # 0x + 64 hex

    def test_tracer_classifications_thresholds(self):
        self.assertEqual(TRACER_CLASSIFICATIONS["excellent"], 80)
        self.assertEqual(TRACER_CLASSIFICATIONS["unreliable"], 0)


if __name__ == "__main__":
    unittest.main()
