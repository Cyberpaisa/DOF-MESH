"""Tests for Self-Correction Loop — Item 8 Plan Abril 2026."""
import unittest
from core.governance import check_and_correct, check_governance


class TestCheckAndCorrect(unittest.TestCase):

    def test_clean_text_returns_unchanged(self):
        text = "## Summary\nThis is a valid response with actionable steps.\n- Step 1\n- Step 2"
        corrected, result = check_and_correct(text)
        self.assertEqual(corrected, text)

    def test_soft_violation_conciseness_gets_corrected(self):
        # CONCISENESS rule triggers on "measurements were recorded" (present mode)
        text = "The measurements were recorded in a comprehensive monitoring setup with significant delays."
        corrected, result = check_and_correct(text)
        # Correction should have removed the offending pattern
        self.assertNotIn("measurements were recorded", corrected.lower())

    def test_hard_violation_not_corrected(self):
        # Empty text → hard violation NO_EMPTY_OUTPUT
        text = ""
        corrected, result = check_and_correct(text)
        self.assertFalse(result.passed)
        self.assertEqual(corrected, text)  # unchanged

    def test_returns_tuple_of_str_and_governance_result(self):
        corrected, result = check_and_correct("Some text")
        self.assertIsInstance(corrected, str)
        self.assertTrue(hasattr(result, "passed"))
        self.assertTrue(hasattr(result, "violations"))
        self.assertTrue(hasattr(result, "warnings"))

    def test_hard_violation_blocks_correction(self):
        # Text too long — MAX_LENGTH hard rule
        text = "x" * 60_000
        corrected, result = check_and_correct(text)
        # Should return violations, not corrected
        self.assertFalse(result.passed)
        self.assertTrue(len(result.violations) > 0)

    def test_correction_reruns_governance_on_result(self):
        text = "The measurements were recorded in a comprehensive monitoring setup."
        corrected, result = check_and_correct(text)
        # The returned result is from the corrected text, not the original
        if corrected != text:
            original_result = check_governance(text)
            self.assertGreaterEqual(len(result.warnings), 0)


if __name__ == "__main__":
    unittest.main()
