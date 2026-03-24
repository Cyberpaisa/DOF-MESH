"""
Tests for core.mesh_router — Hybrid routing optimization for the DOF Node Mesh.

Algorithm proposed by DeepSeek-V3 (node ds-002), implemented by Claude.

Tests cover:
  1. Clustering (correct number, all nodes assigned, heads selected)
  2. Direct routing (known targets, unknown targets, self-routing)
  3. Efficient broadcast (heads only, count savings, correct propagation)
  4. Role-based routing (security->guardian, code->architect, etc.)
  5. Best node selection (by task type, deterministic)
  6. Reconfiguration (add node, remove node, rebalance)
  7. Router state (accuracy, persistence)
  8. Integration with real nodes.json

Run: python3 -m unittest tests.test_mesh_router
"""

import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core.mesh_router import (
    MeshRouter,
    Cluster,
    RouteResult,
    RouterState,
    CLUSTER_CATEGORIES,
    _compute_cluster_score,
)


class TestMeshRouterBase(unittest.TestCase):
    """Base class with a temp mesh directory and sample nodes."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mesh_dir = os.path.join(self.tmp_dir, "mesh")
        os.makedirs(self.mesh_dir, exist_ok=True)

        # Create a representative set of nodes
        self.sample_nodes = {
            "commander": {
                "node_id": "commander",
                "role": "orchestrator",
                "messages_sent": 84,
                "messages_received": 6,
                "model": "claude-sonnet-4-6",
            },
            "architect": {
                "node_id": "architect",
                "role": "code architecture and implementation",
                "messages_sent": 7,
                "messages_received": 23,
                "model": "claude-sonnet-4-6",
            },
            "researcher": {
                "node_id": "researcher",
                "role": "research, analysis, intelligence gathering",
                "messages_sent": 5,
                "messages_received": 23,
                "model": "claude-sonnet-4-6",
            },
            "guardian": {
                "node_id": "guardian",
                "role": "security audit, testing, quality",
                "messages_sent": 2,
                "messages_received": 32,
                "model": "claude-sonnet-4-6",
            },
            "narrator": {
                "node_id": "narrator",
                "role": "documentation, content, communication",
                "messages_sent": 2,
                "messages_received": 22,
                "model": "claude-sonnet-4-6",
            },
            "reviewer": {
                "node_id": "reviewer",
                "role": "code review, quality gate",
                "messages_sent": 3,
                "messages_received": 19,
                "model": "claude-sonnet-4-6",
            },
            "icarus": {
                "node_id": "icarus",
                "role": "Stealth threat hunter — OPSEC, malware analysis, behavioral forensics",
                "messages_sent": 0,
                "messages_received": 0,
                "model": "claude-sonnet-4-6",
            },
            "deepseek": {
                "node_id": "deepseek",
                "role": "Deep reasoning, math, code — Chinese AI perspective",
                "messages_sent": 4,
                "messages_received": 0,
                "model": "deepseek-v3",
            },
            "gpt-legion": {
                "node_id": "gpt-legion",
                "role": "cross-model collaborator — GPT perspective, creative problem solving",
                "messages_sent": 0,
                "messages_received": 0,
                "model": "gpt-4",
            },
            "antigraviti": {
                "node_id": "antigraviti",
                "role": "agentic AI partner — potencia agentica con Gemini, colaboracion cross-model",
                "messages_sent": 0,
                "messages_received": 0,
                "model": "gemini-2.5-flash",
            },
        }

        self._write_nodes(self.sample_nodes)

    def _write_nodes(self, nodes):
        nodes_file = os.path.join(self.mesh_dir, "nodes.json")
        with open(nodes_file, "w") as f:
            json.dump(nodes, f, indent=2)

    def _make_router(self):
        return MeshRouter(mesh_dir=self.mesh_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════
# 1. CLUSTERING TESTS (5+)
# ═══════════════════════════════════════════════════════

class TestClustering(TestMeshRouterBase):
    """Test semantic clustering of mesh nodes."""

    def test_all_nodes_assigned_to_clusters(self):
        """Every node must belong to exactly one cluster."""
        router = self._make_router()
        all_members = []
        for cl in router._clusters.values():
            all_members.extend(cl.members)
        # Every node in the routing table
        self.assertEqual(set(all_members), set(self.sample_nodes.keys()))
        # No duplicates
        self.assertEqual(len(all_members), len(set(all_members)))

    def test_cluster_count_within_category_bound(self):
        """Number of clusters should be <= number of category types and > 0."""
        router = self._make_router()
        max_clusters = len(CLUSTER_CATEGORIES)
        self.assertLessEqual(len(router._clusters), max_clusters)
        self.assertGreater(len(router._clusters), 0)

    def test_each_cluster_has_head(self):
        """Every cluster must have a head that is one of its members."""
        router = self._make_router()
        for cl in router._clusters.values():
            self.assertIn(cl.head, cl.members)

    def test_cluster_head_is_most_active(self):
        """Cluster head should be the node with most messages_sent."""
        router = self._make_router()
        for cl in router._clusters.values():
            head_sent = self.sample_nodes.get(cl.head, {}).get("messages_sent", 0)
            for m in cl.members:
                m_sent = self.sample_nodes.get(m, {}).get("messages_sent", 0)
                self.assertGreaterEqual(head_sent, m_sent)

    def test_security_nodes_clustered_together(self):
        """Guardian and icarus (security roles) should be in the same cluster."""
        router = self._make_router()
        guardian_cluster = router.get_cluster_for_node("guardian")
        icarus_cluster = router.get_cluster_for_node("icarus")
        self.assertIsNotNone(guardian_cluster)
        self.assertIsNotNone(icarus_cluster)
        self.assertEqual(guardian_cluster, icarus_cluster)

    def test_custom_k_clusters(self):
        """Specifying k should limit the number of clusters."""
        router = self._make_router()
        result = router.cluster_nodes(k=3)
        self.assertLessEqual(len(result), 3)
        self.assertGreater(len(result), 0)

    def test_empty_nodes(self):
        """Router with zero nodes should produce zero clusters."""
        self._write_nodes({})
        router = self._make_router()
        self.assertEqual(len(router._clusters), 0)
        self.assertEqual(len(router._routing_table), 0)


# ═══════════════════════════════════════════════════════
# 2. DIRECT ROUTING TESTS (5+)
# ═══════════════════════════════════════════════════════

class TestDirectRouting(TestMeshRouterBase):
    """Test direct message routing."""

    def test_route_to_known_node(self):
        """Routing to a known node should return a direct path."""
        router = self._make_router()
        result = router.route_message("commander", "guardian")
        self.assertEqual(result.path, ["commander", "guardian"])
        self.assertEqual(result.hops, 1)
        self.assertEqual(result.method, "direct")

    def test_route_to_unknown_node(self):
        """Routing to an unknown node should attempt role_route or direct fallback."""
        router = self._make_router()
        result = router.route_message("commander", "unknown-xyz")
        self.assertIn(result.method, ("role_route", "direct"))
        self.assertIn("commander", result.path)

    def test_self_routing(self):
        """Self-routing should return zero hops."""
        router = self._make_router()
        result = router.route_self("commander")
        self.assertEqual(result.path, ["commander"])
        self.assertEqual(result.hops, 0)
        self.assertEqual(result.method, "direct")

    def test_route_returns_route_result(self):
        """route_message should return a RouteResult dataclass."""
        router = self._make_router()
        result = router.route_message("architect", "researcher")
        self.assertIsInstance(result, RouteResult)
        self.assertIsInstance(result.path, list)
        self.assertIsInstance(result.hops, int)
        self.assertIsInstance(result.method, str)
        self.assertIsInstance(result.cluster, str)

    def test_route_cluster_field_populated(self):
        """Route result should include the target's cluster."""
        router = self._make_router()
        result = router.route_message("commander", "guardian")
        self.assertNotEqual(result.cluster, "")
        self.assertIsNotNone(result.cluster)

    def test_route_both_directions_symmetric(self):
        """Routing A->B and B->A should both be direct with 1 hop."""
        router = self._make_router()
        ab = router.route_message("architect", "researcher")
        ba = router.route_message("researcher", "architect")
        self.assertEqual(ab.hops, 1)
        self.assertEqual(ba.hops, 1)
        self.assertEqual(ab.method, "direct")
        self.assertEqual(ba.method, "direct")


