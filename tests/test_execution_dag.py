"""
Tests for core/execution_dag.py — ExecutionDAG, DAGNode, DAGEdge.

All tests are deterministic, no network or blockchain calls.
"""

import os
import sys
import json
import tempfile
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.execution_dag import (
    ExecutionDAG, DAGNode, DAGEdge, CycleDetectedError,
    NODE_TYPES, EDGE_TYPES,
)


class TestDAGNodeCreation(unittest.TestCase):
    """Test adding nodes to the DAG."""

    def test_add_node_basic(self):
        dag = ExecutionDAG()
        node = dag.add_node("n1", "AGENT", {"agent_name": "TestAgent"})
        self.assertEqual(node.node_id, "n1")
        self.assertEqual(node.node_type, "AGENT")
        self.assertEqual(node.metadata["agent_name"], "TestAgent")
        self.assertEqual(node.status, "PENDING")
        self.assertIn("n1", dag.nodes)

    def test_add_node_all_types(self):
        dag = ExecutionDAG()
        for i, nt in enumerate(NODE_TYPES):
            dag.add_node(f"n{i}", nt)
        self.assertEqual(len(dag.nodes), len(NODE_TYPES))

    def test_add_node_invalid_type(self):
        dag = ExecutionDAG()
        with self.assertRaises(ValueError):
            dag.add_node("n1", "INVALID_TYPE")

    def test_add_node_no_metadata(self):
        dag = ExecutionDAG()
        node = dag.add_node("n1", "TOOL")
        self.assertEqual(node.metadata, {})

    def test_dag_has_uuid(self):
        dag = ExecutionDAG()
        self.assertTrue(len(dag.dag_id) > 0)
        self.assertIn("-", dag.dag_id)  # UUID format


