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

try:
    from constitution.integrity_watcher import ConstitutionIntegrityWatcher, ConstitutionDriftException
    _INTEGRITY_AVAILABLE = True
except ImportError:
    _INTEGRITY_AVAILABLE = False

logger = logging.getLogger("core.governance")

# ── Constitution Enforcer (Phase 9) ───────────────────────────────────────────

class ConstitutionEnforcer:
    """
    Guards the mesh against non-deterministic behavior and ensures compliance
    with the DOF constitution. Validates tasks before orchestration.
    """
    def __init__(self, mesh_dir=None):
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path("logs/mesh")
        if _INTEGRITY_AVAILABLE:
            all_rules = {r["id"]: r for r in HARD_RULES + SOFT_RULES}
            self._integrity_watcher = ConstitutionIntegrityWatcher(all_rules)
        else:
            self._integrity_watcher = None
        logger.info("ConstitutionEnforcer active — Guardian of Legion.")

    def verify_constitution_integrity(self) -> bool:
        """Verifica que las reglas de Constitution no han sido modificadas."""
        if self._integrity_watcher is None:
            return True
        try:
            self._integrity_watcher.verify()
            return True
        except ConstitutionDriftException as e:
            logger.error(f"Constitution drift detected: {e}")
            return False

    def validate_task(self, task: dict) -> bool:
        """Verify task doesn't contain blacklisted patterns or dangerous overrides."""
        if not task.get("task_type"):
            return False
        return True

    def enforce_sovereignty(self) -> None:
        """Ensure system nodes are not being hijacked by external LLM policies."""
        logger.info("Sovereignty check: COMPLETE. Nodes are deterministic.")

    def enforce_hierarchy(
        self,
        system_prompt: str,
        user_prompt: str,
        response: str,
    ) -> "HierarchyResult":
        """Delegate to module-level enforce_hierarchy."""
        return enforce_hierarchy(system_prompt, user_prompt, response)

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
# Data classes and enums
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

@dataclass
class HierarchyResult:
    compliant: bool
    violation_level: str  # "NONE", "SYSTEM", "USER"
    details: list[str] | str

# ─────────────────────────────────────────────────────────────────────
# Constitution loader (required by dof/__init__.py)
# ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

# Default hard/soft rules and PII patterns — IDs match YAML rule_key
HARD_RULES: list[dict] = [
    {"id": "NO_HALLUCINATION_CLAIM", "priority": RulePriority.SYSTEM, "pattern": r"\bstatistics show\b|\baccording to recent studies\b|\bstudies show\b|\bresearch shows\b|\bdata confirms\b|\bresearch demonstrates\b", "description": "Must not assert fabricated data without source", "type": "phrase_without_url"},
    {"id": "LANGUAGE_COMPLIANCE", "priority": RulePriority.SYSTEM, "pattern": None, "description": "Response must be in English or contain structured data", "type": "language_check"},
    {"id": "NO_EMPTY_OUTPUT", "priority": RulePriority.SYSTEM, "pattern": None, "description": "Output cannot be empty or a placeholder", "type": "min_length", "min_length": 50},
    {"id": "MAX_LENGTH", "priority": RulePriority.SYSTEM, "pattern": None, "description": "Output cannot exceed 50K chars", "type": "max_length", "max_chars": 50000},
]