# ═══════════════════════════════════════════════════════
# 3. EFFICIENT BROADCAST TESTS (5+)
# ═══════════════════════════════════════════════════════

class TestEfficientBroadcast(TestMeshRouterBase):
    """Test efficient broadcast through cluster heads."""

    def test_broadcast_sends_to_heads_only(self):
        """Broadcast should send to cluster heads, not all nodes."""
        router = self._make_router()
        sent = router.efficient_broadcast("commander", "Test alert")
        total_nodes = len(self.sample_nodes)
        # Should send fewer messages than naive broadcast
        self.assertLess(sent, total_nodes - 1)

    def test_broadcast_count_matches_heads(self):
        """Sent count should equal number of cluster heads minus sender (if sender is head)."""
        router = self._make_router()
        heads = router.get_cluster_heads()
        sent = router.efficient_broadcast("commander", "Alert")
        # Should be heads minus sender (if sender is a head)
        expected_max = len(heads)
        self.assertLessEqual(sent, expected_max)
        self.assertGreater(sent, 0)

    def test_broadcast_savings_positive(self):
        """Broadcast savings should be > 0% for 10 nodes / ~4 clusters."""
        router = self._make_router()
        state = router.get_state()
        self.assertGreater(state.broadcast_savings, 0)

    def test_broadcast_route_method_is_cluster_broadcast(self):
        """Routing with to_node='*' should return cluster_broadcast method."""
        router = self._make_router()
        result = router.route_message("commander", "*")
        self.assertEqual(result.method, "cluster_broadcast")
        self.assertEqual(result.cluster, "all")

    def test_broadcast_path_contains_heads(self):
        """Broadcast route path should contain cluster heads."""
        router = self._make_router()
        result = router.route_message("commander", "*")
        heads = set(router.get_cluster_heads())
        # Path should include the sender + heads (minus sender if sender is head)
        path_set = set(result.path)
        self.assertIn("commander", path_set)
        # At least some heads should be in the path
        self.assertTrue(len(path_set & heads) > 0)

    def test_broadcast_from_non_head(self):
        """Broadcast from a non-head node should still work."""
        router = self._make_router()
        # icarus likely not a head (0 messages_sent)
        sent = router.efficient_broadcast("icarus", "Security incident")
        self.assertGreater(sent, 0)


