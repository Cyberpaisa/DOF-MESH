"""Tests para Z3 Portfolio Solver y Versioned Cache."""
import unittest

import z3

from core.z3_portfolio import Z3PortfolioSolver, SolveStrategy, PortfolioResult
from core.versioned_cache import VersionedCache


class TestPortfolioSolver(unittest.TestCase):

    def test_sat_simple_constraint(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        result = solver.solve([x > 0, x < 10])
        self.assertEqual(result.result, "sat")

    def test_unsat_contradiction(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        result = solver.solve([x > 10, x < 5])
        self.assertEqual(result.result, "unsat")

    def test_empty_constraints_sat(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        result = solver.solve([])
        self.assertEqual(result.result, "sat")

    def test_strategy_used_is_valid(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        result = solver.solve([x > 0, x < 10])
        self.assertIsInstance(result.strategy_used, SolveStrategy)

    def test_solve_count_increments(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        self.assertEqual(solver.solve_count, 0)
        solver.solve([x > 0])
        self.assertEqual(solver.solve_count, 1)
        solver.solve([x > 0])
        self.assertEqual(solver.solve_count, 2)

    def test_strategies_tried_at_least_one(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        result = solver.solve([x > 0, x < 10])
        self.assertGreaterEqual(result.strategies_tried, 1)

    def test_solve_time_positive(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        result = solver.solve([x > 0, x < 10])
        self.assertGreater(result.solve_time_ms, 0)

    def test_multiple_solves_deterministic(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        constraints = [x > 0, x < 10]
        r1 = solver.solve(constraints)
        r2 = solver.solve(constraints)
        self.assertEqual(r1.result, r2.result)

    def test_custom_strategies(self):
        solver = Z3PortfolioSolver(timeout_ms=500, strategies=[SolveStrategy.DEFAULT])
        x = z3.Int("x")
        result = solver.solve([x > 0, x < 10])
        self.assertEqual(result.result, "sat")

    def test_strategy_stats_tracks_wins(self):
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        solver.solve([x > 0, x < 10])
        stats = solver.strategy_stats()
        self.assertIn("default", stats)
        self.assertIn("optimize", stats)
        self.assertIn("qf_lia", stats)


class TestVersionedCache(unittest.TestCase):

    def test_empty_on_init(self):
        cache = VersionedCache(ttl_epochs=10)
        self.assertEqual(cache.size, 0)

    def test_put_and_get(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", {"ok": True}, current_epoch=5)
        result = cache.get("h1", current_epoch=5)
        self.assertEqual(result, {"ok": True})

    def test_miss_returns_none(self):
        cache = VersionedCache(ttl_epochs=10)
        result = cache.get("nonexistent", current_epoch=1)
        self.assertIsNone(result)

    def test_expired_by_epoch_returns_none(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", "val", current_epoch=5)
        # expires_at_epoch = 15, so epoch 16 → expired
        result = cache.get("h1", current_epoch=16)
        self.assertIsNone(result)

    def test_not_expired_within_ttl(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", "val", current_epoch=5)
        # expires_at_epoch = 15, epoch 14 → still valid
        result = cache.get("h1", current_epoch=14)
        self.assertEqual(result, "val")

    def test_invalidate_before_epoch(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("old", "v1", current_epoch=1)
        cache.put("new", "v2", current_epoch=5)
        removed = cache.invalidate_before_epoch(3)
        self.assertEqual(removed, 1)
        self.assertIsNone(cache.get("old", current_epoch=5))
        self.assertEqual(cache.get("new", current_epoch=5), "v2")

    def test_clear_removes_all(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("a", 1, current_epoch=1)
        cache.put("b", 2, current_epoch=2)
        count = cache.clear()
        self.assertEqual(count, 2)
        self.assertEqual(cache.size, 0)

    def test_hit_rate_calculation(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", "val", current_epoch=1)
        cache.get("h1", current_epoch=1)  # hit
        cache.get("h1", current_epoch=1)  # hit
        cache.get("miss", current_epoch=1)  # miss
        self.assertAlmostEqual(cache.hit_rate, 2 / 3)

    def test_hit_increments_on_success(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", "val", current_epoch=1)
        self.assertEqual(cache.hits, 0)
        cache.get("h1", current_epoch=1)
        self.assertEqual(cache.hits, 1)

    def test_miss_increments_on_failure(self):
        cache = VersionedCache(ttl_epochs=10)
        self.assertEqual(cache.misses, 0)
        cache.get("nope", current_epoch=1)
        self.assertEqual(cache.misses, 1)

    def test_expired_entry_removed(self):
        cache = VersionedCache(ttl_epochs=10)
        cache.put("h1", "val", current_epoch=1)
        cache.get("h1", current_epoch=20)  # expired → removed
        self.assertEqual(cache.size, 0)

    def test_ttl_epochs_respected(self):
        cache = VersionedCache(ttl_epochs=3)
        cache.put("h1", "val", current_epoch=10)
        # expires_at_epoch = 13
        self.assertEqual(cache.get("h1", current_epoch=13), "val")
        self.assertIsNone(cache.get("h1", current_epoch=14))


if __name__ == "__main__":
    unittest.main()
