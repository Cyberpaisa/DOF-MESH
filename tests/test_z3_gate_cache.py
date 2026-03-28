"""
Tests for Z3 Proof Caching in core/z3_gate.py.
Validates cache hit behavior and correctness of cached results.
"""

import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.z3_gate import Z3Gate, GateResult


class TestZ3ProofCache(unittest.TestCase):
    """SMT proof cache avoids redundant Z3 solving."""

    def test_cache_empty_on_init(self):
        gate = Z3Gate()
        self.assertEqual(gate.cache_size, 0)

    def test_trust_score_cached_on_first_call(self):
        gate = Z3Gate()
        gate.validate_trust_score("agent-1", 0.9, {"current_level": 1})
        self.assertEqual(gate.cache_size, 1)

    def test_trust_score_cache_hit_returns_same_result(self):
        gate = Z3Gate()
        result1 = gate.validate_trust_score("agent-1", 0.9, {"current_level": 1})
        result2 = gate.validate_trust_score("agent-2", 0.9, {"current_level": 1})
        # Same constraints (score + level) → same cached result
        self.assertEqual(result1.result, result2.result)
        self.assertEqual(gate.cache_size, 1)  # Only one entry — same key

    def test_different_inputs_produce_separate_cache_entries(self):
        gate = Z3Gate()
        gate.validate_trust_score("agent-1", 0.9, {"current_level": 1})
        gate.validate_trust_score("agent-1", 0.5, {"current_level": 3})
        self.assertEqual(gate.cache_size, 2)

    def test_promotion_cached(self):
        gate = Z3Gate()
        gate.validate_promotion("agent-1", 1, 2)
        self.assertEqual(gate.cache_size, 1)

    def test_promotion_cache_hit_same_levels(self):
        gate = Z3Gate()
        r1 = gate.validate_promotion("agent-a", 1, 2)
        r2 = gate.validate_promotion("agent-b", 1, 2)  # same levels, different agent_id
        self.assertEqual(r1.result, r2.result)
        self.assertEqual(gate.cache_size, 1)

    def test_valid_trust_score_approved(self):
        gate = Z3Gate()
        result = gate.validate_trust_score("agent-1", 0.85, {"current_level": 2})
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_invalid_trust_score_rejected(self):
        gate = Z3Gate()
        result = gate.validate_trust_score("agent-1", 0.7, {"current_level": 3})
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_valid_promotion_approved(self):
        gate = Z3Gate()
        result = gate.validate_promotion("agent-1", 1, 2)
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_invalid_promotion_skip_rejected(self):
        gate = Z3Gate()
        result = gate.validate_promotion("agent-1", 1, 3)  # jump → invalid
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_constraint_hash_is_deterministic(self):
        gate = Z3Gate()
        h1 = gate._constraint_hash("trust_score", 0.9, 1)
        h2 = gate._constraint_hash("trust_score", 0.9, 1)
        self.assertEqual(h1, h2)

    def test_constraint_hash_differs_for_different_inputs(self):
        gate = Z3Gate()
        h1 = gate._constraint_hash("trust_score", 0.9, 1)
        h2 = gate._constraint_hash("trust_score", 0.5, 2)
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
