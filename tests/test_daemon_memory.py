"""
tests/test_daemon_memory.py — Tests for core/daemon_memory.py
Run with: python3 -m unittest tests.test_daemon_memory
"""

import json
import tempfile
import time
import unittest
from pathlib import Path

from core.daemon_memory import DaemonMemory, CycleSummary, ErrorPattern, MemoryScan


def _make_cycles(tmp_dir: str, cycles: list[dict]) -> Path:
    path = Path(tmp_dir) / "cycles.jsonl"
    with path.open("w") as f:
        for c in cycles:
            f.write(json.dumps(c) + "\n")
    return path


class TestDaemonMemoryEmpty(unittest.TestCase):
    def test_empty_path_returns_zero(self):
        mem = DaemonMemory("/nonexistent/path/cycles.jsonl")
        self.assertEqual(mem.total_cycles(), 0)
        self.assertEqual(mem.success_rate(), 1.0)
        self.assertEqual(mem.avg_elapsed_ms(), 0.0)
        self.assertEqual(mem.error_patterns(), [])
        self.assertIsNone(mem.last_failure())

    def test_empty_file_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cycles.jsonl"
            path.write_text("")
            mem = DaemonMemory(path)
            self.assertEqual(mem.total_cycles(), 0)


class TestDaemonMemoryBasic(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        now = time.time()
        cycles = [
            {"cycle": 1, "iso": "2026-04-12T10:00:00", "mode": "build", "action": "implement feature X", "result_status": "success", "elapsed_ms": 1000, "agents_spawned": 1},
            {"cycle": 2, "iso": "2026-04-12T10:01:00", "mode": "patrol", "action": "check health", "result_status": "success", "elapsed_ms": 500, "agents_spawned": 0},
            {"cycle": 3, "iso": "2026-04-12T10:02:00", "mode": "build", "action": "failing build task", "result_status": "error", "elapsed_ms": 2000, "agents_spawned": 1},
            {"cycle": 4, "iso": "2026-04-12T10:03:00", "mode": "build", "action": "failing build task", "result_status": "error", "elapsed_ms": 1800, "agents_spawned": 1},
            {"cycle": 5, "iso": "2026-04-12T10:04:00", "mode": "report", "action": "generate report", "result_status": "success", "elapsed_ms": 300, "agents_spawned": 0},
        ]
        self._path = _make_cycles(self._tmp, cycles)
        self._mem = DaemonMemory(self._path)

    def test_total_cycles(self):
        self.assertEqual(self._mem.total_cycles(), 5)

    def test_success_rate(self):
        # 3 success out of 5
        self.assertAlmostEqual(self._mem.success_rate(), 0.6)

    def test_avg_elapsed_ms(self):
        # (1000+500+2000+1800+300) / 5 = 1120
        self.assertAlmostEqual(self._mem.avg_elapsed_ms(), 1120.0)

    def test_error_patterns_top1(self):
        top = self._mem.error_patterns(top_n=1)
        self.assertEqual(len(top), 1)
        self.assertIsInstance(top[0], ErrorPattern)
        self.assertEqual(top[0].action, "failing build task")
        self.assertEqual(top[0].count, 2)

    def test_mode_distribution(self):
        dist = self._mem.mode_distribution()
        self.assertEqual(dist["build"], 3)
        self.assertEqual(dist["patrol"], 1)
        self.assertEqual(dist["report"], 1)

    def test_recent_summary_returns_cycles(self):
        recent = self._mem.recent_summary(n=3)
        self.assertEqual(len(recent), 3)
        self.assertIsInstance(recent[0], CycleSummary)
        # Most recent first
        self.assertEqual(recent[0].cycle, 5)

    def test_last_failure_returns_most_recent(self):
        last = self._mem.last_failure()
        self.assertIsNotNone(last)
        self.assertEqual(last["cycle"], 4)
        self.assertEqual(last["result_status"], "error")

    def test_module_health_found(self):
        # "failing build task" appears in cycles 3 and 4 (searches action text)
        result = self._mem.module_health("failing")
        self.assertEqual(result["cycles_found"], 2)
        self.assertIn("success_rate", result)
        self.assertEqual(result["success_rate"], 0.0)

    def test_module_health_not_found(self):
        result = self._mem.module_health("nonexistent_module_xyz")
        self.assertEqual(result["cycles_found"], 0)

    def test_scan_summary(self):
        scan = self._mem.scan_summary()
        self.assertIsInstance(scan, MemoryScan)
        self.assertEqual(scan.total_cycles, 5)
        self.assertAlmostEqual(scan.success_rate, 0.6)
        self.assertEqual(len(scan.recent_cycles), 5)
        self.assertIsInstance(scan.mode_distribution, dict)


class TestDaemonMemoryRefresh(unittest.TestCase):
    def test_refresh_picks_up_new_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cycles.jsonl"
            path.write_text("")
            mem = DaemonMemory(path)
            self.assertEqual(mem.total_cycles(), 0)

            # Add a cycle to the file
            with path.open("a") as f:
                f.write(json.dumps({"cycle": 1, "result_status": "success", "mode": "build", "action": "x", "elapsed_ms": 100}) + "\n")

            mem.refresh()
            self.assertEqual(mem.total_cycles(), 1)


class TestDaemonMemoryLiveData(unittest.TestCase):
    def test_loads_real_log_without_error(self):
        """Integration: load from the real cycles.jsonl if it exists."""
        real_path = Path("logs/daemon/cycles.jsonl")
        if not real_path.exists():
            self.skipTest("No real cycles.jsonl found")
        mem = DaemonMemory(real_path)
        self.assertGreater(mem.total_cycles(), 0)
        scan = mem.scan_summary()
        self.assertIsInstance(scan.success_rate, float)
        self.assertGreaterEqual(scan.success_rate, 0.0)
        self.assertLessEqual(scan.success_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
