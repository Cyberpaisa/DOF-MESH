"""
Tests for core/metrics.py — Structured JSONL metrics logger.

Uses temp directories and singleton reset to avoid polluting production logs.
All tests are deterministic, zero LLM, zero network.
"""

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.metrics as metrics_mod
from core.metrics import MetricsLogger


# ── Helpers ─────────────────────────────────────────────────────────

def make_logger() -> tuple[MetricsLogger, str]:
    """Return a fresh MetricsLogger instance backed by a temp directory."""
    tmpdir = tempfile.mkdtemp()
    # Reset singleton so we get a clean instance
    MetricsLogger._instance = None
    metrics_mod.METRICS_DIR = tmpdir
    ml = MetricsLogger()
    ml._file = os.path.join(tmpdir, "events.jsonl")
    return ml, tmpdir


def read_entries(ml: MetricsLogger) -> list[dict]:
    """Read all JSONL entries from the logger's file."""
    if not os.path.exists(ml._file):
        return []
    with open(ml._file) as f:
        return [json.loads(line) for line in f if line.strip()]


# ─────────────────────────────────────────────────────────────────────
# Singleton behaviour
# ─────────────────────────────────────────────────────────────────────

class TestSingleton(unittest.TestCase):

    def setUp(self):
        MetricsLogger._instance = None
        self._tmpdir = tempfile.mkdtemp()
        metrics_mod.METRICS_DIR = self._tmpdir

    def test_same_instance_returned(self):
        a = MetricsLogger()
        b = MetricsLogger()
        self.assertIs(a, b)

    def test_initialized_once(self):
        ml = MetricsLogger()
        self.assertTrue(ml._initialized)


# ─────────────────────────────────────────────────────────────────────
# log() — base method
# ─────────────────────────────────────────────────────────────────────

class TestLog(unittest.TestCase):

    def setUp(self):
        self.ml, self.tmpdir = make_logger()

    def test_log_creates_file(self):
        self.ml.log("test_event")
        self.assertTrue(os.path.exists(self.ml._file))

    def test_log_writes_valid_json(self):
        self.ml.log("test_event")
        entries = read_entries(self.ml)
        self.assertEqual(len(entries), 1)

    def test_log_entry_has_required_fields(self):
        self.ml.log("my_event", run_id="r1", agent="a1",
                    provider="groq", latency_ms=42.5, status="ok")
        e = read_entries(self.ml)[0]
        for field in ("ts", "iso", "event", "run_id", "agent",
                      "provider", "latency_ms", "status"):
            self.assertIn(field, e, f"Missing field: {field}")

    def test_log_event_name_stored(self):
        self.ml.log("crew_start")
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "crew_start")

    def test_log_latency_rounded(self):
        self.ml.log("x", latency_ms=42.567)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["latency_ms"], 42.6)

    def test_log_meta_included_when_provided(self):
        self.ml.log("x", meta={"key": "value"})
        e = read_entries(self.ml)[0]
        self.assertIn("meta", e)
        self.assertEqual(e["meta"]["key"], "value")

    def test_log_meta_omitted_when_none(self):
        self.ml.log("x", meta=None)
        e = read_entries(self.ml)[0]
        self.assertNotIn("meta", e)

    def test_log_timestamp_is_recent(self):
        before = time.time()
        self.ml.log("x")
        after = time.time()
        e = read_entries(self.ml)[0]
        self.assertGreaterEqual(e["ts"], before)
        self.assertLessEqual(e["ts"], after)

    def test_multiple_events_appended(self):
        for i in range(5):
            self.ml.log(f"event_{i}")
        self.assertEqual(len(read_entries(self.ml)), 5)


# ─────────────────────────────────────────────────────────────────────
# Convenience log methods
# ─────────────────────────────────────────────────────────────────────

