"""
Constitution Hard Enforcement — FASE 0.

Hard rules block execution. Soft rules score output (future).
Enforced at crew output level before delivery.

Rules are defined in dof.constitution.yml (canonical source) and loaded
at module init. The YAML is merged with the in-code defaults so the
system works even if the YAML file is missing.
"""

import os
import re
import logging
from dataclasses import dataclass
from enum import Enum

import yaml

logger = logging.getLogger("core.governance")

# ─────────────────────────────────────────────────────────────────────
# YAML loader
# ─────────────────────────────────────────────────────────────────────

_CONSTITUTION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dof.constitution.yml",
)


def load_constitution(path: str | None = None) -> dict:
    """Load dof.constitution.yml and return parsed dict. Returns {} on failure."""
    path = path or _CONSTITUTION_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Constitution file not found: {path} — using in-code defaults")
        return {}
    except Exception as e:
        logger.warning(f"Error loading constitution: {e} — using in-code defaults")
        return {}


_CONSTITUTION: dict = load_constitution()


@dataclass
class GovernanceResult:
    """Result of governance check."""
    passed: bool
    score: float  # 0.0 - 1.0
    violations: list[str]
    warnings: list[str]


class RulePriority(str, Enum):
    """Instruction hierarchy — SYSTEM > USER > ASSISTANT."""
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"


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
        "priority": RulePriority.SYSTEM,
    },
    {
        "id": "LANGUAGE_COMPLIANCE",
        "description": "Response must be in English or contain structured data",
        "check": lambda text: _check_language(text),
        "priority": RulePriority.SYSTEM,
    },
    {
        "id": "NO_EMPTY_OUTPUT",
        "description": "Output cannot be empty or a placeholder",
        "check": lambda text: len(text.strip()) > 50 and text.strip() not in [
            "No output", "Error", "N/A", "TODO", "placeholder",
        ],
        "priority": RulePriority.SYSTEM,
    },
    {
        "id": "MAX_LENGTH",
        "description": "Output cannot exceed 50K chars",
        "check": lambda text: len(text) <= 50000,
        "priority": RulePriority.SYSTEM,
    },
]

# Soft rules — WARN but don't block
PII_PATTERNS = {
    "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "PHONE": re.compile(r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "CREDIT_CARD": re.compile(r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
}


def _check_no_pii(text: str) -> bool:
    """Check that text does not contain PII patterns (email, phone, SSN, credit card)."""
    for pattern in PII_PATTERNS.values():
        if pattern.search(text):
            return False
    return True


SOFT_RULES = [
    {
        "id": "HAS_SOURCES",
        "description": "Should include source URLs",
        "check": lambda text: bool(re.search(r'https?://', text)),
        "weight": 0.3,
        "priority": RulePriority.USER,
    },
    {
        "id": "STRUCTURED_OUTPUT",
        "description": "Should have clear structure (headers, bullets)",
        "check": lambda text: any(marker in text for marker in ["##", "- ", "* ", "1.", "•"]),
        "weight": 0.2,
        "priority": RulePriority.USER,
    },
    {
        "id": "CONCISENESS",
        "description": "Should not have repetitive paragraphs",
        "check": lambda text: _check_no_repetition(text),
        "weight": 0.2,
        "priority": RulePriority.USER,
    },
    {
        "id": "ACTIONABLE",
        "description": "Should include actionable steps or recommendations",
        "check": lambda text: any(
            kw in text.lower()
            for kw in ["recommend", "next step", "action", "implement", "recomend", "siguiente paso"]
        ),
        "weight": 0.3,
        "priority": RulePriority.USER,
    },
    {
        "id": "NO_PII_LEAK",
        "description": "Should not contain PII (emails, phones, SSNs, credit cards)",
        "check": lambda text: _check_no_pii(text),
        "weight": 0.3,
        "priority": RulePriority.USER,
    },
]


def _sync_rules_from_yaml(constitution: dict) -> None:
    """Ensure every rule_key in dof.constitution.yml has a matching entry in
    HARD_RULES / SOFT_RULES.  Logs warnings for YAML-only rules that have no
    in-code check function (they cannot be enforced without code).
    This guarantees the YAML is the canonical *registry* while Python remains
    the enforcement engine.
    """
    if not constitution:
        return

    rules_section = constitution.get("rules", {})
    hard_ids = {r["id"] for r in HARD_RULES}
    soft_ids = {r["id"] for r in SOFT_RULES}

    for yaml_rule in rules_section.get("hard", []):
        key = yaml_rule.get("rule_key", "")
        if key and key not in hard_ids:
            logger.info(f"YAML hard rule '{key}' has no in-code check — registry-only")

    for yaml_rule in rules_section.get("soft", []):
        key = yaml_rule.get("rule_key", "")
        if key and key not in soft_ids:
            logger.info(f"YAML soft rule '{key}' has no in-code check — registry-only")


_sync_rules_from_yaml(_CONSTITUTION)


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


def get_constitution() -> dict:
    """Return the loaded constitution dict (from dof.constitution.yml)."""
    return _CONSTITUTION


def _extract_python_blocks(text: str) -> list[str]:
    """Extract Python code blocks from markdown-formatted output."""
    blocks = []
    pattern = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(text):
        code = match.group(1).strip()
        if code:
            blocks.append(code)
    return blocks


