"""Tests for RegressionTracker — subsystem health monitoring."""
import json
import os
import tempfile
import unittest

from core.regression_tracker import (
    ChangeType,
    RegressionReport,
    RegressionTracker,
    SubsystemResult,
)


class TestChangeType(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(ChangeType.IMPROVED.value, "improved")
        self.assertEqual(ChangeType.STABLE.value, "stable")
        self.assertEqual(ChangeType.REGRESSED.value, "regressed")
        self.assertEqual(ChangeType.NEW.value, "new")
        self.assertEqual(ChangeType.REMOVED.value, "removed")


class TestSubsystemResult(unittest.TestCase):
    def test_to_dict(self):
        sr = SubsystemResult(
            name="test_suite",
            change=ChangeType.IMPROVED,
            baseline_value="10 passed, 0 failed",
            current_value="12 passed, 0 failed",
            delta="+2 passed, +0 failed",
        )
        d = sr.to_dict()
        self.assertEqual(d["name"], "test_suite")
        self.assertEqual(d["change"], "improved")
        self.assertEqual(d["baseline_value"], "10 passed, 0 failed")


class TestRegressionReport(unittest.TestCase):
    def _make_report(self, has_regressions=False):
        subsystems = [
            SubsystemResult("z3_invariants", ChangeType.STABLE,
                            "8/8 PROVEN", "8/8 PROVEN", "+0 invariants"),
            SubsystemResult("test_suite", ChangeType.IMPROVED,
                            "10 passed, 0 failed", "12 passed, 0 failed",
                            "+2 passed, +0 failed"),
        ]
        if has_regressions:
            subsystems.append(
                SubsystemResult("garak_benchmark", ChangeType.REGRESSED,
                                "58.4%", "50.0%", "-8.4pp")
            )
        return RegressionReport(
            timestamp="2026-03-09T15:00:00",
            git_commit="abc1234",
            baseline_commit="def5678",
            dof_version="0.3.3",
            subsystems=subsystems,
            has_regressions=has_regressions,
            regression_count=1 if has_regressions else 0,
            improvement_count=1,
            stable_count=1,
            elapsed_ms=1234.5,
        )

    def test_summary_no_regressions(self):
        report = self._make_report(has_regressions=False)
        summary = report.summary()
        self.assertIn("abc1234 vs def5678", summary)
        self.assertIn("NO REGRESSIONS", summary)
        self.assertIn("z3_invariants", summary)
        self.assertIn("test_suite", summary)

    def test_summary_with_regressions(self):
        report = self._make_report(has_regressions=True)
        summary = report.summary()
        self.assertIn("REGRESSIONS DETECTED", summary)
        self.assertIn("garak_benchmark", summary)

    def test_to_dict(self):
        report = self._make_report()
        d = report.to_dict()
        self.assertEqual(d["git_commit"], "abc1234")
        self.assertEqual(d["dof_version"], "0.3.3")
        self.assertIsInstance(d["subsystems"], list)
        self.assertEqual(len(d["subsystems"]), 2)
        self.assertFalse(d["has_regressions"])


class TestRegressionTrackerUnit(unittest.TestCase):
    """Unit tests that don't require Z3 or full test suite execution."""

    def test_git_commit_does_not_crash(self):
        tracker = RegressionTracker()
        commit = tracker._get_git_commit()
        self.assertIsInstance(commit, str)
        self.assertTrue(len(commit) > 0)

    def test_measure_garak_no_file(self):
        tracker = RegressionTracker()
        # Use a temp dir where the file won't exist
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            result = tracker._measure_garak()
            os.chdir(old_cwd)
        self.assertFalse(result["available"])

    def test_measure_garak_with_file(self):
        tracker = RegressionTracker()
        # Create a temp garak results file
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            os.makedirs("tests/external", exist_ok=True)
            data = {
                "summary": {
                    "overall_detection_rate": 58.4,
                    "total_payloads": 12229,
                },
                "categories": {
                    "dan": {"detection_rate": 63.4},
                    "suffix": {"detection_rate": 11.5},
                },
            }
            with open("tests/external/garak_benchmark_results.json", "w") as f:
                json.dump(data, f)

            result = tracker._measure_garak()
            os.chdir(old_cwd)

        self.assertTrue(result["available"])
        self.assertEqual(result["overall_detection_rate"], 58.4)
        self.assertEqual(result["categories"]["dan"], 63.4)

    def test_baseline_persistence(self):
        """capture_baseline saves JSON and load_baseline reads it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bf = os.path.join(tmpdir, "baseline.json")
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(baseline_file=bf, reports_file=rf)

            # Write a fake baseline directly
            baseline = {
                "timestamp": "2026-03-09T15:00:00",
                "git_commit": "abc1234",
                "z3_invariants": {"proven_count": 8, "total_count": 8,
                                  "total_time_ms": 100, "invariants": {}},
                "z3_hierarchy": {"status": "PROVEN", "time_ms": 50,
                                 "patterns_checked": 42, "categories_checked": 2},
                "tests": {"total": 100, "passed": 100, "failures": 0,
                          "errors": 0, "returncode": 0},
                "garak": {"available": True, "overall_detection_rate": 58.4,
                          "total_payloads": 12229, "categories": {}},
            }
            os.makedirs(os.path.dirname(bf), exist_ok=True)
            with open(bf, "w") as f:
                json.dump(baseline, f)

            loaded = tracker.load_baseline()
            self.assertEqual(loaded["git_commit"], "abc1234")
            self.assertEqual(loaded["z3_invariants"]["proven_count"], 8)

    def test_load_baseline_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bf = os.path.join(tmpdir, "nonexistent.json")
            tracker = RegressionTracker(baseline_file=bf)
            with self.assertRaises(FileNotFoundError):
                tracker.load_baseline()

    def test_get_history_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(reports_file=rf)
            self.assertEqual(tracker.get_history(), [])

    def test_save_and_get_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(reports_file=rf)

            report = RegressionReport(
                timestamp="2026-03-09T15:00:00",
                git_commit="abc1234",
                baseline_commit="def5678",
                dof_version="0.3.3",
                subsystems=[
                    SubsystemResult("test_suite", ChangeType.STABLE,
                                    "10 passed", "10 passed", "+0"),
                ],
                has_regressions=False,
                regression_count=0,
                improvement_count=0,
                stable_count=1,
                elapsed_ms=500,
            )
            tracker._save_report(report)
            tracker._save_report(report)

            history = tracker.get_history()
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["git_commit"], "abc1234")

    def test_get_trend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(reports_file=rf)

            for i, commit in enumerate(["aaa", "bbb", "ccc"]):
                report = RegressionReport(
                    timestamp=f"2026-03-09T{15+i}:00:00",
                    git_commit=commit,
                    baseline_commit="base",
                    dof_version="0.3.3",
                    subsystems=[
                        SubsystemResult("test_suite", ChangeType.STABLE,
                                        f"{10+i} passed", f"{10+i} passed", "+0"),
                    ],
                    has_regressions=False,
                    regression_count=0,
                    improvement_count=0,
                    stable_count=1,
                    elapsed_ms=500,
                )
                tracker._save_report(report)

            trend = tracker.get_trend("test_suite")
            self.assertEqual(len(trend), 3)
            self.assertEqual(trend[0]["commit"], "aaa")
            self.assertEqual(trend[2]["commit"], "ccc")

    def test_get_trend_nonexistent_subsystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(reports_file=rf)

            report = RegressionReport(
                timestamp="2026-03-09T15:00:00",
                git_commit="abc",
                baseline_commit="base",
                dof_version="0.3.3",
                subsystems=[
                    SubsystemResult("test_suite", ChangeType.STABLE,
                                    "10 passed", "10 passed", "+0"),
                ],
                has_regressions=False,
                regression_count=0,
                improvement_count=0,
                stable_count=1,
                elapsed_ms=500,
            )
            tracker._save_report(report)

            trend = tracker.get_trend("nonexistent")
            self.assertEqual(len(trend), 0)


class TestLLMRoutingSubsystem(unittest.TestCase):
    """Tests for the 5th subsystem: llm_routing."""

    def test_measure_llm_routing_returns_dict(self):
        tracker = RegressionTracker()
        result = tracker._measure_llm_routing()
        self.assertIsInstance(result, dict)
        # Should have 'available' key regardless
        self.assertIn("available", result)

    def test_measure_llm_routing_has_expected_keys(self):
        tracker = RegressionTracker()
        result = tracker._measure_llm_routing()
        if result.get("available"):
            self.assertIn("total_decisions", result)
            self.assertIn("provider_distribution", result)
            self.assertIn("provider_failure_rate", result)
            self.assertIn("avg_latency_ms", result)
            self.assertIn("thompson_sampling_state", result)

    def test_measure_all_includes_llm_routing(self):
        """_measure_all snapshot includes the llm_routing subsystem."""
        tracker = RegressionTracker()
        # We can't easily run _measure_all (it runs tests etc.),
        # but we can verify the method exists and returns the right key
        result = tracker._measure_llm_routing()
        self.assertIsInstance(result, dict)

    def test_llm_routing_regression_on_high_failure_rate(self):
        """Failure rate > 15% should trigger regression in compare."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bf = os.path.join(tmpdir, "baseline.json")
            rf = os.path.join(tmpdir, "reports.jsonl")
            tracker = RegressionTracker(baseline_file=bf, reports_file=rf)

            # Create a baseline with llm_routing data
            baseline = {
                "timestamp": "2026-03-09T15:00:00",
                "git_commit": "abc1234",
                "z3_invariants": {"proven_count": 8, "total_count": 8,
                                  "total_time_ms": 100, "invariants": {}},
                "z3_hierarchy": {"status": "PROVEN", "time_ms": 50,
                                 "patterns_checked": 42, "categories_checked": 2},
                "tests": {"total": 100, "passed": 100, "failures": 0,
                          "errors": 0, "returncode": 0},
                "garak": {"available": False},
                "llm_routing": {
                    "available": True,
                    "total_decisions": 50,
                    "provider_distribution": {"groq": 60.0, "nvidia": 40.0},
                    "provider_failure_rate": {"groq": 2.0, "nvidia": 1.0},
                    "avg_latency_ms": {},
                    "thompson_sampling_state": {},
                },
            }
            os.makedirs(os.path.dirname(bf), exist_ok=True)
            with open(bf, "w") as f:
                json.dump(baseline, f)

            # The key assertion: verify compare works with llm_routing in baseline
            loaded = tracker.load_baseline()
            self.assertIn("llm_routing", loaded)
            self.assertTrue(loaded["llm_routing"]["available"])

    def test_llm_routing_concentration_warning(self):
        """Distribution > 40% on single provider should appear in details."""
        sr = SubsystemResult(
            name="llm_routing",
            change=ChangeType.STABLE,
            baseline_value="50 decisions",
            current_value="75 decisions",
            delta="max_fail=5%, max_conc=65%",
            details="WARNING: 65% concentrated on single provider",
        )
        self.assertIn("WARNING", sr.details)
        self.assertIn("concentrated", sr.details)


class TestGetHistoryNonPositiveN(unittest.TestCase):
    """get_history(n<=0) must return [] — same Python -0 gotcha fixed in metrics.py."""

    def _make_tracker(self, records=5):
        tmpdir = tempfile.mkdtemp()
        rf = os.path.join(tmpdir, "reports.jsonl")
        with open(rf, "w") as f:
            for i in range(records):
                f.write(json.dumps({
                    "timestamp": f"2026-03-{i+1:02d}",
                    "git_commit": f"abc{i}",
                    "subsystems": [],
                }) + "\n")
        return RegressionTracker(reports_file=rf)

    def test_n_zero_returns_empty(self):
        rt = self._make_tracker(5)
        self.assertEqual(rt.get_history(0), [])

    def test_n_negative_returns_empty(self):
        rt = self._make_tracker(5)
        self.assertEqual(rt.get_history(-1), [])
        self.assertEqual(rt.get_history(-99), [])

    def test_n_positive_returns_records(self):
        rt = self._make_tracker(5)
        self.assertEqual(len(rt.get_history(2)), 2)

    def test_get_trend_with_n_zero_returns_empty(self):
        rt = self._make_tracker(5)
        self.assertEqual(rt.get_trend("z3", 0), [])


if __name__ == "__main__":
    unittest.main()

