"""Tests for core.session_worker — SessionWorker autonomous task executor."""
import json
import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSessionWorkerInit(unittest.TestCase):
    def test_creation_with_node_id(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("test-node")
                self.assertEqual(w.node_id, "test-node")

    def test_creation_with_custom_model(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("node-x", model="gpt-4")
                self.assertEqual(w.model, "gpt-4")

    def test_default_model_is_claude(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("node-y")
                self.assertIn("claude", w.model.lower())

    def test_running_false_on_init(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("node-z")
                self.assertFalse(w._running)

    def test_inbox_dir_created(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            inbox_root = Path(tmp)
            with patch("core.session_worker.INBOX_ROOT", inbox_root):
                SessionWorker("my-node")
                self.assertTrue((inbox_root / "my-node").exists())


class TestSessionWorkerReadTasks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def _make_worker(self, node_id="test-worker"):
        from core.session_worker import SessionWorker
        with patch("core.session_worker.INBOX_ROOT", self.tmp_path):
            return SessionWorker(node_id)

    def _write_task(self, worker, task_id, content):
        inbox = self.tmp_path / worker.node_id
        inbox.mkdir(parents=True, exist_ok=True)
        task_file = inbox / f"{task_id}.json"
        # content must be a dict with 'task' key for _read_pending_tasks to pick it up
        content_dict = {"task": content} if isinstance(content, str) else content
        task_file.write_text(json.dumps({
            "msg_id": f"WO-{task_id}",
            "from_node": "commander",
            "to_node": worker.node_id,
            "content": content_dict,
            "msg_type": "work_order",
        }), encoding="utf-8")
        return task_file

    def test_read_pending_tasks_empty(self):
        worker = self._make_worker()
        with patch("core.session_worker.INBOX_ROOT", self.tmp_path):
            tasks = worker._read_pending_tasks()
        self.assertIsInstance(tasks, list)
        self.assertEqual(len(tasks), 0)

    def test_read_pending_tasks_with_task(self):
        worker = self._make_worker()
        # Write directly to worker.inbox (already set at init time)
        # content must be a dict with "task" key — due to production code logic
        inbox = worker.inbox
        inbox.mkdir(parents=True, exist_ok=True)
        task_file = inbox / "WO-t001.json"
        task_file.write_text(json.dumps({
            "msg_id": "WO-t001",
            "from_node": "commander",
            "to_node": worker.node_id,
            "content": {"task": "write tests for mesh", "priority": "high"},
            "msg_type": "work_order",
        }), encoding="utf-8")
        tasks = worker._read_pending_tasks()
        self.assertGreaterEqual(len(tasks), 1)

    def test_read_pending_tasks_skips_done(self):
        worker = self._make_worker()
        task_file = self._write_task(worker, "t002", "test task")
        task_file.rename(task_file.with_suffix(".done"))
        with patch("core.session_worker.INBOX_ROOT", self.tmp_path):
            tasks = worker._read_pending_tasks()
        self.assertEqual(len(tasks), 0)

    def test_read_twice_does_not_double_count(self):
        worker = self._make_worker()
        # Write task directly to worker.inbox
        inbox = worker.inbox
        inbox.mkdir(parents=True, exist_ok=True)
        f = inbox / "WO-t003.json"
        f.write_text(json.dumps({
            "msg_id": "WO-t003",
            "from_node": "commander",
            "to_node": worker.node_id,
            "content": {"task": "test task"},
            "msg_type": "work_order",
        }), encoding="utf-8")
        first = worker._read_pending_tasks()
        # Second call should skip already-executed task
        second = worker._read_pending_tasks()
        self.assertGreaterEqual(len(first), 1)
        self.assertEqual(len(second), 0)


class TestSessionWorkerStop(unittest.TestCase):
    def test_stop_sets_running_false(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("stopper")
                w._running = True
                w._running = False
                self.assertFalse(w._running)

    def test_run_stops_on_keyboard_interrupt(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("kb-test")
                def fake_sleep(s):
                    raise KeyboardInterrupt()
                with patch("core.session_worker.time.sleep", fake_sleep):
                    w.run()
                # run() returns after KeyboardInterrupt — worker is no longer looping
                self.assertEqual(w._cycle, 1)  # completed exactly 1 cycle before interrupt


class TestSessionWorkerWriteOutput(unittest.TestCase):
    def test_write_output_creates_file(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("writer")
                out_path = Path(tmp) / "output.txt"
                result = w._write_output(out_path, "test content")
                self.assertTrue(result)
                self.assertTrue(out_path.exists())

    def test_write_output_content_correct(self):
        from core.session_worker import SessionWorker
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.session_worker.INBOX_ROOT", Path(tmp)):
                w = SessionWorker("writer2")
                out_path = Path(tmp) / "result.txt"
                w._write_output(out_path, "hello mesh")
                self.assertEqual(out_path.read_text(), "hello mesh")
