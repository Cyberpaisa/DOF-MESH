"""
Integration tests for Z3Gate: Fast Path + cache invalidation flow.

Validates that validate_output() uses the Fast Path for recurring policies,
and that invalidate_policies() clears both _policy_cache and _cache.
"""

import unittest

from core.z3_gate import Z3Gate, GateResult
from core.agent_output import AgentOutput, OutputType


class TestValidateOutputUsesFastPath(unittest.TestCase):
    """validate_output() debe registrar resultados APPROVED en Fast Path."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_validate_output_uses_fast_path(self):
        """Segunda llamada con mismo output debe usar Fast Path (policy_cache_size > 0)."""
        output = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent-fp-1",
            proposed_value=0.85,
            evidence={"current_level": 1},
            source_agent="supervisor",
            confidence=0.9,
        )
        # Primera llamada: resuelve Z3, registra en Fast Path
        result1 = self.gate.validate_output(output)
        self.assertEqual(result1.result, GateResult.APPROVED)
        self.assertGreater(self.gate.policy_cache_size, 0)

        # Segunda llamada: debe usar Fast Path (misma policy_id)
        result2 = self.gate.validate_output(output)
        self.assertEqual(result2.result, GateResult.APPROVED)
        # Ambos resultados deben ser iguales
        self.assertEqual(result1.decision_type, result2.decision_type)

    def test_rejected_output_not_cached_in_fast_path(self):
        """Outputs rechazados NO se registran en Fast Path."""
        output = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent-fp-rejected",
            proposed_value=1.5,  # Fuera de rango -> REJECTED
            evidence={},
            source_agent="supervisor",
            confidence=0.9,
        )
        result = self.gate.validate_output(output)
        self.assertEqual(result.result, GateResult.REJECTED)
        # No debe estar en Fast Path
        policy_id = f"{output.output_type.value}:{output.agent_id}"
        self.assertIsNone(self.gate.fast_path_check(policy_id))

    def test_fast_path_different_agents_separate_entries(self):
        """Diferentes agent_ids generan entradas separadas en Fast Path."""
        for i in range(3):
            output = AgentOutput(
                output_type=OutputType.MITIGATION_RECOMMENDATION,
                agent_id=f"agent-{i}",
                proposed_value="block_ip",
                evidence={},
                source_agent="blue",
                confidence=0.8,
            )
            self.gate.validate_output(output)
        self.assertEqual(self.gate.policy_cache_size, 3)


class TestInvalidateClearsBothCaches(unittest.TestCase):
    """invalidate_policies() debe limpiar _policy_cache Y _cache SMT."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_invalidate_clears_both_caches(self):
        """invalidate_policies() limpia Fast Path y cache SMT."""
        # Poblar cache SMT via validate_trust_score
        self.gate.validate_trust_score("agent-1", 0.9, {"current_level": 1})
        self.assertGreater(self.gate.cache_size, 0)

        # Poblar Fast Path via validate_output
        output = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent-inv",
            proposed_value=0.85,
            evidence={},
            source_agent="supervisor",
            confidence=0.9,
        )
        self.gate.validate_output(output)
        self.assertGreater(self.gate.policy_cache_size, 0)

        # Invalidar
        self.gate.invalidate_policies()

        # Ambos caches deben estar vacíos
        self.assertEqual(self.gate.policy_cache_size, 0)
        self.assertEqual(self.gate.cache_size, 0)

    def test_invalidate_increments_epoch(self):
        """invalidate_policies() incrementa epoch."""
        initial = self.gate.policy_epoch
        self.gate.invalidate_policies()
        self.assertEqual(self.gate.policy_epoch, initial + 1)


if __name__ == "__main__":
    unittest.main()
