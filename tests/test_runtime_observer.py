"""Tests for core/runtime_observer.py — all 5 formal metrics + anomaly detection."""

import json
import math
import os
import tempfile
import unittest

from core.runtime_observer import (
    MetricResult,
    RuntimeObserver,
    _bessel_std,
    _mean,
)


# ── helpers ─────────────────────────────────────────────

def _run(status="success", retries=0, governance_passed=True,
         supervisor_decision="ACCEPT", error=None, attempts=1):
    r = {
        "status": status,
        "retries": retries,
        "governance_passed": governance_passed,
        "supervisor_decision": supervisor_decision,
        "attempts": attempts,
    }
    if error is not None:
        r["error"] = error
    return r


def _write_log(path, runs):
    with open(path, "w") as f:
        for r in runs:
            f.write(json.dumps(r) + "\n")


class TmpLogMixin(unittest.TestCase):
    def setUp(self):
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmpfile.close()
        self.log_path = self._tmpfile.name
        self.obs = RuntimeObserver(log_path=self.log_path)

    def tearDown(self):
        os.unlink(self.log_path)


# ─────────────────────────────────────────────────────────
# Pure math helpers
# ─────────────────────────────────────────────────────────

class TestMean(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_mean([]), 0.0)

    def test_single(self):
        self.assertAlmostEqual(_mean([7.0]), 7.0)

    def test_uniform(self):
        self.assertAlmostEqual(_mean([1.0, 1.0, 1.0]), 1.0)

    def test_mixed(self):
        self.assertAlmostEqual(_mean([0.0, 1.0]), 0.5)

    def test_all_zeros(self):
        self.assertAlmostEqual(_mean([0.0, 0.0, 0.0]), 0.0)


class TestBesselStd(unittest.TestCase):

    def test_single_returns_zero(self):
        self.assertEqual(_bessel_std([5.0]), 0.0)

    def test_empty_returns_zero(self):
        self.assertEqual(_bessel_std([]), 0.0)

    def test_uniform_returns_zero(self):
        self.assertAlmostEqual(_bessel_std([3.0, 3.0, 3.0]), 0.0)

    def test_known_value(self):
        # [0, 1] → mean=0.5, variance=(0.25+0.25)/1=0.5, std=√0.5
        self.assertAlmostEqual(_bessel_std([0.0, 1.0]), math.sqrt(0.5), places=6)

    def test_always_nonnegative(self):
        self.assertGreaterEqual(_bessel_std([0.0, 1.0, 0.5, 0.75]), 0.0)


# ─────────────────────────────────────────────────────────
# MetricResult
# ─────────────────────────────────────────────────────────

class TestMetricResult(unittest.TestCase):

    def test_repr_contains_name(self):
        m = MetricResult(name="SS", mean=0.95, std=0.02, n=50)
        self.assertIn("SS", repr(m))

    def test_repr_contains_mean(self):
        m = MetricResult(name="PFI", mean=0.123, std=0.01, n=10)
        self.assertIn("0.1230", repr(m))

    def test_fields(self):
        m = MetricResult(name="RP", mean=0.5, std=0.1, n=20)
        self.assertEqual(m.name, "RP")
        self.assertEqual(m.n, 20)


# ─────────────────────────────────────────────────────────
# load_runs
# ─────────────────────────────────────────────────────────

