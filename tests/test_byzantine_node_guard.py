"""Tests para ByzantineNodeGuard — reputación por nodo."""

import unittest

from core.byzantine_node_guard import (
    ByzantineNodeGuard,
    NodeStatus,
    NodeSnapshot,
    QUARANTINE_THRESHOLD,
    PROBATION_THRESHOLD,
    REPUTATION_INCREMENT,
    REPUTATION_PENALTY,
    TIMEOUT_PENALTY,
    MAX_REPUTATION,
    MIN_REPUTATION,
)


class TestByzantineNodeGuard(unittest.TestCase):

    def setUp(self):
        self.guard = ByzantineNodeGuard()

    def test_fresh_node_is_active(self):
        """Nodo nuevo tiene rep=1.0, status=ACTIVE."""
        self.assertEqual(self.guard.reputation("new-node"), 1.0)
        self.assertEqual(self.guard.status("new-node"), NodeStatus.ACTIVE)

    def test_success_increments_reputation(self):
        """Success sube reputación en 0.01."""
        # Bajamos primero para que haya espacio para subir
        self.guard._reputation["node-1"] = 0.5
        new_rep = self.guard.record_success("node-1")
        self.assertAlmostEqual(new_rep, 0.51, places=4)

    def test_failure_decrements_reputation(self):
        """Failure baja reputación en 0.05."""
        self.guard._reputation["node-1"] = 1.0
        new_rep = self.guard.record_failure("node-1", reason="consensus_fail")
        self.assertAlmostEqual(new_rep, 0.95, places=4)

    def test_timeout_penalty_smaller(self):
        """Timeout baja solo 0.03 (menos que fallo general)."""
        self.guard._reputation["node-1"] = 1.0
        new_rep = self.guard.record_failure("node-1", reason="z3_timeout")
        self.assertAlmostEqual(new_rep, 0.97, places=4)

    def test_quarantine_below_threshold(self):
        """Rep < 0.3 → status=QUARANTINED."""
        self.guard._reputation["node-1"] = 0.29
        self.assertEqual(self.guard.status("node-1"), NodeStatus.QUARANTINED)

    def test_probation_between_thresholds(self):
        """Rep 0.3-0.5 → PROBATION."""
        self.guard._reputation["node-1"] = 0.4
        self.assertEqual(self.guard.status("node-1"), NodeStatus.PROBATION)

    def test_is_allowed_false_when_quarantined(self):
        """is_allowed() False si rep < 0.3."""
        self.guard._reputation["node-1"] = 0.2
        self.assertFalse(self.guard.is_allowed("node-1"))

    def test_is_allowed_true_when_active(self):
        """is_allowed() True si rep >= 0.3."""
        self.guard._reputation["node-1"] = 0.5
        self.assertTrue(self.guard.is_allowed("node-1"))

    def test_reputation_floor_zero(self):
        """Reputación no baja de 0.0."""
        self.guard._reputation["node-1"] = 0.01
        new_rep = self.guard.record_failure("node-1", reason="crash")
        self.assertGreaterEqual(new_rep, MIN_REPUTATION)

    def test_reputation_ceiling_one(self):
        """Reputación no sube de 1.0."""
        self.guard._reputation["node-1"] = 1.0
        new_rep = self.guard.record_success("node-1")
        self.assertLessEqual(new_rep, MAX_REPUTATION)

    def test_snapshot_fields(self):
        """Snapshot tiene todos los campos correctos."""
        self.guard.record_success("node-1")
        snap = self.guard.snapshot("node-1")
        self.assertIsInstance(snap, NodeSnapshot)
        self.assertEqual(snap.node_id, "node-1")
        self.assertEqual(snap.total_transactions, 1)
        self.assertEqual(snap.failed_transactions, 0)
        self.assertEqual(snap.consecutive_clean, 1)
        self.assertEqual(snap.status, NodeStatus.ACTIVE)

    def test_consecutive_clean_resets_on_failure(self):
        """Failure resetea consecutive_clean a 0."""
        for _ in range(10):
            self.guard.record_success("node-1")
        self.assertEqual(self.guard._consecutive_clean["node-1"], 10)
        self.guard.record_failure("node-1")
        self.assertEqual(self.guard._consecutive_clean["node-1"], 0)

    def test_can_restore_after_50_clean(self):
        """can_restore() True después de 50 successes consecutivos."""
        self.guard._reputation["node-1"] = 0.2  # cuarentena
        for _ in range(50):
            self.guard.record_success("node-1")
        self.assertTrue(self.guard.can_restore("node-1"))

    def test_can_restore_false_before_50(self):
        """can_restore() False con 49 successes."""
        self.guard._reputation["node-1"] = 0.2
        for _ in range(49):
            self.guard.record_success("node-1")
        self.assertFalse(self.guard.can_restore("node-1"))

    def test_reset_restores_to_active(self):
        """reset_node() → rep=1.0, status=ACTIVE."""
        self.guard._reputation["node-1"] = 0.1
        self.guard.reset_node("node-1")
        self.assertEqual(self.guard.reputation("node-1"), 1.0)
        self.assertEqual(self.guard.status("node-1"), NodeStatus.ACTIVE)

    def test_all_quarantined_returns_quarantined_nodes(self):
        """all_quarantined() retorna solo nodos en cuarentena."""
        self.guard._reputation["good"] = 0.8
        self.guard._reputation["bad1"] = 0.1
        self.guard._reputation["bad2"] = 0.2
        self.guard._reputation["ok"] = 0.4
        quarantined = self.guard.all_quarantined()
        self.assertIn("bad1", quarantined)
        self.assertIn("bad2", quarantined)
        self.assertNotIn("good", quarantined)
        self.assertNotIn("ok", quarantined)


if __name__ == "__main__":
    unittest.main()
