"""
Tests for integrations/langgraph_adapter.py

Covers:
  - DOFGovernanceNode: output extraction, pass/fail, empty state
  - DOFASTNode: safe code, unsafe code, empty code
  - DOFMemoryNode: add, query, unknown action
  - DOFObservabilityNode: trace step creation
  - GenericAdapter: wrap_output, wrap_code
  - CrewAIAdapter: wrap_output, wrap_code
  - LangGraphAdapter: wrap_output, wrap_code, get_nodes
  - create_governed_pipeline: returns all nodes
  - dof public API imports
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from integrations.langgraph_adapter import (
    DOFGovernanceNode,
    DOFASTNode,
    DOFMemoryNode,
    DOFObservabilityNode,
    FrameworkAdapter,
    GenericAdapter,
    CrewAIAdapter,
    LangGraphAdapter,
    create_governed_pipeline,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

GOOD_OUTPUT = (
    "## Analysis\n\n"
    "The technology sector shows strong growth indicators.\n\n"
    "- Cloud computing revenue increased 28% YoY\n"
    "- AI adoption reached 67% in enterprise\n\n"
    "Sources: https://example.com/report\n\n"
    "Next steps:\n"
    "1. Implement cloud-first strategy\n"
    "2. Recommend investing in AI training programs\n"
)

BAD_OUTPUT = "According to recent studies, Python is 10x faster than C++."

SAFE_CODE = "def add(a, b):\n    return a + b\n"

UNSAFE_CODE = "import subprocess\nresult = eval('2+2')\n"


# ── DOFGovernanceNode ────────────────────────────────────────────────────────

class TestDOFGovernanceNode(unittest.TestCase):

    def setUp(self):
        self.node = DOFGovernanceNode()

    def test_good_output_passes(self):
        state = {"output": GOOD_OUTPUT}
        state = self.node(state)
        self.assertTrue(state["governance_pass"])
        self.assertIsInstance(state["governance_result"], dict)
        self.assertGreater(state["governance_result"]["score"], 0.0)

    def test_bad_output_fails(self):
        state = {"output": BAD_OUTPUT}
        state = self.node(state)
        self.assertFalse(state["governance_pass"])
        self.assertTrue(len(state["governance_result"]["violations"]) > 0)

    def test_empty_state(self):
        state = {}
        state = self.node(state)
        self.assertFalse(state["governance_pass"])

    def test_extract_from_messages(self):
        state = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": GOOD_OUTPUT},
            ]
        }
        state = self.node(state)
        self.assertTrue(state["governance_pass"])

    def test_extract_from_string_messages(self):
        state = {"messages": ["first message", GOOD_OUTPUT]}
        state = self.node(state)
        # Should extract last string message
        self.assertTrue(state["governance_pass"])


# ── DOFASTNode ───────────────────────────────────────────────────────────────

class TestDOFASTNode(unittest.TestCase):

    def setUp(self):
        self.node = DOFASTNode()

    def test_safe_code_passes(self):
        state = {"code": SAFE_CODE}
        state = self.node(state)
        self.assertTrue(state["ast_result"]["passed"])
        self.assertEqual(state["ast_result"]["score"], 1.0)

    def test_unsafe_code_fails(self):
        state = {"code": UNSAFE_CODE}
        state = self.node(state)
        self.assertFalse(state["ast_result"]["passed"])
        self.assertTrue(len(state["ast_result"]["violations"]) > 0)

    def test_empty_code_passes(self):
        state = {"code": ""}
        state = self.node(state)
        self.assertTrue(state["ast_result"]["passed"])


# ── DOFMemoryNode ────────────────────────────────────────────────────────────

class TestDOFMemoryNode(unittest.TestCase):

    def test_add_action(self):
        node = DOFMemoryNode()
        state = {
            "memory_action": "add",
            "memory_content": "Python is a programming language used for data science and web development.",
            "memory_category": "knowledge",
        }
        state = node(state)
        self.assertEqual(state["memory_result"]["action"], "add")
        self.assertIn("memory_id", state["memory_result"])

    def test_query_action(self):
        node = DOFMemoryNode()
        state = {
            "memory_action": "query",
            "memory_query": "python",
            "memory_category": "knowledge",
        }
        state = node(state)
        self.assertEqual(state["memory_result"]["action"], "query")
        self.assertIn("count", state["memory_result"])

    def test_unknown_action(self):
        node = DOFMemoryNode()
        state = {"memory_action": "delete"}
        state = node(state)
        self.assertIn("error", state["memory_result"])

    def test_add_empty_content(self):
        node = DOFMemoryNode()
        state = {"memory_action": "add", "memory_content": ""}
        state = node(state)
        self.assertIn("error", state["memory_result"])


# ── DOFObservabilityNode ─────────────────────────────────────────────────────

class TestDOFObservabilityNode(unittest.TestCase):

    def test_creates_trace_step(self):
        node = DOFObservabilityNode()
        state = {
            "step_index": 0,
            "agent": "researcher",
            "provider": "groq",
            "latency_ms": 250.0,
            "status": "completed",
            "governance_pass": True,
        }
        state = node(state)
        self.assertIn("trace_step", state)
        self.assertEqual(state["trace_step"]["agent"], "researcher")
        self.assertEqual(state["trace_step"]["provider"], "groq")
        self.assertEqual(state["trace_step"]["latency_ms"], 250.0)


# ── GenericAdapter ───────────────────────────────────────────────────────────

class TestGenericAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = GenericAdapter()

    def test_wrap_output_good(self):
        result = self.adapter.wrap_output(GOOD_OUTPUT)
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["score"], 0.0)

    def test_wrap_output_bad(self):
        result = self.adapter.wrap_output(BAD_OUTPUT)
        self.assertEqual(result["status"], "fail")

    def test_wrap_code_safe(self):
        result = self.adapter.wrap_code(SAFE_CODE)
        self.assertTrue(result["passed"])

    def test_wrap_code_unsafe(self):
        result = self.adapter.wrap_code(UNSAFE_CODE)
        self.assertFalse(result["passed"])

    def test_record_step(self):
        # Should not raise
        self.adapter.record_step({
            "step_index": 0,
            "agent": "test",
            "provider": "test",
        })


# ── CrewAIAdapter ────────────────────────────────────────────────────────────

class TestCrewAIAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = CrewAIAdapter()

    def test_wrap_output(self):
        result = self.adapter.wrap_output(GOOD_OUTPUT)
        self.assertEqual(result["status"], "pass")

    def test_wrap_code(self):
        result = self.adapter.wrap_code(SAFE_CODE)
        self.assertTrue(result["passed"])


# ── LangGraphAdapter ────────────────────────────────────────────────────────

class TestLangGraphAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = LangGraphAdapter()

    def test_wrap_output(self):
        result = self.adapter.wrap_output(GOOD_OUTPUT)
        self.assertTrue(result.get("passed", False))

    def test_wrap_code(self):
        result = self.adapter.wrap_code(SAFE_CODE)
        self.assertTrue(result["passed"])

    def test_get_nodes(self):
        nodes = self.adapter.get_nodes()
        self.assertIn("governance", nodes)
        self.assertIn("ast", nodes)
        self.assertIn("observability", nodes)
        self.assertTrue(callable(nodes["governance"]))
        self.assertTrue(callable(nodes["ast"]))

    def test_record_step(self):
        # Should not raise
        self.adapter.record_step({
            "step_index": 0,
            "agent": "test",
            "provider": "test",
        })


# ── create_governed_pipeline ─────────────────────────────────────────────────

class TestCreateGovernedPipeline(unittest.TestCase):

    def test_returns_all_nodes(self):
        nodes = create_governed_pipeline()
        self.assertIn("governance", nodes)
        self.assertIn("ast", nodes)
        self.assertIn("memory", nodes)
        self.assertIn("observability", nodes)

    def test_nodes_are_callable(self):
        nodes = create_governed_pipeline()
        for name, node in nodes.items():
            self.assertTrue(callable(node), f"{name} is not callable")


# ── dof imports ──────────────────────────────────────────────────────────────

class TestDofIntegrationImports(unittest.TestCase):

    def test_import_governance_node(self):
        from dof import DOFGovernanceNode
        self.assertTrue(callable(DOFGovernanceNode))

    def test_import_framework_adapter(self):
        from dof import FrameworkAdapter
        self.assertIsNotNone(FrameworkAdapter)

    def test_import_generic_adapter(self):
        from dof import GenericAdapter
        adapter = GenericAdapter()
        result = adapter.wrap_output(GOOD_OUTPUT)
        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
