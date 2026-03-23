"""
Tests for core/checkpointing.py — Step-level checkpoint manager.

All tests use a temp CHECKPOINT_DIR to avoid polluting production logs.
Zero LLM, zero network, fully deterministic.
"""

import os
import sys
import time
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.checkpointing as chk_mod
from core.checkpointing import CheckpointManager, StepCheckpoint


# ── Patch CHECKPOINT_DIR to a tempdir for every test ────────────────

class TmpDirMixin(unittest.TestCase):
    """Redirect all JSONL writes to a temporary directory."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = chk_mod.CHECKPOINT_DIR
        chk_mod.CHECKPOINT_DIR = self._tmpdir

    def tearDown(self):
        chk_mod.CHECKPOINT_DIR = self._orig_dir


# ─────────────────────────────────────────────────────────────────────
# StepCheckpoint dataclass
# ─────────────────────────────────────────────────────────────────────

class TestStepCheckpoint(unittest.TestCase):

    def _make(self, **kw):
        defaults = dict(run_id="r1", step_id="s1", agent="agent_a",
                        task_name="task_x")
        defaults.update(kw)
        return StepCheckpoint(**defaults)

    def test_required_fields(self):
        cp = self._make()
        for attr in ("run_id", "step_id", "agent", "task_name",
                     "provider", "status", "input_hash", "output",
                     "error", "start_time", "end_time", "latency_ms", "attempt"):
            self.assertTrue(hasattr(cp, attr), f"Missing: {attr}")

    def test_default_status_pending(self):
        cp = self._make()
        self.assertEqual(cp.status, "pending")

    def test_default_attempt_one(self):
        cp = self._make()
        self.assertEqual(cp.attempt, 1)

    def test_custom_fields(self):
        cp = self._make(provider="groq", status="running", attempt=3)
        self.assertEqual(cp.provider, "groq")
        self.assertEqual(cp.status, "running")
        self.assertEqual(cp.attempt, 3)


# ─────────────────────────────────────────────────────────────────────
# CheckpointManager construction
# ─────────────────────────────────────────────────────────────────────

class TestConstruction(TmpDirMixin):

    def test_run_id_auto_generated(self):
        mgr = CheckpointManager()
        self.assertTrue(mgr.run_id.startswith("run_"))

    def test_explicit_run_id(self):
        mgr = CheckpointManager(run_id="my_run")
        self.assertEqual(mgr.run_id, "my_run")

    def test_checkpoint_dir_created(self):
        CheckpointManager(run_id="init_test")
        self.assertTrue(os.path.isdir(self._tmpdir))

    def test_jsonl_file_path(self):
        mgr = CheckpointManager(run_id="abc")
        self.assertTrue(mgr._file.endswith("abc.jsonl"))


# ─────────────────────────────────────────────────────────────────────
# _hash_input
# ─────────────────────────────────────────────────────────────────────

class TestHashInput(unittest.TestCase):

    def test_returns_16_char_hex(self):
        h = CheckpointManager._hash_input("hello world")
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_deterministic(self):
        h1 = CheckpointManager._hash_input("same text")
        h2 = CheckpointManager._hash_input("same text")
        self.assertEqual(h1, h2)

    def test_different_inputs_differ(self):
        h1 = CheckpointManager._hash_input("text A")
        h2 = CheckpointManager._hash_input("text B")
        self.assertNotEqual(h1, h2)

    def test_empty_input(self):
        h = CheckpointManager._hash_input("")
        self.assertEqual(len(h), 16)


# ─────────────────────────────────────────────────────────────────────
# start_step
# ─────────────────────────────────────────────────────────────────────

class TestStartStep(TmpDirMixin):

    def setUp(self):
        super().setUp()
        self.mgr = CheckpointManager(run_id="run_start")

    def test_returns_step_checkpoint(self):
        cp = self.mgr.start_step("s1", "agent_a", "task_x")
        self.assertIsInstance(cp, StepCheckpoint)

    def test_status_is_running(self):
        cp = self.mgr.start_step("s1", "agent_a", "task_x")
        self.assertEqual(cp.status, "running")

    def test_step_stored_in_memory(self):
        self.mgr.start_step("s1", "agent_a", "task_x")
        self.assertIn("s1", self.mgr._steps)

    def test_run_id_propagated(self):
        cp = self.mgr.start_step("s1", "agent_a", "task_x")
        self.assertEqual(cp.run_id, "run_start")

    def test_input_hash_computed(self):
        cp = self.mgr.start_step("s1", "agent_a", "task_x",
                                  input_text="some input")
        self.assertEqual(len(cp.input_hash), 16)

    def test_provider_stored(self):
        cp = self.mgr.start_step("s1", "agent_a", "task_x", provider="groq")
        self.assertEqual(cp.provider, "groq")

    def test_persisted_to_disk(self):
        self.mgr.start_step("s1", "agent_a", "task_x")
        self.assertTrue(os.path.exists(self.mgr._file))


# ─────────────────────────────────────────────────────────────────────
# complete_step
# ─────────────────────────────────────────────────────────────────────

class TestCompleteStep(TmpDirMixin):

    def setUp(self):
        super().setUp()
        self.mgr = CheckpointManager(run_id="run_complete")
        self.mgr.start_step("s1", "agent_a", "task_x", input_text="q")

    def test_returns_checkpoint(self):
        cp = self.mgr.complete_step("s1", output="done")
        self.assertIsInstance(cp, StepCheckpoint)

    def test_status_completed(self):
        cp = self.mgr.complete_step("s1")
        self.assertEqual(cp.status, "completed")

    def test_output_stored(self):
        cp = self.mgr.complete_step("s1", output="result text")
        self.assertEqual(cp.output, "result text")

    def test_output_truncated_at_5000(self):
        long_output = "x" * 6000
        cp = self.mgr.complete_step("s1", output=long_output)
        self.assertEqual(len(cp.output), 5000)

    def test_latency_positive(self):
        cp = self.mgr.complete_step("s1")
        self.assertGreater(cp.latency_ms, 0)

    def test_end_time_set(self):
        cp = self.mgr.complete_step("s1")
        self.assertGreater(cp.end_time, 0)

    def test_unknown_step_returns_none(self):
        result = self.mgr.complete_step("nonexistent")
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────
# fail_step
# ─────────────────────────────────────────────────────────────────────

class TestFailStep(TmpDirMixin):

    def setUp(self):
        super().setUp()
        self.mgr = CheckpointManager(run_id="run_fail")
        self.mgr.start_step("s1", "agent_a", "task_x")

    def test_returns_checkpoint(self):
        cp = self.mgr.fail_step("s1", error="timeout")
        self.assertIsInstance(cp, StepCheckpoint)

    def test_status_failed(self):
        cp = self.mgr.fail_step("s1")
        self.assertEqual(cp.status, "failed")

    def test_error_stored(self):
        cp = self.mgr.fail_step("s1", error="RateLimitError")
        self.assertEqual(cp.error, "RateLimitError")

    def test_error_truncated_at_500(self):
        long_err = "e" * 600
        cp = self.mgr.fail_step("s1", error=long_err)
        self.assertEqual(len(cp.error), 500)

    def test_latency_positive(self):
        cp = self.mgr.fail_step("s1")
        self.assertGreater(cp.latency_ms, 0)

    def test_unknown_step_returns_none(self):
        result = self.mgr.fail_step("nonexistent")
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────
# get_failed_steps / get_completed_steps
# ─────────────────────────────────────────────────────────────────────

class TestQuerySteps(TmpDirMixin):

    def setUp(self):
        super().setUp()
        self.mgr = CheckpointManager(run_id="run_query")
        self.mgr.start_step("ok",  "a", "t")
        self.mgr.start_step("bad", "b", "t")
        self.mgr.start_step("run", "c", "t")
        self.mgr.complete_step("ok")
        self.mgr.fail_step("bad", error="boom")
        # "run" stays in running state

    def test_get_failed_steps(self):
        failed = self.mgr.get_failed_steps()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].step_id, "bad")

    def test_get_completed_steps(self):
        completed = self.mgr.get_completed_steps()
        self.assertEqual(completed, ["ok"])

    def test_failed_returns_list_of_checkpoints(self):
        failed = self.mgr.get_failed_steps()
        for f in failed:
            self.assertIsInstance(f, StepCheckpoint)

    def test_no_failures_empty_list(self):
        mgr = CheckpointManager(run_id="clean_run")
        mgr.start_step("s1", "a", "t")
        mgr.complete_step("s1")
        self.assertEqual(mgr.get_failed_steps(), [])


# ─────────────────────────────────────────────────────────────────────
# get_summary
# ─────────────────────────────────────────────────────────────────────

class TestGetSummary(TmpDirMixin):

    def setUp(self):
        super().setUp()
        self.mgr = CheckpointManager(run_id="run_summary")
        self.mgr.start_step("s1", "a", "t1")
        self.mgr.start_step("s2", "b", "t2")
        self.mgr.start_step("s3", "c", "t3")
        self.mgr.complete_step("s1", output="ok")
        self.mgr.fail_step("s2", error="err")

    def test_summary_keys(self):
        s = self.mgr.get_summary()
        for key in ("run_id", "total_steps", "completed", "failed",
                    "running", "total_latency_ms", "steps"):
            self.assertIn(key, s)

    def test_run_id_in_summary(self):
        s = self.mgr.get_summary()
        self.assertEqual(s["run_id"], "run_summary")

    def test_total_steps(self):
        s = self.mgr.get_summary()
        self.assertEqual(s["total_steps"], 3)

    def test_completed_count(self):
        s = self.mgr.get_summary()
        self.assertEqual(s["completed"], 1)

    def test_failed_count(self):
        s = self.mgr.get_summary()
        self.assertEqual(s["failed"], 1)

    def test_running_count(self):
        s = self.mgr.get_summary()
        self.assertEqual(s["running"], 1)

    def test_steps_list_length(self):
        s = self.mgr.get_summary()
        self.assertEqual(len(s["steps"]), 3)

    def test_steps_have_required_keys(self):
        s = self.mgr.get_summary()
        for step in s["steps"]:
            for k in ("step_id", "agent", "provider", "status",
                      "latency_ms", "attempt"):
                self.assertIn(k, step)

    def test_total_latency_positive(self):
        s = self.mgr.get_summary()
        self.assertGreaterEqual(s["total_latency_ms"], 0)

    def test_empty_manager_summary(self):
        mgr = CheckpointManager(run_id="empty")
        s = mgr.get_summary()
        self.assertEqual(s["total_steps"], 0)
        self.assertEqual(s["completed"], 0)


# ─────────────────────────────────────────────────────────────────────
# load_run  — JSONL persistence round-trip
# ─────────────────────────────────────────────────────────────────────

class TestLoadRun(TmpDirMixin):

    def test_load_nonexistent_run_is_empty(self):
        mgr = CheckpointManager.load_run("ghost_run")
        self.assertEqual(len(mgr._steps), 0)

    def test_completed_step_survives_reload(self):
        mgr1 = CheckpointManager(run_id="persist_run")
        mgr1.start_step("s1", "agent_a", "task_x", input_text="hello")
        mgr1.complete_step("s1", output="result")

        mgr2 = CheckpointManager.load_run("persist_run")
        self.assertIn("s1", mgr2._steps)
        # load_run replays JSONL — last record per step_id wins
        self.assertEqual(mgr2._steps["s1"].status, "completed")

    def test_failed_step_survives_reload(self):
        mgr1 = CheckpointManager(run_id="fail_persist")
        mgr1.start_step("s1", "agent_a", "task_x")
        mgr1.fail_step("s1", error="crash")

        mgr2 = CheckpointManager.load_run("fail_persist")
        self.assertIn("s1", mgr2._steps)
        self.assertEqual(mgr2._steps["s1"].status, "failed")

    def test_multiple_steps_all_loaded(self):
        mgr1 = CheckpointManager(run_id="multi_persist")
        for i in range(3):
            mgr1.start_step(f"s{i}", "agent", f"task{i}")
            mgr1.complete_step(f"s{i}")

        mgr2 = CheckpointManager.load_run("multi_persist")
        self.assertEqual(len(mgr2._steps), 3)

    def test_loaded_run_id_correct(self):
        mgr1 = CheckpointManager(run_id="id_check")
        mgr1.start_step("s1", "a", "t")

        mgr2 = CheckpointManager.load_run("id_check")
        self.assertEqual(mgr2.run_id, "id_check")


if __name__ == "__main__":
    unittest.main()
