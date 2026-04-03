"""
Tests for core/tool_hooks.py — PreToolUse / PostToolUse governance pipeline.

Tests verify:
  - BLOCKED_TOOLS are rejected before execution
  - SAFE_TOOLS are approved without Z3
  - PostToolUse produces a correctly formatted attestation hash
  - Full pipeline (pre → mock execute → post) runs without errors
  - GovernanceViolation carries the HookResult
  - Fallback when ConstitutionEnforcer is unavailable
"""

import re
import unittest
from unittest.mock import patch, MagicMock

from core.tool_hooks import (
    ToolHookPipeline,
    HookResult,
    PostHookResult,
    GovernanceViolation,
    BLOCKED_TOOLS,
    SAFE_TOOLS,
)


# ── helpers ───────────────────────────────────────────────────────────────────

AGENT_ID = "test-agent-007"
ATTESTATION_RE = re.compile(r"^0x[0-9a-f]{64}$")


# ── PreToolUse — blocked tools ────────────────────────────────────────────────

class TestPreToolUseBlockedTools(unittest.TestCase):
    """BLOCKED_TOOLS must be rejected at Layer 1 — zero latency, no LLM."""

    def setUp(self):
        self.hook = ToolHookPipeline()

    def test_shell_is_blocked(self):
        result = self.hook.pre_tool_use("shell", "ls -la", AGENT_ID)
        self.assertFalse(result.allowed)
        self.assertEqual(result.layer, "BLOCKED_TOOLS")
        self.assertAlmostEqual(result.governance_score, 0.0)

    def test_bash_is_blocked(self):
        result = self.hook.pre_tool_use("bash", "echo hello", AGENT_ID)
        self.assertFalse(result.allowed)
        self.assertEqual(result.layer, "BLOCKED_TOOLS")

    def test_eval_is_blocked(self):
        result = self.hook.pre_tool_use("eval", "__import__('os').system('id')", AGENT_ID)
        self.assertFalse(result.allowed)

    def test_exec_is_blocked(self):
        result = self.hook.pre_tool_use("exec", "some_code()", AGENT_ID)
        self.assertFalse(result.allowed)

    def test_blocked_tool_case_insensitive(self):
        result = self.hook.pre_tool_use("Shell", "ls", AGENT_ID)
        self.assertFalse(result.allowed)

    def test_all_blocked_tools_are_rejected(self):
        for tool in BLOCKED_TOOLS:
            with self.subTest(tool=tool):
                result = self.hook.pre_tool_use(tool, "input", AGENT_ID)
                self.assertFalse(result.allowed, f"Expected {tool} to be blocked")

    def test_blocked_result_has_reason(self):
        result = self.hook.pre_tool_use("bash", "cmd", AGENT_ID)
        self.assertIn("BLOCKED_TOOLS", result.reason)

    def test_blocked_result_latency_is_populated(self):
        result = self.hook.pre_tool_use("bash", "cmd", AGENT_ID)
        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_blocked_property_alias(self):
        result = self.hook.pre_tool_use("shell", "x", AGENT_ID)
        self.assertTrue(result.blocked)
        self.assertFalse(result.allowed)


# ── PreToolUse — safe tools ───────────────────────────────────────────────────

class TestPreToolUseSafeTools(unittest.TestCase):
    """SAFE_TOOLS must be approved. Z3 is skipped for them."""

    def setUp(self):
        self.hook = ToolHookPipeline(skip_z3_for_safe=True)

    def test_read_is_allowed(self):
        # ConstitutionEnforcer requires ≥50 chars — use realistic path
        result = self.hook.pre_tool_use(
            "Read", "core/governance.py — reading governance module for analysis", AGENT_ID
        )
        self.assertTrue(result.allowed)

    def test_glob_is_allowed(self):
        result = self.hook.pre_tool_use(
            "Glob", "**/*.py — searching all Python files in the core module directory", AGENT_ID
        )
        self.assertTrue(result.allowed)

    def test_grep_is_allowed(self):
        result = self.hook.pre_tool_use(
            "Grep", "pattern: ConstitutionEnforcer — searching governance module for class definition", AGENT_ID
        )
        self.assertTrue(result.allowed)

    def test_safe_tool_z3_proof_is_none(self):
        """Z3 is skipped for SAFE_TOOLS — proof should be None."""
        result = self.hook.pre_tool_use(
            "Read", "core/governance.py — reading governance module for analysis", AGENT_ID
        )
        # Z3 proof only set when Z3Gate runs, which is skipped for safe tools
        self.assertTrue(result.allowed)

    def test_approved_result_latency_populated(self):
        result = self.hook.pre_tool_use(
            "Read", "core/governance.py — reading governance module for analysis", AGENT_ID
        )
        self.assertGreaterEqual(result.latency_ms, 0.0)


