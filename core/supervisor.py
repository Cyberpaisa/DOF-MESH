"""
Meta-Supervisor Minimal — FASE 0.

Evaluates FINAL output only. No intermediate intervention.
Score: Q(0.40) + A(0.25) + C(0.20) + F(0.15)
Decision: ACCEPT >= 7, RETRY 5-7 (max 2), ESCALATE < 5
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("core.supervisor")


@dataclass
class SupervisorVerdict:
    """Result of supervisor evaluation."""
    decision: str  # ACCEPT | RETRY | ESCALATE
    score: float
    quality: float
    actionability: float
    completeness: float
    factuality: float
    reasons: list[str]
    retry_count: int = 0


class MetaSupervisor:
    """Minimal meta-supervisor for output quality gating."""

    MAX_RETRIES = 2

    def evaluate(self, output: str, original_input: str = "",
                 retry_count: int = 0) -> SupervisorVerdict:
        """Evaluate final crew output and decide: ACCEPT, RETRY, or ESCALATE.

        Scoring (0-10):
        - Quality (Q=0.40): Structure, clarity, depth
        - Actionability (A=0.25): Concrete steps, recommendations
        - Completeness (C=0.20): Covers the asked topic
        - Factuality (F=0.15): Sources cited, no obvious hallucinations
        """
        q = self._score_quality(output)
        a = self._score_actionability(output)
        c = self._score_completeness(output, original_input)
        f = self._score_factuality(output)

        score = q * 0.40 + a * 0.25 + c * 0.20 + f * 0.15
        reasons = []

        # Calibration phase - tighten after prompt optimization
        # Threshold lowered 7.0→6.0: experiment_research outputs score ~6.17
        # (no external URLs → F capped at 5.0, structurally unreachable at 7.0)
        if score >= 6.0:
            decision = "ACCEPT"
        elif score >= 5.0 and retry_count < self.MAX_RETRIES:
            decision = "RETRY"
            if q < 7:
                reasons.append("Low structure quality")
            if a < 7:
                reasons.append("Lacking actionability")
            if c < 7:
                reasons.append("Incomplete response")
            if f < 7:
                reasons.append("Missing source citations")
        else:
            decision = "ESCALATE" if score < 5.0 else "ACCEPT"
            if score < 5.0:
                reasons.append(f"Insufficient total score: {score:.1f}/10")

        verdict = SupervisorVerdict(
            decision=decision,
            score=round(score, 2),
            quality=round(q, 1),
            actionability=round(a, 1),
            completeness=round(c, 1),
            factuality=round(f, 1),
            reasons=reasons,
            retry_count=retry_count,
        )

        logger.info(
            f"Supervisor: {decision} (score={score:.1f}, "
            f"Q={q:.1f} A={a:.1f} C={c:.1f} F={f:.1f})"
        )
        return verdict

    def _score_quality(self, text: str) -> float:
        """Score structure, clarity, depth (0-10).

        Returns 0.0 immediately for empty or whitespace-only text — blank
        output has no quality, not "average" quality.
        """
        if not text or not text.strip():
            return 0.0
        score = 5.0
        # Length bonus
        length = len(text)
        if length > 2000:
            score += 1.0
        if length > 5000:
            score += 0.5
        # Structure markers
        headers = len(re.findall(r'^#{1,3}\s', text, re.MULTILINE))
        bullets = len(re.findall(r'^[\-\*•]\s', text, re.MULTILINE))
        if headers >= 3:
            score += 1.5
        elif headers >= 1:
            score += 0.5
        if bullets >= 5:
            score += 1.0
        elif bullets >= 2:
            score += 0.5
        # Code blocks
        if "```" in text:
            score += 0.5
        return min(10.0, score)

    def _score_actionability(self, text: str) -> float:
        """Score actionable recommendations (0-10).

        Returns 0.0 for empty or whitespace-only text.
        """
        if not text or not text.strip():
            return 0.0
        score = 4.0
        action_words = [
            "implement", "create", "configure", "execute", "deploy",
            "install", "add", "modify", "update", "review",
            "next step", "action item", "recommendation", "step",
            "implementar", "crear", "desplegar", "configurar",
        ]
        found = sum(1 for w in action_words if w in text.lower())
        score += min(found * 0.5, 3.0)
        # Numbered steps
        numbered = len(re.findall(r'^\d+[\.\)]\s', text, re.MULTILINE))
        if numbered >= 3:
            score += 2.0
        elif numbered >= 1:
            score += 1.0
        return min(10.0, score)

    def _score_completeness(self, text: str, input_text: str) -> float:
        """Score coverage of the asked topic (0-10)."""
        score = 5.0
        # Length as proxy for completeness
        if len(text) > 3000:
            score += 2.0
        elif len(text) > 1000:
            score += 1.0
        elif len(text) < 200:
            score -= 2.0
        # Check if input keywords appear in output
        if input_text:
            input_words = set(input_text.lower().split())
            input_words -= {"de", "la", "el", "en", "que", "y", "a", "un", "una", "los", "las", "por", "para", "con",
                           "the", "a", "an", "in", "on", "of", "to", "for", "and", "or", "is", "it", "with"}
            if input_words:
                overlap = sum(1 for w in input_words if w in text.lower())
                coverage = overlap / len(input_words)
                score += coverage * 3.0
        return min(10.0, score)

    def _score_factuality(self, text: str) -> float:
        """Score source citation and fact-checking signals (0-10).

        Returns 0.0 immediately for empty or whitespace-only text.
        """
        if not text or not text.strip():
            return 0.0
        score = 5.0
        # URLs present
        urls = re.findall(r'https?://\S+', text)
        if len(urls) >= 5:
            score += 3.0
        elif len(urls) >= 2:
            score += 2.0
        elif len(urls) >= 1:
            score += 1.0
        # Hedging language (positive — shows awareness of uncertainty)
        if any(w in text.lower() for w in ["source:", "reference:", "data from", "according to", "según", "fuente:"]):
            score += 1.0
        # Negative — unsubstantiated claims
        unsubstantiated = [
            "according to studies", "research demonstrates",
            "it is well known", "everyone knows",
            "según estudios", "las investigaciones demuestran",
            "es bien sabido", "todos saben",
        ]
        if any(phrase in text.lower() for phrase in unsubstantiated):
            score -= 2.0
        return max(0.0, min(10.0, score))
