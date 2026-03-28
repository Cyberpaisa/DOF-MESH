"""
Tests for core/adaptive_circuit_breaker.py — per-agent block-rate circuit breaker.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.adaptive_circuit_breaker import AdaptiveCircuitBreaker, CircuitState


class TestCircuitStateMachine(unittest.TestCase):
    """State transitions based on block rate."""

    def test_fresh_breaker_is_closed(self):
        cb = AdaptiveCircuitBreaker("agent-001")
        self.assertEqual(cb.state(), CircuitState.CLOSED)

    def test_all_pass_stays_closed(self):
        cb = AdaptiveCircuitBreaker("agent-001")
        for _ in range(20):
            cb.record(blocked=False)
        self.assertEqual(cb.state(), CircuitState.CLOSED)

    def test_half_open_at_10_percent(self):
        """10% block rate (9-15% range) → HALF_OPEN."""
        cb = AdaptiveCircuitBreaker("agent-001", threshold_rate=0.15)
        for _ in range(9):
            cb.record(blocked=False)
        cb.record(blocked=True)  # 1/10 = 10%
        self.assertEqual(cb.state(), CircuitState.HALF_OPEN)

    def test_open_at_threshold(self):
        """Block rate >= 15% → OPEN."""
        cb = AdaptiveCircuitBreaker("agent-001", threshold_rate=0.15)
        for _ in range(5):
            cb.record(blocked=False)
        for _ in range(2):
            cb.record(blocked=True)  # 2/7 ≈ 28.6% > 15%
        self.assertEqual(cb.state(), CircuitState.OPEN)

    def test_recovery_to_closed_after_passes(self):
        """Adding enough pass events lowers rate back to CLOSED."""
        cb = AdaptiveCircuitBreaker("agent-001", threshold_rate=0.15)
        # Push to OPEN
        for _ in range(2):
            cb.record(blocked=True)
        self.assertEqual(cb.state(), CircuitState.OPEN)
        # Recover with 50 clean passes — rate drops well below 9%
        for _ in range(50):
            cb.record(blocked=False)
        self.assertEqual(cb.state(), CircuitState.CLOSED)

    def test_reset_clears_to_closed(self):
        cb = AdaptiveCircuitBreaker("agent-001")
        cb.record(blocked=True)
        cb.record(blocked=True)
        cb.reset()
        self.assertEqual(cb.state(), CircuitState.CLOSED)

    def test_zero_events_after_window_expires(self):
        """Events outside the sliding window are purged → CLOSED."""
        cb = AdaptiveCircuitBreaker("agent-001", window_seconds=1)
        cb.record(blocked=True)
        cb.record(blocked=True)
        # Simulate time passing by back-dating events
        old_time = datetime.now(timezone.utc) - timedelta(seconds=5)
        for i in range(len(cb._events)):
            ts, blocked = cb._events[i]
            cb._events[i] = (old_time, blocked)
        # Next record triggers purge
        cb.record(blocked=False)
        self.assertEqual(cb.state(), CircuitState.CLOSED)


class TestCircuitSnapshot(unittest.TestCase):
    """Snapshot returns correct read-only state."""

    def test_snapshot_fields(self):
        cb = AdaptiveCircuitBreaker("apex-1687", threshold_rate=0.15, window_seconds=60)
        cb.record(blocked=False)
        cb.record(blocked=True)

        snap = cb.snapshot()
        self.assertEqual(snap.agent_id, "apex-1687")
        self.assertEqual(snap.total_events, 2)
        self.assertEqual(snap.blocked_events, 1)
        self.assertEqual(snap.window_seconds, 60)
        self.assertAlmostEqual(snap.block_rate, 0.5, places=2)

    def test_snapshot_state_matches_state_method(self):
        cb = AdaptiveCircuitBreaker("apex-1687")
        cb.record(blocked=True)
        cb.record(blocked=True)
        snap = cb.snapshot()
        self.assertEqual(snap.state, cb.state())


class TestCustomThresholds(unittest.TestCase):
    """Custom threshold and window parameters are respected."""

    def test_custom_threshold_20_percent(self):
        cb = AdaptiveCircuitBreaker("agent-x", threshold_rate=0.20)
        for _ in range(4):
            cb.record(blocked=False)
        cb.record(blocked=True)  # 1/5 = 20% → OPEN
        self.assertEqual(cb.state(), CircuitState.OPEN)

    def test_custom_threshold_below_does_not_open(self):
        cb = AdaptiveCircuitBreaker("agent-x", threshold_rate=0.20)
        for _ in range(9):
            cb.record(blocked=False)
        cb.record(blocked=True)  # 1/10 = 10% < 20% → not OPEN
        self.assertNotEqual(cb.state(), CircuitState.OPEN)


if __name__ == "__main__":
    unittest.main()
