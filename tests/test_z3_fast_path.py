"""Tests for Z3 Fast Path (policy cache) and Context Epoch System."""

import unittest
from datetime import datetime, timezone

from core.z3_gate import Z3Gate, GateVerification, GateResult
from core.z3_verifier import Z3Verifier


class TestZ3FastPath(unittest.TestCase):
    """Tests para el Fast Path policy cache en Z3Gate."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=1000)

    def _make_verification(self, result=GateResult.APPROVED):
        return GateVerification(
            result=result,
            decision_type="test_policy",
            invariants_checked=["INV-1"],
            verification_time_ms=1.0,
        )

    def test_fast_path_empty_on_init(self):
        self.assertEqual(self.gate.policy_cache_size, 0)

    def test_register_policy(self):
        v = self._make_verification()
        self.gate.register_policy("pol-1", v)
        result = self.gate.fast_path_check("pol-1")
        self.assertIsNotNone(result)
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_fast_path_miss_returns_none(self):
        self.assertIsNone(self.gate.fast_path_check("nonexistent"))

    def test_invalidate_policies_clears_cache(self):
        self.gate.register_policy("a", self._make_verification())
        self.gate.register_policy("b", self._make_verification())
        self.gate.invalidate_policies()
        self.assertEqual(self.gate.policy_cache_size, 0)
        self.assertIsNone(self.gate.fast_path_check("a"))

    def test_invalidate_returns_count(self):
        self.gate.register_policy("a", self._make_verification())
        self.gate.register_policy("b", self._make_verification())
        self.gate.register_policy("c", self._make_verification())
        count = self.gate.invalidate_policies()
        self.assertEqual(count, 3)

    def test_policy_epoch_increments_on_invalidate(self):
        self.gate.invalidate_policies()
        self.assertEqual(self.gate.policy_epoch, 1)
        self.gate.invalidate_policies()
        self.assertEqual(self.gate.policy_epoch, 2)

    def test_policy_epoch_starts_at_zero(self):
        fresh = Z3Gate()
        self.assertEqual(fresh.policy_epoch, 0)

    def test_fast_path_survives_constraint_cache_clear(self):
        """Fast Path es independiente del _cache de constraints SMT."""
        self.gate.register_policy("pol-x", self._make_verification())
        # Simular limpieza del cache SMT de constraints
        self.gate._cache.clear()
        # Fast Path debe seguir intacto
        self.assertIsNotNone(self.gate.fast_path_check("pol-x"))
        self.assertEqual(self.gate.policy_cache_size, 1)


class TestContextEpoch(unittest.TestCase):
    """Tests para el Context Epoch System en Z3Verifier."""

    def setUp(self):
        self.verifier = Z3Verifier()

    def test_epoch_starts_at_zero(self):
        self.assertEqual(self.verifier.context_epoch, 0)

    def test_increment_epoch(self):
        new_epoch = self.verifier.increment_epoch()
        self.assertEqual(new_epoch, 1)
        self.assertEqual(self.verifier.context_epoch, 1)

    def test_epoch_compatible_same(self):
        self.verifier.increment_epoch()  # epoch = 1
        self.assertTrue(self.verifier.verify_epoch_compatible(1))

    def test_epoch_incompatible_lower(self):
        self.verifier.increment_epoch()  # epoch = 1
        self.assertFalse(self.verifier.verify_epoch_compatible(0))

    def test_epoch_incompatible_higher(self):
        self.verifier.increment_epoch()  # epoch = 1
        self.assertFalse(self.verifier.verify_epoch_compatible(2))

    def test_epoch_history_tracks(self):
        self.verifier.increment_epoch()
        self.verifier.increment_epoch()
        history = self.verifier.epoch_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][0], 1)
        self.assertEqual(history[1][0], 2)
        # Timestamps deben ser datetime UTC
        self.assertIsInstance(history[0][1], datetime)

    def test_multiple_increments(self):
        for _ in range(5):
            self.verifier.increment_epoch()
        self.assertEqual(self.verifier.context_epoch, 5)
        self.assertEqual(len(self.verifier.epoch_history()), 5)


if __name__ == "__main__":
    unittest.main()