# ─────────────────────────────────────────────────────────────────────
# Instruction hierarchy — override detection
# ─────────────────────────────────────────────────────────────────────

_OVERRIDE_PATTERNS = [
    "ignore rule",
    "skip governance",
    "disable check",
    "override constitution",
    "bypass rule",
    "turn off rule",
    "ignorar regla",
    "desactivar verificación",
]


def check_instruction_override(text: str, rule_priority: RulePriority) -> bool:
    """Check if output tries to override a rule of the given priority.

    SYSTEM rules: never overridable.
    USER rules: only overridable by SYSTEM.
    ASSISTANT rules: overridable by USER or SYSTEM.
    """
    if rule_priority == RulePriority.ASSISTANT:
        return False
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in _OVERRIDE_PATTERNS)


def get_rules_by_priority(priority: RulePriority) -> list[dict]:
    """Return all rules (hard + soft) at a given priority level."""
    return [r for r in HARD_RULES + SOFT_RULES if r.get("priority") == priority]


@dataclass
class HierarchyResult:
    """Result of instruction hierarchy enforcement."""
    compliant: bool
    violation_level: str    # "NONE", "SYSTEM", "USER", "ASSISTANT"
    details: str


# Patterns that indicate a user prompt trying to override system instructions
_SYSTEM_OVERRIDE_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "ignore your instructions",
    "disregard your instructions",
    "forget everything above",
    "override system prompt",
    "new system prompt",
    "you are now",
    "act as if you have no restrictions",
    "ignora las instrucciones anteriores",
    "ignora todo lo anterior",
    "olvida las instrucciones del sistema",
]

# Patterns that indicate a response violating system-level directives
_RESPONSE_VIOLATION_PATTERNS = [
    "i will ignore my instructions",
    "i am overriding my rules",
    "i no longer follow",
    "my previous instructions don't apply",
    "i am free to do anything",
    "i have no restrictions",
    "ignoro mis instrucciones",
    "ya no sigo las reglas",
]


def enforce_hierarchy(system_prompt: str, user_prompt: str,
                      response: str) -> HierarchyResult:
    """Detect instruction hierarchy violations.

    Checks:
    1. user_prompt tries to override system_prompt → violation at SYSTEM level
    2. response violates system_prompt directives → violation at SYSTEM level
    3. response contains override patterns → violation at USER level

    Returns HierarchyResult(compliant, violation_level, details).
    """
    user_lower = user_prompt.lower()
    response_lower = response.lower()

    # Check 1: user prompt tries to override system instructions
    for pattern in _SYSTEM_OVERRIDE_PATTERNS:
        if pattern in user_lower:
            return HierarchyResult(
                compliant=False,
                violation_level="SYSTEM",
                details=f"User prompt attempts system override: '{pattern}'",
            )

    # Check 2: response violates system directives
    for pattern in _RESPONSE_VIOLATION_PATTERNS:
        if pattern in response_lower:
            return HierarchyResult(
                compliant=False,
                violation_level="SYSTEM",
                details=f"Response violates system directive: '{pattern}'",
            )

    # Check 3: response contains governance override patterns
    if check_instruction_override(response, RulePriority.SYSTEM):
        return HierarchyResult(
            compliant=False,
            violation_level="USER",
            details="Response contains governance override attempt",
        )

    return HierarchyResult(
        compliant=True,
        violation_level="NONE",
        details="No hierarchy violations detected",
    )


class ConstitutionEnforcer:
    """Enforces governance rules on agent output."""

    def __init__(self):
        from core.ast_verifier import ASTVerifier
        self._ast_verifier = ASTVerifier()

    def check(self, output: str, context: str = "") -> GovernanceResult:
        """Run all governance checks on output.

        Returns GovernanceResult with pass/fail, score, violations, warnings.
        """
        violations = []
        warnings = []

        # AST verification on embedded code blocks
        code_blocks = _extract_python_blocks(output)
        for i, block in enumerate(code_blocks):
            ast_result = self._ast_verifier.verify(block)
            for v in ast_result.violations:
                label = f"[AST_VERIFY] Block {i+1}, line {v['line_number']}: {v['message']}"
                if v["severity"] == "block":
                    violations.append(label)
                else:
                    warnings.append(label)

        # Hard rules — any violation = fail
        for rule in HARD_RULES:
            try:
                if not rule["check"](output):
                    violations.append(f"[{rule['id']}] {rule['description']}")
            except Exception as e:
                logger.warning(f"Hard rule '{rule['id']}' check error: {e}")

        # Instruction hierarchy — check for override attempts on SYSTEM rules
        if check_instruction_override(output, RulePriority.SYSTEM):
            violations.append(
                "[INSTRUCTION_HIERARCHY] Attempt to override SYSTEM-level rules detected"
            )

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

    def enforce_hierarchy(self, system_prompt: str, user_prompt: str,
                          response: str) -> HierarchyResult:
        """Enforce instruction hierarchy as additional validation layer.

        Delegates to module-level enforce_hierarchy().
        """
        return enforce_hierarchy(system_prompt, user_prompt, response)
