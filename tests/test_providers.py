"""Tests for core/providers.py — BetaParams and BayesianProviderSelector."""

import time
import unittest
from unittest.mock import patch

from core.providers import BayesianProviderSelector, BetaParams


# ─────────────────────────────────────────────────────────
# BetaParams
# ─────────────────────────────────────────────────────────

class TestBetaParams(unittest.TestCase):

    def test_default_uniform_prior(self):
        p = BetaParams()
        self.assertEqual(p.alpha, 1.0)
        self.assertEqual(p.beta, 1.0)

    def test_mean_uniform(self):
        """Beta(1,1) mean = 0.5."""
        self.assertAlmostEqual(BetaParams(1.0, 1.0).mean(), 0.5)

    def test_mean_high_alpha(self):
        """Beta(9,1) mean = 0.9."""
        self.assertAlmostEqual(BetaParams(9.0, 1.0).mean(), 0.9)

    def test_mean_high_beta(self):
        """Beta(1,9) mean = 0.1."""
        self.assertAlmostEqual(BetaParams(1.0, 9.0).mean(), 0.1)

    def test_variance_uniform(self):
        """Beta(1,1) variance = 1/12."""
        self.assertAlmostEqual(BetaParams(1.0, 1.0).variance(), 1 / 12, places=6)

    def test_variance_concentrated(self):
        """Higher observation count → lower variance."""
        v_low = BetaParams(2.0, 2.0).variance()
        v_high = BetaParams(20.0, 20.0).variance()
        self.assertGreater(v_low, v_high)

    def test_sample_returns_float_in_01(self):
        p = BetaParams(5.0, 2.0)
        for _ in range(50):
            s = p.sample()
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_custom_last_decay(self):
        t = time.time() - 3600
        p = BetaParams(last_decay=t)
        self.assertAlmostEqual(p.last_decay, t, places=0)

    def test_mean_range(self):
        for alpha in (1, 5, 50):
            for beta in (1, 5, 50):
                m = BetaParams(float(alpha), float(beta)).mean()
                self.assertGreater(m, 0.0)
                self.assertLess(m, 1.0)


# ─────────────────────────────────────────────────────────
# BayesianProviderSelector — construction
# ─────────────────────────────────────────────────────────

class TestSelectorConstruction(unittest.TestCase):

    def test_empty_construction(self):
        sel = BayesianProviderSelector()
        self.assertEqual(len(sel._providers), 0)

    def test_list_construction(self):
        sel = BayesianProviderSelector(["a", "b", "c"])
        self.assertIn("a", sel._providers)
        self.assertIn("b", sel._providers)
        self.assertIn("c", sel._providers)

    def test_initial_alpha_beta_uniform(self):
        sel = BayesianProviderSelector(["x"])
        p = sel._providers["x"]
        self.assertEqual(p.alpha, 1.0)
        self.assertEqual(p.beta, 1.0)

    def test_confidence_initial_half(self):
        sel = BayesianProviderSelector(["x"])
        self.assertAlmostEqual(sel.get_confidence("x"), 0.5)


# ─────────────────────────────────────────────────────────
# select_provider
# ─────────────────────────────────────────────────────────

class TestSelectProvider(unittest.TestCase):

    def setUp(self):
        self.sel = BayesianProviderSelector(["fast", "slow", "backup"])

    def test_raises_on_empty_list(self):
        with self.assertRaises(ValueError):
            self.sel.select_provider([])

    def test_single_provider_always_selected(self):
        for _ in range(10):
            result = self.sel.select_provider(["fast"])
            self.assertEqual(result, "fast")

    def test_returns_one_of_available(self):
        available = ["fast", "slow"]
        for _ in range(20):
            result = self.sel.select_provider(available)
            self.assertIn(result, available)

    def test_high_confidence_wins_most(self):
        """Provider with many successes should be selected most often."""
        sel = BayesianProviderSelector(["good", "bad"])
        for _ in range(30):
            sel.record_success("good")
        for _ in range(30):
            sel.record_failure("bad")
        wins = {"good": 0, "bad": 0}
        for _ in range(200):
            wins[sel.select_provider(["good", "bad"])] += 1
        self.assertGreater(wins["good"], wins["bad"])

    def test_unknown_provider_auto_registered(self):
        """Providers not in initial list are auto-registered on selection."""
        result = self.sel.select_provider(["newcomer"])
        self.assertEqual(result, "newcomer")
        self.assertIn("newcomer", self.sel._providers)


# ─────────────────────────────────────────────────────────
# record_success / record_failure
# ─────────────────────────────────────────────────────────

