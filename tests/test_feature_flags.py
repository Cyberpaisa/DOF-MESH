"""
tests/test_feature_flags.py — Tests for core/feature_flags.py
Run with: python3 -m unittest tests.test_feature_flags
"""

import unittest
from core.feature_flags import FeatureFlags


class TestFeatureFlagsDefaults(unittest.TestCase):
    def setUp(self):
        # Fresh instance with no YAML (use a non-existent path)
        from pathlib import Path
        self.ff = FeatureFlags(constitution_path=Path("/nonexistent.yml"))

    def test_stable_flags_are_enabled(self):
        for flag in [
            "disk_task_queue", "system_prompt_boundary", "abort_signal_cascade",
            "streaming_executor", "daemon_governance_gate", "daemon_memory",
        ]:
            self.assertTrue(self.ff.is_enabled(flag), f"Expected {flag} to be enabled")

    def test_candidate_flags_are_disabled(self):
        # dof_leaderboard remains disabled (needs 10+ agents to make sense)
        # feynman_research_crew, graphify_integration, media_generation_tool are now enabled (v0.8.0)
        for flag in ["dof_leaderboard"]:
            self.assertFalse(self.ff.is_enabled(flag), f"Expected {flag} to be disabled")

    def test_unknown_flag_returns_false(self):
        self.assertFalse(self.ff.is_enabled("nonexistent_flag"))

    def test_unknown_flag_respects_default(self):
        self.assertTrue(self.ff.is_enabled("nonexistent_flag", default=True))
        self.assertFalse(self.ff.is_enabled("nonexistent_flag", default=False))


class TestFeatureFlagsOverrides(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.ff = FeatureFlags(constitution_path=Path("/nonexistent.yml"))

    def test_enable_overrides_default(self):
        # graphify_integration is now True by default; verify disable→enable round-trip
        self.ff.disable("graphify_integration")
        self.assertFalse(self.ff.is_enabled("graphify_integration"))
        self.ff.enable("graphify_integration")
        self.assertTrue(self.ff.is_enabled("graphify_integration"))

    def test_disable_overrides_default(self):
        self.assertTrue(self.ff.is_enabled("disk_task_queue"))
        self.ff.disable("disk_task_queue")
        self.assertFalse(self.ff.is_enabled("disk_task_queue"))

    def test_set_explicit_value(self):
        self.ff.set("disk_task_queue", False)
        self.assertFalse(self.ff.is_enabled("disk_task_queue"))
        self.ff.set("disk_task_queue", True)
        self.assertTrue(self.ff.is_enabled("disk_task_queue"))

    def test_reset_single_flag(self):
        # graphify_integration default is now True; disable via override then reset
        self.ff.disable("graphify_integration")
        self.assertFalse(self.ff.is_enabled("graphify_integration"))
        self.ff.reset("graphify_integration")
        self.assertTrue(self.ff.is_enabled("graphify_integration"))

    def test_reset_all_flags(self):
        # graphify_integration default is True; disk_task_queue default is True
        self.ff.disable("graphify_integration")
        self.ff.disable("disk_task_queue")
        self.ff.reset()
        # After reset, both return to their compiled defaults
        self.assertTrue(self.ff.is_enabled("graphify_integration"))
        self.assertTrue(self.ff.is_enabled("disk_task_queue"))

    def test_override_takes_priority_over_yaml(self):
        # Simulate YAML setting a flag to True
        self.ff._from_yaml["some_flag"] = True
        self.ff.disable("some_flag")
        self.assertFalse(self.ff.is_enabled("some_flag"))


class TestFeatureFlagsSnapshot(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.ff = FeatureFlags(constitution_path=Path("/nonexistent.yml"))

    def test_all_flags_returns_dict(self):
        result = self.ff.all_flags()
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 5)

    def test_snapshot_has_all_layers(self):
        snap = self.ff.snapshot()
        self.assertIn("defaults", snap)
        self.assertIn("from_yaml", snap)
        self.assertIn("overrides", snap)
        self.assertIn("effective", snap)

    def test_snapshot_effective_matches_all_flags(self):
        snap = self.ff.snapshot()
        self.assertEqual(snap["effective"], self.ff.all_flags())

    def test_repr_contains_enabled_disabled(self):
        r = repr(self.ff)
        self.assertIn("enabled=", r)
        self.assertIn("disabled=", r)


class TestFeatureFlagsYAML(unittest.TestCase):
    def test_loads_from_real_constitution(self):
        """Integration: load from the real dof.constitution.yml."""
        ff = FeatureFlags()
        # All stable flags should still be True even after YAML load
        self.assertTrue(ff.is_enabled("disk_task_queue"))
        self.assertTrue(ff.is_enabled("daemon_memory"))
        self.assertTrue(ff.is_enabled("feature_flags_governance"))
        # graphify_integration is now enabled (v0.8.0 promotion)
        self.assertTrue(ff.is_enabled("graphify_integration"))

    def test_yaml_section_missing_uses_defaults(self):
        """If YAML has no feature_flags section, fall back to defaults silently."""
        import tempfile, os
        from pathlib import Path
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("metadata:\n  spec_version: '1.0'\n")
            tmp = f.name
        try:
            ff = FeatureFlags(constitution_path=Path(tmp))
            self.assertTrue(ff.is_enabled("disk_task_queue"))
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
