"""Tests for core/experiment.py — ExperimentRecord, ExperimentDataset, SimulatedCrew, run_experiment."""

import csv
import json
import os
import tempfile
import unittest
import uuid

import core.experiment as exp_mod
from core.experiment import (
    ExperimentDataset,
    ExperimentRecord,
    SimulatedCrew,
    _hash,
    run_experiment,
    run_parametric_sweep,
)


# ── Isolation mixin ──────────────────────────────────────

class TmpExperimentMixin(unittest.TestCase):
    """Redirect EXPERIMENTS_DIR to a temp directory per test."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = exp_mod.EXPERIMENTS_DIR
        exp_mod.EXPERIMENTS_DIR = self._tmpdir

    def tearDown(self):
        exp_mod.EXPERIMENTS_DIR = self._orig_dir


# ─────────────────────────────────────────────────────────
# ExperimentRecord
# ─────────────────────────────────────────────────────────

class TestExperimentRecord(unittest.TestCase):

    def test_auto_uuid(self):
        r = ExperimentRecord()
        # Must be parseable as UUID
        parsed = uuid.UUID(r.experiment_id)
        self.assertEqual(str(parsed), r.experiment_id)

    def test_two_records_have_different_ids(self):
        r1 = ExperimentRecord()
        r2 = ExperimentRecord()
        self.assertNotEqual(r1.experiment_id, r2.experiment_id)

    def test_default_fields(self):
        r = ExperimentRecord()
        self.assertEqual(r.hypothesis, "")
        self.assertEqual(r.variables, {})
        self.assertEqual(r.run_id, "")
        self.assertEqual(r.metrics, {})
        self.assertEqual(r.status, "")

    def test_to_dict_contains_all_fields(self):
        r = ExperimentRecord(hypothesis="h1", status="ok")
        d = r.to_dict()
        for key in ("experiment_id", "hypothesis", "variables", "run_id",
                     "metrics", "raw_trace_path", "timestamp", "status"):
            self.assertIn(key, d)

    def test_to_dict_values_match(self):
        r = ExperimentRecord(hypothesis="test_hyp", status="error")
        d = r.to_dict()
        self.assertEqual(d["hypothesis"], "test_hyp")
        self.assertEqual(d["status"], "error")

    def test_custom_metrics(self):
        r = ExperimentRecord(metrics={"stability_score": 0.95})
        self.assertEqual(r.metrics["stability_score"], 0.95)


# ─────────────────────────────────────────────────────────
# ExperimentDataset
# ─────────────────────────────────────────────────────────

class TestExperimentDataset(TmpExperimentMixin):

    def _make_dataset(self):
        return ExperimentDataset()

    def test_schema_created_on_init(self):
        self._make_dataset()
        schema_path = os.path.join(self._tmpdir, "schema.json")
        self.assertTrue(os.path.exists(schema_path))

    def test_schema_is_valid_json(self):
        self._make_dataset()
        with open(os.path.join(self._tmpdir, "schema.json")) as f:
            data = json.load(f)
        self.assertIn("properties", data)
        self.assertIn("required", data)

    def test_schema_not_overwritten_on_second_init(self):
        ds = self._make_dataset()
        schema_path = os.path.join(self._tmpdir, "schema.json")
        mtime1 = os.path.getmtime(schema_path)
        self._make_dataset()
        mtime2 = os.path.getmtime(schema_path)
        self.assertEqual(mtime1, mtime2)

    def test_load_all_empty(self):
        ds = self._make_dataset()
        self.assertEqual(ds.load_all(), [])

    def test_append_and_load_all(self):
        ds = self._make_dataset()
        r = ExperimentRecord(hypothesis="h1", status="ok")
        ds.append(r)
        records = ds.load_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["hypothesis"], "h1")
        self.assertEqual(records[0]["status"], "ok")

    def test_append_multiple(self):
        ds = self._make_dataset()
        for i in range(5):
            ds.append(ExperimentRecord(hypothesis=f"h{i}"))
        self.assertEqual(len(ds.load_all()), 5)

    def test_append_preserves_order(self):
        ds = self._make_dataset()
        for i in range(3):
            ds.append(ExperimentRecord(hypothesis=f"h{i}"))
        records = ds.load_all()
        for i, r in enumerate(records):
            self.assertEqual(r["hypothesis"], f"h{i}")

    def test_each_line_is_valid_json(self):
        ds = self._make_dataset()
        ds.append(ExperimentRecord(hypothesis="test"))
        path = os.path.join(self._tmpdir, "run_dataset.jsonl")
        with open(path) as f:
            for line in f:
                json.loads(line.strip())  # must not raise

    def test_load_by_hypothesis_filters(self):
        ds = self._make_dataset()
        ds.append(ExperimentRecord(hypothesis="alpha"))
        ds.append(ExperimentRecord(hypothesis="beta"))
        ds.append(ExperimentRecord(hypothesis="alpha"))
        results = ds.load_by_hypothesis("alpha")
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r["hypothesis"], "alpha")

    def test_load_by_hypothesis_no_match(self):
        ds = self._make_dataset()
        ds.append(ExperimentRecord(hypothesis="alpha"))
        self.assertEqual(ds.load_by_hypothesis("gamma"), [])

    def test_dataset_path_inside_tmpdir(self):
        ds = self._make_dataset()
        self.assertTrue(ds._dataset_path.startswith(self._tmpdir))


# ─────────────────────────────────────────────────────────
# SimulatedCrew
# ─────────────────────────────────────────────────────────

class TestSimulatedCrew(unittest.TestCase):

    def test_kickoff_returns_result_with_raw(self):
        crew = SimulatedCrew()
        result = crew.kickoff()
        self.assertTrue(hasattr(result, "raw"))

    def test_raw_contains_agent_names(self):
        crew = SimulatedCrew()
        result = crew.kickoff()
        self.assertIn("researcher", result.raw)
        self.assertIn("strategist", result.raw)
        self.assertIn("qa_reviewer", result.raw)

    def test_no_fail_step_never_raises(self):
        crew = SimulatedCrew(fail_step=-1)
        for _ in range(5):
            result = crew.kickoff()
            self.assertIsNotNone(result.raw)

    def test_fail_step_raises_on_first_call(self):
        crew = SimulatedCrew(fail_step=0)
        with self.assertRaises(RuntimeError) as ctx:
            crew.kickoff()
        self.assertIn("rate_limit_exceeded", str(ctx.exception))

    def test_fail_step_succeeds_on_second_call(self):
        crew = SimulatedCrew(fail_step=0)
        with self.assertRaises(RuntimeError):
            crew.kickoff()
        # Second call must succeed
        result = crew.kickoff()
        self.assertTrue(hasattr(result, "raw"))

    def test_custom_steps(self):
        steps = [{"agent": "alpha", "provider": "groq", "latency_ms": 100}]
        crew = SimulatedCrew(steps=steps)
        result = crew.kickoff()
        self.assertIn("alpha", result.raw)

    def test_call_count_increments(self):
        crew = SimulatedCrew()
        crew.kickoff()
        crew.kickoff()
        self.assertEqual(crew._call_count, 2)


# ─────────────────────────────────────────────────────────
# _hash utility
# ─────────────────────────────────────────────────────────

class TestHash(unittest.TestCase):

    def test_returns_16_char_hex(self):
        h = _hash("hello")
        self.assertEqual(len(h), 16)
        int(h, 16)  # must be valid hex

    def test_deterministic(self):
        self.assertEqual(_hash("abc"), _hash("abc"))

    def test_different_inputs_differ(self):
        self.assertNotEqual(_hash("a"), _hash("b"))

    def test_empty_string(self):
        h = _hash("")
        self.assertEqual(len(h), 16)


# ─────────────────────────────────────────────────────────
# run_experiment — smoke tests (small n_runs)
# ─────────────────────────────────────────────────────────

class TestRunExperiment(TmpExperimentMixin):

    def _run(self, **kwargs):
        defaults = dict(
            n_runs=2,
            prompt="Analyze security posture of this system.",
            mode="research",
            hypothesis="smoke_test",
            verbose=False,
        )
        defaults.update(kwargs)
        return run_experiment(**defaults)

    def test_returns_dict(self):
        result = self._run()
        self.assertIsInstance(result, dict)

    def test_result_keys(self):
        result = self._run()
        for key in ("experiment_id", "hypothesis", "n_runs", "runs", "aggregated"):
            self.assertIn(key, result)

    def test_experiment_id_is_uuid(self):
        result = self._run()
        uuid.UUID(result["experiment_id"])  # must not raise

    def test_runs_count_matches_n(self):
        result = self._run(n_runs=3)
        self.assertEqual(len(result["runs"]), 3)

    def test_hypothesis_preserved(self):
        result = self._run(hypothesis="my_hypothesis")
        self.assertEqual(result["hypothesis"], "my_hypothesis")

    def test_aggregated_has_stability_score(self):
        result = self._run()
        self.assertIn("stability_score", result["aggregated"])

    def test_aggregated_stability_score_has_mean(self):
        result = self._run()
        ss = result["aggregated"]["stability_score"]
        self.assertIn("mean", ss)
        self.assertIn("stddev", ss)

    def test_dataset_written(self):
        self._run(n_runs=2)
        path = os.path.join(self._tmpdir, "run_dataset.jsonl")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_failure_rate_zero_no_failures(self):
        result = self._run(n_runs=4, failure_rate=0.0)
        statuses = [r["status"] for r in result["runs"]]
        self.assertTrue(all(s in ("ok", "escalated") for s in statuses))

    def test_failure_rate_one_all_retry(self):
        """100% failure rate → all runs hit retry path, still complete."""
        result = self._run(n_runs=2, failure_rate=1.0, fail_step=0)
        self.assertEqual(len(result["runs"]), 2)

    def test_deterministic_flag_accepted(self):
        result = self._run(deterministic=True)
        self.assertIn("runs", result)


# ─────────────────────────────────────────────────────────
# run_parametric_sweep — smoke test
# ─────────────────────────────────────────────────────────

class TestRunParametricSweep(TmpExperimentMixin):

    def test_sweep_returns_dict(self):
        result = run_parametric_sweep(
            failure_rates=[0.0, 0.5],
            n_runs=2,
            prompt="Security analysis.",
            verbose=False,
            csv_path=os.path.join(self._tmpdir, "sweep.csv"),
        )
        self.assertIsInstance(result, dict)

    def test_sweep_result_keys(self):
        result = run_parametric_sweep(
            failure_rates=[0.0],
            n_runs=2,
            prompt="Analysis.",
            verbose=False,
            csv_path=os.path.join(self._tmpdir, "sweep.csv"),
        )
        for key in ("sweep_results", "csv_path", "failure_rates", "n_runs_per_rate"):
            self.assertIn(key, result)

    def test_sweep_results_count(self):
        rates = [0.0, 0.3, 1.0]
        result = run_parametric_sweep(
            failure_rates=rates,
            n_runs=2,
            prompt="Test.",
            verbose=False,
            csv_path=os.path.join(self._tmpdir, "sweep.csv"),
        )
        self.assertEqual(len(result["sweep_results"]), len(rates))

    def test_csv_written(self):
        csv_path = os.path.join(self._tmpdir, "sweep.csv")
        run_parametric_sweep(
            failure_rates=[0.0, 1.0],
            n_runs=2,
            prompt="Test.",
            verbose=False,
            csv_path=csv_path,
        )
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)

    def test_csv_has_failure_rate_column(self):
        csv_path = os.path.join(self._tmpdir, "sweep.csv")
        run_parametric_sweep(
            failure_rates=[0.25],
            n_runs=2,
            prompt="Test.",
            verbose=False,
            csv_path=csv_path,
        )
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        self.assertIn("failure_rate", row)
        self.assertAlmostEqual(float(row["failure_rate"]), 0.25, places=2)


if __name__ == "__main__":
    unittest.main()
