"""
Tests for core/loop_guard.py — LoopGuard and LoopGuardResult.

All tests are deterministic, no network or blockchain calls.
"""

import os
import sys
import time
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loop_guard import LoopGuard, LoopGuardResult


class TestLoopGuardBasic(unittest.TestCase):
    """Test basic LoopGuard functionality."""

    def test_continue_on_unique_outputs(self):
        guard = LoopGuard()
        result = guard.check("This is output one", 0)
        self.assertEqual(result.status, "CONTINUE")
        result = guard.check("This is output two, completely different", 1)
        self.assertEqual(result.status, "CONTINUE")

    def test_loop_detected_identical_output(self):
        guard = LoopGuard()
        guard.check("The agent produced this exact output", 0)
        result = guard.check("The agent produced this exact output", 1)
        self.assertEqual(result.status, "LOOP_DETECTED")
        self.assertEqual(result.matched_iteration, 0)
        self.assertEqual(result.similarity_score, 1.0)

    def test_loop_detected_similar_output(self):
        guard = LoopGuard(similarity_threshold=0.85)
        guard.check("The quick brown fox jumps over the lazy dog near the river bank", 0)
        # Very similar — same words, slightly different
        result = guard.check("The quick brown fox jumps over the lazy dog near the bank river", 1)
        self.assertEqual(result.status, "LOOP_DETECTED")
        self.assertGreaterEqual(result.similarity_score, 0.85)

    def test_no_loop_below_threshold(self):
        guard = LoopGuard(similarity_threshold=0.85)
        guard.check("The quick brown fox jumps over the lazy dog", 0)
        result = guard.check("A completely different sentence about cats and mice playing", 1)
        self.assertEqual(result.status, "CONTINUE")

    def test_loop_detected_third_iteration(self):
        guard = LoopGuard()
        guard.check("Output A about topic X", 0)
        guard.check("Output B about topic Y which is very different", 1)
        result = guard.check("Output A about topic X", 2)
        self.assertEqual(result.status, "LOOP_DETECTED")
        self.assertEqual(result.matched_iteration, 0)


class TestMaxIterations(unittest.TestCase):
    """Test max iterations limit."""

    def test_max_iterations_exceeded(self):
        guard = LoopGuard(max_iterations=3)
        guard.check("output 0", 0)
        guard.check("output 1", 1)
        guard.check("output 2", 2)
        result = guard.check("output 3", 3)
        self.assertEqual(result.status, "MAX_ITERATIONS_EXCEEDED")
        self.assertEqual(result.iteration, 3)

    def test_within_max_iterations(self):
        guard = LoopGuard(max_iterations=5)
        for i in range(5):
            result = guard.check(f"unique output number {i} with random text {i*7}", i)
            self.assertEqual(result.status, "CONTINUE")

    def test_max_iterations_one(self):
        guard = LoopGuard(max_iterations=1)
        result0 = guard.check("first output", 0)
        self.assertEqual(result0.status, "CONTINUE")
        result1 = guard.check("second output", 1)
        self.assertEqual(result1.status, "MAX_ITERATIONS_EXCEEDED")


class TestTimeout(unittest.TestCase):
    """Test timeout detection."""

    def test_timeout_detected(self):
        guard = LoopGuard(max_duration_seconds=0.01)
        time.sleep(0.02)
        result = guard.check("some output", 0)
        self.assertEqual(result.status, "TIMEOUT")
        self.assertGreater(result.elapsed_seconds, 0.01)

    def test_no_timeout(self):
        guard = LoopGuard(max_duration_seconds=300)
        result = guard.check("some output", 0)
        self.assertEqual(result.status, "CONTINUE")
        self.assertLess(result.elapsed_seconds, 1.0)


class TestSimilarity(unittest.TestCase):
    """Test Jaccard similarity function."""

    def test_identical_strings(self):
        sim = LoopGuard.similarity("hello world", "hello world")
        self.assertEqual(sim, 1.0)

    def test_completely_different(self):
        sim = LoopGuard.similarity("apple banana", "cat dog")
        self.assertEqual(sim, 0.0)

    def test_partial_overlap(self):
        sim = LoopGuard.similarity("a b c d", "a b e f")
        # intersection: {a, b}, union: {a, b, c, d, e, f}
        self.assertAlmostEqual(sim, 2 / 6)

    def test_case_insensitive(self):
        sim = LoopGuard.similarity("Hello World", "hello world")
        self.assertEqual(sim, 1.0)

    def test_empty_strings(self):
        sim = LoopGuard.similarity("", "")
        self.assertEqual(sim, 1.0)

    def test_one_empty_string(self):
        sim = LoopGuard.similarity("hello world", "")
        self.assertEqual(sim, 0.0)

    def test_symmetry(self):
        a = "the quick brown fox"
        b = "the lazy brown dog"
        self.assertEqual(LoopGuard.similarity(a, b), LoopGuard.similarity(b, a))