class TestConvenienceMethods(unittest.TestCase):

    def setUp(self):
        self.ml, _ = make_logger()

    def test_log_crew_start(self):
        self.ml.log_crew_start("r1", "my_crew", input_text="hello world")
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "crew_start")
        self.assertEqual(e["run_id"], "r1")
        self.assertEqual(e["meta"]["crew"], "my_crew")
        self.assertEqual(e["meta"]["input_len"], 11)

    def test_log_crew_start_preview_truncated(self):
        self.ml.log_crew_start("r1", "c", input_text="x" * 300)
        e = read_entries(self.ml)[0]
        self.assertEqual(len(e["meta"]["input_preview"]), 200)

    def test_log_crew_end(self):
        self.ml.log_crew_end("r1", "my_crew", status="ok",
                             total_ms=1234.5, output_len=42)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "crew_end")
        self.assertEqual(e["status"], "ok")
        self.assertEqual(e["latency_ms"], 1234.5)
        self.assertEqual(e["meta"]["output_len"], 42)

    def test_log_agent_step(self):
        self.ml.log_agent_step("r1", "agent_a", "groq", 99.9, "ok", attempt=2)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "agent_step")
        self.assertEqual(e["agent"], "agent_a")
        self.assertEqual(e["provider"], "groq")
        self.assertEqual(e["meta"]["attempt"], 2)

    def test_log_provider_event(self):
        self.ml.log_provider_event("cerebras", "exhausted",
                                   error="rate limit", ttl=60.0)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "provider_exhausted")
        self.assertEqual(e["provider"], "cerebras")
        self.assertEqual(e["meta"]["ttl_seconds"], 60.0)

    def test_log_provider_error_truncated(self):
        self.ml.log_provider_event("p", "exhausted", error="x" * 300)
        e = read_entries(self.ml)[0]
        self.assertLessEqual(len(e["meta"]["error"]), 200)

    def test_log_governance_pass(self):
        self.ml.log_governance("r1", passed=True, score=9.1)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "governance_check")
        self.assertEqual(e["status"], "pass")
        self.assertAlmostEqual(e["meta"]["score"], 9.1)

    def test_log_governance_fail(self):
        self.ml.log_governance("r1", passed=False, score=3.0,
                               violations=["NO_HALLUCINATION"])
        e = read_entries(self.ml)[0]
        self.assertEqual(e["status"], "fail")
        self.assertIn("NO_HALLUCINATION", e["meta"]["violations"])

    def test_log_governance_violations_default_empty(self):
        self.ml.log_governance("r1", passed=True, score=8.0)
        e = read_entries(self.ml)[0]
        self.assertEqual(e["meta"]["violations"], [])

    def test_log_supervisor(self):
        self.ml.log_supervisor("r1", "approve", {"quality": 0.9, "safety": 1.0})
        e = read_entries(self.ml)[0]
        self.assertEqual(e["event"], "supervisor_eval")
        self.assertEqual(e["status"], "approve")
        self.assertAlmostEqual(e["meta"]["quality"], 0.9)


# ─────────────────────────────────────────────────────────────────────
# get_recent()
# ─────────────────────────────────────────────────────────────────────

class TestGetRecent(unittest.TestCase):

    def setUp(self):
        self.ml, _ = make_logger()

    def test_empty_when_no_file(self):
        result = self.ml.get_recent()
        self.assertEqual(result, [])

    def test_returns_all_when_fewer_than_n(self):
        for i in range(5):
            self.ml.log(f"e{i}")
        result = self.ml.get_recent(n=50)
        self.assertEqual(len(result), 5)

    def test_respects_n_limit(self):
        for i in range(20):
            self.ml.log(f"e{i}")
        result = self.ml.get_recent(n=10)
        self.assertEqual(len(result), 10)

    def test_returns_last_n_events(self):
        for i in range(10):
            self.ml.log(f"event_{i}")
        result = self.ml.get_recent(n=3)
        # Last 3 logged events should be event_7, event_8, event_9
        event_names = [r["event"] for r in result]
        self.assertIn("event_9", event_names)
        self.assertNotIn("event_0", event_names)

    def test_returns_list_of_dicts(self):
        self.ml.log("x")
        result = self.ml.get_recent()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

    def test_n_zero_returns_empty(self):
        # Python gotcha: list[-0:] == list[0:] returns everything;
        # get_recent(0) must explicitly guard and return [].
        for i in range(5):
            self.ml.log(f"e{i}")
        self.assertEqual(self.ml.get_recent(0), [])

    def test_n_negative_returns_empty(self):
        for i in range(5):
            self.ml.log(f"e{i}")
        self.assertEqual(self.ml.get_recent(-1), [])
        self.assertEqual(self.ml.get_recent(-99), [])


