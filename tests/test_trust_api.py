"""
test_trust_api.py — Tests para Trust Score API pública.

Testea funciones handler directamente sin levantar servidor.
Usa unittest (NO pytest).

Cyber Paisa / Enigma Group — DOF Mesh Legion
"""

import io
import json
import sys
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from interfaces.trust_api import (
    RateLimiter,
    TrustAPIHandler,
    TrustAPIServer,
    TrustResult,
    compute_trust_score,
    generate_governance_proof,
    verify_governance_proof,
    _proof_store,
)


class MockRequest:
    """Simula un socket para BaseHTTPRequestHandler."""

    def __init__(self, method: str, path: str, body: str = "", headers: dict = None):
        self.method = method
        self.path = path
        self.body = body
        self.headers = headers or {}

    def makefile(self, mode, buffering=-1):
        if "r" in mode:
            body_bytes = self.body.encode() if self.body else b""
            content_length = len(body_bytes)
            header_lines = [f"{self.method} {self.path} HTTP/1.1"]
            all_headers = {"Host": "localhost", "Content-Length": str(content_length)}
            all_headers.update(self.headers)
            for k, v in all_headers.items():
                header_lines.append(f"{k}: {v}")
            header_lines.append("")
            header_lines.append("")
            raw = "\r\n".join(header_lines).encode() + body_bytes
            return io.BytesIO(raw)
        else:
            return io.BytesIO()


def _make_handler(method: str, path: str, body: str = "", headers: dict = None, server_instance=None):
    """Crea un TrustAPIHandler mockeado sin socket real."""
    mock_request = MockRequest(method, path, body, headers)

    handler = TrustAPIHandler.__new__(TrustAPIHandler)
    handler.server_instance = server_instance
    handler.client_address = ("127.0.0.1", 12345)
    handler.request = mock_request
    handler.rfile = mock_request.makefile("rb")
    handler.wfile = io.BytesIO()
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.command = method
    handler.path = path

    # Parse headers
    import http.client
    handler.headers = http.client.HTTPMessage()
    if body:
        handler.headers["Content-Length"] = str(len(body.encode()))
    if headers:
        for k, v in headers.items():
            handler.headers[k] = v

    # Capture responses
    handler._response_code = None
    handler._response_headers = {}
    handler._response_body = b""
    handler._headers_sent = False

    original_send_response = handler.send_response.__func__ if hasattr(handler.send_response, '__func__') else None

    def mock_send_response(code, message=None):
        handler._response_code = code

    def mock_send_header(key, value):
        handler._response_headers[key] = value

    def mock_end_headers():
        handler._headers_sent = True

    handler.send_response = mock_send_response
    handler.send_header = mock_send_header
    handler.end_headers = mock_end_headers

    return handler


def _get_response_json(handler) -> dict:
    """Extrae el JSON de la respuesta del handler."""
    body = handler.wfile.getvalue()
    if body:
        return json.loads(body.decode())
    return {}


# ═══════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════


class TestHealthEndpoint(unittest.TestCase):
    """Test GET /health."""

    def test_health_endpoint(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", "/health", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 200)
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["status"], "ok")
        self.assertEqual(resp["data"]["service"], "DOF-MESH Trust Score API")
        self.assertIn("timestamp", resp)


class TestTrustScoreValidAgent(unittest.TestCase):
    """Test GET /api/v1/trust-score/<valid_agent_id>."""

    def test_trust_score_valid_agent(self):
        agent_id = "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        result = compute_trust_score(agent_id)

        self.assertTrue(result.valid_format)
        self.assertGreaterEqual(result.score, 50.0)
        self.assertLessEqual(result.score, 100.0)
        self.assertIn(result.classification, ["excellent", "good", "acceptable", "poor"])
        self.assertIsNotNone(result.breakdown)
        self.assertEqual(result.agent_id, agent_id)

    def test_trust_score_deterministic(self):
        """El mismo agent_id siempre produce el mismo score."""
        agent_id = "0x29a45b03F07D1207f2e3ca34c38e7BE5458CE71a"
        r1 = compute_trust_score(agent_id)
        r2 = compute_trust_score(agent_id)
        self.assertEqual(r1.score, r2.score)
        self.assertEqual(r1.classification, r2.classification)
        self.assertEqual(r1.breakdown.engagement, r2.breakdown.engagement)

    def test_trust_score_via_handler(self):
        """Test completo via handler HTTP."""
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        agent_id = "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        handler = _make_handler("GET", f"/api/v1/trust-score/{agent_id}", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 200)
        self.assertTrue(resp["success"])
        self.assertIn("score", resp["data"])
        self.assertIn("classification", resp["data"])
        self.assertIn("breakdown", resp["data"])
        self.assertIn(agent_id, srv._agents_scored)


