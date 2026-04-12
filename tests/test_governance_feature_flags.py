"""
tests/test_governance_feature_flags.py — Tests for feature_flags_governance gate.

Verifies that ConstitutionEnforcer skips rules gated by disabled feature flags
when feature_flags_governance is enabled.

Run with: python3 -m unittest tests.test_governance_feature_flags
"""

import unittest
from core.feature_flags import FeatureFlags, flags as _global_flags
from core import governance as gov


_CLEAN_TEXT = (
    "The analysis shows that all security checks passed. "
    "Recommendation: review the following items to ensure compliance. "
    "See https://example.com/docs for details."
)


class TestFeatureFlagGovernanceGate(unittest.TestCase):
    """feature_flags_governance: rules with feature_flag field are skipped when flag is off."""

    def setUp(self):
        # Snapshot original rules and flags state
        self._orig_hard = list(gov.HARD_RULES)
        self._orig_soft = list(gov.SOFT_RULES)

    def tearDown(self):
        # Restore original rules
        gov.HARD_RULES = self._orig_hard
        gov.SOFT_RULES = self._orig_soft
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES
        # Reset flag overrides
        _global_flags.reset("feature_flags_governance")

    def test_feature_flags_governance_is_enabled_by_default(self):
        """flag must be True in v0.7.0 compiled defaults."""
        from pathlib import Path
        ff = FeatureFlags(constitution_path=Path("/nonexistent.yml"))
        self.assertTrue(ff.is_enabled("feature_flags_governance"))

    def test_rule_without_feature_flag_always_runs(self):
        """Rules without feature_flag field are unaffected by the gate."""
        _global_flags.enable("feature_flags_governance")
        # Inject a custom soft rule with NO feature_flag
        gov.SOFT_RULES = [
            {
                "id": "TEST_ALWAYS_WARN",
                "priority": gov.RulePriority.USER,
                "pattern": r"ALWAYS_TRIGGER_PATTERN_XYZ",
                "description": "Always warns on test pattern",
                "weight": 0.1,
                "match_mode": "present",
            }
        ]
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES
        # Pattern not present → no warning; rule executed normally
        result = gov.check_governance(_CLEAN_TEXT)
        # We only care that the rule didn't cause an unintended warning
        self.assertNotIn("TEST_ALWAYS_WARN", " ".join(result.warnings))

    def test_rule_with_disabled_flag_is_skipped(self):
        """A soft rule with feature_flag pointing to a disabled flag must be skipped."""
        _global_flags.enable("feature_flags_governance")
        _global_flags.disable("experimental_new_rule")

        gov.SOFT_RULES = [
            {
                "id": "EXPERIMENTAL_RULE",
                "priority": gov.RulePriority.USER,
                "pattern": r"analysis shows",  # present in _CLEAN_TEXT
                "description": "Experimental rule that should be skipped",
                "weight": 0.1,
                "match_mode": "present",
                "feature_flag": "experimental_new_rule",
            }
        ]
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES

        result = gov.check_governance(_CLEAN_TEXT)
        self.assertNotIn("EXPERIMENTAL_RULE", " ".join(result.warnings))

    def test_rule_with_enabled_flag_runs_normally(self):
        """A soft rule with feature_flag pointing to an ENABLED flag must execute."""
        _global_flags.enable("feature_flags_governance")
        _global_flags.enable("experimental_new_rule")

        gov.SOFT_RULES = [
            {
                "id": "EXPERIMENTAL_RULE",
                "priority": gov.RulePriority.USER,
                "pattern": r"analysis shows",  # present in _CLEAN_TEXT
                "description": "Experimental rule that should run",
                "weight": 0.1,
                "match_mode": "present",
                "feature_flag": "experimental_new_rule",
            }
        ]
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES

        result = gov.check_governance(_CLEAN_TEXT)
        # Rule executed → warning added because pattern IS present
        self.assertTrue(
            any("EXPERIMENTAL_RULE" in w for w in result.warnings),
            f"Expected EXPERIMENTAL_RULE warning; got: {result.warnings}",
        )

    def test_gate_off_disabled_rule_still_runs(self):
        """When feature_flags_governance is OFF, gated rules run regardless of their flag."""
        _global_flags.disable("feature_flags_governance")
        _global_flags.disable("experimental_new_rule")

        gov.SOFT_RULES = [
            {
                "id": "GATED_RULE",
                "priority": gov.RulePriority.USER,
                "pattern": r"analysis shows",
                "description": "Gated rule — should run when gate is off",
                "weight": 0.1,
                "match_mode": "present",
                "feature_flag": "experimental_new_rule",
            }
        ]
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES

        result = gov.check_governance(_CLEAN_TEXT)
        # Gate off → rule always runs → warning present
        self.assertTrue(
            any("GATED_RULE" in w for w in result.warnings),
            f"Expected GATED_RULE warning (gate is off); got: {result.warnings}",
        )

    def test_hard_rule_with_disabled_flag_is_skipped(self):
        """A hard rule with disabled feature_flag must not block when gate is on."""
        _global_flags.enable("feature_flags_governance")
        _global_flags.disable("strict_length_v2")

        gov.HARD_RULES = [
            {
                "id": "STRICT_LENGTH_V2",
                "priority": gov.RulePriority.SYSTEM,
                "pattern": None,
                "description": "Strict length check v2",
                "type": "max_length",
                "max_chars": 5,  # Would block _CLEAN_TEXT (len > 5)
                "feature_flag": "strict_length_v2",
            }
        ]
        gov.GOVERNANCE_RULES = gov.HARD_RULES + gov.SOFT_RULES

        result = gov.check_governance(_CLEAN_TEXT)
        self.assertNotIn("STRICT_LENGTH_V2", " ".join(result.violations))


if __name__ == "__main__":
    unittest.main()
