"""
Constitution Hard Enforcement — FASE 0.

Hard rules block execution. Soft rules score output (future).
Enforced at crew output level before delivery.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("core.governance")


@dataclass
class GovernanceResult:
    """Result of governance check."""
    passed: bool
    score: float  # 0.0 - 1.0
    violations: list[str]
    warnings: list[str]


def _check_no_hallucination(text: str) -> bool:
    """Check that unsubstantiated claims have nearby URLs."""
    claim_phrases = [
        "according to recent studies",
        "statistics show",
        "data confirms",
        "research demonstrates",
        "según estudios recientes",
        "las estadísticas muestran",
        "datos confirman",
        "investigaciones demuestran",
    ]
    text_lower = text.lower()
    has_urls = "http" in text_lower
    for phrase in claim_phrases:
        if phrase in text_lower and not has_urls:
            return False
    return True


# Hard rules — BLOCK if violated
HARD_RULES = [
    {
        "id": "NO_HALLUCINATION_CLAIM",
        "description": "Must not assert fabricated data without source",
        "check": lambda text: _check_no_hallucination(text),
    },
    {
        "id": "LANGUAGE_COMPLIANCE",
        "description": "Response must be in English or contain structured data",
        "check": lambda text: _check_language(text),
    },
    {
        "id": "NO_EMPTY_OUTPUT",
        "description": "Output cannot be empty or a placeholder",
        "check": lambda text: len(text.strip()) > 50 and text.strip() not in [
            "No output", "Error", "N/A", "TODO", "placeholder",
        ],
    },
    {
        "id": "MAX_LENGTH",
        "description": "Output cannot exceed 50K chars",
        "check": lambda text: len(text) <= 50000,
    },
]

# Soft rules — WARN but don't block
SOFT_RULES = [
    {
        "id": "HAS_SOURCES",
        "description": "Should include source URLs",
        "check": lambda text: bool(re.search(r'https?://', text)),
        "weight": 0.3,
    },
    {
        "id": "STRUCTURED_OUTPUT",
        "description": "Should have clear structure (headers, bullets)",
        "check": lambda text: any(marker in text for marker in ["##", "- ", "* ", "1.", "•"]),
        "weight": 0.2,
    },
    {
        "id": "CONCISENESS",
        "description": "Should not have repetitive paragraphs",
        "check": lambda text: _check_no_repetition(text),
        "weight": 0.2,
    },
    {
        "id": "ACTIONABLE",
        "description": "Should include actionable steps or recommendations",
        "check": lambda text: any(
            kw in text.lower()
            for kw in ["recommend", "next step", "action", "implement", "recomend", "siguiente paso"]
        ),
        "weight": 0.3,
    },
]


def _check_language(text: str) -> bool:
    """Check if text is in English or contains structured data (JSON, markdown)."""
    # Structured data (JSON, pydantic output) always passes
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return True
    # English markers
    english_markers = [
        "the", "is", "and", "of", "to", "in", "for", "with", "that", "this",
        "are", "was", "has", "have", "from", "by", "an", "be", "as", "on",
    ]
    words = text.lower().split()[:200]
    if not words:
        return False
    english_count = sum(1 for w in words if w in english_markers)
    return english_count / len(words) > 0.05


def _check_no_repetition(text: str) -> bool:
    """Check for excessive paragraph repetition."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
    if len(paragraphs) < 3:
        return True
    seen = set()
    duplicates = 0
    for p in paragraphs:
        normalized = p[:100].lower()
        if normalized in seen:
            duplicates += 1
        seen.add(normalized)
    return duplicates < len(paragraphs) * 0.3


class ConstitutionEnforcer:
    """Enforces governance rules on agent output."""

    def check(self, output: str, context: str = "") -> GovernanceResult:
        """Run all governance checks on output.

        Returns GovernanceResult with pass/fail, score, violations, warnings.
        """
        violations = []
        warnings = []

        # Hard rules — any violation = fail
        for rule in HARD_RULES:
            try:
                if not rule["check"](output):
                    violations.append(f"[{rule['id']}] {rule['description']}")
            except Exception as e:
                logger.warning(f"Hard rule '{rule['id']}' check error: {e}")

        # Soft rules — calculate score
        soft_score = 0.0
        total_weight = 0.0
        for rule in SOFT_RULES:
            weight = rule.get("weight", 0.25)
            total_weight += weight
            try:
                if rule["check"](output):
                    soft_score += weight
                else:
                    warnings.append(f"[{rule['id']}] {rule['description']}")
            except Exception as e:
                logger.warning(f"Soft rule '{rule['id']}' check error: {e}")

        normalized_score = soft_score / total_weight if total_weight > 0 else 0.0
        passed = len(violations) == 0

        if violations:
            logger.warning(f"Governance FAILED: {violations}")
        if warnings:
            logger.info(f"Governance warnings: {[w.split(']')[0] + ']' for w in warnings]}")

        return GovernanceResult(
            passed=passed,
            score=round(normalized_score, 2),
            violations=violations,
            warnings=warnings,
        )

    def enforce(self, output: str, context: str = "") -> tuple[bool, str]:
        """Check and return (passed, message).

        Use this for simple pass/fail enforcement.
        """
        result = self.check(output, context)
        if result.passed:
            return True, f"OK (score={result.score})"
        return False, f"BLOCKED: {'; '.join(result.violations)}"
