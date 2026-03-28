"""Tests para Node Capability Manifest + Tiered Z3 Validation."""
import unittest
from datetime import datetime

from core.node_capability import (
    NodeCapabilityRegistry,
    NodeManifest,
    NodeTier,
    TIER_REQUIREMENTS,
)


class TestNodeRegistration(unittest.TestCase):
    def setUp(self):
        self.registry = NodeCapabilityRegistry()

    def test_register_core_node(self):
        m = self.registry.register_node("c1", 32.0, 50, ["avalanche-c"], "validator")
        self.assertEqual(m.tier, NodeTier.CORE)

    def test_register_standard_node(self):
        m = self.registry.register_node("s1", 8.0, 200, ["avalanche-c"], "executor")
        self.assertEqual(m.tier, NodeTier.STANDARD)

    def test_register_edge_node(self):
        m = self.registry.register_node("e1", 2.0, 400, ["fuji"], "observer")
        self.assertEqual(m.tier, NodeTier.EDGE)

    def test_low_memory_is_edge(self):
        m = self.registry.register_node("lo", 1.0, 50, ["fuji"], "observer")
        self.assertEqual(m.tier, NodeTier.EDGE)

    def test_high_timeout_is_standard(self):
        m = self.registry.register_node("ht", 16.0, 250, ["avalanche-c"], "validator")
        self.assertEqual(m.tier, NodeTier.STANDARD)

    def test_node_stored_in_registry(self):
        self.registry.register_node("n1", 32.0, 50, ["avalanche-c"], "validator")
        node = self.registry.get_node("n1")
        self.assertIsNotNone(node)
        self.assertEqual(node.node_id, "n1")

    def test_total_nodes_increments(self):
        self.assertEqual(self.registry.total_nodes, 0)
        self.registry.register_node("a", 4.0, 100, [], "observer")
        self.assertEqual(self.registry.total_nodes, 1)
        self.registry.register_node("b", 4.0, 100, [], "observer")
        self.assertEqual(self.registry.total_nodes, 2)

    def test_registered_at_is_set(self):
        m = self.registry.register_node("ts", 8.0, 200, [], "executor")
        self.assertIsInstance(m.registered_at, datetime)


class TestTierOperations(unittest.TestCase):
    def setUp(self):
        self.registry = NodeCapabilityRegistry()

    def test_get_nodes_by_tier_core(self):
        self.registry.register_node("c1", 32.0, 50, ["avalanche-c"], "validator")
        self.registry.register_node("c2", 64.0, 30, ["avalanche-c"], "validator")
        self.registry.register_node("s1", 8.0, 200, ["fuji"], "executor")
        cores = self.registry.get_nodes_by_tier(NodeTier.CORE)
        self.assertEqual(len(cores), 2)
        for n in cores:
            self.assertEqual(n.tier, NodeTier.CORE)

    def test_get_nodes_by_tier_empty(self):
        self.registry.register_node("s1", 8.0, 200, ["fuji"], "executor")
        cores = self.registry.get_nodes_by_tier(NodeTier.CORE)
        self.assertEqual(len(cores), 0)

    def test_tier_distribution(self):
        self.registry.register_node("c1", 32.0, 50, [], "validator")
        self.registry.register_node("c2", 64.0, 30, [], "validator")
        self.registry.register_node("s1", 8.0, 200, [], "executor")
        dist = self.registry.tier_distribution()
        self.assertEqual(dist["CORE"], 2)
        self.assertEqual(dist["STANDARD"], 1)
        self.assertEqual(dist["EDGE"], 0)

    def test_z3_mode_for_tier(self):
        modes = self.registry.z3_mode_for_tier
        self.assertEqual(modes["CORE"], "full")
        self.assertEqual(modes["STANDARD"], "partial")
        self.assertEqual(modes["EDGE"], "deferred")


class TestNodeRouting(unittest.TestCase):
    def setUp(self):
        self.registry = NodeCapabilityRegistry()
        self.registry.register_node("c1", 32.0, 50, ["avalanche-c"], "validator")
        self.registry.register_node("s1", 8.0, 200, ["avalanche-c", "fuji"], "executor")
        self.registry.register_node("e1", 2.0, 400, ["fuji"], "observer")

    def test_best_node_high_complexity(self):
        best = self.registry.best_node_for_constraint(complexity="high")
        self.assertIsNotNone(best)
        self.assertEqual(best.tier, NodeTier.CORE)

    def test_best_node_medium_complexity(self):
        best = self.registry.best_node_for_constraint(complexity="medium")
        self.assertIsNotNone(best)
        self.assertIn(best.tier, [NodeTier.CORE, NodeTier.STANDARD])

    def test_best_node_low_returns_fastest(self):
        best = self.registry.best_node_for_constraint(complexity="low")
        self.assertIsNotNone(best)
        self.assertEqual(best.node_id, "c1")  # 50ms es el más rápido

    def test_best_node_empty_registry(self):
        empty = NodeCapabilityRegistry()
        best = empty.best_node_for_constraint(complexity="high")
        self.assertIsNone(best)

    def test_get_nodes_by_chain(self):
        avax = self.registry.get_nodes_by_chain("avalanche-c")
        self.assertEqual(len(avax), 2)  # c1 y s1
        fuji = self.registry.get_nodes_by_chain("fuji")
        self.assertEqual(len(fuji), 2)  # s1 y e1


class TestNodeManagement(unittest.TestCase):
    def setUp(self):
        self.registry = NodeCapabilityRegistry()
        self.registry.register_node("n1", 32.0, 50, ["avalanche-c"], "validator")
        self.registry.register_node("n2", 8.0, 200, ["fuji"], "executor")

    def test_remove_node(self):
        result = self.registry.remove_node("n1")
        self.assertTrue(result)
        self.assertIsNone(self.registry.get_node("n1"))

    def test_remove_nonexistent(self):
        result = self.registry.remove_node("ghost")
        self.assertFalse(result)

    def test_chain_support_filter(self):
        self.registry.register_node("n3", 4.0, 300, ["avalanche-c", "fuji"], "observer")
        avax = self.registry.get_nodes_by_chain("avalanche-c")
        fuji = self.registry.get_nodes_by_chain("fuji")
        avax_ids = {n.node_id for n in avax}
        fuji_ids = {n.node_id for n in fuji}
        self.assertIn("n1", avax_ids)
        self.assertNotIn("n2", avax_ids)
        self.assertIn("n2", fuji_ids)
        self.assertIn("n3", avax_ids)
        self.assertIn("n3", fuji_ids)


if __name__ == "__main__":
    unittest.main()
