"""
Loop Guard — Detects infinite loops in agent executions.

Uses Jaccard similarity to detect repeated or near-identical outputs
across iterations. Enforces max iteration and timeout limits.

Zero external dependencies — pure Python.

Usage:
    from core.loop_guard import LoopGuard

    guard = LoopGuard(max_iterations=10, similarity_threshold=0.85)
    for i in range(100):
        output = agent.run()
        result = guard.check(output, i)
        if result.status != "CONTINUE":
            print(f"Loop detected: {result.status}")
            break
"""

import time
import logging
from dataclasses import dataclass

logger = logging.getLogger("core.loop_guard")


@dataclass
class LoopGuardResult:
    """Result of a loop guard check."""
    status: str  # CONTINUE | LOOP_DETECTED | MAX_ITERATIONS_EXCEEDED | TIMEOUT
    iteration: int
    similarity_score: float = 0.0
    matched_iteration: int = -1
    elapsed_seconds: float = 0.0


class LoopGuard:
    """Detects infinite loops in agent executions.

    Compares each output against all previous outputs using Jaccard
    similarity of word sets. If similarity exceeds the threshold,
    a loop is detected.

    Args:
        max_iterations: Maximum allowed iterations before stopping.
        max_duration_seconds: Maximum elapsed time before timeout.
        similarity_threshold: Jaccard similarity threshold for loop detection.
    """

    def __init__(self, max_iterations: int = 10,
                 max_duration_seconds: float = 300,
                 similarity_threshold: float = 0.85):
        self.max_iterations = max_iterations
        self.max_duration_seconds = max_duration_seconds
        self.similarity_threshold = similarity_threshold
        self._history: list[str] = []
        self._start_time: float = time.time()

    @property
    def history(self) -> list[str]:
        """Read-only access to output history."""
        return list(self._history)

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Compute Jaccard similarity between two strings.

        Splits on whitespace, compares word sets.
        Returns 1.0 if both strings are empty (or whitespace-only) — two
        blank outputs are considered identical.  Returns 0.0 if exactly
        one side is empty.

        Args:
            a: First string.
            b: Second string.

        Returns:
            Float in [0.0, 1.0].
        """
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def check(self, output: str, iteration: int) -> LoopGuardResult:
        """Check if the current output indicates a loop.

        Args:
            output: The agent output to check.
            iteration: Current iteration number (0-based).

        Returns:
            LoopGuardResult with status and diagnostics.
        """
        elapsed = time.time() - self._start_time

        # Check timeout
        if elapsed > self.max_duration_seconds:
            logger.warning(
                f"LoopGuard: TIMEOUT at iteration {iteration} "
                f"({elapsed:.1f}s > {self.max_duration_seconds}s)"
            )
            return LoopGuardResult(
                status="TIMEOUT",
                iteration=iteration,
                elapsed_seconds=elapsed,
            )

        # Check max iterations
        if iteration >= self.max_iterations:
            logger.warning(
                f"LoopGuard: MAX_ITERATIONS_EXCEEDED at {iteration} "
                f"(limit: {self.max_iterations})"
            )
            return LoopGuardResult(
                status="MAX_ITERATIONS_EXCEEDED",
                iteration=iteration,
                elapsed_seconds=elapsed,
            )

        # Check similarity against history
        for hist_idx, prev_output in enumerate(self._history):
            sim = self.similarity(output, prev_output)
            if sim >= self.similarity_threshold:
                logger.warning(
                    f"LoopGuard: LOOP_DETECTED at iteration {iteration} "
                    f"(similarity={sim:.3f} with iteration {hist_idx})"
                )
                self._history.append(output)
                return LoopGuardResult(
                    status="LOOP_DETECTED",
                    iteration=iteration,
                    similarity_score=sim,
                    matched_iteration=hist_idx,
                    elapsed_seconds=elapsed,
                )

        # All clear
        self._history.append(output)
        return LoopGuardResult(
            status="CONTINUE",
            iteration=iteration,
            elapsed_seconds=elapsed,
        )

    def reset(self):
        """Clear history and reset timer."""
        self._history.clear()
        self._start_time = time.time()
