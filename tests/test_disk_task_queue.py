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


class TestDiskTaskQueueTTL(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "q.jsonl"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_non_expired_task_is_returned(self):
        q = DiskTaskQueue(self.path, ttl_seconds=60)
        q.push(TaskSlot.create("live", "p", "n"))
        self.assertEqual(q.size(), 1)
        task = q.pop()
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "live")

    def test_expired_task_is_dropped_on_pop(self):
        q = DiskTaskQueue(self.path, ttl_seconds=1)
        # Write a task with a past queued_at directly (already expired)
        import time as _time
        old_slot = TaskSlot(
            priority=NORMAL,
            queued_at=_time.time() - 10,  # 10 seconds ago
            task_id="expired",
            prompt="p",
            node="n",
        )
        q.push(old_slot)
        self.assertIsNone(q.pop())

    def test_expired_task_not_counted_in_size(self):
        import time as _time
        q = DiskTaskQueue(self.path, ttl_seconds=1)
        old = TaskSlot(priority=NORMAL, queued_at=_time.time() - 10, task_id="old", prompt="p", node="n")
        q.push(old)
        q.push(TaskSlot.create("fresh", "p", "n"))
        self.assertEqual(q.size(), 1)

    def test_evict_removes_expired_returns_count(self):
        import time as _time
        q = DiskTaskQueue(self.path, ttl_seconds=1)
        old = TaskSlot(priority=NORMAL, queued_at=_time.time() - 10, task_id="old", prompt="p", node="n")
        q.push(old)
        q.push(TaskSlot.create("fresh", "p", "n"))
        evicted = q.evict()
        self.assertEqual(evicted, 1)
        self.assertEqual(q.size(), 1)

    def test_evict_without_ttl_returns_zero(self):
        q = DiskTaskQueue(self.path)  # no ttl
        q.push(TaskSlot.create("t1", "p", "n"))
        self.assertEqual(q.evict(), 0)

    def test_no_ttl_never_expires(self):
        import time as _time
        q = DiskTaskQueue(self.path)  # no ttl
        old = TaskSlot(priority=NORMAL, queued_at=0.0, task_id="ancient", prompt="p", node="n")
        q.push(old)
        task = q.pop()
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "ancient")

    def test_mixed_expired_and_live_drain(self):
        import time as _time
        q = DiskTaskQueue(self.path, ttl_seconds=1)
        old = TaskSlot(priority=NORMAL, queued_at=_time.time() - 10, task_id="old", prompt="p", node="n")
        q.push(old)
        q.push(TaskSlot.create("live1", "p", "n"))
        q.push(TaskSlot.create("live2", "p", "n"))
        tasks = q.drain()
        ids = [t.task_id for t in tasks]
        self.assertNotIn("old", ids)
        self.assertIn("live1", ids)
        self.assertIn("live2", ids)


if __name__ == "__main__":
    unittest.main()
