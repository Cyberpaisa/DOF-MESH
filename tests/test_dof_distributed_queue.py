"""Tests for DistributedMeshQueue."""
import os
import tempfile
import time
import unittest
from core.dof_sharding import DOFShardManager
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask


def make_queue(shard_count=10, wal=False):
    sm = DOFShardManager(
        ["machine-a", "machine-b", "machine-c"],
        shard_count=shard_count,
        replication_factor=2,
    )
    wal_path = tempfile.mkdtemp() if wal else None
    return DistributedMeshQueue("test-node", sm, wal_path=wal_path), sm


class TestDistributedTask(unittest.TestCase):

    def test_from_dict(self):
        d = {"task_id": "t1", "shard_key": "agent-5", "prompt": "hello", "priority": "high"}
        t = DistributedTask.from_dict(d)
        self.assertEqual(t.task_id, "t1")
        self.assertEqual(t.priority, 0)  # high=0

    def test_to_dict(self):
        t = DistributedTask(task_id="t1", shard_key="s", prompt="p")
        d = t.to_dict()
        self.assertEqual(d["task_id"], "t1")

    def test_ordering_by_priority(self):
        high = DistributedTask(priority=0, task_id="h", shard_key="s", prompt="p")
        low = DistributedTask(priority=2, task_id="l", shard_key="s", prompt="p")
        self.assertLess(high, low)


class TestDistributedMeshQueue(unittest.TestCase):

    def setUp(self):
        self.q, self.sm = make_queue()

    def test_enqueue_returns_task_id(self):
        task = DistributedTask(task_id="t1", shard_key="agent-0", prompt="hello")
        result = self.q.enqueue(task)
        self.assertEqual(result, "t1")

    def test_qsize_increases(self):
        self.assertEqual(self.q.qsize(), 0)
        self.q.enqueue(DistributedTask(task_id="t1", shard_key="agent-0", prompt="x"))
        self.q.enqueue(DistributedTask(task_id="t2", shard_key="agent-1", prompt="y"))
        self.assertEqual(self.q.qsize(), 2)

    def test_dequeue_returns_task(self):
        task = DistributedTask(task_id="t1", shard_key="agent-0", prompt="hello")
        shard = self.sm.get_shard_for_key("agent-0")
        self.q.enqueue(task)
        result = self.q.dequeue(shard.id, timeout=0.5)
        self.assertIsNotNone(result)
        self.assertEqual(result.task_id, "t1")

    def test_dequeue_any(self):
        self.q.enqueue(DistributedTask(task_id="t1", shard_key="agent-5", prompt="x"))
        result = self.q.dequeue_any(timeout=0.5)
        self.assertIsNotNone(result)

    def test_dequeue_empty_returns_none(self):
        result = self.q.dequeue(0, timeout=0.05)
        self.assertIsNone(result)

    def test_shard_routing_deterministic(self):
        shard1 = self.sm.get_shard_for_key("agent-42")
        shard2 = self.sm.get_shard_for_key("agent-42")
        self.assertEqual(shard1.id, shard2.id)

    def test_task_done_dedup(self):
        task = DistributedTask(task_id="t1", shard_key="agent-0", prompt="x")
        shard = self.sm.get_shard_for_key("agent-0")
        self.q.enqueue(task)
        # Dequeue first, then mark done
        got = self.q.dequeue(shard.id, timeout=0.2)
        self.assertIsNotNone(got)
        self.q.task_done(got)
        # Re-enqueue same task_id — should be deduped
        self.q.enqueue(task)
        self.assertEqual(self.q.qsize(), 0)

    def test_priority_ordering(self):
        shard = self.sm.get_shard_for_key("agent-0")
        low = DistributedTask(priority=2, task_id="low", shard_key="agent-0", prompt="low")
        high = DistributedTask(priority=0, task_id="high", shard_key="agent-0", prompt="high")
        self.q.enqueue(low)
        self.q.enqueue(high)
        first = self.q.dequeue(shard.id, timeout=0.1)
        self.assertEqual(first.task_id, "high")

    def test_status(self):
        self.q.enqueue(DistributedTask(task_id="t1", shard_key="a", prompt="x"))
        s = self.q.status()
        self.assertEqual(s["node_id"], "test-node")
        self.assertEqual(s["total_queued"], 1)
        self.assertEqual(s["enqueued_total"], 1)

    def test_80_agents_distributed(self):
        for i in range(80):
            self.q.enqueue(DistributedTask(
                task_id=f"t{i}", shard_key=f"agent-{i}", prompt=f"task {i}"
            ))
        self.assertEqual(self.q.qsize(), 80)
        s = self.q.status()
        # Verify tasks spread across shards
        non_empty = sum(1 for v in s["per_shard"].values() if v > 0)
        self.assertGreater(non_empty, 1)

    def test_benchmark(self):
        from core.dof_distributed_queue import benchmark
        # Just verify it runs without error
        benchmark(1000)

    def test_wal_recovery(self):
        tmpdir = tempfile.mkdtemp()
        sm = DOFShardManager(["m-a", "m-b"], shard_count=5)
        q = DistributedMeshQueue("n", sm, wal_path=tmpdir)
        q.enqueue(DistributedTask(task_id="recover-me", shard_key="agent-0", prompt="x"))
        del q

        # Reopen — should recover the task
        q2 = DistributedMeshQueue("n", sm, wal_path=tmpdir)
        self.assertEqual(q2.qsize(), 1)


if __name__ == "__main__":
    unittest.main()