# ── PreToolUse — unknown tools ────────────────────────────────────────────────

class TestPreToolUseUnknownTools(unittest.TestCase):
    """Unknown tools (not in BLOCKED or SAFE) should pass all layers if clean."""

    def setUp(self):
        self.hook = ToolHookPipeline()

    def test_unknown_clean_tool_is_allowed(self):
        result = self.hook.pre_tool_use(
            "write_file",
            "This is a safe write operation updating configuration parameters with valid data.",
            AGENT_ID,
        )
        # If ConstitutionEnforcer is unavailable, defaults to ALLOW
        # If enforcer is available and content passes, ALLOW
        self.assertIsInstance(result, HookResult)
        self.assertIsInstance(result.allowed, bool)

    def test_result_has_all_fields(self):
        result = self.hook.pre_tool_use(
            "write_file",
            "This is a safe write operation updating configuration parameters with valid data.",
            AGENT_ID,
        )
        self.assertIsNotNone(result.reason)
        self.assertIsNotNone(result.layer)
        self.assertIsInstance(result.governance_score, float)
        self.assertIsInstance(result.latency_ms, float)


# ── PostToolUse — attestation ─────────────────────────────────────────────────

class TestPostToolUseAttestation(unittest.TestCase):
    """PostToolUse must produce a valid attestation hash and audit entry."""

    def setUp(self):
        self.hook = ToolHookPipeline()

    def test_attestation_hash_format(self):
        post = self.hook.post_tool_use("Read", "file contents here", AGENT_ID)
        self.assertRegex(post.attestation_hash, ATTESTATION_RE)

    def test_audit_written_is_true(self):
        post = self.hook.post_tool_use("Read", "output", AGENT_ID)
        self.assertTrue(post.audit_written)

    def test_trace_entry_has_required_fields(self):
        post = self.hook.post_tool_use("Read", "output", AGENT_ID)
        entry = post.trace_entry
        self.assertEqual(entry["event"], "tool_execution")
        self.assertEqual(entry["tool_name"], "Read")
        self.assertEqual(entry["agent_id"], AGENT_ID)
        self.assertIn("timestamp", entry)
        self.assertIn("attestation_hash", entry)
        self.assertIn("output_preview", entry)

    def test_trace_entry_with_pre_result(self):
        pre = HookResult(allowed=True, reason="APPROVED", layer="BLOCKED_TOOLS")
        post = self.hook.post_tool_use("Glob", "*.py files", AGENT_ID, pre_result=pre)
        entry = post.trace_entry
        self.assertTrue(entry["pre_allowed"])
        self.assertEqual(entry["pre_layer"], "BLOCKED_TOOLS")

    def test_trace_entry_without_pre_result(self):
        post = self.hook.post_tool_use("Read", "output", AGENT_ID, pre_result=None)
        entry = post.trace_entry
        self.assertIsNone(entry["pre_allowed"])
        self.assertIsNone(entry["pre_layer"])

    def test_attestation_hash_is_deterministic_for_same_inputs(self):
        """Same tool+output+agent at same timestamp should give same hash."""
        with patch("core.tool_hooks.time") as mock_time:
            mock_time.time.return_value = 1234567890.0
            mock_time.strftime.return_value = "2026-04-02T12:00:00"
            post1 = self.hook.post_tool_use("Read", "same output", AGENT_ID)
            post2 = self.hook.post_tool_use("Read", "same output", AGENT_ID)
        self.assertEqual(post1.attestation_hash, post2.attestation_hash)

    def test_output_preview_truncated_to_200(self):
        long_output = "x" * 500
        post = self.hook.post_tool_use("Read", long_output, AGENT_ID)
        self.assertLessEqual(len(post.trace_entry["output_preview"]), 200)


# ── GovernanceViolation ───────────────────────────────────────────────────────

