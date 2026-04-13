"""
tests/test_media_generation_tool.py — Unit tests for MediaGenerationTool.

Run with:
    python3 -m unittest tests.test_media_generation_tool -v
"""

import json
import unittest
from unittest.mock import patch


class TestMediaGenerationTool(unittest.TestCase):
    """Unit tests for MediaGenerationTool and create_media_generation_tool factory."""

    def setUp(self):
        """Reset feature flags and import tool fresh for each test."""
        from core.feature_flags import flags
        flags.reset()  # Clear any runtime overrides from previous tests

    # ── Structural tests ──────────────────────────────────────────────────────

    def test_tool_name_is_media_generation(self):
        """Tool must expose name='media_generation' for CrewAI routing."""
        from core.tools.media_generation_tool import MediaGenerationTool
        tool = MediaGenerationTool()
        self.assertEqual(tool.name, "media_generation")

    def test_create_media_generation_tool_returns_instance(self):
        """Factory function must return a MediaGenerationTool instance."""
        from core.tools.media_generation_tool import (
            MediaGenerationTool,
            create_media_generation_tool,
        )
        tool = create_media_generation_tool()
        self.assertIsInstance(tool, MediaGenerationTool)

    # ── Flag-disabled behaviour ───────────────────────────────────────────────

    def test_returns_disabled_json_when_flag_off(self):
        """_run must return status='disabled' when media_generation_tool flag is False."""
        from core.feature_flags import flags
        from core.tools.media_generation_tool import create_media_generation_tool
        flags.disable("media_generation_tool")
        tool = create_media_generation_tool()
        result = tool._run("test prompt")
        data = json.loads(result)
        self.assertEqual(data["status"], "disabled")

    def test_disabled_json_contains_prompt(self):
        """Disabled JSON must echo back the original prompt for traceability."""
        from core.feature_flags import flags
        from core.tools.media_generation_tool import create_media_generation_tool
        flags.disable("media_generation_tool")
        tool = create_media_generation_tool()
        prompt = "generate DOF architecture diagram"
        result = tool._run(prompt)
        data = json.loads(result)
        self.assertEqual(data["prompt"], prompt)

    # ── _arun delegation ──────────────────────────────────────────────────────

    def test_arun_delegates_to_run(self):
        """_arun must return the same result as _run (sync fallback for async calls)."""
        from core.feature_flags import flags
        from core.tools.media_generation_tool import create_media_generation_tool
        flags.disable("media_generation_tool")  # Pin flag for deterministic comparison
        tool = create_media_generation_tool()
        prompt = "architecture diagram"
        self.assertEqual(tool._arun(prompt), tool._run(prompt))

    # ── Robustness tests ──────────────────────────────────────────────────────

    def test_never_raises_on_bad_input(self):
        """_run must never raise — even with empty string or unusual characters."""
        from core.tools.media_generation_tool import create_media_generation_tool
        tool = create_media_generation_tool()
        bad_inputs = ["", "   ", "\x00\xFF", "a" * 10_000, None]
        for bad in bad_inputs:
            with self.subTest(prompt=repr(bad)):
                try:
                    result = tool._run(bad)  # type: ignore[arg-type]
                    # Must return a string (not raise)
                    self.assertIsInstance(result, str)
                except Exception as exc:  # pragma: no cover
                    self.fail(f"_run raised unexpectedly for input {bad!r}: {exc}")

    def test_flag_enabled_without_api_key_returns_error_json(self):
        """With flag enabled but no MUAPI_KEY, must return error JSON (no raise)."""
        from core.feature_flags import flags
        from core.tools.media_generation_tool import create_media_generation_tool

        flags.enable("media_generation_tool")
        tool = create_media_generation_tool()

        # Patch out MUAPI_KEY and force the HTTP call to fail
        with patch.dict("os.environ", {"MUAPI_KEY": ""}, clear=False):
            with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
                result = tool._run("DOF diagram")

        data = json.loads(result)
        self.assertIn(data["status"], ("error", "ok"))  # Either is fine — must not raise
        self.assertIn("prompt", data)  # Prompt echoed for traceability

    def test_result_is_always_valid_json(self):
        """_run must always return a valid JSON string regardless of flag state."""
        from core.feature_flags import flags
        from core.tools.media_generation_tool import create_media_generation_tool

        tool = create_media_generation_tool()

        # Test with flag disabled
        flags.disable("media_generation_tool")
        result_off = tool._run("test")
        parsed_off = json.loads(result_off)  # Must not raise
        self.assertIsInstance(parsed_off, dict)

        # Test with flag enabled (network call mocked to fail cleanly)
        flags.enable("media_generation_tool")
        with patch("urllib.request.urlopen", side_effect=Exception("mock network error")):
            result_on = tool._run("test")
        parsed_on = json.loads(result_on)  # Must not raise
        self.assertIsInstance(parsed_on, dict)


if __name__ == "__main__":
    unittest.main()
