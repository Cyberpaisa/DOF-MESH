"""
Tests for BayesianProviderSelector in core/providers.py.
Thompson Sampling with Beta distributions and temporal decay.
"""

import os
import sys
import time
import json
import unittest
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.providers import BayesianProviderSelector, BetaParams


# ─────────────────────────────────────────────────────────────────────
# Tests: BetaParams
# ─────────────────────────────────────────────────────────────────────

class TestBetaParams(unittest.TestCase):
    """Beta distribution parameter operations."""

    def test_uniform_prior(self):
        p = BetaParams(alpha=1.0, beta=1.0)
        self.assertAlmostEqual(p.mean(), 0.5)

    def test_mean_after_successes(self):
        p = BetaParams(alpha=11.0, beta=1.0)  # 10 successes, 0 failures
        self.assertAlmostEqual(p.mean(), 11.0 / 12.0, places=4)

    def test_mean_after_failures(self):
        p = BetaParams(alpha=1.0, beta=11.0)  # 0 successes, 10 failures
        self.assertAlmostEqual(p.mean(), 1.0 / 12.0, places=4)

    def test_sample_in_range(self):
        p = BetaParams(alpha=5.0, beta=5.0)
        for _ in range(100):
            s = p.sample()
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_variance_decreases_with_observations(self):
        few = BetaParams(alpha=2.0, beta=2.0)
        many = BetaParams(alpha=50.0, beta=50.0)
        self.assertGreater(few.variance(), many.variance())


# ─────────────────────────────────────────────────────────────────────
# Tests: Thompson Sampling selection
# ─────────────────────────────────────────────────────────────────────

