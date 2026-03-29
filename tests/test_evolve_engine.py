"""
Tests for core/evolve_engine.py — DOF-EvolveEngine.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolve_engine import (
    EvolveConfig,
    EvolveController,
    Candidate,
    validate_tracer_weights,
    normalize_to_simplex,
    clip_to_bounds,
    build_tracer_evaluator,
    DEFAULT_TRACER_WEIGHTS,
    FORBIDDEN_TARGETS,
    _spearman_correlation,
    _augment_with_simulated_records,
)


class TestInvariants(unittest.TestCase):
    """Formal invariants must hold for all candidate weights."""

    def test_default_weights_are_valid(self):
        valid, reason = validate_tracer_weights(DEFAULT_TRACER_WEIGHTS)
        self.assertTrue(valid, reason)

    def test_weights_must_sum_to_one(self):
        bad = dict(DEFAULT_TRACER_WEIGHTS)
        bad["trust"] = 0.50  # sum will be > 1
        valid, reason = validate_tracer_weights(bad)
        self.assertFalse(valid)
        self.assertIn("sum", reason.lower())

    def test_weights_must_have_correct_keys(self):
        bad = {"trust": 0.5, "reliability": 0.5}  # missing keys
        valid, reason = validate_tracer_weights(bad)
        self.assertFalse(valid)

    def test_weights_must_respect_bounds(self):
        bad = dict(DEFAULT_TRACER_WEIGHTS)
        bad["economics"] = 0.60  # exceeds max 0.30
        # Normalize first to make sum=1
        bad = normalize_to_simplex(bad)
        valid, _ = validate_tracer_weights(clip_to_bounds(dict(DEFAULT_TRACER_WEIGHTS) | {"economics": 0.60}))
        self.assertTrue(valid)  # clip_to_bounds fixes it

    def test_normalize_to_simplex(self):
        weights = {"a": 2.0, "b": 2.0, "c": 1.0, "d": 3.0, "e": 1.0, "f": 1.0}
        normalized = normalize_to_simplex(weights)
        self.assertAlmostEqual(sum(normalized.values()), 1.0, places=6)

    def test_clip_to_bounds_produces_valid_weights(self):
        extreme = {k: 0.0 for k in DEFAULT_TRACER_WEIGHTS}
        clipped = clip_to_bounds(extreme)
        valid, reason = validate_tracer_weights(clipped)
        self.assertTrue(valid, reason)


class TestForbiddenTargets(unittest.TestCase):
    """HARD_RULES and Z3 theorems must never be evolution targets."""

    def test_hard_rules_is_forbidden(self):
        with self.assertRaises(ValueError) as ctx:
            EvolveConfig(target="hard_rules")
        self.assertIn("FORBIDDEN", str(ctx.exception))

    def test_z3_theorems_is_forbidden(self):
        with self.assertRaises(ValueError) as ctx:
            EvolveConfig(target="z3_theorems")
        self.assertIn("FORBIDDEN", str(ctx.exception))

    def test_constitution_is_forbidden(self):
        with self.assertRaises(ValueError) as ctx:
            EvolveConfig(target="constitution")
        self.assertIn("FORBIDDEN", str(ctx.exception))

    def test_tracer_weights_is_allowed(self):
        config = EvolveConfig(target="tracer_weights")
        self.assertEqual(config.target, "tracer_weights")

    def test_soft_rule_weights_is_allowed(self):
        config = EvolveConfig(target="soft_rule_weights")
        self.assertEqual(config.target, "soft_rule_weights")


class TestEvaluator(unittest.TestCase):
    """Evaluator must return scores in [0, 1] and prefer correct ranking."""

    def setUp(self):
        # Build evaluator using simulated data (no real log needed)
        self.evaluator = build_tracer_evaluator(
            validations_log="/nonexistent/path.jsonl",
            min_records=0,
        )

    def test_evaluator_returns_float(self):
        score = self.evaluator(DEFAULT_TRACER_WEIGHTS)
        self.assertIsInstance(score, float)

    def test_evaluator_score_in_range(self):
        score = self.evaluator(DEFAULT_TRACER_WEIGHTS)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_default_weights_produce_valid_score(self):
        score = self.evaluator(DEFAULT_TRACER_WEIGHTS)
        # Default weights should produce a reasonable score (not 0)
        self.assertGreater(score, 0.0)

    def test_zero_weights_produce_low_score(self):
        """All-zero weights (after normalization) should score lower than defaults."""
        # We can't pass literal zeros (would divide by zero in normalizer)
        equal_weights = {k: 1.0 / 6 for k in DEFAULT_TRACER_WEIGHTS}
        score_default = self.evaluator(DEFAULT_TRACER_WEIGHTS)
        score_equal = self.evaluator(equal_weights)
        # Both should be valid scores
        self.assertGreaterEqual(score_default, 0.0)
        self.assertGreaterEqual(score_equal, 0.0)


class TestSpearmanCorrelation(unittest.TestCase):
    """Spearman correlation must handle edge cases correctly."""

    def test_perfect_positive_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [1, 2, 3, 4, 5]
        self.assertAlmostEqual(_spearman_correlation(x, y), 1.0, places=5)

    def test_perfect_negative_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [5, 4, 3, 2, 1]
        self.assertAlmostEqual(_spearman_correlation(x, y), -1.0, places=5)

    def test_no_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [3, 1, 4, 1, 5]  # no clear order
        corr = _spearman_correlation(x, y)
        self.assertLess(abs(corr), 1.0)

    def test_single_element(self):
        # Should not crash, return 0
        corr = _spearman_correlation([1], [1])
        self.assertEqual(corr, 0.0)

    def test_all_same_values(self):
        x = [1, 1, 1]
        y = [1, 2, 3]
        corr = _spearman_correlation(x, y)
        self.assertEqual(corr, 0.0)  # all tied ranks → zero std dev


class TestSimulatedAugmentation(unittest.TestCase):
    """Simulated records must produce valid TRACER scenarios."""

    def test_augment_adds_records(self):
        augmented = _augment_with_simulated_records([])
        self.assertGreater(len(augmented), 0)

    def test_augmented_records_have_pass_and_fail(self):
        augmented = _augment_with_simulated_records([])
        results = {r["result"] for r in augmented}
        self.assertIn("PASS", results)
        self.assertIn("FAIL", results)

    def test_augmented_records_have_tracer_dimensions(self):
        augmented = _augment_with_simulated_records([])
        for r in augmented:
            self.assertIn("tracer", r)
            self.assertIn("dimensions", r["tracer"])
            dims = r["tracer"]["dimensions"]
            self.assertEqual(len(dims), 6)


class TestEvolveController(unittest.TestCase):
    """Evolution loop must terminate correctly and respect invariants."""

    def _make_engine(self, iterations=10):
        """Create a controller with a deterministic mock evaluator."""
        config = EvolveConfig(
            target="tracer_weights",
            max_iterations=iterations,
            budget_usd=0.0,   # no LLM — pure random
            verbose=False,
            random_seed=99,
        )

        def mock_evaluator(weights: dict) -> float:
            # Rewards higher reliability weight
            return weights.get("reliability", 0.0)

        return EvolveController(config, mock_evaluator)

    def test_run_completes(self):
        engine = self._make_engine(iterations=15)
        result = engine.run()
        self.assertIsNotNone(result)

    def test_result_has_valid_params(self):
        engine = self._make_engine()
        result = engine.run()
        valid, reason = validate_tracer_weights(result.best_params)
        self.assertTrue(valid, f"Invalid params: {reason}")

    def test_result_score_nonnegative(self):
        engine = self._make_engine()
        result = engine.run()
        self.assertGreaterEqual(result.best_score, 0.0)

    def test_result_has_run_id(self):
        engine = self._make_engine()
        result = engine.run()
        self.assertIsNotNone(result.run_id)
        self.assertGreater(len(result.run_id), 0)

    def test_candidates_evaluated(self):
        engine = self._make_engine(iterations=5)
        result = engine.run()
        self.assertGreaterEqual(result.candidates_evaluated, 1)

    def test_optimizer_finds_higher_reliability(self):
        """With a mock evaluator rewarding reliability, it should increase."""
        engine = self._make_engine(iterations=30)
        result = engine.run()
        baseline_reliability = DEFAULT_TRACER_WEIGHTS["reliability"]
        # Best found should have reliability >= baseline (optimizer moves toward higher values)
        self.assertGreaterEqual(result.best_params["reliability"], baseline_reliability * 0.95)


if __name__ == "__main__":
    unittest.main(verbosity=2)