class TestTrustScoreInvalidAgent(unittest.TestCase):
    """Test trust score con agent_id inválido."""

    def test_trust_score_invalid_agent(self):
        result = compute_trust_score("not-a-valid-address")
        self.assertFalse(result.valid_format)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.classification, "invalid")

    def test_trust_score_short_address(self):
        result = compute_trust_score("0x1234")
        self.assertFalse(result.valid_format)
        self.assertEqual(result.score, 0.0)

    def test_trust_score_empty(self):
        result = compute_trust_score("")
        self.assertFalse(result.valid_format)

    def test_invalid_via_handler(self):
        """Handler devuelve 400 para agente inválido."""
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", "/api/v1/trust-score/invalid-id", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 400)
        self.assertFalse(resp["success"])


class TestStatsEndpoint(unittest.TestCase):
    """Test GET /api/v1/stats."""

    def test_stats_endpoint(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time() - 120  # 2 minutos de uptime simulado
        srv._total_queries = 42
        srv._agents_scored = {"0xaaa", "0xbbb"}
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", "/api/v1/stats", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 200)
        self.assertTrue(resp["success"])
        # do_GET incrementa total_queries en 1, así que 42+1=43
        self.assertEqual(resp["data"]["total_queries"], 43)
        self.assertEqual(resp["data"]["agents_scored"], 2)
        self.assertGreaterEqual(resp["data"]["uptime_seconds"], 119)


class TestGovernanceVerify(unittest.TestCase):
    """Test governance proof verification."""

    def setUp(self):
        _proof_store.clear()

    def test_governance_verify_existing(self):
        proof = generate_governance_proof("0x" + "a" * 40, "test output data")
        found = verify_governance_proof(proof.proof_hash)
        self.assertIsNotNone(found)
        self.assertEqual(found.agent_id, "0x" + "a" * 40)
        self.assertTrue(found.verified)

    def test_governance_verify_not_found(self):
        result = verify_governance_proof("nonexistent_hash_12345")
        self.assertIsNone(result)

    def test_governance_verify_via_handler(self):
        """Test verificación via handler HTTP."""
        proof = generate_governance_proof("0x" + "b" * 40, "output data")

        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", f"/api/v1/governance/verify/{proof.proof_hash}", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 200)
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["proof_hash"], proof.proof_hash)


class TestGovernanceAttest(unittest.TestCase):
    """Test POST /api/v1/governance/attest."""

    def setUp(self):
        _proof_store.clear()

    def test_attest_valid(self):
        proof = generate_governance_proof("0x" + "c" * 40, "governance output")
        self.assertIsNotNone(proof.proof_hash)
        self.assertTrue(len(proof.proof_hash) == 64)
        self.assertTrue(proof.verified)

    def test_attest_via_handler(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        body = json.dumps({"agent_id": "0x" + "d" * 40, "output": "test governance output"})
        handler = _make_handler("POST", "/api/v1/governance/attest", body=body,
                                headers={"Content-Type": "application/json"},
                                server_instance=srv)
        # Reposicionar rfile con el body
        handler.rfile = io.BytesIO(body.encode())
        handler.do_POST()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 201)
        self.assertTrue(resp["success"])
        self.assertIn("proof_hash", resp["data"])

    def test_attest_missing_fields(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        body = json.dumps({"agent_id": "0x" + "e" * 40})
        handler = _make_handler("POST", "/api/v1/governance/attest", body=body,
                                headers={"Content-Type": "application/json"},
                                server_instance=srv)
        handler.rfile = io.BytesIO(body.encode())
        handler.do_POST()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 400)
        self.assertFalse(resp["success"])