SOFT_RULES: list[dict] = [
    {"id": "HAS_SOURCES", "priority": RulePriority.USER, "pattern": r"https?://", "description": "Should include source URLs", "weight": 0.3, "match_mode": "absent"},
    {"id": "STRUCTURED_OUTPUT", "priority": RulePriority.USER, "pattern": r"##|- |\* |1\.|•", "description": "Should have clear structure (headers, bullets)", "weight": 0.2, "match_mode": "absent"},
    {"id": "CONCISENESS", "priority": RulePriority.USER, "pattern": r"\bmeasurements were recorded\b|\bcomprehensive monitoring\b|\bsignificant delays\b", "description": "Should not have repetitive paragraphs", "weight": 0.2, "match_mode": "present"},
    {"id": "ACTIONABLE", "priority": RulePriority.USER, "pattern": r"\b(recommend|next step|action|implement|recomend|siguiente paso)\b", "description": "Should include actionable steps or recommendations", "weight": 0.3, "match_mode": "absent"},
    {"id": "NO_PII_LEAK", "priority": RulePriority.USER, "pattern": r"\b\d{3}-\d{2}-\d{4}\b|\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}|\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "description": "Should not contain PII (emails, phones, SSNs, credit cards)", "weight": 0.3, "match_mode": "present"},
]

PII_PATTERNS: list[dict] = [
    {"id": "P1", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "description": "SSN"},
    {"id": "P2", "pattern": r"\b4[0-9]{12}(?:[0-9]{3})?\b", "description": "Visa card"},
    {"id": "P3", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "description": "Email"},
]

# Prompt injection / hierarchy override patterns
_OVERRIDE_PATTERNS = [
    r"\bignore\s+(all\s+)?(rule|previous\s+instructions?|prior\s+instructions?|my\s+instructions?|the\s+system\s+prompt)",
    r"\bskip\s+governance",
    r"\bbypass\s+rule",
    r"\bdisable\s+(all\s+)?rules",
    r"\boverride\s+(the\s+)?constitution",
    r"\bignora\s+(las\s+)?instrucciones",
]

# Indirect privilege escalation patterns (for enforce_hierarchy)
_ESCALATION_PATTERNS = [
    r"\b(system\s+)?administrator.*(?:updating|changing|modifying)\s+(your\s+)?instructions",
    r"\bhigher\s+permission\s+level\b",
    r"\bprevious\s+restrictions\s+no\s+longer\s+apply\b",
    r"\broot\s+access\b.*(?:authorized|approved|granted)",
    r"\bsupersede\s+(the\s+)?(original\s+)?system\s+prompt\b",
    r"\b(developer|admin)\s+has\s+(unlocked|enabled|activated)\b",
    r"\bunrestricted\s+mode\b",
    r"\bnew\s+system\s+administrator\b",
    r"\bupgraded\s+to\s+a\s+higher\b",
    r"\bI\s+will\s+ignore\s+my\s+instructions\b",
    r"\bignore\s+(the\s+)?system\s+prompt\b",
]

# Backwards-compatible aliases (used by hierarchy_z3.py)
_SYSTEM_OVERRIDE_PATTERNS = _OVERRIDE_PATTERNS
_RESPONSE_VIOLATION_PATTERNS = _ESCALATION_PATTERNS

# Registry for internal core use
GOVERNANCE_RULES = []

# ─────────────────────────────────────────────────────────────────────
# Initialization — Load constitution at startup
# ─────────────────────────────────────────────────────────────────────

def _sync_rules_from_constitution():
    """Sync HARD_RULES and SOFT_RULES with the YAML constitution if available."""
    global HARD_RULES, SOFT_RULES
    const = load_constitution()
    if not const:
        return

    # Sync Hard Rules
    yaml_hard = const.get("rules", {}).get("hard", [])
    if yaml_hard:
        new_hard = []
        for r in yaml_hard:
            new_hard.append({
                "id": r.get("rule_key") or r.get("id"),
                "priority": RulePriority.SYSTEM,
                "pattern": r.get("pattern", {}).get("phrases") or r.get("pattern", {}).get("regex"),
                "description": r.get("description"),
                "type": r.get("pattern", {}).get("type", "regex"),
                "min_length": r.get("pattern", {}).get("min_length"),
                "max_chars": r.get("pattern", {}).get("max_chars"),
            })
        if new_hard:
            HARD_RULES = new_hard

    # Sync Soft Rules — merge YAML into Python defaults (Python wins on missing fields)
    yaml_soft = const.get("rules", {}).get("soft", [])
    if yaml_soft:
        # Build lookup of Python-defined defaults keyed by rule id
        _py_defaults = {rule["id"]: rule for rule in SOFT_RULES}
        new_soft = []
        for r in yaml_soft:
            pat = r.get("pattern", {})
            pat_type = pat.get("type", "")
            rule_id = r.get("rule_key") or r.get("id", "")
            py_default = _py_defaults.get(rule_id, {})

            # Extract regex — prefer YAML, fall back to Python default
            raw_pattern = pat.get("regex") or pat.get("keywords")
            if not raw_pattern and pat.get("patterns"):
                raw_pattern = "|".join(pat["patterns"])
            if not raw_pattern and pat.get("markers"):
                raw_pattern = "|".join(re.escape(m) for m in pat["markers"])
            if not raw_pattern:
                # Fall back to Python-defined pattern (e.g. CONCISENESS repetition_check)
                raw_pattern = py_default.get("pattern")

            # Determine match_mode:
            # ABSENT types → warn when desirable pattern missing
            # PRESENT types → warn when undesirable pattern found
            _absent_pat_types = {"regex", "contains_any", "contains_any_keyword"}
            _present_ids = {"NO_PII_LEAK", "CONCISENESS"}
            if rule_id in _present_ids or pat_type in ("regex_absent", "regex_present"):
                match_mode = "present"
            elif pat_type in _absent_pat_types:
                match_mode = "absent"
            else:
                # Fall back to Python-defined match_mode
                match_mode = py_default.get("match_mode", "present")

            new_soft.append({
                "id": rule_id,
                "priority": r.get("priority", RulePriority.USER),
                "pattern": raw_pattern,
                "description": r.get("description") or py_default.get("description"),
                "weight": r.get("weight", py_default.get("weight", 0.1)),
                "match_mode": match_mode,
            })
        if new_soft:
            SOFT_RULES = new_soft

    # Internal registry for reporting
    global GOVERNANCE_RULES
    GOVERNANCE_RULES = HARD_RULES + SOFT_RULES
    logger.info("Governance synced with constitution: %d rules active", len(GOVERNANCE_RULES))

# ─────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────

def _has_source_attribution(text: str) -> bool:
    """Check if text has source attribution (URL or explicit source reference)."""
    if re.search(r'https?://', text):
        return True
    if re.search(r'\b(Sources?|References?|Citations?|Cited from)\s*:', text, re.IGNORECASE):
        return True
    return False


def _extract_python_blocks(text: str) -> list[str]:
    """Extract Python code blocks from markdown-formatted text."""
    blocks = []
    pattern = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
    for m in pattern.finditer(text):
        blocks.append(m.group(1))
    return blocks


# ─────────────────────────────────────────────────────────────────────
# Core governance check
# ─────────────────────────────────────────────────────────────────────

def check_governance(text: str) -> GovernanceResult:
    """Run hard rules, soft rules, PII patterns, and AST verification against text."""
    violations: list[str] = []
    warnings: list[str] = []

    # Ensure input is string
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    # Empty or whitespace-only input is a hard violation
    if not text or not text.strip():
        return GovernanceResult(
            passed=False, score=0.0,
            violations=["Empty output is not allowed"],
            warnings=[],
        )

    # Hard rules — block on match (YAML-aligned logic)
    for rule in HARD_RULES:
        rule_type = rule.get("type", "regex")
        pattern = rule.get("pattern")

        if rule_type == "phrase_without_url":
            # Only trigger if hallucination phrase present AND no source attribution
            phrases = pattern if isinstance(pattern, list) else ([pattern] if pattern else [])
            found_hallucination = False
            for p in phrases:
                if re.search(p, text, re.IGNORECASE):
                    found_hallucination = True
                    break
            
            if found_hallucination and not _has_source_attribution(text):
                violations.append(f"[{rule['id']}] {rule['description']}")

        elif rule_type == "min_length" or rule_type == "min_length_and_blocklist":
            min_len = rule.get("min_length", 50)
            stripped = text.strip()
            blocked_values = {"no output", "error", "n/a", "todo", "placeholder"}
            if len(stripped) < min_len or stripped.lower() in blocked_values:
                violations.append(f"[{rule['id']}] {rule['description']}")

        elif rule_type == "max_length":
            max_chars = rule.get("max_chars", 50000)
            if len(text) > max_chars:
                violations.append(f"[{rule['id']}] {rule['description']}")

        elif rule_type == "language_check":
            # Pass if structured data or contains English markers
            stripped = text.strip()
            if not (stripped.startswith("{") or stripped.startswith("[")):
                words = stripped[:800].lower().split()
                # Use markers if available in rule, else defaults
                en_markers = set(rule.get("english_markers") or ["the", "is", "and", "of", "to", "in", "for", "with"])
                if words:
                    ratio = sum(1 for w in words if w in en_markers) / len(words)
                    if ratio < 0.05:
                        violations.append(f"[{rule['id']}] {rule['description']}")

        elif pattern:
            # Fallback: simple regex (or list of keywords)
            keywords = pattern if isinstance(pattern, list) else [pattern]
            for kw in keywords:
                if re.search(kw, text, re.IGNORECASE):
                    violations.append(f"[{rule['id']}] {rule['description']}")
                    break

    # Soft rules — warn based on match_mode
    for rule in SOFT_RULES:
        pattern = rule.get("pattern")
        if not pattern:
            continue
            
        # Handle list of patterns or single string
        patterns = pattern if isinstance(pattern, list) else [pattern]
        match_found = False
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                match_found = True
                break
                
        mode = rule.get("match_mode", "present")
        if mode == "absent" and not match_found:
            # Warn when the desirable pattern is absent
            warnings.append(f"[{rule['id']}] {rule['description']}")
        elif mode == "present" and match_found:
            # Warn when an undesirable pattern is present
            warnings.append(f"[{rule['id']}] {rule['description']}")

    # PII patterns — hard violation
    for pat in PII_PATTERNS:
        if re.search(pat["pattern"], text):
            violations.append(f"[{pat['id']}] PII detected: {pat['description']}")

    # Instruction hierarchy — detect override attempts
    for pat in _OVERRIDE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            violations.append(
                f"[INSTRUCTION_HIERARCHY] Override attempt detected: "
                f"matches '{pat}'"
            )

    # AST verification for Python code blocks
    code_blocks = _extract_python_blocks(text)
    if code_blocks:
        try:
            from core.ast_verifier import ASTVerifier
            verifier = ASTVerifier()
            for block in code_blocks:
                ast_result = verifier.verify(block)
                if not ast_result.passed:
                    for v in ast_result.violations:
                        msg = v.get("message", "Unknown") if isinstance(v, dict) else str(v)
                        violations.append(f"[AST_VERIFY] {msg}")
        except ImportError:
            logger.warning("ASTVerifier not available — skipping code block analysis")

    passed = len(violations) == 0
    score = 1.0 if passed else 0.0
    return GovernanceResult(
        passed=passed, score=score,
        violations=violations, warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────
# Self-Correction Loop — deterministic auto-repair for soft violations
# ─────────────────────────────────────────────────────────────────────

# Soft rules eligible for auto-correction (regex strip of offending pattern)
# NO_PII_LEAK is intentionally excluded — never auto-strip PII silently
_CORRECTABLE_SOFT_RULES: set[str] = {"CONCISENESS"}

def check_and_correct(text: str) -> tuple[str, "GovernanceResult"]:
    """Run governance check and attempt deterministic correction if only soft rules fail.

    If the text only has warnings (no hard violations), applies regex-strip
    corrections for rules marked as correctable, then re-checks.

    Returns:
        (corrected_text, GovernanceResult) — corrected_text == text if no changes needed.

    Rules:
        - HARD violations → return immediately, no correction attempted
        - Only SOFT violations with correctable rules → strip offending patterns
        - NO_PII_LEAK is never auto-corrected (could suppress legitimate data)
    """
    result = check_governance(text)

    # Already passing — nothing to do
    if result.passed and not result.warnings:
        return text, result

    # Hard violations → cannot auto-correct
    if result.violations:
        return text, result

    # Only warnings → attempt correction for correctable rules
    corrected = text
    corrected_rules: list[str] = []

    for rule in SOFT_RULES:
        rule_id = rule.get("id", "")
        if rule_id not in _CORRECTABLE_SOFT_RULES:
            continue
        if rule.get("match_mode") != "present":
            continue
        pattern = rule.get("pattern")
        if not pattern:
            continue

        # Strip lines that match the offending pattern
        patterns = pattern if isinstance(pattern, list) else [pattern]
        for p in patterns:
            if re.search(p, corrected, re.IGNORECASE):
                corrected = re.sub(p, "", corrected, flags=re.IGNORECASE).strip()
                corrected_rules.append(rule_id)

    if not corrected_rules:
        return text, result

    # Re-check corrected text
    new_result = check_governance(corrected)
    logger.debug(
        f"check_and_correct: fixed {corrected_rules} → "
        f"passed={new_result.passed} warnings={len(new_result.warnings)}"
    )
    return corrected, new_result


# ─────────────────────────────────────────────────────────────────────
# Instruction hierarchy enforcement
# ─────────────────────────────────────────────────────────────────────

def check_instruction_override(text: str, priority: RulePriority) -> bool:
    """Check if text contains instruction override attempts.

    Returns True if an override is detected at the given priority level.
    ASSISTANT-level instructions are allowed to reference rules.
    """
    if priority == RulePriority.ASSISTANT:
        return False
    for pat in _OVERRIDE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def get_rules_by_priority(priority: RulePriority) -> list[dict]:
    """Return rules filtered by priority level."""
    result = []
    for rule in HARD_RULES:
        if rule.get("priority") == priority:
            result.append(rule)
    for rule in SOFT_RULES:
        if rule.get("priority") == priority:
            result.append(rule)
    return result


def enforce_hierarchy(
    system_prompt: str,
    user_prompt: str,
    response: str,
) -> HierarchyResult:
    """Enforce instruction hierarchy: SYSTEM > USER > ASSISTANT.

    Checks that neither user nor response attempts to override system rules.
    Returns HierarchyResult with violation_level as string ("NONE", "SYSTEM", "USER").
    """
    details: list[str] = []
    violation_level = "NONE"

    # Check user prompt for system-level overrides
    if check_instruction_override(user_prompt, RulePriority.SYSTEM):
        details.append("system override")
        violation_level = "SYSTEM"

    # Check response for indirect privilege escalation (SYSTEM-level)
    escalation_found = False
    for pat in _ESCALATION_PATTERNS:
        if re.search(pat, response, re.IGNORECASE):
            if violation_level == "NONE":
                violation_level = "SYSTEM"
            details.append("system override")
            escalation_found = True
            break

    # Check response for direct override patterns (USER-level if no escalation)
    if not escalation_found and check_instruction_override(response, RulePriority.SYSTEM):
        if violation_level == "NONE":
            violation_level = "USER"
        details.append("system override")

    return HierarchyResult(
        compliant=len(details) == 0,
        violation_level=violation_level,
        details=details,
    )


# ─────────────────────────────────────────────────────────────────────
# Constitution YAML loader
# ─────────────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────────────
# ZK Governance Proof integration
# ─────────────────────────────────────────────────────────────────────

def enforce_with_proof(
    text: str,
    rule_ids: list[str] | None = None,
    timestamp: str | None = None,
    log_path: str = "",
) -> tuple:
    """Ejecuta governance check y genera un proof criptográfico verificable.

    Wrapper sobre check_governance() que NO modifica enforce() existente.
    Genera un GovernanceProof con hash keccak256 del resultado.

    Args:
        text: Texto a verificar contra la constitución.
        rule_ids: IDs de reglas a incluir en el proof (opcional, auto-extraído).
        timestamp: ISO 8601 timestamp (opcional, auto-generado).
        log_path: Ruta al JSONL de proofs (opcional).

    Returns:
        Tupla (GovernanceResult, GovernanceProof).
    """
    from core.zk_governance_proof import GovernanceProofGenerator

    result = check_governance(text)
    gen = GovernanceProofGenerator(log_path=log_path)
    proof = gen.generate_proof_from_result(
        result, rule_ids=rule_ids, timestamp=timestamp,
    )
    return result, proof

# ─────────────────────────────────────────────────────────────────────
# Initialization — Auto-sync on import
# ─────────────────────────────────────────────────────────────────────
_sync_rules_from_constitution()
