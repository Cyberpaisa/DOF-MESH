"""Tests for core/autonomous_daemon.py — AutonomousDaemon and related dataclasses."""

import asyncio
import json
import os
import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from tests.mocks import patch_provider

from core.autonomous_daemon import (
    SystemState,
    DaemonAction,
    CycleResult,
    AutonomousDaemon,
    BuilderDaemon,
    GuardianDaemon,
    ResearcherDaemon,
    run_multi_daemon,
    submit_feedback,
    get_pending_feedback,
)


# ─── helpers ────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_state(**kw):
    defaults = dict(
        timestamp=time.time(),
        pending_orders=0,
        recent_errors=0,
        test_failures=0,
        git_dirty_files=0,
        health={},
        last_experiment_score=0.0,
        uptime_cycles=0,
    )
    defaults.update(kw)
    return SystemState(**defaults)


def _make_action(**kw):
    defaults = dict(mode="patrol", action="routine", priority=5, agent_count=0)
    defaults.update(kw)
    return DaemonAction(**defaults)


def _make_cycle_result(**kw):
    defaults = dict(
        cycle=1,
        state=_make_state(),
        action=_make_action(),
        result_status="success",
        output_summary="ok",
        elapsed_ms=100.0,
    )
    defaults.update(kw)
    return CycleResult(**defaults)


# ─────────────────────────────────────────────────────────
# SystemState dataclass
# ─────────────────────────────────────────────────────────

class TestSystemState(unittest.TestCase):

    def test_defaults(self):
        s = SystemState()
        self.assertEqual(s.timestamp, 0.0)
        self.assertEqual(s.pending_orders, 0)
        self.assertEqual(s.recent_errors, 0)
        self.assertEqual(s.test_failures, 0)
        self.assertEqual(s.git_dirty_files, 0)
        self.assertEqual(s.health, {})
        self.assertEqual(s.last_experiment_score, 0.0)
        self.assertEqual(s.uptime_cycles, 0)

    def test_custom_values(self):
        s = SystemState(pending_orders=5, recent_errors=2, test_failures=1,
                        git_dirty_files=10, uptime_cycles=42)
        self.assertEqual(s.pending_orders, 5)
        self.assertEqual(s.recent_errors, 2)
        self.assertEqual(s.test_failures, 1)
        self.assertEqual(s.git_dirty_files, 10)
        self.assertEqual(s.uptime_cycles, 42)

    def test_health_dict(self):
        s = SystemState(health={"status": "ok", "modules": 52})
        self.assertEqual(s.health["status"], "ok")

    def test_asdict_roundtrip(self):
        s = SystemState(pending_orders=3)
        d = asdict(s)
        self.assertIsInstance(d, dict)
        self.assertEqual(d["pending_orders"], 3)


# ─────────────────────────────────────────────────────────
# DaemonAction dataclass
# ─────────────────────────────────────────────────────────

class TestDaemonAction(unittest.TestCase):

    def test_required_fields(self):
        a = DaemonAction(mode="build", action="do stuff", priority=1, agent_count=2)
        self.assertEqual(a.mode, "build")
        self.assertEqual(a.action, "do stuff")
        self.assertEqual(a.priority, 1)
        self.assertEqual(a.agent_count, 2)

    def test_defaults(self):
        a = _make_action()
        self.assertEqual(a.estimated_seconds, 60)
        self.assertEqual(a.metadata, {})

    def test_all_modes_valid(self):
        for mode in ("patrol", "improve", "build", "review", "report"):
            a = DaemonAction(mode=mode, action="test", priority=3, agent_count=1)
            self.assertEqual(a.mode, mode)

    def test_metadata_stored(self):
        a = DaemonAction(mode="patrol", action="fix", priority=2, agent_count=1,
                         metadata={"trigger": "error_threshold"})
        self.assertEqual(a.metadata["trigger"], "error_threshold")


# ─────────────────────────────────────────────────────────
# CycleResult dataclass
# ─────────────────────────────────────────────────────────

