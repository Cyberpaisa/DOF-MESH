"""
Tests for core/graphify_tool.py — GraphifyTool CrewAI wrapper.
"""

import json
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.graphify_tool import GraphifyTool, create_graphify_tool


class TestGraphifyToolBasic(unittest.TestCase):
    """Metadata and instantiation checks."""

    def setUp(self):
        self.tool = create_graphify_tool()

    def test_tool_has_correct_name(self):
        self.assertEqual(self.tool.name, "graphify_code_graph")

    def test_tool_has_description(self):
        self.assertIsInstance(self.tool.description, str)
        self.assertGreater(len(self.tool.description), 10)

    def test_create_graphify_tool_returns_instance(self):
        tool = create_graphify_tool()
        self.assertIsInstance(tool, GraphifyTool)


class TestGraphifyFallback(unittest.TestCase):
    """Fallback AST scan (graphify_integration=False, the default)."""

    def setUp(self):
        from core.feature_flags import flags
        flags.disable("graphify_integration")
        self.tool = create_graphify_tool()

    def tearDown(self):
        from core.feature_flags import flags
        flags.reset("graphify_integration")

    # ── Core tests ────────────────────────────────────────────────────────────

    def test_fallback_returns_json_when_flag_disabled(self):
        raw = self.tool._run("governance")
        data = json.loads(raw)
        self.assertIn("modules", data)
        self.assertIn("classes", data)
        self.assertIn("functions", data)
        self.assertIn("query", data)
        self.assertEqual(data["query"], "governance")

    def test_fallback_finds_governance_module(self):
        raw = self.tool._run("governance")
        data = json.loads(raw)
        self.assertIn("governance", data["modules"],
                      "Expected 'governance' in modules for query='governance'")

    def test_fallback_finds_z3_verifier(self):
        raw = self.tool._run("z3")
        data = json.loads(raw)
        self.assertTrue(
            any("z3" in m.lower() for m in data["modules"]),
            "Expected at least one module with 'z3' in its name",
        )

    def test_empty_query_returns_all_modules(self):
        raw = self.tool._run("")
        data = json.loads(raw)
        # core/ has dozens of modules — sanity check we get a non-trivial count
        self.assertGreater(len(data["modules"]), 10,
                           "Empty query should return all core modules")

    def test_never_raises(self):
        """_run must never propagate exceptions, even for nonsense input."""
        for query in ["", "nonexistent_xyz_abc", "!!!", "governance", "z3_verifier"]:
            with self.subTest(query=query):
                try:
                    result = self.tool._run(query)
                    # Must be valid JSON
                    json.loads(result)
                except Exception as exc:  # pragma: no cover
                    self.fail(f"_run raised {type(exc).__name__} for query={query!r}: {exc}")

    def test_arun_delegates_to_run(self):
        raw_run = self.tool._run("supervisor")
        raw_arun = self.tool._arun("supervisor")
        self.assertEqual(raw_run, raw_arun)


class TestGraphifyWithFlagEnabled(unittest.TestCase):
    """When flag is enabled, placeholder still returns valid JSON."""

    def setUp(self):
        from core.feature_flags import flags
        flags.enable("graphify_integration")
        self.tool = create_graphify_tool()

    def tearDown(self):
        from core.feature_flags import flags
        flags.reset("graphify_integration")

    def test_plugin_placeholder_returns_valid_json(self):
        raw = self.tool._run("governance")
        data = json.loads(raw)
        self.assertIn("modules", data)
        self.assertIn("query", data)


if __name__ == "__main__":
    unittest.main()
