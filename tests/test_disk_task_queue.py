"""
tests/test_disk_task_queue.py — Tests for DiskTaskQueue (filelock-backed persistence).
Run with: python3 -m unittest tests.test_disk_task_queue
"""

import json
import tempfile
import unittest
from pathlib import Path

from core.mesh_scheduler import DiskTaskQueue, TaskSlot, HIGH, NORMAL, LOW


class TestDiskTaskQueueBasic(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "queue.jsonl"
        self.q = DiskTaskQueue(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_empty_queue_size_is_zero(self):
        self.assertEqual(self.q.size(), 0)

    def test_pop_empty_returns_none(self):
        self.assertIsNone(self.q.pop())

    def test_push_increments_size(self):
        self.q.push(TaskSlot.create("t1", "prompt", "node-a"))
        self.assertEqual(self.q.size(), 1)

    def test_push_multiple_increments_size(self):
        for i in range(5):
            self.q.push(TaskSlot.create(f"t{i}", "p", "n"))
        self.assertEqual(self.q.size(), 5)

    def test_pop_returns_task(self):
        self.q.push(TaskSlot.create("t1", "do X", "node-a"))
        task = self.q.pop()
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "t1")

    def test_pop_decrements_size(self):
        self.q.push(TaskSlot.create("t1", "p", "n"))
        self.q.pop()
        self.assertEqual(self.q.size(), 0)

    def test_pop_empty_after_all_consumed(self):
        self.q.push(TaskSlot.create("t1", "p", "n"))
        self.q.pop()
        self.assertIsNone(self.q.pop())


class TestDiskTaskQueuePriority(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.q = DiskTaskQueue(Path(self._tmpdir.name) / "q.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_high_priority_pops_before_normal(self):
        self.q.push(TaskSlot.create("low", "p", "n", priority=LOW, queued_at=1.0))
        self.q.push(TaskSlot.create("high", "p", "n", priority=HIGH, queued_at=2.0))
        self.q.push(TaskSlot.create("normal", "p", "n", priority=NORMAL, queued_at=3.0))

        self.assertEqual(self.q.pop().task_id, "high")
        self.assertEqual(self.q.pop().task_id, "normal")
        self.assertEqual(self.q.pop().task_id, "low")

    def test_fifo_within_same_priority(self):
        self.q.push(TaskSlot.create("first", "p", "n", priority=NORMAL, queued_at=1.0))
        self.q.push(TaskSlot.create("second", "p", "n", priority=NORMAL, queued_at=2.0))
        self.assertEqual(self.q.pop().task_id, "first")
        self.assertEqual(self.q.pop().task_id, "second")


class TestDiskTaskQueuePersistence(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "q.jsonl"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_tasks_survive_new_instance(self):
        q1 = DiskTaskQueue(self.path)
        q1.push(TaskSlot.create("persist-me", "do something", "node-b", priority=HIGH))

        # New instance reads from the same file
        q2 = DiskTaskQueue(self.path)
        task = q2.pop()
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "persist-me")
        self.assertEqual(task.priority, HIGH)

    def test_file_is_valid_jsonl(self):
        q = DiskTaskQueue(self.path)
        q.push(TaskSlot.create("t1", "prompt one", "n1"))
        q.push(TaskSlot.create("t2", "prompt two", "n2"))

        lines = self.path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            obj = json.loads(line)
            self.assertIn("task_id", obj)
            self.assertIn("priority", obj)
            self.assertIn("queued_at", obj)


class TestDiskTaskQueueDrain(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.q = DiskTaskQueue(Path(self._tmpdir.name) / "q.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_drain_returns_all_tasks_sorted(self):
        self.q.push(TaskSlot.create("low", "p", "n", priority=LOW, queued_at=1.0))
        self.q.push(TaskSlot.create("high", "p", "n", priority=HIGH, queued_at=2.0))
        tasks = self.q.drain()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].task_id, "high")
        self.assertEqual(tasks[1].task_id, "low")

    def test_drain_empties_queue(self):
        for i in range(3):
            self.q.push(TaskSlot.create(f"t{i}", "p", "n"))
        self.q.drain()
        self.assertEqual(self.q.size(), 0)

    def test_drain_empty_returns_empty_list(self):
        self.assertEqual(self.q.drain(), [])

    def test_clear_discards_all(self):
        self.q.push(TaskSlot.create("t1", "p", "n"))
        self.q.push(TaskSlot.create("t2", "p", "n"))
        self.q.clear()
        self.assertEqual(self.q.size(), 0)
        self.assertIsNone(self.q.pop())


if __name__ == "__main__":
    unittest.main()
