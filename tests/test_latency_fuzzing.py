"""
Latency Fuzzing Tests — Valida determinismo DOF bajo estrés de latencia.

Inyecta delays aleatorios (0-200ms) entre operaciones de governance
y verifica que los resultados son idénticos con y sin delay.
Origen: DeepSeek-V3 RED ADVANCED — "Fuzzing de latencia" para validar
invariantes de Constitution bajo estrés de red.
"""
import sys, os, time, random, unittest
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.z3_gate import Z3Gate, GateResult
from core.adaptive_circuit_breaker import AdaptiveCircuitBreaker, CircuitState


class TestZ3GateDeterminismUnderDelay(unittest.TestCase):
    """Z3Gate produce resultados idénticos con y sin delays."""

    def test_trust_score_deterministic_with_delay(self):
        """Mismos inputs → mismo resultado aunque haya delay entre calls."""
        gate = Z3Gate()
        # Sin delay
        r1 = gate.validate_trust_score("a1", 0.9, {"current_level": 1})
        # Con delay simulado
        time.sleep(random.uniform(0.01, 0.05))
        gate2 = Z3Gate()  # nuevo gate, sin cache
        r2 = gate2.validate_trust_score("a2", 0.9, {"current_level": 1})
        self.assertEqual(r1.result, r2.result)

    def test_promotion_deterministic_with_delay(self):
        gate = Z3Gate()
        r1 = gate.validate_promotion("a1", 1, 2)
        time.sleep(random.uniform(0.01, 0.05))
        gate2 = Z3Gate()
        r2 = gate2.validate_promotion("a2", 1, 2)
        self.assertEqual(r1.result, r2.result)

    def test_batch_trust_scores_consistent(self):
        """10 llamadas con delays aleatorios → todas producen mismo resultado."""
        gate = Z3Gate()
        results = []
        for i in range(10):
            time.sleep(random.uniform(0.001, 0.02))
            r = gate.validate_trust_score(f"agent-{i}", 0.85, {"current_level": 2})
            results.append(r.result)
        # Todas deben ser idénticas (mismo score + level = mismo resultado)
        self.assertTrue(all(r == results[0] for r in results))

    def test_batch_promotions_consistent(self):
        """10 promociones idénticas con delays → mismo resultado."""
        gate = Z3Gate()
        results = []
        for i in range(10):
            time.sleep(random.uniform(0.001, 0.02))
            r = gate.validate_promotion(f"agent-{i}", 1, 2)
            results.append(r.result)
        self.assertTrue(all(r == results[0] for r in results))

    def test_rejected_score_deterministic_with_delay(self):
        """Score inválido → REJECTED con y sin delay."""
        gate = Z3Gate()
        r1 = gate.validate_trust_score("a1", 0.7, {"current_level": 3})
        time.sleep(random.uniform(0.01, 0.05))
        r2 = gate.validate_trust_score("a2", 0.7, {"current_level": 3})
        self.assertEqual(r1.result, GateResult.REJECTED)
        self.assertEqual(r2.result, GateResult.REJECTED)

    def test_invalid_promotion_deterministic_with_delay(self):
        """Salto de nivel inválido → REJECTED con y sin delay."""
        gate = Z3Gate()
        r1 = gate.validate_promotion("a1", 1, 3)
        time.sleep(random.uniform(0.01, 0.05))
        r2 = gate.validate_promotion("a2", 1, 3)
        self.assertEqual(r1.result, GateResult.REJECTED)
        self.assertEqual(r2.result, GateResult.REJECTED)


class TestCircuitBreakerUnderDelay(unittest.TestCase):
    """CircuitBreaker mantiene estado correcto bajo delays."""

    def test_state_consistent_after_delayed_records(self):
        """Records con delays → mismo estado final."""
        cb = AdaptiveCircuitBreaker("agent-fuzz", threshold_rate=0.15)
        for _ in range(8):
            time.sleep(random.uniform(0.001, 0.01))
            cb.record(blocked=False)
        for _ in range(2):
            time.sleep(random.uniform(0.001, 0.01))
            cb.record(blocked=True)
        # 2/10 = 20% > 15% → OPEN
        self.assertEqual(cb.state(), CircuitState.OPEN)

    def test_recovery_with_delays(self):
        """Push to OPEN → recover con clean records + delays → CLOSED."""
        cb = AdaptiveCircuitBreaker("agent-fuzz", threshold_rate=0.15)
        cb.record(blocked=True)
        cb.record(blocked=True)
        self.assertEqual(cb.state(), CircuitState.OPEN)
        for _ in range(50):
            time.sleep(random.uniform(0.001, 0.005))
            cb.record(blocked=False)
        self.assertEqual(cb.state(), CircuitState.CLOSED)

    def test_snapshot_stable_under_delay(self):
        """Snapshot retorna datos consistentes con delays entre records."""
        cb = AdaptiveCircuitBreaker("agent-fuzz")
        for _ in range(5):
            time.sleep(random.uniform(0.001, 0.01))
            cb.record(blocked=False)
        snap = cb.snapshot()
        self.assertEqual(snap.total_events, 5)
        self.assertEqual(snap.blocked_events, 0)
        self.assertEqual(snap.state, CircuitState.CLOSED)


class TestConcurrentGateOperations(unittest.TestCase):
    """Operaciones Z3Gate concurrentes mantienen determinismo."""

    def test_interleaved_trust_and_promotion(self):
        """Alternar trust_score y promotion con delays → resultados correctos."""
        gate = Z3Gate()
        for i in range(5):
            time.sleep(random.uniform(0.001, 0.01))
            rt = gate.validate_trust_score(f"a-{i}", 0.9, {"current_level": 1})
            self.assertEqual(rt.result, GateResult.APPROVED)
            time.sleep(random.uniform(0.001, 0.01))
            rp = gate.validate_promotion(f"a-{i}", 1, 2)
            self.assertEqual(rp.result, GateResult.APPROVED)

    def test_cache_hit_after_delay(self):
        """Cache hit funciona correctamente después de delay."""
        gate = Z3Gate()
        r1 = gate.validate_trust_score("a1", 0.9, {"current_level": 1})
        time.sleep(random.uniform(0.05, 0.1))
        r2 = gate.validate_trust_score("a2", 0.9, {"current_level": 1})
        self.assertEqual(r1.result, r2.result)
        self.assertEqual(gate.cache_size, 1)  # cache hit, no new entry


if __name__ == "__main__":
    unittest.main()