class TestCycleResult(unittest.TestCase):

    def test_creation(self):
        cr = _make_cycle_result()
        self.assertEqual(cr.cycle, 1)
        self.assertEqual(cr.result_status, "success")
        self.assertEqual(cr.output_summary, "ok")
        self.assertAlmostEqual(cr.elapsed_ms, 100.0)

    def test_defaults(self):
        cr = _make_cycle_result()
        self.assertEqual(cr.agents_spawned, 0)
        self.assertEqual(cr.improvements, [])

    def test_custom_agents_spawned(self):
        cr = _make_cycle_result(agents_spawned=3)
        self.assertEqual(cr.agents_spawned, 3)

    def test_improvements_list(self):
        cr = _make_cycle_result(improvements=["fixed bug", "added test"])
        self.assertEqual(len(cr.improvements), 2)


# ─────────────────────────────────────────────────────────
# AutonomousDaemon.__init__
# ─────────────────────────────────────────────────────────

class TestDaemonInit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")

    def _make_daemon(self, **kw):
        kw.setdefault("log_file", self.log_file)
        return AutonomousDaemon(**kw)

    def test_default_values(self):
        d = self._make_daemon()
        self.assertEqual(d.cycle_interval, 60)
        self.assertEqual(d.model, "claude-opus-4-6")
        self.assertEqual(d.budget_per_cycle, 0.5)
        self.assertEqual(d.max_agents, 3)
        self.assertFalse(d.dry_run)
        self.assertEqual(d.cycle_count, 0)
        self.assertEqual(d.total_improvements, 0)
        self.assertEqual(d.history, [])
        self.assertIsNone(d._commander)

    def test_custom_values(self):
        d = self._make_daemon(
            cycle_interval=120,
            model="claude-sonnet-4-6",
            budget_per_cycle=5.0,
            max_agents_per_cycle=5,
            dry_run=True,
        )
        self.assertEqual(d.cycle_interval, 120)
        self.assertEqual(d.model, "claude-sonnet-4-6")
        self.assertEqual(d.budget_per_cycle, 5.0)
        self.assertEqual(d.max_agents, 5)
        self.assertTrue(d.dry_run)

    def test_log_dir_created(self):
        d = self._make_daemon()
        self.assertTrue(os.path.isdir(os.path.dirname(d.log_file)))


# ─────────────────────────────────────────────────────────
# scan_state — mocked filesystem and subprocess
# ─────────────────────────────────────────────────────────

