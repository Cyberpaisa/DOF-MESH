"""
tests/test_mesh_scheduler.py — Unit tests for MeshScheduler.
Run with: python3 -m unittest tests/test_mesh_scheduler.py
"""

import time
import unittest
from unittest.mock import patch

from core.mesh_scheduler import (
    HIGH,
    LOW,
    NORMAL,
    MeshScheduler,
    TaskSlot,
)


class TestPriorityConstants(unittest.TestCase):
    def test_priority_ordering(self):
        self.assertLess(HIGH, NORMAL)
        self.assertLess(NORMAL, LOW)
        self.assertEqual(HIGH, 1)
        self.assertEqual(NORMAL, 2)
        self.assertEqual(LOW, 3)


class TestTaskSlot(unittest.TestCase):
    def test_create_defaults(self):
        slot = TaskSlot.create("t1", "do something", "node-a")
        self.assertEqual(slot.task_id, "t1")
        self.assertEqual(slot.priority, NORMAL)
        self.assertIsNotNone(slot.queued_at)

    def test_create_with_priority(self):
        slot = TaskSlot.create("t2", "urgent", "node-b", priority=HIGH)
        self.assertEqual(slot.priority, HIGH)

    def test_ordering_by_priority(self):
        low = TaskSlot.create("low", "low task", "n", priority=LOW, queued_at=1.0)
        high = TaskSlot.create("high", "high task", "n", priority=HIGH, queued_at=2.0)
        self.assertLess(high, low)

    def test_tiebreak_by_queued_at(self):
        first = TaskSlot.create("first", "first", "n", priority=NORMAL, queued_at=1.0)
        second = TaskSlot.create("second", "second", "n", priority=NORMAL, queued_at=2.0)
        self.assertLess(first, second)


class TestMeshSchedulerConcurrency(unittest.TestCase):
    def setUp(self):
        self.sched = MeshScheduler(max_concurrent=3)

    def test_initial_state(self):
        self.assertEqual(self.sched._active, 0)
        self.assertTrue(self.sched.can_accept())

    def test_acquire_increments_active(self):
        self.sched.acquire()
        self.assertEqual(self.sched._active, 1)

    def test_release_decrements_active(self):
        self.sched.acquire()
        self.sched.acquire()
        self.sched.release()
        self.assertEqual(self.sched._active, 1)

    def test_release_floor_at_zero(self):
        self.sched.release()
        self.assertEqual(self.sched._active, 0)

    def test_can_accept_false_when_full(self):
        for _ in range(3):
            self.sched.acquire()
        self.assertFalse(self.sched.can_accept())

    def test_can_accept_true_after_release(self):
        for _ in range(3):
            self.sched.acquire()
        self.sched.release()
        self.assertTrue(self.sched.can_accept())


class TestMeshSchedulerQueue(unittest.TestCase):
    def setUp(self):
        self.sched = MeshScheduler(max_concurrent=3)

    def test_enqueue_increases_queue_size(self):
        slot = TaskSlot.create("t1", "prompt", "node")
        self.sched.enqueue(slot)
        self.assertEqual(self.sched.queue_size(), 1)

    def test_dequeue_returns_none_when_empty(self):
        self.assertIsNone(self.sched.dequeue())

    def test_dequeue_returns_highest_priority(self):
        self.sched.enqueue(TaskSlot.create("low", "low", "n", priority=LOW, queued_at=1.0))
        self.sched.enqueue(TaskSlot.create("high", "high", "n", priority=HIGH, queued_at=2.0))
        self.sched.enqueue(TaskSlot.create("normal", "normal", "n", priority=NORMAL, queued_at=3.0))

        first = self.sched.dequeue()
        second = self.sched.dequeue()
        third = self.sched.dequeue()

        self.assertEqual(first.task_id, "high")
        self.assertEqual(second.task_id, "normal")
        self.assertEqual(third.task_id, "low")

    def test_dequeue_tiebreak_fifo(self):
        self.sched.enqueue(TaskSlot.create("a", "a", "n", priority=NORMAL, queued_at=1.0))
        self.sched.enqueue(TaskSlot.create("b", "b", "n", priority=NORMAL, queued_at=2.0))
        self.assertEqual(self.sched.dequeue().task_id, "a")

    def test_queue_empties_after_all_dequeues(self):
        for i in range(3):
            self.sched.enqueue(TaskSlot.create(f"t{i}", "p", "n"))
        for _ in range(3):
            self.sched.dequeue()
        self.assertEqual(self.sched.queue_size(), 0)


class TestMeshSchedulerRAM(unittest.TestCase):
    def setUp(self):
        self.sched = MeshScheduler(max_concurrent=4)

    def test_available_ram_gb_returns_positive_float(self):
        ram = self.sched.available_ram_gb()
        self.assertIsInstance(ram, float)
        self.assertGreater(ram, 0)

    def test_recommended_slots_capped_at_max_concurrent(self):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.available = 200 * (1024 ** 3)  # 200 GB
            slots = self.sched.recommended_slots()
        self.assertEqual(slots, self.sched.max_concurrent)

    def test_recommended_slots_floors_division(self):
        # new formula: usable = available - 9 (model resident) - 2 (safety) = 16 - 11 = 5
        # floor(5 / 2.5) = 2
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.available = 16 * (1024 ** 3)  # 16 GB → usable=5 → floor(5/2.5)=2
            slots = self.sched.recommended_slots()
        self.assertEqual(slots, 2)

    def test_recommended_slots_minimum_one(self):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.available = 1 * (1024 ** 3)  # 1 GB → floor(0.1) = 0 → clamped to 1
            slots = self.sched.recommended_slots()
        self.assertEqual(slots, 1)


class TestMeshSchedulerStatus(unittest.TestCase):
    def test_status_keys(self):
        sched = MeshScheduler(max_concurrent=2)
        status = sched.status()
        for key in ("active", "queued", "max_concurrent", "can_accept",
                    "recommended_slots", "available_ram_gb"):
            self.assertIn(key, status)

    def test_status_reflects_state(self):
        sched = MeshScheduler(max_concurrent=2)
        sched.acquire()
        sched.enqueue(TaskSlot.create("x", "p", "n"))
        status = sched.status()
        self.assertEqual(status["active"], 1)
        self.assertEqual(status["queued"], 1)
        self.assertTrue(status["can_accept"])


if __name__ == "__main__":
    unittest.main()
