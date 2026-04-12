"""Tests for Concurrency Classification — Item 2 Plan Abril 2026."""
import unittest
from core.tool_hooks import ToolHookPipeline, CONCURRENT_SAFE_TOOLS, WRITE_TOOLS, SAFE_TOOLS


class TestConcurrencyClassification(unittest.TestCase):

    def setUp(self):
        self.pipeline = ToolHookPipeline()

    def test_read_is_concurrent_safe(self):
        self.assertEqual(self.pipeline.classify_tool("Read"), "concurrent_safe")

    def test_glob_is_concurrent_safe(self):
        self.assertEqual(self.pipeline.classify_tool("Glob"), "concurrent_safe")

    def test_grep_is_concurrent_safe(self):
        self.assertEqual(self.pipeline.classify_tool("Grep"), "concurrent_safe")

    def test_web_search_is_concurrent_safe(self):
        self.assertEqual(self.pipeline.classify_tool("web_search"), "concurrent_safe")

    def test_edit_is_write(self):
        self.assertEqual(self.pipeline.classify_tool("Edit"), "write")

    def test_write_tool_is_write(self):
        self.assertEqual(self.pipeline.classify_tool("Write"), "write")

    def test_bash_is_write(self):
        # Bash is in WRITE_TOOLS — executes arbitrary shell commands, must run serially
        self.assertEqual(self.pipeline.classify_tool("Bash"), "write")

    def test_unknown_tool_is_default(self):
        self.assertEqual(self.pipeline.classify_tool("SomeRandomTool"), "default")

    def test_concurrent_safe_is_superset_of_safe_tools(self):
        # Every SAFE_TOOL must be in CONCURRENT_SAFE_TOOLS
        for tool in SAFE_TOOLS:
            self.assertIn(tool, CONCURRENT_SAFE_TOOLS, f"{tool} not in CONCURRENT_SAFE_TOOLS")

    def test_write_and_concurrent_safe_are_disjoint(self):
        overlap = CONCURRENT_SAFE_TOOLS & WRITE_TOOLS
        self.assertEqual(len(overlap), 0, f"Overlap: {overlap}")


if __name__ == "__main__":
    unittest.main()