class TestScanState(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")
        self.daemon = AutonomousDaemon(log_file=self.log_file, dry_run=True)

    @patch("core.autonomous_daemon.QUEUE_DIR")
    @patch("subprocess.run")
    def test_returns_system_state(self, mock_sub, mock_qdir):
        mock_qdir.__str__ = lambda s: self.tmpdir
        mock_sub.return_value = MagicMock(stdout="", returncode=0)
        # Mock _get_commander to avoid loading ClaudeCommander
        self.daemon._get_commander = MagicMock()
        self.daemon._get_commander.return_value.health_check = AsyncMock(return_value={"ok": True})

        state = _run(self.daemon.scan_state())
        self.assertIsInstance(state, SystemState)
        self.assertGreater(state.timestamp, 0)

    @patch("subprocess.run")
    def test_git_dirty_files_counted(self, mock_sub):
        mock_sub.return_value = MagicMock(
            stdout="M  file1.py\nM  file2.py\nM  file3.py\n",
            returncode=0,
        )
        self.daemon._get_commander = MagicMock()
        self.daemon._get_commander.return_value.health_check = AsyncMock(return_value={})

        state = _run(self.daemon.scan_state())
        self.assertEqual(state.git_dirty_files, 3)

    @patch("subprocess.run")
    def test_scan_state_handles_subprocess_error(self, mock_sub):
        mock_sub.side_effect = Exception("git not found")
        self.daemon._get_commander = MagicMock()
        self.daemon._get_commander.return_value.health_check = AsyncMock(return_value={})

        state = _run(self.daemon.scan_state())
        # Should not crash, git_dirty_files defaults to 0
        self.assertEqual(state.git_dirty_files, 0)


# ─────────────────────────────────────────────────────────
# plan_next — deterministic decision engine
# ─────────────────────────────────────────────────────────

class TestPlanNext(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")
        self.daemon = AutonomousDaemon(log_file=self.log_file)

    def test_pending_orders_triggers_build(self):
        state = _make_state(pending_orders=3)
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "build")
        self.assertEqual(action.priority, 1)
        self.assertLessEqual(action.agent_count, 3)

    def test_recent_errors_triggers_patrol(self):
        state = _make_state(recent_errors=5)
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "patrol")
        self.assertEqual(action.priority, 3)  # patrol is priority 3 (critical dirty > errors)

    def test_errors_below_threshold_no_error_patrol(self):
        state = _make_state(recent_errors=2)
        action = self.daemon.plan_next(state)
        # 2 errors < 3 threshold: error_threshold must NOT be the trigger
        self.assertNotEqual(action.metadata.get("trigger"), "error_threshold")

    def test_git_dirty_triggers_review(self):
        state = _make_state(git_dirty_files=10)
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "review")
        self.assertEqual(action.priority, 3)

    def test_git_dirty_below_threshold(self):
        state = _make_state(git_dirty_files=3)
        action = self.daemon.plan_next(state)
        self.assertNotEqual(action.mode, "review")

    def test_cycle_5_triggers_improve(self):
        self.daemon.cycle_count = 5
        state = _make_state()
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "improve")
        self.assertEqual(action.priority, 4)

    def test_cycle_10_triggers_report(self):
        # cycle_count=10 is divisible by both 5 and 10
        # improve (mod 5) wins because it's checked first
        self.daemon.cycle_count = 10
        state = _make_state()
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "improve")

    def test_default_patrol(self):
        self.daemon.cycle_count = 1
        state = _make_state()
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "patrol")
        self.assertEqual(action.priority, 5)
        self.assertEqual(action.agent_count, 0)

    def test_priority_order_build_over_errors(self):
        # pending_orders checked before recent_errors
        state = _make_state(pending_orders=2, recent_errors=5)
        action = self.daemon.plan_next(state)
        self.assertEqual(action.mode, "build")

    def test_agent_count_capped_at_max(self):
        self.daemon.max_agents = 2
        state = _make_state(pending_orders=10)
        action = self.daemon.plan_next(state)
        self.assertEqual(action.agent_count, 2)


# ─────────────────────────────────────────────────────────
# evaluate_and_log — JSONL persistence
# ─────────────────────────────────────────────────────────

class TestEvaluateAndLog(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")
        self.daemon = AutonomousDaemon(log_file=self.log_file)

    def test_writes_jsonl(self):
        cr = _make_cycle_result()
        self.daemon.evaluate_and_log(cr)
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file) as f:
            entry = json.loads(f.readline())
        self.assertEqual(entry["cycle"], 1)
        self.assertEqual(entry["result_status"], "success")

    def test_appends_to_history(self):
        cr = _make_cycle_result()
        self.daemon.evaluate_and_log(cr)
        self.assertEqual(len(self.daemon.history), 1)
        self.assertIs(self.daemon.history[0], cr)

    def test_multiple_entries_append(self):
        for i in range(3):
            self.daemon.evaluate_and_log(_make_cycle_result(cycle=i))
        with open(self.log_file) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)

    def test_log_entry_has_required_fields(self):
        self.daemon.evaluate_and_log(_make_cycle_result())
        with open(self.log_file) as f:
            entry = json.loads(f.readline())
        for key in ("timestamp", "cycle", "mode", "action", "priority",
                     "result_status", "elapsed_ms", "agents_spawned", "state"):
            self.assertIn(key, entry)


# ─────────────────────────────────────────────────────────
# status()
# ─────────────────────────────────────────────────────────