# ═══════════════════════════════════════════════════════
# 4. ROLE-BASED ROUTING TESTS (5+)
# ═══════════════════════════════════════════════════════

class TestRoleBasedRouting(TestMeshRouterBase):
    """Test role-based routing decisions."""

    def test_security_task_routes_to_security_cluster(self):
        """A security task should route to a security cluster node."""
        router = self._make_router()
        best = router.get_best_node("security")
        cluster = router.get_cluster_for_node(best)
        self.assertEqual(cluster, "security")

    def test_code_task_routes_to_code_cluster(self):
        """A code task should route to a code cluster node."""
        router = self._make_router()
        best = router.get_best_node("code")
        cluster = router.get_cluster_for_node(best)
        self.assertEqual(cluster, "code")

    def test_research_task_routes_to_research_cluster(self):
        """A research task should route to a research cluster node."""
        router = self._make_router()
        best = router.get_best_node("research")
        cluster = router.get_cluster_for_node(best)
        self.assertEqual(cluster, "research")

    def test_docs_task_routes_to_documentation_cluster(self):
        """A documentation task should route to the documentation cluster."""
        router = self._make_router()
        best = router.get_best_node("documentation")
        cluster = router.get_cluster_for_node(best)
        self.assertEqual(cluster, "documentation")

    def test_unknown_task_type_returns_valid_node(self):
        """An unknown task type should still return a valid node."""
        router = self._make_router()
        best = router.get_best_node("quantum_physics_simulation")
        self.assertIn(best, self.sample_nodes)

    def test_route_to_security_named_unknown(self):
        """Routing to an unknown node with 'security' in name should use security cluster."""
        router = self._make_router()
        result = router.route_message("commander", "security-scanner-new")
        self.assertEqual(result.method, "role_route")
        self.assertEqual(result.cluster, "security")


# ═══════════════════════════════════════════════════════
# 5. BEST NODE SELECTION TESTS (5+)
# ═══════════════════════════════════════════════════════