# ─────────────────────────────────────────────────────────────────────
# get_stats()
# ─────────────────────────────────────────────────────────────────────

class TestGetStats(unittest.TestCase):

    def setUp(self):
        self.ml, _ = make_logger()

    def test_empty_stats_when_no_events(self):
        stats = self.ml.get_stats()
        self.assertEqual(stats["total_events"], 0)

    def test_crews_completed_counted(self):
        self.ml.log_crew_end("r1", "c", status="ok", total_ms=100)
        self.ml.log_crew_end("r2", "c", status="ok", total_ms=200)
        stats = self.ml.get_stats()
        self.assertEqual(stats["crews_completed"], 2)

    def test_crews_failed_counted(self):
        self.ml.log_crew_end("r1", "c", status="error")
        stats = self.ml.get_stats()
        self.assertEqual(stats["crews_failed"], 1)
        self.assertEqual(stats["crews_completed"], 0)

    def test_avg_crew_latency(self):
        self.ml.log_crew_end("r1", "c", status="ok", total_ms=100)
        self.ml.log_crew_end("r2", "c", status="ok", total_ms=300)
        stats = self.ml.get_stats()
        self.assertAlmostEqual(stats["avg_crew_latency_ms"], 200.0, delta=1)

    def test_total_agent_steps(self):
        self.ml.log_agent_step("r1", "a", "groq", 50, "ok")
        self.ml.log_agent_step("r1", "b", "groq", 80, "ok")
        stats = self.ml.get_stats()
        self.assertEqual(stats["total_agent_steps"], 2)

    def test_required_stat_keys(self):
        self.ml.log("x")
        stats = self.ml.get_stats()
        for key in ("total_events", "crews_completed", "crews_failed",
                    "avg_crew_latency_ms", "total_agent_steps",
                    "provider_exhaustions"):
            self.assertIn(key, stats)

    def test_total_events_count(self):
        for _ in range(7):
            self.ml.log("x")
        stats = self.ml.get_stats()
        self.assertEqual(stats["total_events"], 7)


# ─────────────────────────────────────────────────────────────────────
# _rotate_if_needed()
# ─────────────────────────────────────────────────────────────────────

class TestRotation(unittest.TestCase):

    def setUp(self):
        self.ml, self.tmpdir = make_logger()

    def test_no_rotation_when_file_absent(self):
        # Should not raise
        self.ml._rotate_if_needed()

    def test_no_rotation_below_threshold(self):
        self.ml.log("small event")
        before = self.ml._file
        self.ml._rotate_if_needed()
        self.assertTrue(os.path.exists(before))  # file unchanged

    def test_rotation_renames_file_when_oversized(self):
        # Write a fake oversized file
        with open(self.ml._file, "wb") as f:
            f.write(b"x" * (metrics_mod.MAX_FILE_SIZE + 1))

        self.ml._rotate_if_needed()

        # Original file should be gone (renamed)
        self.assertFalse(os.path.exists(self.ml._file))

        # A rotated file should exist in tmpdir
        rotated = [f for f in os.listdir(self.tmpdir)
                   if "events.jsonl." in f]
        self.assertEqual(len(rotated), 1)


if __name__ == "__main__":
    unittest.main()