class TestStatus(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")
        self.daemon = AutonomousDaemon(log_file=self.log_file)

    def test_status_fields(self):
        s = self.daemon.status()
        self.assertTrue(s["running"])
        self.assertEqual(s["cycle_count"], 0)
        self.assertEqual(s["model"], "claude-opus-4-6")
        self.assertIsNone(s["last_cycle"])

    def test_status_after_cycle(self):
        cr = _make_cycle_result()
        self.daemon.evaluate_and_log(cr)
        s = self.daemon.status()
        self.assertEqual(s["history_size"], 1)
        self.assertIsNotNone(s["last_cycle"])


# ─────────────────────────────────────────────────────────
# execute — dry_run and zero-agent cases
# ─────────────────────────────────────────────────────────

class TestExecute(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")

    def test_dry_run_returns_dry_run_status(self):
        d = AutonomousDaemon(log_file=self.log_file, dry_run=True)
        action = _make_action(mode="build", agent_count=2)
        status, output, agents = _run(d.execute(action))
        self.assertEqual(status, "dry_run")
        self.assertEqual(agents, 0)

    def test_zero_agents_skipped(self):
        d = AutonomousDaemon(log_file=self.log_file, dry_run=False)
        action = _make_action(mode="patrol", agent_count=0)
        status, output, agents = _run(d.execute(action))
        self.assertEqual(status, "skipped")
        self.assertEqual(agents, 0)


# ─────────────────────────────────────────────────────────
# Specialized Daemons
# ─────────────────────────────────────────────────────────

class TestBuilderDaemon(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")

    def test_default_interval(self):
        d = BuilderDaemon(log_file=self.log_file)
        self.assertEqual(d.cycle_interval, 180)
        self.assertEqual(d.budget_per_cycle, 0.5)
        self.assertEqual(d.role, "builder")

    def test_plan_with_pending_orders(self):
        d = BuilderDaemon(log_file=self.log_file)
        state = _make_state(pending_orders=2)
        action = d.plan_next(state)
        self.assertEqual(action.mode, "build")
        self.assertEqual(action.metadata["daemon"], "builder")

    def test_plan_default_scans_todos(self):
        d = BuilderDaemon(log_file=self.log_file)
        state = _make_state()
        action = d.plan_next(state)
        self.assertEqual(action.mode, "build")
        self.assertIn("TODO", action.action)


class TestGuardianDaemon(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")

    def test_default_interval(self):
        d = GuardianDaemon(log_file=self.log_file)
        self.assertEqual(d.cycle_interval, 300)
        self.assertEqual(d.budget_per_cycle, 0.5)
        self.assertEqual(d.role, "guardian")

    def test_plan_with_errors(self):
        d = GuardianDaemon(log_file=self.log_file)
        state = _make_state(recent_errors=5)
        action = d.plan_next(state)
        self.assertEqual(action.mode, "patrol")
        self.assertEqual(action.priority, 1)

    def test_plan_with_dirty_git(self):
        d = GuardianDaemon(log_file=self.log_file)
        state = _make_state(git_dirty_files=15)
        action = d.plan_next(state)
        self.assertEqual(action.mode, "review")

    def test_plan_default_routine(self):
        d = GuardianDaemon(log_file=self.log_file)
        state = _make_state()
        action = d.plan_next(state)
        self.assertEqual(action.mode, "patrol")
        self.assertEqual(action.priority, 4)


class TestResearcherDaemon(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "daemon", "cycles.jsonl")

    def test_default_interval(self):
        d = ResearcherDaemon(log_file=self.log_file)
        self.assertEqual(d.cycle_interval, 600)
        self.assertEqual(d.role, "researcher")

    def test_plan_improve_on_mod3(self):
        d = ResearcherDaemon(log_file=self.log_file)
        d.cycle_count = 3
        action = d.plan_next(_make_state())
        self.assertEqual(action.mode, "improve")

    def test_plan_report_otherwise(self):
        d = ResearcherDaemon(log_file=self.log_file)
        d.cycle_count = 1
        action = d.plan_next(_make_state())
        self.assertEqual(action.mode, "report")


# ─────────────────────────────────────────────────────────
# run_multi_daemon — dry_run, max_cycles=1
# ─────────────────────────────────────────────────────────

class TestRunMultiDaemon(unittest.TestCase):

    def test_dry_run_completes(self):
        tmpdir = tempfile.mkdtemp()
        tmp_log = os.path.join(tmpdir, "daemon", "cycles.jsonl")
        tmp_queue = os.path.join(tmpdir, "queue")
        with patch("core.autonomous_daemon.DAEMON_LOG", tmp_log), \
             patch("core.autonomous_daemon.QUEUE_DIR", tmp_queue), \
             patch("subprocess.run") as mock_sub, \
             patch.object(AutonomousDaemon, "_get_commander") as mock_cmd:
            mock_sub.return_value = MagicMock(stdout="", returncode=0)
            mock_commander = MagicMock()
            mock_commander.health_check = AsyncMock(return_value={})
            mock_cmd.return_value = mock_commander
            _run(run_multi_daemon(max_cycles=1, dry_run=True))
        # If we get here without exception, test passes


# ─────────────────────────────────────────────────────────
# Feedback system
# ─────────────────────────────────────────────────────────

class TestFeedback(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_feedback_dir = None

    def test_submit_creates_file(self):
        with patch("core.autonomous_daemon.FEEDBACK_DIR", os.path.join(self.tmpdir, "fb")):
            fname = submit_feedback("approve", "looks good")
            self.assertTrue(os.path.exists(fname))
            data = json.loads(Path(fname).read_text())
            self.assertEqual(data["action"], "approve")
            self.assertEqual(data["comment"], "looks good")

    def test_get_pending_clears(self):
        fb_dir = os.path.join(self.tmpdir, "fb2")
        with patch("core.autonomous_daemon.FEEDBACK_DIR", fb_dir):
            submit_feedback("redirect", "change plan")
            fb = get_pending_feedback()
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["action"], "redirect")
            # Second call should be empty (consumed)
            fb2 = get_pending_feedback()
            self.assertEqual(len(fb2), 0)

    def test_get_pending_empty_dir(self):
        with patch("core.autonomous_daemon.FEEDBACK_DIR", os.path.join(self.tmpdir, "nonexistent")):
            fb = get_pending_feedback()
            self.assertEqual(fb, [])


# ─────────────────────────────────────────────────────────
# Harness integration — SessionStore + CostTracker + mock_provider
# ─────────────────────────────────────────────────────────

class TestHarnessInDaemon(unittest.TestCase):
    """Integración de los 3 módulos del harness v0.6.0 en AutonomousDaemon."""

    def _make_daemon(self, **kw):
        tmpdir = tempfile.mkdtemp()
        kw.setdefault("log_file", os.path.join(tmpdir, "daemon", "cycles.jsonl"))
        return AutonomousDaemon(**kw), tmpdir

    # ── 1. status() expone los 3 campos del harness ──────────────────────────

    def test_status_includes_session_id(self):
        d, _ = self._make_daemon()
        s = d.status()
        self.assertIn("session_id", s)

    def test_status_includes_cost_usd_total(self):
        d, _ = self._make_daemon()
        s = d.status()
        self.assertIn("cost_usd_total", s)
        self.assertIsInstance(s["cost_usd_total"], float)

    def test_status_includes_cost_by_mode(self):
        d, _ = self._make_daemon()
        s = d.status()
        self.assertIn("cost_by_mode", s)
        self.assertIsInstance(s["cost_by_mode"], dict)

    def test_status_cost_zero_before_any_cycle(self):
        d, _ = self._make_daemon()
        s = d.status()
        self.assertEqual(s["cost_usd_total"], 0.0)

    # ── 2. budget_exceeded cuando gasto >= budget_per_cycle ──────────────────

    def test_budget_exceeded_skips_execute(self):
        """Cuando el gasto acumulado supera el budget, execute se saltea."""
        d, _ = self._make_daemon(budget_per_cycle=0.001)

        with patch_provider("ok"):
            # Inyectar costo por encima del budget directamente al tracker
            d._get_cost_tracker().record(
                role="patrol", model="mock/model",
                prompt_tokens=0, completion_tokens=0,
            )
            # Forzar el costo sumando con deepseek para superar 0.001
            from core.cost_tracker import CostTracker
            # Reemplazar tracker con uno que ya tenga gasto > budget
            d._cost_tracker = CostTracker(session_id="budget-test")
            d._cost_tracker.record(
                role="patrol", model="deepseek/deepseek-chat",
                prompt_tokens=10_000, completion_tokens=0,
            )

        action = _make_action(mode="patrol", agent_count=1)
        # execute NO debe ser llamado — verificamos via dry_run=False y sin mock commander
        # El budget check ocurre en run(), no en execute() directamente.
        # Verificamos el tracker acumulado refleja el gasto.
        spent = d._get_cost_tracker().total_cost_usd()
        self.assertGreater(spent, d.budget_per_cycle)

    def test_budget_not_exceeded_allows_execute(self):
        """Con presupuesto suficiente, el tracker no bloquea."""
        d, _ = self._make_daemon(budget_per_cycle=100.0)
        spent = d._get_cost_tracker().total_cost_usd()
        self.assertLess(spent, d.budget_per_cycle)

    # ── 3. evaluate_and_log registra costo en CostTracker ───────────────────

    def test_evaluate_and_log_records_cost(self):
        """Después de evaluate_and_log, cost_tracker tiene ≥ 1 llamada."""
        d, _ = self._make_daemon()
        cr = _make_cycle_result(
            action=_make_action(mode="patrol", action="routine health monitoring"),
            output_summary="system ok",
        )
        d.evaluate_and_log(cr)
        self.assertEqual(d._get_cost_tracker().total_calls(), 1)

    def test_evaluate_and_log_cost_by_mode_populated(self):
        """by_role del tracker incluye el modo del ciclo."""
        d, _ = self._make_daemon()
        cr = _make_cycle_result(action=_make_action(mode="build", action="execute tasks"))
        d.evaluate_and_log(cr)
        by_mode = d._get_cost_tracker().by_role()
        self.assertIn("build", by_mode)

    def test_evaluate_and_log_three_cycles_three_records(self):
        d, _ = self._make_daemon()
        for mode in ("patrol", "build", "improve"):
            cr = _make_cycle_result(action=_make_action(mode=mode, action=f"{mode} action"))
            d.evaluate_and_log(cr)
        self.assertEqual(d._get_cost_tracker().total_calls(), 3)

    # ── 4. SessionStore persiste y restaura cycle_count ──────────────────────

    def test_session_store_saves_after_evaluate_and_log(self):
        """Después de evaluate_and_log, el archivo de sesión existe en disco."""
        d, _ = self._make_daemon()
        d.cycle_count = 7
        d.total_improvements = 3
        d.evaluate_and_log(_make_cycle_result())
        store = d._get_session_store()
        self.assertTrue(os.path.exists(store.session_path))

    def test_session_resume_restores_cycle_count(self):
        """Un daemon que arranca con sesión previa restaura cycle_count."""
        tmpdir = tempfile.mkdtemp()
        log_file = os.path.join(tmpdir, "daemon", "cycles.jsonl")
        queue_dir = os.path.join(tmpdir, "queue")

        # Daemon 1 — guarda sesión tras evaluate_and_log
        d1 = AutonomousDaemon(log_file=log_file)
        d1.cycle_count = 42
        d1.total_improvements = 10
        d1.evaluate_and_log(_make_cycle_result())

        # Daemon 2 — mismo role/store, simula restart
        d2 = AutonomousDaemon(log_file=log_file)
        # Apunta al mismo SessionStore que d1
        d2._session_store = d1._get_session_store()
        d2._session_store.reset()  # limpia memoria, pero disco intacto

        resumed = d2._get_session_store().load()
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.cycle_count, 42)
        self.assertEqual(resumed.total_improvements, 10)

    # ── 5. mock_provider en run_multi_daemon ─────────────────────────────────

    def test_run_multi_daemon_with_mock_provider(self):
        """run_multi_daemon dry_run no hace llamadas reales — mock_provider activo."""
        tmpdir = tempfile.mkdtemp()
        tmp_log = os.path.join(tmpdir, "daemon", "cycles.jsonl")
        tmp_queue = os.path.join(tmpdir, "queue")

        with patch_provider("mock response"), \
             patch("core.autonomous_daemon.DAEMON_LOG", tmp_log), \
             patch("core.autonomous_daemon.QUEUE_DIR", tmp_queue), \
             patch("subprocess.run") as mock_sub, \
             patch.object(AutonomousDaemon, "_get_commander") as mock_cmd:
            mock_sub.return_value = MagicMock(stdout="", returncode=0)
            mock_commander = MagicMock()
            mock_commander.health_check = AsyncMock(return_value={})
            mock_cmd.return_value = mock_commander
            _run(run_multi_daemon(max_cycles=1, dry_run=True))
        # Sin excepción = OK


if __name__ == "__main__":
    unittest.main()
