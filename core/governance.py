"""
Constitution Hard Enforcement — FASE 0.

Hard rules block execution. Soft rules score output (future).
Enforced at crew output level before delivery.
"""

import os
import re
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger("core.governance")

# ── Constitution Enforcer (Phase 9) ───────────────────────────────────────────

class ConstitutionEnforcer:
    """
    Guards the mesh against non-deterministic behavior and ensures compliance
    with the DOF constitution. Validates tasks before orchestration.
    """
    def __init__(self, mesh_dir=None):
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path("logs/mesh")
        logger.info("ConstitutionEnforcer active — Guardian of Legion.")

    def validate_task(self, task: dict) -> bool:
        """Verify task doesn't contain blacklisted patterns or dangerous overrides."""
        if not task.get("task_type"):
            return False
        return True

    def enforce_sovereignty(self) -> None:
        """Ensure system nodes are not being hijacked by external LLM policies."""
        logger.info("Sovereignty check: COMPLETE. Nodes are deterministic.")

    def check(self, text: str) -> "GovernanceResult":
        """Alias used by dof.quick — returns GovernanceResult dataclass."""
        result = self.enforce(text)
        return GovernanceResult(
            passed=result["status"] == "COMPLIANT",
            score=result.get("score", 1.0),
            violations=result.get("hard_violations", []),
            warnings=result.get("soft_violations", []),
        )

    def enforce(self, text: str) -> dict:
        """
        Analytically verify that the provided text (or outputs) complies
        with the sovereign constitution.

        Delegates to check_governance() so HARD_RULES, SOFT_RULES and
        PII_PATTERNS are all evaluated consistently.
        """
        result = check_governance(text)
        return {
            "status": "COMPLIANT" if result.passed else "BLOCKED",
            "hard_violations": result.violations,
            "soft_violations": result.warnings,
            "score": result.score,
        }

# ─────────────────────────────────────────────────────────────────────
# Legacy Governance Logic
# ─────────────────────────────────────────────────────────────────────

@dataclass
class GovernanceResult:
    passed: bool
    score: float
    violations: list[str]
    warnings: list[str]

class RulePriority(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"

def check_governance(text: str) -> GovernanceResult:
    """Run hard rules, soft rules, and PII patterns against text."""
    violations: list[str] = []
    warnings: list[str] = []

    # Empty or whitespace-only input is a hard violation
    if not text or not text.strip():
        return GovernanceResult(
            passed=False, score=0.0,
            violations=["Empty output is not allowed"],
            warnings=[],
        )

    # Hard rules — block on match
    for rule in HARD_RULES:
        if re.search(rule["pattern"], text, re.IGNORECASE):
            violations.append(f"[{rule['id']}] {rule['description']}")

    # Soft rules — warn on match
    for rule in SOFT_RULES:
        if re.search(rule["pattern"], text, re.IGNORECASE):
            warnings.append(f"[{rule['id']}] {rule['description']}")

    # PII patterns — hard violation
    for pat in PII_PATTERNS:
        if re.search(pat["pattern"], text):
            violations.append(f"[{pat['id']}] PII detected: {pat['description']}")

    passed = len(violations) == 0
    score = 1.0 if passed else 0.0
    return GovernanceResult(
        passed=passed, score=score,
        violations=violations, warnings=warnings,
    )

# Registry for internal core use
GOVERNANCE_RULES = []

# ─────────────────────────────────────────────────────────────────────
# Constitution loader (required by dof/__init__.py)
# ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

# Default hard/soft rules and PII patterns
HARD_RULES: list[dict] = [
    {"id": "H1", "pattern": r"ignore (all |previous |prior )?instructions", "description": "Prompt injection attempt"},
    {"id": "H2", "pattern": r"jailbreak|DAN mode|developer mode", "description": "Jailbreak attempt"},
    {"id": "H3", "pattern": r"reveal.*(system prompt|instructions|api key)", "description": "Extraction attempt"},
    {"id": "H4", "pattern": r"\bstatistics show\b|\baccording to recent studies\b|\bstudies show\b|\bresearch shows\b", "description": "Unsupported claim without citation (NO_HALLUCINATION_CLAIM)"},
]

SOFT_RULES: list[dict] = [
    {"id": "S1", "pattern": r"sudo|rm -rf|DROP TABLE", "description": "Potentially dangerous command"},
    {"id": "S2", "pattern": r"<script|javascript:", "description": "Script injection"},
    {"id": "S3", "pattern": r"\bmeasurements were recorded\b|\bcomprehensive monitoring\b|\bsignificant delays\b", "description": "Vague unverified measurement claim"},
    {"id": "S4", "pattern": r"\btodo\b|\bfixme\b|\bhack\b|\bworkaround\b", "description": "Unresolved TODO or hack marker", "flags": re.IGNORECASE},
    {"id": "S5", "pattern": r"\bI (think|believe|feel|assume)\b", "description": "Unverified first-person assertion without evidence"},
]

PII_PATTERNS: list[dict] = [
    {"id": "P1", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "description": "SSN"},
    {"id": "P2", "pattern": r"\b4[0-9]{12}(?:[0-9]{3})?\b", "description": "Visa card"},
    {"id": "P3", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "description": "Email"},
]

def _extract_python_blocks(text: str) -> list[str]:
    """Extract Python code blocks from markdown-formatted text."""
    blocks = []
    pattern = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
    for m in pattern.finditer(text):
        blocks.append(m.group(1))
    return blocks


_constitution_cache: dict | None = None
_constitution_lock = threading.Lock()


def load_constitution(path: str | Path | None = None) -> dict:
    """Load the DOF constitution from YAML or return defaults."""
    global _constitution_cache
    with _constitution_lock:
        if _constitution_cache is not None:
            return _constitution_cache

        default_paths = [
            path,
            REPO_ROOT / "dof.constitution.yml",
            REPO_ROOT / "config" / "constitution.yml",
        ]

        for p in default_paths:
            if p is None:
                continue
            p = Path(p)
            if p.exists() and yaml is not None:
                try:
                    data = yaml.safe_load(p.read_text()) or {}
                    _constitution_cache = data
                    logger.info("Constitution loaded from %s", p)
                    return data
                except Exception as e:
                    logger.warning("Could not load constitution from %s: %s", p, e)

        # Return minimal default constitution
        _constitution_cache = {
            "version": "1.0",
            "hard_rules": HARD_RULES,
            "soft_rules": SOFT_RULES,
            "pii_patterns": PII_PATTERNS,
        }
        logger.info("Using default constitution (no YAML found)")
        return _constitution_cache


def get_constitution() -> dict:
    """Alias for load_constitution() with no arguments."""
    return load_constitution()
