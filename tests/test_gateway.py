"""
Tests para DOF-MCP Gateway (core/gateway/).

Cubre: health endpoint, autenticación, rate limiter, tool dispatch.
Usa fastapi.testclient.TestClient (sin necesidad de servidor real).
"""

import os
import sys
import unittest

# Asegurar que el proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar modo dev antes de importar el gateway
os.environ.pop("DOF_GATEWAY_KEYS", None)  # modo dev: acepta sk-dof-*

from fastapi.testclient import TestClient
from core.gateway.server import app
from core.gateway.auth import APIKeyAuth
from core.gateway.router import ToolRouter, TOOL_MAP
from core.gateway.server import _rate_limiter

VALID_KEY = "sk-dof-test-key-001"
INVALID_KEY = "invalid-key-xyz"


class TestGatewayHealth(unittest.TestCase):
    """Test 1: GET /health retorna 200 sin autenticación."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint_no_auth(self):
        """GET /health debe retornar 200 sin necesidad de x-api-key."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "0.8.0")
        self.assertEqual(data["tools"], 15)
        self.assertIn("uptime_ms", data)


class TestGatewayAuth(unittest.TestCase):
    """Tests 2-4: Validación de API keys."""

    def setUp(self):
        self.client = TestClient(app)

    def test_auth_valid_key(self):
        """POST con key válida (sk-dof-*) debe retornar 200."""
        # Usamos dof_get_metrics que es liviana (no requiere parámetros complejos)
        response = self.client.post(
            "/mcp/tools/dof_get_metrics",
            json={},
            headers={"x-api-key": VALID_KEY},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # No debe ser un error de auth
        self.assertNotEqual(data.get("error"), "invalid_api_key")

    def test_auth_invalid_key(self):
        """POST con key inválida debe retornar 401."""
        response = self.client.post(
            "/mcp/tools/dof_get_metrics",
            json={},
            headers={"x-api-key": INVALID_KEY},
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_missing_key(self):
        """POST sin header x-api-key debe retornar 401 o 403."""
        response = self.client.post(
            "/mcp/tools/dof_get_metrics",
            json={},
        )
        self.assertIn(response.status_code, [401, 403])


class TestGatewayToolDispatch(unittest.TestCase):
    """Tests 5-6: Despacho de tools."""

    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"x-api-key": VALID_KEY}

    def test_tool_verify_governance_call(self):
        """dof_verify_governance con texto válido debe retornar resultado de governance."""
        payload = {
            "output_text": (
                "The DOF framework provides deterministic governance for AI agents. "
                "See https://dofmesh.com for more information."
            )
        }
        response = self.client.post(
            "/mcp/tools/dof_verify_governance",
            json=payload,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Debe retornar status pass/fail y score
        self.assertIn("status", data)
        self.assertIn(data["status"], ["pass", "fail"])
        self.assertIn("score", data)

    def test_tool_not_found(self):
        """Tool inexistente debe retornar error JSON, no excepción (sin 500)."""
        response = self.client.post(
            "/mcp/tools/tool_que_no_existe",
            json={},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], "tool_not_found")
        self.assertIn("available", data)
        self.assertIsInstance(data["available"], list)
        self.assertEqual(len(data["available"]), 15)


class TestRateLimiter(unittest.TestCase):
    """Test 7: El rate limiter existe y tiene método check()."""

    def test_rate_limit_structure(self):
        """RateLimiter debe existir y tener método check() funcional."""
        from core.gateway.server import RateLimiter
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # check() debe existir
        self.assertTrue(hasattr(limiter, "check"))

        # Primeras 5 requests deben pasar
        for i in range(5):
            result = limiter.check("sk-dof-test-rate")
            self.assertTrue(result, f"Request {i+1} debería pasar")

        # La 6ta debe fallar
        result = limiter.check("sk-dof-test-rate")
        self.assertFalse(result, "Request 6 debería fallar (rate limit)")

        # Keys diferentes son independientes
        result_other = limiter.check("sk-dof-other-key")
        self.assertTrue(result_other, "Key diferente no debe verse afectada")


class TestToolRouter(unittest.TestCase):
    """Test 8: ToolRouter.dispatch() devuelve dict con resultado."""

    def test_tool_router_dispatch(self):
        """ToolRouter.dispatch() debe retornar un dict válido."""
        import asyncio
        router = ToolRouter()

        # Verificar que tiene los 15 tools
        self.assertEqual(len(router.available_tools()), 15)

        # dispatch() debe retornar dict
        result = asyncio.run(router.dispatch("dof_get_metrics", {}))
        self.assertIsInstance(result, dict)
        # dof_get_metrics sin parámetros retorna métricas por defecto
        # No debe ser un error de tool_not_found
        self.assertNotEqual(result.get("error"), "tool_not_found")

    def test_tool_map_has_all_15_tools(self):
        """TOOL_MAP debe tener exactamente 15 tools."""
        expected_tools = [
            "dof_verify_governance", "dof_verify_ast", "dof_run_z3",
            "dof_memory_add", "dof_memory_query", "dof_memory_snapshot",
            "dof_get_metrics", "dof_create_attestation",
            "dof_oags_identity", "dof_conformance_check",
            "mesh_send_task", "mesh_broadcast", "mesh_route_smart",
            "mesh_read_inbox", "mesh_consensus",
        ]
        self.assertEqual(len(TOOL_MAP), 15)
        for tool in expected_tools:
            self.assertIn(tool, TOOL_MAP, f"Tool faltante: {tool}")

    def test_auth_class_dev_mode(self):
        """APIKeyAuth en modo dev debe aceptar sk-dof-* y rechazar otros."""
        # Modo dev (sin DOF_GATEWAY_KEYS)
        os.environ.pop("DOF_GATEWAY_KEYS", None)
        auth = APIKeyAuth()
        self.assertTrue(auth.validate("sk-dof-cualquier-cosa"))
        self.assertFalse(auth.validate("invalid-key"))
        self.assertFalse(auth.validate(""))
        self.assertFalse(auth.validate("bearer abc"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