class TestThompsonSampling(unittest.TestCase):
    """select_provider() uses Thompson Sampling to pick the best provider."""

    def test_select_returns_valid_provider(self):
        selector = BayesianProviderSelector(["groq", "nvidia", "cerebras"])
        selector.reset()
        result = selector.select_provider(["groq", "nvidia", "cerebras"])
        self.assertIn(result, ["groq", "nvidia", "cerebras"])

    def test_select_from_available_subset(self):
        selector = BayesianProviderSelector(["groq", "nvidia", "cerebras"])
        selector.reset()
        result = selector.select_provider(["groq"])
        self.assertEqual(result, "groq")

    def test_select_empty_raises(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        with self.assertRaises(ValueError):
            selector.select_provider([])

    def test_high_confidence_provider_selected_more(self):
        """A provider with many successes should be selected more often."""
        selector = BayesianProviderSelector(["good", "bad"])
        selector.reset()
        now = time.time()
        # Good: 20 successes, 1 failure
        selector._providers["good"] = BetaParams(alpha=21.0, beta=2.0, last_decay=now)
        # Bad: 1 success, 20 failures
        selector._providers["bad"] = BetaParams(alpha=2.0, beta=21.0, last_decay=now)

        counts = {"good": 0, "bad": 0}
        for _ in range(1000):
            chosen = selector.select_provider(["good", "bad"])
            counts[chosen] += 1

        # Good should be selected significantly more
        self.assertGreater(counts["good"], counts["bad"])
        self.assertGreater(counts["good"], 800)  # Should be >80%

    def test_uniform_prior_explores(self):
        """With uniform priors, both providers get selected sometimes."""
        selector = BayesianProviderSelector(["a", "b"])
        selector.reset()
        counts = {"a": 0, "b": 0}
        for _ in range(1000):
            chosen = selector.select_provider(["a", "b"])
            counts[chosen] += 1

        # Both should be selected at least some of the time
        self.assertGreater(counts["a"], 100)
        self.assertGreater(counts["b"], 100)


# ─────────────────────────────────────────────────────────────────────
# Tests: record_success and record_failure
# ─────────────────────────────────────────────────────────────────────

class TestBayesianUpdates(unittest.TestCase):
    """Recording successes and failures updates Beta parameters."""

    def setUp(self):
        self.selector = BayesianProviderSelector(["groq", "nvidia"])
        self.selector.reset()

    def test_success_increases_alpha(self):
        before = self.selector._providers["groq"].alpha
        self.selector.record_success("groq")
        after = self.selector._providers["groq"].alpha
        self.assertEqual(after, before + 1.0)

    def test_failure_increases_beta(self):
        before = self.selector._providers["nvidia"].beta
        self.selector.record_failure("nvidia")
        after = self.selector._providers["nvidia"].beta
        self.assertEqual(after, before + 1.0)

    def test_success_increases_confidence(self):
        before = self.selector.get_confidence("groq")
        self.selector.record_success("groq")
        after = self.selector.get_confidence("groq")
        self.assertGreater(after, before)

    def test_failure_decreases_confidence(self):
        before = self.selector.get_confidence("nvidia")
        self.selector.record_failure("nvidia")
        after = self.selector.get_confidence("nvidia")
        self.assertLess(after, before)

    def test_multiple_updates(self):
        # 5 successes, 2 failures for groq
        for _ in range(5):
            self.selector.record_success("groq")
        for _ in range(2):
            self.selector.record_failure("groq")

        params = self.selector._providers["groq"]
        self.assertEqual(params.alpha, 6.0)  # 1 (prior) + 5
        self.assertEqual(params.beta, 3.0)   # 1 (prior) + 2

    def test_unknown_provider_gets_initialized(self):
        self.selector.record_success("new_provider")
        self.assertIn("new_provider", self.selector._providers)
        self.assertEqual(self.selector._providers["new_provider"].alpha, 2.0)


# ─────────────────────────────────────────────────────────────────────
# Tests: get_confidence
# ─────────────────────────────────────────────────────────────────────

class TestGetConfidence(unittest.TestCase):
    """get_confidence() returns the Beta mean."""

    def test_uniform_prior_is_0_5(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        self.assertAlmostEqual(selector.get_confidence("groq"), 0.5)

    def test_unknown_provider_is_0_5(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        self.assertAlmostEqual(selector.get_confidence("unknown"), 0.5)

    def test_all_successes_approaches_1(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        for _ in range(100):
            selector.record_success("groq")
        confidence = selector.get_confidence("groq")
        self.assertGreater(confidence, 0.95)

    def test_all_failures_approaches_0(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        for _ in range(100):
            selector.record_failure("groq")
        confidence = selector.get_confidence("groq")
        self.assertLess(confidence, 0.05)

    def test_get_all_confidences(self):
        selector = BayesianProviderSelector(["groq", "nvidia"])
        selector.reset()
        result = selector.get_all_confidences()
        self.assertIn("groq", result)
        self.assertIn("nvidia", result)
        self.assertAlmostEqual(result["groq"], 0.5)


# ─────────────────────────────────────────────────────────────────────
# Tests: Temporal decay
# ─────────────────────────────────────────────────────────────────────

class TestTemporalDecay(unittest.TestCase):
    """Temporal decay fades old observations."""

    def test_decay_reduces_parameters(self):
        selector = BayesianProviderSelector(["groq"])
        selector._providers["groq"] = BetaParams(
            alpha=10.0, beta=5.0,
            last_decay=time.time() - 7200,  # 2 hours ago
        )
        selector._apply_decay()
        params = selector._providers["groq"]
        # After 2 hours of decay at λ=0.95: α * 0.95² ≈ 9.025
        self.assertLess(params.alpha, 10.0)
        self.assertLess(params.beta, 5.0)

    def test_decay_preserves_minimum(self):
        """α and β should never drop below 1.0."""
        selector = BayesianProviderSelector(["groq"])
        selector._providers["groq"] = BetaParams(
            alpha=1.1, beta=1.1,
            last_decay=time.time() - 360000,  # 100 hours ago
        )
        selector._apply_decay()
        params = selector._providers["groq"]
        self.assertGreaterEqual(params.alpha, 1.0)
        self.assertGreaterEqual(params.beta, 1.0)

    def test_no_decay_within_interval(self):
        selector = BayesianProviderSelector(["groq"])
        selector._providers["groq"] = BetaParams(
            alpha=10.0, beta=5.0,
            last_decay=time.time() - 1800,  # 30 min ago (< 1 hour)
        )
        selector._apply_decay()
        params = selector._providers["groq"]
        self.assertEqual(params.alpha, 10.0)
        self.assertEqual(params.beta, 5.0)


# ─────────────────────────────────────────────────────────────────────
# Tests: get_status
# ─────────────────────────────────────────────────────────────────────

class TestGetStatus(unittest.TestCase):
    """get_status() returns full Bayesian state."""

    def test_status_keys(self):
        selector = BayesianProviderSelector(["groq", "nvidia"])
        selector.reset()
        status = selector.get_status()
        self.assertIn("groq", status)
        self.assertIn("nvidia", status)
        for provider_data in status.values():
            self.assertIn("alpha", provider_data)
            self.assertIn("beta", provider_data)
            self.assertIn("confidence", provider_data)
            self.assertIn("variance", provider_data)
            self.assertIn("total_observations", provider_data)

    def test_initial_total_observations_is_0(self):
        selector = BayesianProviderSelector(["groq"])
        selector.reset()
        status = selector.get_status()
        # total_observations = α + β - 2 (subtract the 2 prior counts)
        self.assertAlmostEqual(status["groq"]["total_observations"], 0.0)


# ─────────────────────────────────────────────────────────────────────
# Tests: Persistence
# ─────────────────────────────────────────────────────────────────────

class TestPersistence(unittest.TestCase):
    """State save/load across instances."""

    def test_reset_clears_state(self):
        selector = BayesianProviderSelector(["groq"])
        selector.record_success("groq")
        selector.record_success("groq")
        self.assertGreater(selector.get_confidence("groq"), 0.5)

        selector.reset()
        self.assertAlmostEqual(selector.get_confidence("groq"), 0.5)


if __name__ == "__main__":
    unittest.main()