class TestDAGEdgeCreation(unittest.TestCase):
    """Test adding edges to the DAG."""

    def test_add_edge_basic(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        edge = dag.add_edge("a", "b", "VERIFIES")
        self.assertEqual(edge.from_id, "a")
        self.assertEqual(edge.to_id, "b")
        self.assertEqual(edge.edge_type, "VERIFIES")
        self.assertEqual(len(dag.edges), 1)

    def test_add_edge_all_types(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "BLOCKCHAIN")
        for et in EDGE_TYPES:
            dag.add_edge("a", "b", et)
        self.assertEqual(len(dag.edges), len(EDGE_TYPES))

    def test_add_edge_invalid_type(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "TOOL")
        with self.assertRaises(ValueError):
            dag.add_edge("a", "b", "INVALID")

    def test_add_edge_missing_source(self):
        dag = ExecutionDAG()
        dag.add_node("b", "TOOL")
        with self.assertRaises(ValueError):
            dag.add_edge("missing", "b", "DELEGATES")

    def test_add_edge_missing_target(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        with self.assertRaises(ValueError):
            dag.add_edge("a", "missing", "DELEGATES")

    def test_add_edge_with_metadata(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "STORAGE")
        edge = dag.add_edge("a", "b", "PUBLISHES", {"latency_ms": 42.5, "protocol": "JSONL"})
        self.assertEqual(edge.latency_ms, 42.5)
        self.assertEqual(edge.metadata["protocol"], "JSONL")


class TestCycleDetection(unittest.TestCase):
    """Test cycle detection in the DAG."""

    def test_no_cycles_linear(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "BLOCKCHAIN")
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("b", "c", "PUBLISHES")
        self.assertEqual(dag.detect_cycles(), [])

    def test_no_cycles_diamond(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "VERIFICATION")
        dag.add_node("d", "BLOCKCHAIN")
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("a", "c", "VERIFIES")
        dag.add_edge("b", "d", "PUBLISHES")
        dag.add_edge("c", "d", "PUBLISHES")
        self.assertEqual(dag.detect_cycles(), [])

    def test_cycle_detected_simple(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "AGENT")
        dag.add_node("c", "AGENT")
        dag.add_edge("a", "b", "DELEGATES")
        dag.add_edge("b", "c", "DELEGATES")
        dag.add_edge("c", "a", "DELEGATES")
        cycles = dag.detect_cycles()
        self.assertTrue(len(cycles) > 0)
        # The cycle should contain a, b, c
        cycle_nodes = set(cycles[0][:-1])  # last is repeat of first
        self.assertTrue({"a", "b", "c"}.issubset(cycle_nodes))

    def test_cycle_detected_self_loop(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_edge("a", "a", "DELEGATES")
        cycles = dag.detect_cycles()
        self.assertTrue(len(cycles) > 0)

    def test_no_cycles_empty_graph(self):
        dag = ExecutionDAG()
        self.assertEqual(dag.detect_cycles(), [])

    def test_no_cycles_single_node(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        self.assertEqual(dag.detect_cycles(), [])


class TestTopologicalSort(unittest.TestCase):
    """Test topological sorting."""

    def test_topo_sort_linear(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "BLOCKCHAIN")
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("b", "c", "PUBLISHES")
        order = dag.topological_sort()
        self.assertEqual(order.index("a"), 0)
        self.assertTrue(order.index("b") < order.index("c"))

    def test_topo_sort_with_cycle_raises(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "AGENT")
        dag.add_edge("a", "b", "DELEGATES")
        dag.add_edge("b", "a", "DELEGATES")
        with self.assertRaises(CycleDetectedError) as ctx:
            dag.topological_sort()
        self.assertTrue(len(ctx.exception.cycles) > 0)

    def test_topo_sort_empty(self):
        dag = ExecutionDAG()
        self.assertEqual(dag.topological_sort(), [])

    def test_topo_sort_single_node(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        self.assertEqual(dag.topological_sort(), ["a"])

    def test_topo_sort_respects_all_edges(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "VERIFICATION")
        dag.add_node("d", "BLOCKCHAIN")
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("a", "c", "VERIFIES")
        dag.add_edge("b", "d", "PUBLISHES")
        dag.add_edge("c", "d", "PUBLISHES")
        order = dag.topological_sort()
        self.assertTrue(order.index("a") < order.index("b"))
        self.assertTrue(order.index("a") < order.index("c"))
        self.assertTrue(order.index("b") < order.index("d"))
        self.assertTrue(order.index("c") < order.index("d"))


class TestCriticalPath(unittest.TestCase):
    """Test critical path calculation."""

    def test_critical_path_linear(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "BLOCKCHAIN")
        dag.nodes["a"].duration_ms = 100
        dag.nodes["b"].duration_ms = 200
        dag.nodes["c"].duration_ms = 50
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("b", "c", "PUBLISHES")
        cp = dag.critical_path()
        self.assertEqual(cp["path"], ["a", "b", "c"])
        self.assertEqual(cp["total_duration_ms"], 350.0)
        self.assertEqual(cp["bottleneck_node"], "b")

    def test_critical_path_two_branches(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b1", "GOVERNANCE")
        dag.add_node("b2", "VERIFICATION")
        dag.add_node("c", "BLOCKCHAIN")
        dag.nodes["a"].duration_ms = 10
        dag.nodes["b1"].duration_ms = 100
        dag.nodes["b2"].duration_ms = 500
        dag.nodes["c"].duration_ms = 10
        dag.add_edge("a", "b1", "VERIFIES")
        dag.add_edge("a", "b2", "VERIFIES")
        dag.add_edge("b1", "c", "PUBLISHES")
        dag.add_edge("b2", "c", "PUBLISHES")
        cp = dag.critical_path()
        # Longer path goes through b2
        self.assertIn("b2", cp["path"])
        self.assertEqual(cp["bottleneck_node"], "b2")

    def test_critical_path_empty_dag(self):
        dag = ExecutionDAG()
        cp = dag.critical_path()
        self.assertEqual(cp["path"], [])
        self.assertEqual(cp["total_duration_ms"], 0.0)


class TestDependencies(unittest.TestCase):
    """Test get_dependencies and get_dependents."""

    def setUp(self):
        self.dag = ExecutionDAG()
        self.dag.add_node("a", "AGENT")
        self.dag.add_node("b", "GOVERNANCE")
        self.dag.add_node("c", "BLOCKCHAIN")
        self.dag.add_edge("a", "b", "VERIFIES")
        self.dag.add_edge("b", "c", "PUBLISHES")

    def test_get_dependencies(self):
        deps = self.dag.get_dependencies("b")
        self.assertEqual(deps, ["a"])

    def test_get_dependencies_root(self):
        deps = self.dag.get_dependencies("a")
        self.assertEqual(deps, [])

    def test_get_dependents(self):
        deps = self.dag.get_dependents("b")
        self.assertEqual(deps, ["c"])

    def test_get_dependents_leaf(self):
        deps = self.dag.get_dependents("c")
        self.assertEqual(deps, [])

    def test_get_dependencies_invalid_node(self):
        with self.assertRaises(ValueError):
            self.dag.get_dependencies("nonexistent")

    def test_get_dependents_invalid_node(self):
        with self.assertRaises(ValueError):
            self.dag.get_dependents("nonexistent")


class TestNodeDepth(unittest.TestCase):
    """Test get_node_depth."""

    def test_depth_root(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        self.assertEqual(dag.get_node_depth("a"), 0)

    def test_depth_linear(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_node("c", "BLOCKCHAIN")
        dag.add_edge("a", "b", "VERIFIES")
        dag.add_edge("b", "c", "PUBLISHES")
        self.assertEqual(dag.get_node_depth("a"), 0)
        self.assertEqual(dag.get_node_depth("b"), 1)
        self.assertEqual(dag.get_node_depth("c"), 2)

    def test_depth_invalid_node(self):
        dag = ExecutionDAG()
        with self.assertRaises(ValueError):
            dag.get_node_depth("nonexistent")


class TestSerialization(unittest.TestCase):
    """Test to_dict and JSON serialization."""

    def test_to_dict_roundtrip(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT", {"agent_name": "Apex"})
        dag.add_node("b", "GOVERNANCE")
        dag.nodes["a"].duration_ms = 100
        dag.nodes["b"].duration_ms = 50
        dag.add_edge("a", "b", "VERIFIES")

        d = dag.to_dict()
        self.assertEqual(d["node_count"], 2)
        self.assertEqual(d["edge_count"], 1)
        self.assertIn("a", d["nodes"])
        self.assertIn("b", d["nodes"])
        self.assertEqual(d["cycles"], [])
        self.assertIn("critical_path", d)
        self.assertIn("depth_map", d)

    def test_json_serializable(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "BLOCKCHAIN")
        dag.add_edge("a", "b", "PUBLISHES")
        d = dag.to_dict()
        s = json.dumps(d)
        self.assertIsInstance(s, str)
        parsed = json.loads(s)
        self.assertEqual(parsed["node_count"], 2)

    def test_save_to_file(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT")
        dag.add_node("b", "GOVERNANCE")
        dag.add_edge("a", "b", "VERIFIES")

        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test_dag.json")
        saved = dag.save(path)
        self.assertTrue(os.path.exists(saved))

        with open(saved) as f:
            data = json.load(f)
        self.assertEqual(data["node_count"], 2)


class TestMermaid(unittest.TestCase):
    """Test Mermaid diagram generation."""

    def test_mermaid_basic(self):
        dag = ExecutionDAG()
        dag.add_node("a", "AGENT", {"agent_name": "Apex"})
        dag.add_node("b", "GOVERNANCE", {"agent_name": "DOF Gov"})
        dag.add_edge("a", "b", "VERIFIES")
        mermaid = dag.to_mermaid()
        self.assertIn("graph LR", mermaid)
        self.assertIn("Apex", mermaid)
        self.assertIn("DOF Gov", mermaid)
        self.assertIn("VERIFIES", mermaid)
        self.assertIn("classDef agent", mermaid)
        self.assertIn("classDef governance", mermaid)

    def test_mermaid_all_node_types(self):
        dag = ExecutionDAG()
        for i, nt in enumerate(NODE_TYPES):
            dag.add_node(f"n{i}", nt, {"agent_name": f"Node_{nt}"})
        mermaid = dag.to_mermaid()
        self.assertIn("classDef agent", mermaid)
        self.assertIn("classDef blockchain", mermaid)
        self.assertIn("classDef storage", mermaid)

    def test_mermaid_empty(self):
        dag = ExecutionDAG()
        mermaid = dag.to_mermaid()
        self.assertIn("graph LR", mermaid)


class TestFromTraceRecords(unittest.TestCase):
    """Test building DAG from trace records."""

    def test_from_trace_records_basic(self):
        records = [
            {
                "round_number": 1,
                "round_type": "AVAX_TRANSFER",
                "initiator_name": "Apex",
                "target_name": "AvaBuilder",
                "action_duration_ms": 2947.3,
                "governance_duration_ms": 3.1,
                "onchain_duration_ms": 2783.1,
                "enigma_duration_ms": 4285.7,
            },
            {
                "round_number": 2,
                "round_type": "AVAX_TRANSFER",
                "initiator_name": "AvaBuilder",
                "target_name": "Apex",
                "action_duration_ms": 3212.5,
                "governance_duration_ms": 0.2,
                "onchain_duration_ms": 4527.3,
                "enigma_duration_ms": 3932.9,
            },
        ]
        dag = ExecutionDAG.from_trace_records(records)
        # 2 rounds × 4 nodes = 8 nodes
        self.assertEqual(len(dag.nodes), 8)
        # Each round has 3 internal edges + 1 cross-round edge (R1→R2) = 7
        self.assertEqual(len(dag.edges), 7)
        # No cycles
        self.assertEqual(dag.detect_cycles(), [])

    def test_from_trace_records_single(self):
        records = [
            {
                "round_number": 1,
                "round_type": "A2A_DISCOVERY",
                "initiator_name": "Apex",
                "target_name": "AvaBuilder",
                "action_duration_ms": 468.0,
                "governance_duration_ms": 0.1,
                "onchain_duration_ms": 4925.0,
                "enigma_duration_ms": 3802.6,
            },
        ]
        dag = ExecutionDAG.from_trace_records(records)
        self.assertEqual(len(dag.nodes), 4)
        self.assertEqual(len(dag.edges), 3)

    def test_from_trace_records_durations_correct(self):
        records = [
            {
                "round_number": 1,
                "round_type": "TEST",
                "initiator_name": "A",
                "target_name": "B",
                "action_duration_ms": 100.0,
                "governance_duration_ms": 5.0,
                "onchain_duration_ms": 200.0,
                "enigma_duration_ms": 50.0,
            },
        ]
        dag = ExecutionDAG.from_trace_records(records)
        self.assertEqual(dag.nodes["R1_action"].duration_ms, 100.0)
        self.assertEqual(dag.nodes["R1_gov"].duration_ms, 5.0)
        self.assertEqual(dag.nodes["R1_chain"].duration_ms, 200.0)
        self.assertEqual(dag.nodes["R1_enigma"].duration_ms, 50.0)

    def test_from_trace_records_critical_path(self):
        records = [
            {
                "round_number": 1,
                "round_type": "TEST",
                "initiator_name": "A",
                "target_name": "B",
                "action_duration_ms": 100.0,
                "governance_duration_ms": 5.0,
                "onchain_duration_ms": 200.0,
                "enigma_duration_ms": 50.0,
            },
        ]
        dag = ExecutionDAG.from_trace_records(records)
        cp = dag.critical_path()
        self.assertEqual(cp["total_duration_ms"], 355.0)
        self.assertEqual(cp["bottleneck_node"], "R1_chain")

    def test_from_trace_records_empty(self):
        dag = ExecutionDAG.from_trace_records([])
        self.assertEqual(len(dag.nodes), 0)
        self.assertEqual(len(dag.edges), 0)


class TestFromRealData(unittest.TestCase):
    """Test building DAG from actual agent_10_rounds.json if available."""

    def test_from_real_data_if_available(self):
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs", "agent_10_rounds.json",
        )
        if not os.path.exists(data_path):
            self.skipTest("logs/agent_10_rounds.json not found")

        with open(data_path) as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            records = data
        else:
            records = data.get("rounds", data.get("traces", []))
        if not records:
            self.skipTest("No round data in agent_10_rounds.json")

        dag = ExecutionDAG.from_trace_records(records)
        self.assertTrue(len(dag.nodes) > 0)
        self.assertEqual(dag.detect_cycles(), [])


if __name__ == "__main__":
    unittest.main()
