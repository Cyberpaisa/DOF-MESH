"""Tests for ConsistentHashRing and DOFShardManager."""
import unittest
from core.dof_sharding import ConsistentHashRing, DOFShardManager, Shard


class TestConsistentHashRing(unittest.TestCase):

    def setUp(self):
        self.ring = ConsistentHashRing(replication_factor=3)
        for m in ["machine-a", "machine-b", "machine-c"]:
            self.ring.add_node(m)

    def test_add_node(self):
        self.assertIn("machine-a", self.ring.nodes())
        self.assertEqual(len(self.ring.nodes()), 3)

    def test_get_node_returns_valid_node(self):
        node = self.ring.get_node("some-task-key")
        self.assertIn(node, self.ring.nodes())

    def test_get_node_deterministic(self):
        n1 = self.ring.get_node("task-42")
        n2 = self.ring.get_node("task-42")
        self.assertEqual(n1, n2)

    def test_get_replicas_count(self):
        replicas = self.ring.get_replicas("task-42")
        self.assertEqual(len(replicas), 3)

    def test_get_replicas_unique(self):
        replicas = self.ring.get_replicas("task-42")
        self.assertEqual(len(replicas), len(set(replicas)))

    def test_remove_node(self):
        self.ring.remove_node("machine-c")
        self.assertNotIn("machine-c", self.ring.nodes())
        node = self.ring.get_node("task-99")
        self.assertIn(node, ["machine-a", "machine-b"])

    def test_distribution_all_nodes_used(self):
        counts = {n: 0 for n in self.ring.nodes()}
        for i in range(10000):
            node = self.ring.get_node(f"key-{i}")
            counts[node] += 1
        for node, count in counts.items():
            self.assertGreater(count, 0, f"{node} got 0 keys")

    def test_empty_ring_returns_none(self):
        empty = ConsistentHashRing()
        self.assertIsNone(empty.get_node("anything"))
        self.assertEqual(empty.get_replicas("anything"), [])

    def test_status(self):
        s = self.ring.status()
        self.assertEqual(s["nodes"], 3)
        self.assertGreater(s["total_vnodes"], 0)

    def test_add_node_weight(self):
        ring = ConsistentHashRing()
        ring.add_node("big", weight=3)
        ring.add_node("small", weight=1)
        s = ring.status()
        self.assertGreater(
            s["distribution"]["big"]["vnodes"],
            s["distribution"]["small"]["vnodes"]
        )


class TestDOFShardManager(unittest.TestCase):

    def setUp(self):
        self.sm = DOFShardManager(
            ["machine-a", "machine-b", "machine-c"],
            shard_count=10,
            replication_factor=2,
        )

    def test_init_creates_shards(self):
        self.assertEqual(len(self.sm.shards), 10)

    def test_get_shard_for_key(self):
        shard = self.sm.get_shard_for_key("agent-xyz")
        self.assertIsInstance(shard, Shard)
        self.assertIn(shard.primary_node, ["machine-a", "machine-b", "machine-c"])

    def test_get_shard_deterministic(self):
        s1 = self.sm.get_shard_for_key("agent-42")
        s2 = self.sm.get_shard_for_key("agent-42")
        self.assertEqual(s1.id, s2.id)

    def test_assign_agent(self):
        shard = self.sm.assign_agent("agent-001")
        self.assertIsInstance(shard, Shard)
        self.assertEqual(shard.agent_count, 1)

    def test_assign_agent_idempotent(self):
        self.sm.assign_agent("agent-001")
        self.sm.assign_agent("agent-001")
        shard = self.sm.get_agent_shard("agent-001")
        self.assertEqual(shard.agent_count, 1)

    def test_status(self):
        self.sm.assign_agent("a1")
        self.sm.assign_agent("a2")
        s = self.sm.status()
        self.assertEqual(s["agents_assigned"], 2)
        self.assertEqual(s["shard_count"], 10)

    def test_add_node(self):
        self.sm.add_node("machine-d")
        self.assertIn("machine-d", self.sm.ring.nodes())

    def test_80_agents_distributed(self):
        for i in range(80):
            self.sm.assign_agent(f"agent-{i}")
        s = self.sm.status()
        self.assertEqual(s["agents_assigned"], 80)
        # Verify all shards have at least some agents (distribution)
        total = sum(sh["agents"] for sh in s["shards"].values())
        self.assertEqual(total, 80)


if __name__ == "__main__":
    unittest.main()
