"""Tests for Tool Result Budgeting — Item 4 Plan Abril 2026."""
import unittest
from core.tool_hooks import ToolHookPipeline, TOOL_OUTPUT_LIMITS


class TestBudgetOutput(unittest.TestCase):

    def setUp(self):
        self.pipeline = ToolHookPipeline()

    def test_output_within_limit_unchanged(self):
        short = "x" * 100
        result = self.pipeline._budget_output("Bash", short)
        self.assertEqual(result, short)

    def test_bash_truncated_at_limit(self):
        big = "a" * 20_000
        result = self.pipeline._budget_output("Bash", big)
        self.assertLessEqual(len(result), TOOL_OUTPUT_LIMITS["Bash"] + 100)
        self.assertIn("truncated", result)

    def test_read_has_larger_limit_than_bash(self):
        self.assertGreater(TOOL_OUTPUT_LIMITS["Read"], TOOL_OUTPUT_LIMITS["Bash"])

    def test_default_limit_applied_for_unknown_tool(self):
        big = "z" * 20_000
        result = self.pipeline._budget_output("UnknownTool", big)
        self.assertLessEqual(len(result), TOOL_OUTPUT_LIMITS["_default"] + 100)
        self.assertIn("truncated", result)

    def test_empty_output_unchanged(self):
        self.assertEqual(self.pipeline._budget_output("Bash", ""), "")

    def test_post_tool_use_output_preview_respects_budget(self):
        big_output = "B" * 20_000
        result = self.pipeline.post_tool_use("Bash", big_output, "agent-test")
        preview = result.trace_entry.get("output_preview", "")
        # preview is max 200 chars of budgeted output
        self.assertLessEqual(len(preview), 200)
        self.assertTrue(result.trace_entry.get("output_budgeted"))

    def test_post_tool_use_small_output_not_budgeted(self):
        small = "ok"
        result = self.pipeline.post_tool_use("Bash", small, "agent-test")
        self.assertFalse(result.trace_entry.get("output_budgeted"))

    def test_hash_uses_raw_not_budgeted(self):
        """Attestation hash must be stable regardless of budgeting."""
        import hashlib, time
        output = "C" * 20_000
        result1 = self.pipeline.post_tool_use("Bash", output, "agent-1")
        # hash is based on first 500 chars of raw output — not the budgeted version
        self.assertTrue(result1.attestation_hash.startswith("0x"))


if __name__ == "__main__":
    unittest.main()