class TestRateLimit(unittest.TestCase):
    """Test rate limiting."""

    def test_rate_limiter_allows_under_limit(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            self.assertTrue(rl.is_allowed("192.168.1.1"))

    def test_rate_limiter_blocks_over_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            self.assertTrue(rl.is_allowed("10.0.0.1"))
        self.assertFalse(rl.is_allowed("10.0.0.1"))

    def test_rate_limiter_different_ips(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(rl.is_allowed("10.0.0.1"))
        self.assertTrue(rl.is_allowed("10.0.0.1"))
        self.assertFalse(rl.is_allowed("10.0.0.1"))
        # Otra IP sigue OK
        self.assertTrue(rl.is_allowed("10.0.0.2"))

    def test_rate_limiter_window_expiry(self):
        rl = RateLimiter(max_requests=2, window_seconds=1)
        self.assertTrue(rl.is_allowed("10.0.0.1"))
        self.assertTrue(rl.is_allowed("10.0.0.1"))
        self.assertFalse(rl.is_allowed("10.0.0.1"))
        # Simular que pasó la ventana
        rl._requests["10.0.0.1"] = [time.time() - 2]
        self.assertTrue(rl.is_allowed("10.0.0.1"))

    def test_rate_limit_handler_returns_429(self):
        """Handler devuelve 429 cuando se excede el límite."""
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Primera request OK
        h1 = _make_handler("GET", "/health", server_instance=srv)
        h1.do_GET()
        self.assertEqual(h1._response_code, 200)

        # Segunda request bloqueada
        h2 = _make_handler("GET", "/health", server_instance=srv)
        h2.do_GET()
        self.assertEqual(h2._response_code, 429)


class TestCORSHeaders(unittest.TestCase):
    """Test CORS headers en las respuestas."""

    def test_cors_headers(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", "/health", server_instance=srv)
        handler.do_GET()

        self.assertEqual(handler._response_headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("GET", handler._response_headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("POST", handler._response_headers.get("Access-Control-Allow-Methods", ""))

    def test_options_preflight(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("OPTIONS", "/api/v1/trust-score/test", server_instance=srv)
        handler.do_OPTIONS()

        self.assertEqual(handler._response_code, 204)
        self.assertEqual(handler._response_headers.get("Access-Control-Allow-Origin"), "*")


class TestNotFound(unittest.TestCase):
    """Test rutas no existentes."""

    def test_404_route(self):
        srv = TrustAPIServer.__new__(TrustAPIServer)
        srv._start_time = time.time()
        srv._total_queries = 0
        srv._agents_scored = set()
        srv._rate_limiter = RateLimiter()

        handler = _make_handler("GET", "/nonexistent/path", server_instance=srv)
        handler.do_GET()

        resp = _get_response_json(handler)
        self.assertEqual(handler._response_code, 404)
        self.assertFalse(resp["success"])


class TestScoreClassifications(unittest.TestCase):
    """Test que diferentes agentes producen diferentes clasificaciones."""

    def test_multiple_agents_varied_scores(self):
        """Múltiples agentes producen scores variados (cobertura de clasificación)."""
        agents = [f"0x{i:040x}" for i in range(100)]
        classifications = set()
        for agent_id in agents:
            result = compute_trust_score(agent_id)
            self.assertTrue(result.valid_format)
            classifications.add(result.classification)
        # Con 100 agentes deberíamos tener al menos 2 clasificaciones distintas
        self.assertGreaterEqual(len(classifications), 2)

    def test_breakdown_sums_reasonable(self):
        """Los componentes del breakdown son coherentes."""
        agent_id = "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983"
        result = compute_trust_score(agent_id)
        b = result.breakdown
        total_breakdown = b.engagement + b.service + b.publisher + b.compliance + b.momentum
        # Score = 50 (base) + breakdown total
        expected = min(100.0, round(50.0 + total_breakdown, 1))
        self.assertAlmostEqual(result.score, expected, places=1)


if __name__ == "__main__":
    unittest.main()