class TestReset(unittest.TestCase):
    """Test reset clears history."""

    def test_reset_clears_history(self):
        guard = LoopGuard()
        guard.check("output one", 0)
        guard.check("output two", 1)
        self.assertEqual(len(guard.history), 2)
        guard.reset()
        self.assertEqual(len(guard.history), 0)

    def test_reset_allows_same_output(self):
        guard = LoopGuard()
        guard.check("same output", 0)
        guard.reset()
        result = guard.check("same output", 0)
        self.assertEqual(result.status, "CONTINUE")


class TestLoopGuardResult(unittest.TestCase):
    """Test LoopGuardResult dataclass."""

    def test_result_fields(self):
        result = LoopGuardResult(
            status="LOOP_DETECTED",
            iteration=5,
            similarity_score=0.92,
            matched_iteration=2,
            elapsed_seconds=1.5,
        )
        self.assertEqual(result.status, "LOOP_DETECTED")
        self.assertEqual(result.iteration, 5)
        self.assertEqual(result.similarity_score, 0.92)
        self.assertEqual(result.matched_iteration, 2)
        self.assertEqual(result.elapsed_seconds, 1.5)

    def test_default_values(self):
        result = LoopGuardResult(status="CONTINUE", iteration=0)
        self.assertEqual(result.similarity_score, 0.0)
        self.assertEqual(result.matched_iteration, -1)
        self.assertEqual(result.elapsed_seconds, 0.0)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and integration scenarios."""

    def test_many_unique_outputs(self):
        guard = LoopGuard(max_iterations=100)
        for i in range(50):
            text = f"completely unique output {i} with special content {i * 13}"
            result = guard.check(text, i)
            self.assertEqual(result.status, "CONTINUE", f"Failed at iteration {i}")

    def test_custom_threshold(self):
        guard = LoopGuard(similarity_threshold=0.5)
        guard.check("alpha beta gamma delta", 0)
        # Half overlap
        result = guard.check("alpha beta epsilon zeta", 1)
        # intersection: {alpha, beta}, union: {alpha, beta, gamma, delta, epsilon, zeta}
        # Jaccard = 2/6 ≈ 0.333 — below 0.5
        self.assertEqual(result.status, "CONTINUE")

    def test_priority_timeout_over_max_iterations(self):
        """Timeout should be checked before max_iterations."""
        guard = LoopGuard(max_iterations=5, max_duration_seconds=0.01)
        time.sleep(0.02)
        result = guard.check("output", 10)
        self.assertEqual(result.status, "TIMEOUT")

    def test_history_grows(self):
        guard = LoopGuard(max_iterations=100)
        for i in range(10):
            guard.check(f"unique_{i}", i)
        self.assertEqual(len(guard.history), 10)


class TestSimilarityEmptyWhitespace(unittest.TestCase):
    """Verify documented behaviour: empty/whitespace strings yield 1.0, not 0.0."""

    def test_both_empty_is_one(self):
        # Two empty outputs are considered identical (loop signal)
        self.assertEqual(LoopGuard.similarity("", ""), 1.0)

    def test_whitespace_only_both_is_one(self):
        # Whitespace-only strings have no tokens → same as both empty
        self.assertEqual(LoopGuard.similarity("   ", "\t\n"), 1.0)

    def test_empty_and_whitespace_is_one(self):
        self.assertEqual(LoopGuard.similarity("", "   "), 1.0)

    def test_one_empty_one_nonempty_is_zero(self):
        self.assertEqual(LoopGuard.similarity("", "hello"), 0.0)

    def test_whitespace_vs_nonempty_is_zero(self):
        self.assertEqual(LoopGuard.similarity("   ", "hello"), 0.0)

    def test_consecutive_blank_outputs_detected_as_loop(self):
        lg = LoopGuard(max_iterations=10)
        lg.check("", 0)
        result = lg.check("   ", 1)
        self.assertEqual(result.status, "LOOP_DETECTED")


if __name__ == "__main__":
    unittest.main()