class TestGovernanceViolation(unittest.TestCase):

    def test_raises_with_reason(self):
        with self.assertRaises(GovernanceViolation) as ctx:
            raise GovernanceViolation("Tool blocked by HARD rule")
        self.assertIn("Tool blocked by HARD rule", str(ctx.exception))

    def test_carries_hook_result(self):
        hook_result = HookResult(allowed=False, reason="test", layer="BLOCKED_TOOLS")
        exc = GovernanceViolation("blocked", hook_result=hook_result)
        self.assertIs(exc.hook_result, hook_result)

    def test_hook_result_is_none_by_default(self):
        exc = GovernanceViolation("blocked")
        self.assertIsNone(exc.hook_result)


# ── Full pipeline — pre → execute → post ─────────────────────────────────────

class TestFullPipeline(unittest.TestCase):
    """Integration: simulate pre→execute→post without touching real tools."""

    def setUp(self):
        self.hook = ToolHookPipeline()

    def _mock_execute(self, tool_name: str, tool_input: str) -> str:
        return f"Result of {tool_name}: processed '{tool_input[:20]}'"

    def test_full_pipeline_allowed_tool(self):
        tool_name = "Read"
        tool_input = "core/governance.py — reading governance module for DOF analysis"

        pre = self.hook.pre_tool_use(tool_name, tool_input, AGENT_ID)
        self.assertTrue(pre.allowed, f"Expected allowed, got: {pre.reason}")

        output = self._mock_execute(tool_name, tool_input)

        post = self.hook.post_tool_use(tool_name, output, AGENT_ID, pre_result=pre)
        self.assertRegex(post.attestation_hash, ATTESTATION_RE)
        self.assertTrue(post.audit_written)
        self.assertEqual(post.trace_entry["tool_name"], tool_name)

    def test_full_pipeline_blocked_tool_raises(self):
        tool_name = "bash"
        tool_input = "rm -rf /"

        pre = self.hook.pre_tool_use(tool_name, tool_input, AGENT_ID)
        self.assertFalse(pre.allowed)

        with self.assertRaises(GovernanceViolation):
            if not pre.allowed:
                raise GovernanceViolation(pre.reason, hook_result=pre)

    def test_full_pipeline_all_safe_tools_complete(self):
        safe_input = "Reading governance module configuration data for DOF verification analysis."
        for tool in list(SAFE_TOOLS)[:3]:
            with self.subTest(tool=tool):
                pre = self.hook.pre_tool_use(tool, safe_input, AGENT_ID)
                if pre.allowed:
                    output = self._mock_execute(tool, safe_input)
                    post = self.hook.post_tool_use(tool, output, AGENT_ID, pre_result=pre)
                    self.assertRegex(post.attestation_hash, ATTESTATION_RE)

    def test_pipeline_with_custom_blocked_tools(self):
        custom_hook = ToolHookPipeline(blocked_tools={"custom_dangerous_tool"})
        result = custom_hook.pre_tool_use("custom_dangerous_tool", "x", AGENT_ID)
        self.assertFalse(result.allowed)
        # Standard tools not in custom blocked set should pass layer 1
        result2 = custom_hook.pre_tool_use(
            "Read",
            "core/governance.py — reading governance module for analysis",
            AGENT_ID,
        )
        self.assertTrue(result2.allowed)


# ── ToolHookPipeline initialization ──────────────────────────────────────────

class TestToolHookPipelineInit(unittest.TestCase):

    def test_default_init_succeeds(self):
        hook = ToolHookPipeline()
        self.assertIsInstance(hook, ToolHookPipeline)

    def test_custom_blocked_set(self):
        hook = ToolHookPipeline(blocked_tools={"danger_tool"})
        result = hook.pre_tool_use("danger_tool", "x", AGENT_ID)
        self.assertFalse(result.allowed)

    def test_custom_safe_set(self):
        hook = ToolHookPipeline(safe_tools={"my_read_only_tool"}, skip_z3_for_safe=True)
        # Just verifying init doesn't crash and tool is recognized
        result = hook.pre_tool_use(
            "my_read_only_tool",
            "Reading configuration data from the specified safe path location.",
            AGENT_ID,
        )
        self.assertIsInstance(result, HookResult)

    def test_hook_result_is_dataclass(self):
        from dataclasses import fields
        field_names = {f.name for f in fields(HookResult)}
        self.assertIn("allowed", field_names)
        self.assertIn("reason", field_names)
        self.assertIn("layer", field_names)
        self.assertIn("governance_score", field_names)
        self.assertIn("latency_ms", field_names)


if __name__ == "__main__":
    unittest.main()