class TestLoadRuns(TmpLogMixin):

    def test_missing_file_returns_empty(self):
        obs = RuntimeObserver(log_path="/nonexistent/path.jsonl")
        self.assertEqual(obs.load_runs(), [])

    def test_empty_file_returns_empty(self):
        self.assertEqual(self.obs.load_runs(), [])

    def test_loads_all_entries(self):
        _write_log(self.log_path, [_run(), _run(), _run()])
        runs = self.obs.load_runs()
        self.assertEqual(len(runs), 3)

    def test_window_limits_results(self):
        _write_log(self.log_path, [_run() for _ in range(10)])
        runs = self.obs.load_runs(window=3)
        self.assertEqual(len(runs), 3)

    def test_window_returns_last_n(self):
        entries = [{"status": "success", "idx": i} for i in range(5)]
        _write_log(self.log_path, entries)
        runs = self.obs.load_runs(window=2)
        self.assertEqual(runs[0]["idx"], 3)
        self.assertEqual(runs[1]["idx"], 4)

    def test_skips_blank_lines(self):
        with open(self.log_path, "w") as f:
            f.write(json.dumps(_run()) + "\n")
            f.write("\n")
            f.write(json.dumps(_run()) + "\n")
        self.assertEqual(len(self.obs.load_runs()), 2)

    def test_skips_invalid_json(self):
        with open(self.log_path, "w") as f:
            f.write(json.dumps(_run()) + "\n")
            f.write("{bad json\n")
            f.write(json.dumps(_run()) + "\n")
        self.assertEqual(len(self.obs.load_runs()), 2)


# ─────────────────────────────────────────────────────────
# compute_ss — Stability Score
# ─────────────────────────────────────────────────────────