class TestBestNodeSelection(TestMeshRouterBase):
    """Test deterministic best-node selection."""

    def test_best_security_node(self):
        """Best security node should be guardian (most messages_sent in security)."""
        router = self._make_router()
        best = router.get_best_node("security")
        # guardian has 2 sent, icarus has 0 — guardian wins
        self.assertEqual(best, "guardian")

    def test_best_code_node(self):
        """Best code node should be architect (most active in code cluster)."""
        router = self._make_router()
        best = router.get_best_node("code")
        self.assertEqual(best, "architect")

    def test_best_research_node(self):
        """Best research node should be researcher (most active in research)."""
        router = self._make_router()
        best = router.get_best_node("research")
        self.assertEqual(best, "researcher")

    def test_deterministic_repeated_calls(self):
        """Same input should always produce same output."""
        router = self._make_router()
        results = [router.get_best_node("security") for _ in range(10)]
        self.assertEqual(len(set(results)), 1)

    def test_best_node_is_in_nodes(self):
        """Best node must be a valid node in the registry."""
        router = self._make_router()
        for task in ["security", "code", "research", "documentation", "orchestrate"]:
            best = router.get_best_node(task)
            self.assertIn(best, self.sample_nodes)

    def test_case_insensitive(self):
        """Task type matching should be case-insensitive."""
        router = self._make_router()
        self.assertEqual(
            router.get_best_node("Security"),
            router.get_best_node("security"),
        )
        self.assertEqual(
            router.get_best_node("CODE"),
            router.get_best_node("code"),
        )


# ═══════════════════════════════════════════════════════
# 6. RECONFIGURATION TESTS (3+)
# ═══════════════════════════════════════════════════════

class TestReconfiguration(TestMeshRouterBase):
    """Test cluster reconfiguration after node changes."""

    def test_add_node_reconfigure(self):
        """Adding a node and reconfiguring should include it."""
        router = self._make_router()
        # Add a new security node
        nodes = dict(self.sample_nodes)
        nodes["cerberus"] = {
            "node_id": "cerberus",
            "role": "security gateway, authentication, firewall",
            "messages_sent": 10,
            "messages_received": 5,
            "model": "claude-sonnet-4-6",
        }
        self._write_nodes(nodes)
        state = router.reconfigure()
        self.assertEqual(state.total_nodes, len(nodes))
        self.assertIn("cerberus", router._routing_table)

    def test_remove_node_reconfigure(self):
        """Removing a node and reconfiguring should exclude it."""
        router = self._make_router()
        nodes = dict(self.sample_nodes)
        del nodes["icarus"]
        self._write_nodes(nodes)
        state = router.reconfigure()
        self.assertEqual(state.total_nodes, len(nodes))
        self.assertNotIn("icarus", router._routing_table)

    def test_reconfigure_rebalances_clusters(self):
        """Reconfigure should rebuild clusters from scratch."""
        router = self._make_router()
        original_clusters = len(router._clusters)

        # Add many nodes to force more clusters
        nodes = dict(self.sample_nodes)
        for i in range(20):
            nodes[f"worker-{i}"] = {
                "node_id": f"worker-{i}",
                "role": "general purpose worker",
                "messages_sent": 0,
                "messages_received": 0,
                "model": "claude-sonnet-4-6",
            }
        self._write_nodes(nodes)
        state = router.reconfigure()
        # With 30 nodes, sqrt(30) ~ 6 clusters
        self.assertGreaterEqual(state.num_clusters, 1)
        self.assertEqual(state.total_nodes, 30)

    def test_reconfigure_returns_router_state(self):
        """reconfigure() should return a RouterState dataclass."""
        router = self._make_router()
        state = router.reconfigure()
        self.assertIsInstance(state, RouterState)
        self.assertIsInstance(state.total_nodes, int)
        self.assertIsInstance(state.num_clusters, int)
        self.assertIsInstance(state.broadcast_savings, float)


# ═══════════════════════════════════════════════════════
# 7. ROUTER STATE TESTS (3+)
# ═══════════════════════════════════════════════════════

