"""Tests for VectorClock and GossipProtocol."""
import time
import unittest
from core.dof_consensus import VectorClock, GossipState, GossipProtocol


class TestVectorClock(unittest.TestCase):

    def test_increment(self):
        vc = VectorClock()
        vc.increment("a")
        self.assertEqual(vc.clock["a"], 1)
        vc.increment("a")
        self.assertEqual(vc.clock["a"], 2)

    def test_increment_multiple_nodes(self):
        vc = VectorClock()
        vc.increment("a")
        vc.increment("b")
        self.assertEqual(vc.clock, {"a": 1, "b": 1})

    def test_merge(self):
        a = VectorClock.from_dict({"a": 3, "b": 1})
        b = VectorClock.from_dict({"a": 1, "b": 4, "c": 2})
        merged = a.merge(b)
        self.assertEqual(merged.clock, {"a": 3, "b": 4, "c": 2})

    def test_merge_does_not_mutate(self):
        a = VectorClock.from_dict({"a": 1})
        b = VectorClock.from_dict({"b": 1})
        _ = a.merge(b)
        self.assertNotIn("b", a.clock)

    def test_is_ancestor_equal(self):
        a = VectorClock.from_dict({"a": 1})
        b = VectorClock.from_dict({"a": 1})
        self.assertTrue(a.is_ancestor_of(b))
        self.assertTrue(b.is_ancestor_of(a))

    def test_is_ancestor_strict(self):
        a = VectorClock.from_dict({"a": 1})
        b = VectorClock.from_dict({"a": 2})
        self.assertTrue(a.is_ancestor_of(b))
        self.assertFalse(b.is_ancestor_of(a))

    def test_conflicts_with(self):
        a = VectorClock.from_dict({"a": 1, "b": 0})
        b = VectorClock.from_dict({"a": 0, "b": 1})
        self.assertTrue(a.conflicts_with(b))
        self.assertTrue(b.conflicts_with(a))

    def test_no_conflict_when_ancestor(self):
        a = VectorClock.from_dict({"a": 1})
        b = VectorClock.from_dict({"a": 2})
        self.assertFalse(a.conflicts_with(b))

    def test_to_dict_from_dict(self):
        vc = VectorClock.from_dict({"x": 5, "y": 3})
        d = vc.to_dict()
        vc2 = VectorClock.from_dict(d)
        self.assertEqual(vc.clock, vc2.clock)

    def test_copy_independent(self):
        vc = VectorClock.from_dict({"a": 1})
        copy = vc.copy()
        copy.increment("a")
        self.assertEqual(vc.clock["a"], 1)
        self.assertEqual(copy.clock["a"], 2)

    def test_empty_is_ancestor_of_everything(self):
        empty = VectorClock()
        other = VectorClock.from_dict({"a": 5})
        self.assertTrue(empty.is_ancestor_of(other))

    def test_equality(self):
        a = VectorClock.from_dict({"a": 1, "b": 2})
        b = VectorClock.from_dict({"a": 1, "b": 2})
        self.assertEqual(a, b)


class TestGossipProtocol(unittest.TestCase):

    def _make_cluster(self, n=3):
        nodes = [GossipProtocol(f"node-{i}", fanout=n, interval_ms=20) for i in range(n)]
        for a in nodes:
            for b in nodes:
                if a is not b:
                    a.register_peer(b)
        return nodes

    def test_put_and_get_local(self):
        g = GossipProtocol("solo")
        g.put("key", "value")
        self.assertEqual(g.get("key"), "value")

    def test_get_missing_returns_none(self):
        g = GossipProtocol("solo")
        self.assertIsNone(g.get("missing"))

    def test_convergence_3_nodes(self):
        nodes = self._make_cluster(3)
        for n in nodes:
            n.start()
        nodes[0].put("mesh_key", "hyperion")
        time.sleep(0.2)  # wait for gossip rounds
        for n in nodes:
            self.assertEqual(n.get("mesh_key"), "hyperion", f"{n.node_id} didn't converge")
        for n in nodes:
            n.stop()

    def test_convergence_multiple_keys(self):
        nodes = self._make_cluster(3)
        for n in nodes:
            n.start()
        nodes[0].put("shard_map", {"a": [0, 1]})
        nodes[1].put("ring_version", 42)
        time.sleep(0.3)
        for n in nodes:
            self.assertIsNotNone(n.get("shard_map"))
            self.assertEqual(n.get("ring_version"), 42)
        for n in nodes:
            n.stop()

    def test_lww_conflict_resolution(self):
        a = GossipProtocol("a", interval_ms=50)
        b = GossipProtocol("b", interval_ms=50)
        a.register_peer(b)
        b.register_peer(a)

        a.put("x", "old")
        time.sleep(0.01)
        b.put("x", "new")  # newer timestamp

        a.start()
        b.start()
        time.sleep(0.2)

        # Both should converge to "new" (LWW)
        self.assertEqual(a.get("x"), "new")
        self.assertEqual(b.get("x"), "new")
        a.stop()
        b.stop()

    def test_status(self):
        nodes = self._make_cluster(3)
        nodes[0].put("k", "v")
        s = nodes[0].status()
        self.assertEqual(s["node_id"], "node-0")
        self.assertEqual(s["peers"], 2)
        self.assertEqual(s["keys"], 1)

    def test_get_with_clock(self):
        g = GossipProtocol("n")
        g.put("k", "v")
        result = g.get_with_clock("k")
        self.assertIsNotNone(result)
        val, clock = result
        self.assertEqual(val, "v")
        self.assertIsInstance(clock, VectorClock)
        self.assertEqual(clock.clock.get("n"), 1)

    def test_no_self_peer(self):
        g = GossipProtocol("n")
        g.register_peer(g)  # should not register self
        self.assertEqual(len(g._peers), 0)

    def test_keys(self):
        g = GossipProtocol("n")
        g.put("a", 1)
        g.put("b", 2)
        self.assertIn("a", g.keys())
        self.assertIn("b", g.keys())


if __name__ == "__main__":
    unittest.main()
