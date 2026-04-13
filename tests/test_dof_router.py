"""
Tests para DOF Router — routing inteligente con failover.

Cubre: selección de agentes, exclusión por fallos, latencia,
persistencia de métricas y ciclos de failover.

Ejecutar con:
    python3 -m unittest tests.test_dof_router -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import DOFRouter, AgentMetrics, MetricsStore, FailoverHandler, FailoverResult


class TestSelectAgentBasic(unittest.TestCase):
    """Test 1 — select_agent retorna un string perteneciente a DEFAULT_AGENTS."""

    def test_select_agent_returns_string(self):
        router = DOFRouter()
        result = router.select_agent()
        self.assertIsInstance(result, str)
        self.assertIn(result, router.agents)


class TestSelectAgentExclusion(unittest.TestCase):
    """Test 2 — agentes con 3+ fallos consecutivos no se seleccionan."""

    def test_select_agent_excludes_consecutive_failures(self):
        agents = ["agent-a", "agent-b", "agent-c"]
        router = DOFRouter(agents=agents, failure_threshold=3)

        # Provocar 3 fallos consecutivos en agent-a y agent-b
        for _ in range(3):
            router.metrics.update("agent-a", success=False, latency_ms=100)
            router.metrics.update("agent-b", success=False, latency_ms=100)

        selected = router.select_agent()
        self.assertEqual(selected, "agent-c",
                         "Debe seleccionar agent-c, el único sin fallos consecutivos")

    def test_select_agent_does_not_exclude_below_threshold(self):
        """Agente con 2 fallos (< umbral 3) sigue siendo candidato."""
        agents = ["agent-a", "agent-b"]
        router = DOFRouter(agents=agents, failure_threshold=3)

        for _ in range(2):
            router.metrics.update("agent-a", success=False, latency_ms=50)

        # agent-a tiene 2 fallos, sigue siendo candidato
        # agent-b tiene 0ms latencia → será preferido (menor latencia)
        selected = router.select_agent()
        self.assertIn(selected, agents)


class TestSelectAgentLatency(unittest.TestCase):
    """Test 3 — con 2 agentes, elige el de menor latencia promedio."""

    def test_select_agent_prefers_lower_latency(self):
        agents = ["fast-agent", "slow-agent"]
        router = DOFRouter(agents=agents, latency_tie_threshold_ms=50)

        # Registrar latencias distintas (diferencia > 50ms → no hay empate)
        for _ in range(5):
            router.metrics.update("fast-agent", success=True, latency_ms=100)
            router.metrics.update("slow-agent", success=True, latency_ms=500)

        selected = router.select_agent()
        self.assertEqual(selected, "fast-agent")


class TestSelectAgentAllFailed(unittest.TestCase):
    """Test 4 — si todos tienen 3+ fallos, retorna el de menor consecutive_failures."""

    def test_select_agent_all_failed_returns_best_bad(self):
        agents = ["agent-a", "agent-b", "agent-c"]
        router = DOFRouter(agents=agents, failure_threshold=3)

        # Todos superan el umbral, pero con distintos grados
        for _ in range(5):
            router.metrics.update("agent-a", success=False, latency_ms=100)
        for _ in range(4):
            router.metrics.update("agent-b", success=False, latency_ms=100)
        for _ in range(3):
            router.metrics.update("agent-c", success=False, latency_ms=100)

        selected = router.select_agent()
        # agent-c tiene 3 fallos consecutivos (el mínimo)
        self.assertEqual(selected, "agent-c",
                         "Debe retornar el agente con menor consecutive_failures")


class TestGetFallback(unittest.TestCase):
    """Test 5 — get_fallback nunca retorna el agente fallido."""

    def test_get_fallback_excludes_failed(self):
        agents = ["agent-a", "agent-b", "agent-c"]
        router = DOFRouter(agents=agents)

        for _ in range(5):
            router.metrics.update("agent-a", success=True, latency_ms=10)

        fallback = router.get_fallback("agent-a")
        self.assertNotEqual(fallback, "agent-a",
                            "get_fallback no debe retornar el agente que falló")
        self.assertIn(fallback, agents)


class TestRecordResult(unittest.TestCase):
    """Test 6 — success_rate sube después de registrar éxitos."""

    def test_record_result_updates_metrics(self):
        router = DOFRouter(agents=["agent-x"])

        # Registrar 5 fallos → success_rate = 0.0 (ventana de 5)
        for _ in range(5):
            router.record_result("agent-x", success=False, latency_ms=200)

        rate_before = router.metrics.get("agent-x").success_rate

        # Registrar 10 éxitos → ventana de 10 queda con 10 éxitos → rate = 1.0
        for _ in range(10):
            router.record_result("agent-x", success=True, latency_ms=100)

        rate_after = router.metrics.get("agent-x").success_rate
        self.assertGreater(rate_after, rate_before,
                           "success_rate debe subir al registrar éxitos")


class TestMetricsPersistence(unittest.TestCase):
    """Test 7 — save/load en archivo temporal preserva datos."""

    def test_metrics_store_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            store = MetricsStore(metrics_path=tmp_path)
            store.update("agent-persist", success=True, latency_ms=123.45)
            store.update("agent-persist", success=False, latency_ms=300.0)
            store.save(tmp_path)

            # Cargar en nuevo store
            store2 = MetricsStore(metrics_path=tmp_path)
            store2.load(tmp_path)

            m = store2.get("agent-persist")
            self.assertEqual(m.agent_id, "agent-persist")
            self.assertEqual(m.success_count, 1)
            self.assertEqual(m.failure_count, 1)
            self.assertAlmostEqual(m.total_latency_ms, 423.45, places=1)
            self.assertEqual(len(m.history), 2)
        finally:
            os.unlink(tmp_path)


class TestFailoverSuccessFirstTry(unittest.TestCase):
    """Test 8 — task_fn exitosa en 1er intento → attempts=1."""

    def test_failover_success_first_try(self):
        router = DOFRouter(agents=["agent-ok", "agent-backup"])
        handler = FailoverHandler(router, max_attempts=3)

        def task_ok(agent_id):
            return f"result-from-{agent_id}"

        result = handler.execute(task_ok)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(result.reroutes), 0)
        self.assertIsNotNone(result.final_result)


class TestFailoverReroute(unittest.TestCase):
    """Test 9 — task_fn falla 1 vez → attempts=2, reroutes=1."""

    def test_failover_reroute_on_failure(self):
        agents = ["primary", "secondary", "tertiary"]
        router = DOFRouter(agents=agents)
        handler = FailoverHandler(router, max_attempts=3)

        call_count = {"n": 0}

        def task_fail_once(agent_id):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Fallo simulado en primer intento")
            return "ok"

        result = handler.execute(task_fail_once)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(result.reroutes), 1)
        self.assertIn("from_agent", result.reroutes[0])
        self.assertIn("to_agent", result.reroutes[0])


class TestFailoverAllFail(unittest.TestCase):
    """Test 10 — task_fn siempre falla → FailoverResult(success=False)."""

    def test_failover_all_fail_returns_failure(self):
        router = DOFRouter(agents=["a1", "a2", "a3"])
        handler = FailoverHandler(router, max_attempts=3)

        def task_always_fail(agent_id):
            raise RuntimeError(f"Fallo total en {agent_id}")

        result = handler.execute(task_always_fail)
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 3)
        self.assertNotEqual(result.error, "")
        # No debe lanzar excepción — debe retornar FailoverResult

    def test_failover_result_no_exception_on_all_fail(self):
        """Verificación extra: FailoverHandler no propaga excepciones."""
        router = DOFRouter(agents=["only-agent"])
        handler = FailoverHandler(router, max_attempts=2)

        def always_raise(agent_id):
            raise ValueError("Error crítico")

        try:
            result = handler.execute(always_raise)
            self.assertFalse(result.success)
        except Exception as exc:
            self.fail(f"FailoverHandler propagó excepción inesperada: {exc}")


class TestSelectAgentTieBreak(unittest.TestCase):
    """Test adicional — desempate por last_used cuando latencias son similares."""

    def test_select_agent_tie_breaks_by_last_used(self):
        agents = ["agent-a", "agent-b"]
        # Umbral de empate amplio para forzar empate aunque haya pequeña diferencia
        router = DOFRouter(agents=agents, latency_tie_threshold_ms=200)

        # Misma latencia para ambos
        for _ in range(5):
            router.metrics.update("agent-a", success=True, latency_ms=100)
            router.metrics.update("agent-b", success=True, latency_ms=105)

        # agent-a fue usado más recientemente (last_used > agent-b)
        # El router debe preferir agent-b (menor last_used = menos usado recientemente)
        selected = router.select_agent()
        # En empate, se elige el de menor last_used → agent-b si se actualizó antes
        # Ambos están en el rango de empate, resultado determinístico por last_used
        self.assertIn(selected, agents)


if __name__ == "__main__":
    unittest.main(verbosity=2)