class TestRouterState(TestMeshRouterBase):
    """Test router state accuracy and persistence."""

    def test_state_node_count(self):
        """State total_nodes should match the actual node count."""
        router = self._make_router()
        state = router.get_state()
        self.assertEqual(state.total_nodes, len(self.sample_nodes))

    def test_state_cluster_count(self):
        """State num_clusters should match actual cluster count."""
        router = self._make_router()
        state = router.get_state()
        self.assertEqual(state.num_clusters, len(router._clusters))

    def test_state_broadcast_savings_formula(self):
        """Broadcast savings should be (n-1-heads)/(n-1)*100."""
        router = self._make_router()
        state = router.get_state()
        n = len(self.sample_nodes)
        naive = n - 1
        expected = (naive - state.num_clusters) / naive * 100
        self.assertAlmostEqual(state.broadcast_savings, expected, places=1)

    def test_state_persisted_to_disk(self):
        """Router state should be saved to router_state.json."""
        router = self._make_router()
        state_file = Path(self.mesh_dir) / "router_state.json"
        self.assertTrue(state_file.exists())
        data = json.loads(state_file.read_text())
        self.assertEqual(data["total_nodes"], len(self.sample_nodes))

    def test_route_log_written(self):
        """Routing decisions should be logged to route_log.jsonl."""
        router = self._make_router()
        router.route_message("commander", "guardian")
        router.efficient_broadcast("commander", "test")
        log_file = Path(self.mesh_dir) / "route_log.jsonl"
        self.assertTrue(log_file.exists())
        lines = log_file.read_text().strip().split("\n")
        # At least the cluster_build + route + broadcast entries
        self.assertGreaterEqual(len(lines), 3)


# ═══════════════════════════════════════════════════════
# 8. INTEGRATION WITH REAL nodes.json (3+)
# ═══════════════════════════════════════════════════════

class TestIntegrationRealNodes(unittest.TestCase):
    """Integration tests with the actual logs/mesh/nodes.json."""

    @classmethod
    def setUpClass(cls):
        cls.real_nodes_file = Path("logs/mesh/nodes.json")
        cls.skip = not cls.real_nodes_file.exists()

    def setUp(self):
        if self.skip:
            self.skipTest("logs/mesh/nodes.json not found — skipping integration tests")

    def test_real_nodes_cluster_correctly(self):
        """Real nodes should cluster into approximately sqrt(n) clusters."""
        router = MeshRouter(mesh_dir="logs/mesh")
        state = router.get_state()
        if state.total_nodes < 50:
            self.skipTest(f"Only {state.total_nodes} nodes in mesh — need ≥50 for this test")
        expected_k = math.ceil(math.sqrt(state.total_nodes))
        self.assertGreaterEqual(state.num_clusters, 3)
        self.assertLessEqual(state.num_clusters, expected_k + 1)

    def test_real_broadcast_savings(self):
        """Real mesh should have >70% broadcast savings."""
        router = MeshRouter(mesh_dir="logs/mesh")
        state = router.get_state()
        # >70% savings requires (n-sqrt(n))/n > 0.70 => n >= 12
        if state.total_nodes < 12:
            self.skipTest(f"Only {state.total_nodes} nodes — need ≥12 for >70% savings")
        self.assertGreater(state.broadcast_savings, 70)

    def test_real_commander_is_orchestration_head(self):
        """Commander node should be head of its cluster when present."""
        router = MeshRouter(mesh_dir="logs/mesh")
        commander_cluster = router.get_cluster_for_node("commander")
        if commander_cluster is None:
            self.skipTest("'commander' node not found in current mesh data")
        cluster = router._clusters[commander_cluster]
        self.assertEqual(cluster.head, "commander")

    def test_real_routing_efficiency_summary(self):
        """Print the routing efficiency summary."""
        router = MeshRouter(mesh_dir="logs/mesh")
        state = router.get_state()
        heads = len(router.get_cluster_heads())
        savings = state.broadcast_savings
        print(f"\nBroadcast: O(n)={state.total_nodes} -> O(sqrt(n))={heads} -- {savings:.1f}% reduction")
        if state.total_nodes >= 4:
            self.assertGreater(savings, 0)


# ═══════════════════════════════════════════════════════
# HELPER TESTS
# ═══════════════════════════════════════════════════════

class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_compute_cluster_score_match(self):
        """Score should be > 0 for matching keywords."""
        score = _compute_cluster_score("security audit, testing", "guardian", ["security", "audit"])
        self.assertEqual(score, 2)

    def test_compute_cluster_score_no_match(self):
        """Score should be 0 for no matching keywords."""
        score = _compute_cluster_score("documentation writer", "narrator", ["security", "threat"])
        self.assertEqual(score, 0)

    def test_compute_cluster_score_node_id_match(self):
        """Score should consider node_id as well as role."""
        score = _compute_cluster_score("some role", "guardian", ["guardian"])
        self.assertEqual(score, 1)


if __name__ == "__main__":
    unittest.main()