class TestComputeSS(unittest.TestCase):

    def setUp(self):
        self.obs = RuntimeObserver(log_path="/dev/null")

    def test_empty_returns_zeros(self):
        self.assertEqual(self.obs.compute_ss([]), (0.0, 0.0))

    def test_all_success(self):
        runs = [_run("success")] * 4
        mean, std = self.obs.compute_ss(runs)
        self.assertAlmostEqual(mean, 1.0)
        self.assertAlmostEqual(std, 0.0)

    def test_all_error(self):
        runs = [_run("error")] * 4
        mean, std = self.obs.compute_ss(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_escalated_counts_as_stable(self):
        runs = [_run("escalated")] * 4
        mean, _ = self.obs.compute_ss(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_mixed(self):
        runs = [_run("success"), _run("success"), _run("error"), _run("error")]
        mean, _ = self.obs.compute_ss(runs)
        self.assertAlmostEqual(mean, 0.5)


# ─────────────────────────────────────────────────────────
# compute_pfi — Provider Fragility Index
# ─────────────────────────────────────────────────────────

class TestComputePFI(unittest.TestCase):

    def setUp(self):
        self.obs = RuntimeObserver(log_path="/dev/null")

    def test_empty_returns_zeros(self):
        self.assertEqual(self.obs.compute_pfi([]), (0.0, 0.0))

    def test_no_retries_zero_pfi(self):
        runs = [_run(retries=0)] * 5
        mean, _ = self.obs.compute_pfi(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_max_retries_capped_at_1(self):
        runs = [_run(retries=10)]
        mean, _ = self.obs.compute_pfi(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_ratelimit_error_counts(self):
        runs = [_run(status="error", retries=0, error="ratelimit exceeded")]
        mean, _ = self.obs.compute_pfi(runs)
        self.assertGreater(mean, 0.0)

    def test_non_provider_error_ignored(self):
        runs = [_run(status="error", retries=0, error="some other error")]
        mean, _ = self.obs.compute_pfi(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_normalized_by_3(self):
        runs = [_run(retries=3)]
        mean, _ = self.obs.compute_pfi(runs)
        self.assertAlmostEqual(mean, 1.0)

        runs = [_run(retries=1)]
        mean, _ = self.obs.compute_pfi(runs)
        self.assertAlmostEqual(mean, 1 / 3)


# ─────────────────────────────────────────────────────────
# compute_rp — Retry Pressure
# ─────────────────────────────────────────────────────────

class TestComputeRP(unittest.TestCase):

    def setUp(self):
        self.obs = RuntimeObserver(log_path="/dev/null")

    def test_empty_returns_zeros(self):
        self.assertEqual(self.obs.compute_rp([]), (0.0, 0.0))

    def test_no_retries_zero_rp(self):
        runs = [_run(retries=0)] * 5
        mean, _ = self.obs.compute_rp(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_retries_normalized_by_3(self):
        runs = [_run(retries=3)]
        mean, _ = self.obs.compute_rp(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_retries_capped_at_1(self):
        runs = [_run(retries=99)]
        mean, _ = self.obs.compute_rp(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_attempts_fallback(self):
        # retries=0, attempts=3 → inferred retries = 2
        runs = [{"status": "success", "retries": 0, "attempts": 3}]
        mean, _ = self.obs.compute_rp(runs)
        self.assertAlmostEqual(mean, 2 / 3)


# ─────────────────────────────────────────────────────────
# compute_gcr — Governance Compliance Rate
# ─────────────────────────────────────────────────────────

class TestComputeGCR(unittest.TestCase):

    def setUp(self):
        self.obs = RuntimeObserver(log_path="/dev/null")

    def test_empty_returns_zeros(self):
        self.assertEqual(self.obs.compute_gcr([]), (0.0, 0.0))

    def test_all_passed(self):
        runs = [_run(governance_passed=True)] * 4
        mean, _ = self.obs.compute_gcr(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_all_failed(self):
        runs = [_run(governance_passed=False)] * 4
        mean, _ = self.obs.compute_gcr(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_mixed(self):
        runs = [_run(governance_passed=True), _run(governance_passed=False)]
        mean, _ = self.obs.compute_gcr(runs)
        self.assertAlmostEqual(mean, 0.5)

    def test_no_governance_field_success_assumed_pass(self):
        runs = [{"status": "success"}]
        mean, _ = self.obs.compute_gcr(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_no_governance_field_error_excluded(self):
        # error status without governance_passed → excluded from GCR
        runs = [{"status": "error"}]
        mean, _ = self.obs.compute_gcr(runs)
        self.assertAlmostEqual(mean, 0.0)


# ─────────────────────────────────────────────────────────
# compute_ssr — Supervisor Strictness Ratio
# ─────────────────────────────────────────────────────────

class TestComputeSSR(unittest.TestCase):

    def setUp(self):
        self.obs = RuntimeObserver(log_path="/dev/null")

    def test_empty_returns_zeros(self):
        self.assertEqual(self.obs.compute_ssr([]), (0.0, 0.0))

    def test_all_accept(self):
        runs = [_run(supervisor_decision="ACCEPT")] * 4
        mean, _ = self.obs.compute_ssr(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_all_escalate(self):
        runs = [_run(supervisor_decision="ESCALATE")] * 4
        mean, _ = self.obs.compute_ssr(runs)
        self.assertAlmostEqual(mean, 1.0)

    def test_retry_not_counted_as_rejected(self):
        runs = [_run(supervisor_decision="RETRY")]
        mean, _ = self.obs.compute_ssr(runs)
        self.assertAlmostEqual(mean, 0.0)

    def test_no_decision_success_assumed_accept(self):
        runs = [{"status": "success"}]
        mean, _ = self.obs.compute_ssr(runs)
        self.assertAlmostEqual(mean, 0.0)


# ─────────────────────────────────────────────────────────
# compute_all
# ─────────────────────────────────────────────────────────

class TestComputeAll(TmpLogMixin):

    def test_empty_log_returns_error(self):
        result = self.obs.compute_all()
        self.assertIn("error", result)
        self.assertEqual(result["n"], 0)

    def test_returns_all_5_metrics(self):
        _write_log(self.log_path, [_run()] * 3)
        result = self.obs.compute_all()
        for key in ("SS", "PFI", "RP", "GCR", "SSR"):
            self.assertIn(key, result)

    def test_each_metric_has_mean_std_domain(self):
        _write_log(self.log_path, [_run()] * 3)
        result = self.obs.compute_all()
        for key in ("SS", "PFI", "RP", "GCR", "SSR"):
            self.assertIn("mean", result[key])
            self.assertIn("std", result[key])
            self.assertIn("domain", result[key])

    def test_n_matches_runs(self):
        _write_log(self.log_path, [_run()] * 7)
        result = self.obs.compute_all()
        self.assertEqual(result["n"], 7)

    def test_means_rounded_to_4dp(self):
        _write_log(self.log_path, [_run()] * 3)
        result = self.obs.compute_all()
        for key in ("SS", "PFI", "RP", "GCR", "SSR"):
            m = result[key]["mean"]
            self.assertEqual(m, round(m, 4))

    def test_perfect_runs_ss_equals_1(self):
        _write_log(self.log_path, [_run("success")] * 5)
        result = self.obs.compute_all()
        self.assertAlmostEqual(result["SS"]["mean"], 1.0)

    def test_window_respected(self):
        _write_log(self.log_path, [_run()] * 20)
        result = self.obs.compute_all(window=5)
        self.assertEqual(result["n"], 5)


# ─────────────────────────────────────────────────────────
# detect_anomalies
# ─────────────────────────────────────────────────────────

class TestDetectAnomalies(TmpLogMixin):

    def test_insufficient_data(self):
        _write_log(self.log_path, [_run()])
        alerts = self.obs.detect_anomalies()
        self.assertEqual(len(alerts), 1)
        self.assertIn("Insufficient", alerts[0])

    def test_perfect_runs_no_anomaly(self):
        _write_log(self.log_path, [_run("success", retries=0,
                                        governance_passed=True,
                                        supervisor_decision="ACCEPT")] * 10)
        alerts = self.obs.detect_anomalies()
        self.assertEqual(alerts, ["No anomalies detected"])

    def test_all_errors_triggers_ss_anomaly(self):
        _write_log(self.log_path, [_run("error")] * 10)
        alerts = self.obs.detect_anomalies()
        ss_alerts = [a for a in alerts if "SS=" in a]
        self.assertTrue(len(ss_alerts) >= 1)

    def test_returns_list_of_strings(self):
        _write_log(self.log_path, [_run()] * 5)
        alerts = self.obs.detect_anomalies()
        self.assertIsInstance(alerts, list)
        for a in alerts:
            self.assertIsInstance(a, str)


# ─────────────────────────────────────────────────────────
# compute_all_typed — typed MetricResult interface
# ─────────────────────────────────────────────────────────

class TestComputeAllTyped(TmpLogMixin):

    def test_empty_log_raises(self):
        with self.assertRaises(ValueError):
            self.obs.compute_all_typed()

    def test_returns_dict_of_metric_results(self):
        _write_log(self.log_path, [_run()] * 4)
        result = self.obs.compute_all_typed()
        self.assertIsInstance(result, dict)
        for v in result.values():
            self.assertIsInstance(v, MetricResult)

    def test_all_five_metrics_present(self):
        _write_log(self.log_path, [_run()] * 4)
        result = self.obs.compute_all_typed()
        for key in ("SS", "PFI", "RP", "GCR", "SSR"):
            self.assertIn(key, result)

    def test_metric_result_name_matches_key(self):
        _write_log(self.log_path, [_run()] * 4)
        for key, mr in self.obs.compute_all_typed().items():
            self.assertEqual(mr.name, key)

    def test_n_matches_run_count(self):
        _write_log(self.log_path, [_run()] * 7)
        result = self.obs.compute_all_typed()
        for mr in result.values():
            self.assertEqual(mr.n, 7)

    def test_means_in_range(self):
        _write_log(self.log_path, [_run()] * 5)
        for mr in self.obs.compute_all_typed().values():
            self.assertGreaterEqual(mr.mean, 0.0)
            self.assertLessEqual(mr.mean, 1.0)

    def test_std_nonnegative(self):
        _write_log(self.log_path, [_run()] * 5)
        for mr in self.obs.compute_all_typed().values():
            self.assertGreaterEqual(mr.std, 0.0)

    def test_means_match_compute_all(self):
        """typed and dict interfaces must agree on values."""
        _write_log(self.log_path, [_run()] * 5)
        typed = self.obs.compute_all_typed()
        plain = self.obs.compute_all()
        for key in ("SS", "PFI", "RP", "GCR", "SSR"):
            self.assertAlmostEqual(typed[key].mean, plain[key]["mean"], places=4)

    def test_repr_readable(self):
        _write_log(self.log_path, [_run()] * 3)
        for key, mr in self.obs.compute_all_typed().items():
            r = repr(mr)
            self.assertIn(key, r)
            self.assertIn("±", r)


if __name__ == "__main__":
    unittest.main()
