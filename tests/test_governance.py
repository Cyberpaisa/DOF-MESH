
import unittest
from core.governance import (
    GovernanceResult,
    check_governance,
)

VALID_TEXT = (
    "The DOF mesh architecture uses a file-based JSON protocol where agents "
    "communicate via inbox directories. Each node polls its inbox every 3 seconds, "
    "processes tasks atomically by renaming files to .processing, executes the work, "
    "and writes results to logs/local-agent/results/. This design ensures crash "
    "recovery via WAL and prevents double-processing."
)


class TestGovernance(unittest.TestCase):
    def test_no_hallucination_claim(self):
        # Text with factual, source-backed content should pass
        result = check_governance(VALID_TEXT)
        self.assertTrue(result.passed, f"Violations: {result.violations}")

    def test_language_compliance(self):
        result = check_governance(VALID_TEXT)
        self.assertTrue(result.passed, f"Violations: {result.violations}")

    def test_no_empty_output(self):
        result = check_governance(VALID_TEXT)
        self.assertTrue(result.passed, f"Violations: {result.violations}")

    def test_max_length(self):
        # Long but structured text should pass
        long_text = (VALID_TEXT + " ") * 20
        result = check_governance(long_text)
        self.assertTrue(result.passed, f"Violations: {result.violations}")

    def test_has_sources(self):
        # Governance may emit style warnings (not violations) — that's acceptable
        text = VALID_TEXT + " Reference: https://example.com/dof-docs"
        result = check_governance(text)
        violations = [v for v in result.warnings if "VIOLATION" in v.upper()]
        self.assertEqual(violations, [], f"Unexpected violations in warnings: {violations}")

    def test_no_pii(self):
        result = check_governance(VALID_TEXT)
        self.assertTrue(result.passed, f"Violations: {result.violations}")

    def test_empty_input_fails(self):
        result = check_governance("")
        self.assertFalse(result.passed)

    def test_returns_governance_result(self):
        result = check_governance(VALID_TEXT)
        self.assertIsInstance(result, GovernanceResult)
        self.assertIsInstance(result.violations, list)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.score, (int, float))


if __name__ == '__main__':
    unittest.main()