class TestRecordOutcomes(unittest.TestCase):

    def setUp(self):
        self.sel = BayesianProviderSelector(["p1"])

    def test_success_increments_alpha(self):
        before = self.sel._providers["p1"].alpha
        self.sel.record_success("p1")
        self.assertAlmostEqual(self.sel._providers["p1"].alpha, before + 1.0)

    def test_failure_increments_beta(self):
        before = self.sel._providers["p1"].beta
        self.sel.record_failure("p1")
        self.assertAlmostEqual(self.sel._providers["p1"].beta, before + 1.0)

    def test_success_raises_confidence(self):
        c0 = self.sel.get_confidence("p1")
        for _ in range(10):
            self.sel.record_success("p1")
        self.assertGreater(self.sel.get_confidence("p1"), c0)

    def test_failure_lowers_confidence(self):
        c0 = self.sel.get_confidence("p1")
        for _ in range(10):
            self.sel.record_failure("p1")
        self.assertLess(self.sel.get_confidence("p1"), c0)

    def test_auto_register_on_success(self):
        self.sel.record_success("brand_new")
        self.assertIn("brand_new", self.sel._providers)
        self.assertAlmostEqual(self.sel._providers["brand_new"].alpha, 2.0)

    def test_auto_register_on_failure(self):
        self.sel.record_failure("brand_new2")
        self.assertIn("brand_new2", self.sel._providers)
        self.assertAlmostEqual(self.sel._providers["brand_new2"].beta, 2.0)


# ─────────────────────────────────────────────────────────
# reset
# ─────────────────────────────────────────────────────────

class TestReset(unittest.TestCase):

    def test_reset_restores_uniform(self):
        sel = BayesianProviderSelector(["a", "b"])
        for _ in range(20):
            sel.record_success("a")
        for _ in range(20):
            sel.record_failure("b")
        sel.reset()
        self.assertAlmostEqual(sel.get_confidence("a"), 0.5)
        self.assertAlmostEqual(sel.get_confidence("b"), 0.5)

    def test_reset_preserves_provider_names(self):
        sel = BayesianProviderSelector(["x", "y"])
        sel.reset()
        self.assertIn("x", sel._providers)
        self.assertIn("y", sel._providers)


# ─────────────────────────────────────────────────────────
# get_status / get_all_confidences
# ─────────────────────────────────────────────────────────

class TestStatus(unittest.TestCase):

    def setUp(self):
        self.sel = BayesianProviderSelector(["a", "b"])
        self.sel.record_success("a")
        self.sel.record_failure("b")

    def test_get_status_keys(self):
        s = self.sel.get_status()
        self.assertIn("a", s)
        self.assertIn("b", s)

    def test_get_status_fields(self):
        s = self.sel.get_status()["a"]
        for field in ("alpha", "beta", "confidence", "variance", "total_observations"):
            self.assertIn(field, s)

    def test_total_observations(self):
        """After 1 success, total_obs for 'a' = (alpha+beta) - 2 = 1."""
        s = self.sel.get_status()["a"]
        self.assertAlmostEqual(s["total_observations"], 1.0)

    def test_get_all_confidences(self):
        confs = self.sel.get_all_confidences()
        self.assertIn("a", confs)
        self.assertIn("b", confs)
        self.assertGreater(confs["a"], confs["b"])

    def test_confidence_in_range(self):
        for conf in self.sel.get_all_confidences().values():
            self.assertGreater(conf, 0.0)
            self.assertLess(conf, 1.0)


# ─────────────────────────────────────────────────────────
# _apply_decay
# ─────────────────────────────────────────────────────────

class TestDecay(unittest.TestCase):

    def test_decay_reduces_excess_observations(self):
        """Simulating 2 hours elapsed: observations should shrink."""
        sel = BayesianProviderSelector(["p"])
        for _ in range(50):
            sel.record_success("p")
        alpha_before = sel._providers["p"].alpha

        # Backdate last_decay by 2 hours to force decay
        sel._providers["p"].last_decay = time.time() - 7201
        sel._apply_decay()

        alpha_after = sel._providers["p"].alpha
        self.assertLess(alpha_after, alpha_before)

    def test_decay_floor_is_1(self):
        """After extreme decay, alpha and beta never drop below 1.0."""
        sel = BayesianProviderSelector(["p"])
        # Backdate by 1000 hours
        sel._providers["p"].last_decay = time.time() - 1000 * 3600
        sel._apply_decay()
        p = sel._providers["p"]
        self.assertGreaterEqual(p.alpha, 1.0)
        self.assertGreaterEqual(p.beta, 1.0)

    def test_no_decay_under_one_hour(self):
        """Less than 1 hour elapsed: no decay applied."""
        sel = BayesianProviderSelector(["p"])
        for _ in range(20):
            sel.record_success("p")
        alpha_before = sel._providers["p"].alpha

        sel._providers["p"].last_decay = time.time() - 1800  # 30 min
        sel._apply_decay()

        self.assertAlmostEqual(sel._providers["p"].alpha, alpha_before)


if __name__ == "__main__":
    unittest.main()
