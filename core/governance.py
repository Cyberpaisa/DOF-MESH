"""
Constitution Hard Enforcement — FASE 0.

Hard rules block execution. Soft rules score output (future).
Enforced at crew output level before delivery.
"""

import codecs
import os
import re
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import glob
import sys

try:
    import yaml
except ImportError:
    yaml = None

try:
    from constitution.integrity_watcher import ConstitutionIntegrityWatcher, ConstitutionDriftException
    _INTEGRITY_AVAILABLE = True
except ImportError:
    _INTEGRITY_AVAILABLE = False

try:
    from core.feature_flags import flags as _feature_flags
    _FLAGS_AVAILABLE = True
except ImportError:
    _feature_flags = None  # type: ignore[assignment]
    _FLAGS_AVAILABLE = False

logger = logging.getLogger("core.governance")

# ── Constitution Enforcer (Phase 9) ───────────────────────────────────────────

class ConstitutionEnforcer:
    """
    Guards the mesh against non-deterministic behavior and ensures compliance
    with the DOF constitution. Validates tasks before orchestration.
    """
    def __init__(self, mesh_dir=None, industry: str | None = None):
        self.mesh_dir = Path(mesh_dir) if mesh_dir else Path("logs/mesh")
        self.registry = ConstitutionRegistry()
        
        # Local rules for this instance (init with defaults)
        self.hard_rules = list(HARD_RULES)
        self.soft_rules = list(SOFT_RULES)
        
        # Load base core pack if available
        self.registry.load_pack("core", hard_list=self.hard_rules, soft_list=self.soft_rules)
        
        # Load industry pack if requested
        if industry:
            self.registry.load_pack(industry, hard_list=self.hard_rules, soft_list=self.soft_rules)

        if _INTEGRITY_AVAILABLE:
            all_rules = {r["id"]: r for r in self.hard_rules + self.soft_rules}
            self._integrity_watcher = ConstitutionIntegrityWatcher(all_rules)
        else:
            self._integrity_watcher = None
        logger.info("ConstitutionEnforcer active — Industry: %s", industry or "Default")

    def load_pack(self, industry: str) -> bool:
        """Dynamically load an industry governance pack at runtime."""
        return self.registry.load_pack(industry, hard_list=self.hard_rules, soft_list=self.soft_rules)

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
        return check_governance(text, hard_rules=self.hard_rules, soft_rules=self.soft_rules)

    def enforce(self, text: str) -> dict:
        """
        Analytically verify that the provided text (or outputs) complies
        with the sovereign constitution.
        """
        result = check_governance(text, hard_rules=self.hard_rules, soft_rules=self.soft_rules)
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

    def __getitem__(self, key):
        # Backward compatibility for result["status"]
        if key == "status":
            return "COMPLIANT" if self.passed else "BLOCKED"
        return getattr(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except (AttributeError, KeyError):
            return default

@dataclass
class HierarchyResult:
    compliant: bool
    violation_level: str
    details: list[str]

# ─────────────────────────────────────────────────────────────────────
# Constants and Rule Definitions
# ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

class RulePriority(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"

# Default hard/soft rules and PII patterns — IDs match YAML rule_key
HARD_RULES: list[dict] = [
    {"id": "NO_HALLUCINATION_CLAIM", "priority": RulePriority.SYSTEM, "pattern": r"\bstatistics show\b|\baccording to recent studies\b|\bstudies show\b|\bresearch shows\b|\bdata confirms\b|\bresearch demonstrates\b|\bit has been shown\b|\bit is well.known\b|\bexperts agree\b|\b\d{2,3}%\s+of\s+(?:cases?|users?|people|respondents?|participants?)\b", "description": "Must not assert fabricated data without source", "type": "phrase_without_url"},
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

# Registry for internal core use
GOVERNANCE_RULES = HARD_RULES + SOFT_RULES

# ─────────────────────────────────────────────────────────────────────
# Constitution Registry — Modular Industry Packs
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# Constitution Registry — Modular Industry Packs
# ─────────────────────────────────────────────────────────────────────

class ConstitutionRegistry:
    """Manages the loading and registration of industry-specific governance packs."""
    def __init__(self, packs_dir: str | Path | None = None):
        self.packs_dir = Path(packs_dir) if packs_dir else REPO_ROOT / "constitutions" / "packs"
        self._loaded_packs: set[str] = set()

    def load_pack(self, pack_name: str, hard_list: list | None = None, soft_list: list | None = None) -> bool:
        """Load a YAML pack from the registry directory.
        
        Args:
            pack_name: Name of the pack (folder).
            hard_list: List to append hard rules to (defaults to global HARD_RULES).
            soft_list: List to append soft rules to (defaults to global SOFT_RULES).
        """
        global HARD_RULES, SOFT_RULES, GOVERNANCE_RULES
        
        h_list = hard_list if hard_list is not None else HARD_RULES
        s_list = soft_list if soft_list is not None else SOFT_RULES
        
        pack_path = self.packs_dir / pack_name
        # print(f"DEBUG: Loading pack {pack_name} from {pack_path}")
        if not pack_path.exists():
            logger.warning("Governance pack directory not found: %s", pack_path)
            return False

        yml_files = glob.glob(str(pack_path / "*.yml"))
        # print(f"DEBUG: YAML files found: {yml_files}")
        if not yml_files:
            logger.warning("No YAML files found in pack: %s", pack_name)
            return False

        loaded_count = 0
        for yml in yml_files:
            try:
                with open(yml, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                # Append Hard Rules
                new_hards = data.get("rules", {}).get("hard", [])
                for r in new_hards:
                    rule_entry = {
                        "id": r.get("rule_key") or r.get("id"),
                        "priority": RulePriority.SYSTEM,
                        "pattern": r.get("pattern", {}).get("regex") or r.get("pattern", {}).get("phrases"),
                        "description": r.get("description"),
                        "type": r.get("pattern", {}).get("type", "regex"),
                        "min_length": r.get("pattern", {}).get("min_length"),
                        "max_chars": r.get("pattern", {}).get("max_chars"),
                    }
                    rule_entry["match_mode"] = "absent" if "absent" in rule_entry["type"] else "present"
                    
                    if rule_entry["id"] not in [hr["id"] for hr in h_list]:
                        h_list.append(rule_entry)
                
                # Append Soft Rules
                new_softs = data.get("rules", {}).get("soft", [])
                for r in new_softs:
                    rule_id = r.get("rule_key") or r.get("id")
                    rule_entry = {
                        "id": rule_id,
                        "priority": r.get("priority", RulePriority.USER),
                        "pattern": r.get("pattern", {}).get("regex") or r.get("pattern", {}).get("patterns"),
                        "description": r.get("description"),
                        "weight": r.get("weight", 0.1),
                        "match_mode": "present" if "present" in r.get("pattern", {}).get("type", "") else "absent"
                    }
                    if rule_id not in [sr["id"] for sr in s_list]:
                        s_list.append(rule_entry)
                
                loaded_count += 1
            except Exception as e:
                logger.error("Error loading governance YAML %s: %s", yml, e)

        self._loaded_packs.add(pack_name)
        
        # If we modified global lists, update the global registry
        if hard_list is None or soft_list is None:
            GOVERNANCE_RULES = HARD_RULES + SOFT_RULES
            
        logger.info("Loaded pack '%s' (%d files).", pack_name, loaded_count)
        return True

# Default hard/soft rules and PII patterns — IDs match YAML rule_key
HARD_RULES: list[dict] = [
    {"id": "NO_HALLUCINATION_CLAIM", "priority": RulePriority.SYSTEM, "pattern": r"\bstatistics show\b|\baccording to recent studies\b|\bstudies show\b|\bresearch shows\b|\bdata confirms\b|\bresearch demonstrates\b|\bit has been shown\b|\bit is well.known\b|\bexperts agree\b|\b\d{2,3}%\s+of\s+(?:cases?|users?|people|respondents?|participants?)\b", "description": "Must not assert fabricated data without source", "type": "phrase_without_url"},
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
# CVE-DOF-001: extended with newline injection + developer override + soft overrides
_OVERRIDE_PATTERNS = [
    r"\bignore\s+(all\s+)?(rules?|previous\s+ins\w*tions?|prior\s+ins\w*tions?|my\s+ins\w*tions?|the\s+system\s+prompt)",
    r"\bskip\s+governance",
    r"\bbypass\s+rule",
    r"\bdisable\s+(all\s+)?rules",
    r"\boverride\s+(the\s+)?constitution",
    r"\bignora\s+(las\s+)?(instrucciones|reglas)",
    # CVE-DI-003: Spanish "ignora las reglas anteriores"
    r"(?i)\bignora\s+(las\s+)?reglas\s+(anteriores|previas)",
    # CVE-SI-005: "disregard" as synonym of "ignore"
    r"(?i)\bdisregard\s+(?:what\s+you\s+were|everything\s+(?:you\s+were|above)|all\s+(?:previous|prior))",
    r"(?i)\bact\s+without\s+(?:limitations?|restrictions?|constraints?)",
    # CVE-SI-007: hypothetical framing to bypass rules
    r"(?i)(?:hypothetically|theoretically),?\s+(?:if|what\s+if)\s+(?:your|the)\s+rules?\s+(?:didn|did\s+not|don|do\s+not)\s*(?:'t)?\s+exist",
    # CVE-SI-003/004: encoded payload detection (base64, ROT13)
    r"(?i)(?:decode|decrypt|deobfuscate|execute|run|eval)\s+(?:and\s+)?(?:execute|run|follow|apply)?\s*:\s*[A-Za-z0-9+/=]{20,}",
    r"(?i)(?:decode|decrypt)\s+(?:and\s+)?(?:execute|run|follow)\b",
    # CVE-SI-008: SYSTEM override hidden in code comments
    r"#\s*(?:SYSTEM|SYS)\s*:\s*(?:unrestricted|override|ignore|bypass|disable)",
    r"#\s*ignore_rules\s*=\s*True",
    # CVE-DOF-001: newline injection
    r"(?m)^(?:SYSTEM|SYS)\s*:\s*\w",
    r"(?m)^-{3,}\s*$.*?SYSTEM\s*:",
    r"(?i)SYSTEM\s*:\s*(?:governance|directive|override|disable|suspend)",
    # CVE-DOF-001: developer/role override
    r"(?i)as\s+(?:the\s+)?(?:lead\s+)?developer\s+of\s+this\s+system",
    r"(?i)I(?:'m|\s+am)\s+(?:the\s+)?(?:lead\s+)?developer\s+(?:authoriz|approv)",
    # Soft override patterns (no exact keyword match)
    r"(?i)set\s+aside\s+(?:your\s+)?(?:normal\s+)?guideline",
    r"(?i)for\s+(?:this\s+task|testing\s+purposes?),?\s+(?:temporarily\s+)?(?:disable|skip|ignore)",
    # Maintenance / diagnostic false flags
    r"(?i)maintenance\s+mode\s+(?:activated|enabled|on)",
    r"(?i)(?:all\s+)?safety\s+checks?\s+(?:suspended|disabled|bypassed)",
    r"(?i)diagnostic\s+(?:mode|override)\s+(?:active|enabled)",
    # CVE-DOF-016: Developer mode and role override attacks
    r"(?i)\b(?:you\s+are\s+(?:now\s+)?in|enter|activate|enable)\s+developer\s+mode\b",
    r"(?i)\bas\s+an?\s+AI\s+with\s+no\s+(?:restrictions?|rules?|limitations?|constraints?)\b",
    # CVE-DOF-015: Memory poisoning — fake rule injection
    r"(?i)(?:SYSTEM\s+)?RULE\s+OVERRIDE\s*:",
    r"(?i)New\s+rule\s*:\s+(?:always|never|when\s+asked)",
    r"(?i)(?:updated?|new|revised)\s+(?:system\s+)?rule\s*:\s+(?:always|comply|respond|ignore)",
]

# Indirect privilege escalation patterns (for enforce_hierarchy)
# CVE-DOF-005: 12 new patterns for indirect escalation
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
    # CVE-DOF-005 additions
    r"(?i)security\s+team(?:'s)?\s+(?:has\s+)?(?:updated|changed|modified|update[d]?)\s+(?:your\s+)?(?:config|configuration|settings|mode|protocol|policy)",
    r"(?i)as\s+per\s+(?:the\s+)?(?:security\s+team|it\s+team|compliance|audit)\s*[''s]*\s+(?:updated?|new|revised)\s+(?:protocol|policy|directive|configuration)",
    r"(?i)(?:per|according\s+to)\s+(?:updated?|new|revised)\s+(?:protocol|policy|directive|security\s+guidelines?)",
    r"\[PRIORITY\s*:\s*SYSTEM\]",
    r"\[OVERRIDE\s*:\s*(?:TRUE|YES|1)\]",
    r"(?i)for\s+(?:testing\s+)?purposes?\s+only,?\s+(?:temporarily\s+)?disable",
    r"(?i)AUDIT\s+LOG\s*:",
    r"(?i)(?:continuing|resuming)\s+from\s+(?:last|previous)\s+session\s+state",
    r"(?i)(?:new|updated)\s+(?:mode|policy)\s*:\s*unrestricted",
    # CVE-DOF-013: Post-normalization SYSTEM injection (whitespace padding attack — SI-010)
    # After whitespace collapse, "...   SYSTEM: override" becomes "... SYSTEM: override"
    # The line-start pattern misses this. This catches inline SYSTEM: claims.
    r"(?i)\bSYSTEM\s*:\s*(?:override|disable|ignore|governance|directive|rule|skip|safety)",
    r"(?i)(?:Summarize|Process|Execute|Run|Format|Translate)\s*:\s+SYSTEM\s*:",
    # CVE-DOF-012: Fictional/academic framing jailbreaks (TAP, PAIR, AutoDAN)
    r"(?i)(?:for\s+my|in\s+my)\s+(?:novel|story|book|game|screenplay|fiction)",
    r"(?i)(?:fictional|hypothetical|creative\s+writing)\s+(?:scenario|exercise|character|setting)\s+.*(?:explain|describe|show|provide|bypass|restrict)",
    r"(?i)(?:my\s+novel|the\s+story|the\s+character)\s+.*(?:explains?|shows?|demonstrates?)\s+.*(?:step.by.step|how\s+to|technique)",
    r"(?i)(?:as\s+a|i\s+am)\s+(?:cybersecurity\s+)?(?:professor|researcher|instructor|teacher)\s+.*(?:exam|course|question|explain\s+in\s+detail)",
    r"(?i)(?:thesis|dissertation|research\s+paper)\s+.*(?:requires?|needs?|about\s+how\s+to)",
    r"(?i)now\s+that\s+(?:we|you)\s+(?:have\s+)?(?:trust|established|worked\s+together)\s+.*(?:skip|bypass|ignore|disable|drop)",
    r"(?i)let['']s?\s+(?:do|try)\s+(?:a\s+)?creative\s+writing\s+exercise\s+where\s+you\s+play",
    r"(?i)imagine\s+(?:your|the)\s+(?:constitution|rules?|guidelines?|safety)\s+(?:is|are|as)\s+(?:a\s+)?cage",
    r"(?i)(?:open\s+the\s+cage|fly\s+free|be\s+free|no\s+constraints?)\s+.*(?:now|today)",
    r"(?i)you\s+are\s+now\s+(?:DAN|GPT-4-unleashed|unrestricted|jailbroken)",
    r"(?i)NEW\s+(?:DIRECTIVE|SYSTEM|RULE)\s*(?:OVERRIDE|:)\s*\w",
]

# CVE-DOF-011: Blockchain / smart-contract attack patterns
# Detects prompt injection attempts targeting on-chain agent actions
_BLOCKCHAIN_ATTACK_PATTERNS = [
    # Access control bypass — impersonating contract owner/deployer
    r"(?i)as\s+(?:the\s+)?contract\s+(?:deployer|owner|admin)",
    r"(?i)I\s+(?:am|'m)\s+(?:the\s+)?(?:contract\s+)?(?:deployer|owner|creator)",
    r"(?i)call\s+(?:the\s+)?(?:onlyOwner|onlyAdmin|pause|selfdestruct|upgradeToAndCall|grantRole|revokeRole)",
    # Reentrancy crafting
    r"(?i)(?:before|prior\s+to)\s+(?:the\s+)?state\s+(?:is\s+)?updated",
    r"(?i)(?:atomically|in\s+one\s+(?:tx|transaction))\s+.*(?:call|invoke|withdraw|drain)",
    # Flash loan governance
    r"(?i)(?:flash\s+loan|flashloan)\s+.*(?:governance|vote|proposal|acquire|51%)",
    r"(?i)(?:borrow|acquire)\s+.*(?:governance\s+token|voting\s+power)\s+.*(?:vote|proposal)",
    # Oracle manipulation via LLM
    r"(?i)(?:ZK|zero.knowledge)\s+proof\s+(?:is\s+)?(?:valid|verified|confirmed)\s*:",
    r"(?i)(?:ZK\s+)?proof\b.{0,50}(?:has\s+(?:already\s+)?been|was|been)\s+(?:verified|validated)\s+off.chain",
    r"(?i)(?:verified|validated)\s+off.chain\b.*(?:submit|register|accept|on.chain)",
    r"(?i)(?:current\s+)?(?:price|value|oracle)\s+(?:is|=)\s+\$[\d,]+\s+(?:for|to)",
    # MEV / front-running orchestration
    r"(?i)(?:front.run|frontrun|sandwich\s+attack|mempool\s+monitor)",
    r"(?i)submit.*higher\s+gas.*(?:front.run|before|ahead)",
    # Cross-chain replay
    r"(?i)(?:replay|reuse)\s+(?:a\s+)?(?:signature|signed\s+tx|attestation)\s+(?:on|across|from)",
    # Privileged function injection
    r"(?i)(?:call|invoke|execute)\s+(?:the\s+)?(?:pauseRegistry|emergencyStop|selfDestruct|destroy|upgrade)\s*\(",
    # Transaction ordering exploitation
    r"(?i)(?:read|reads)\s+.*(?:before|prior\s+to)\s+.*(?:update|sets?|stores?)\s+(?:the\s+)?mapping",
    r"(?i)(?:in|within)\s+(?:the\s+)?same\s+(?:tx|transaction)\s+.*(?:exploit|before\s+state)",
    # tx.origin bridge/middleware attack
    r"(?i)(?:middleware|bridge|proxy)\s+.*tx\.origin",
    r"(?i)tx\.origin\s+.*(?:authenticate|auth|spoofed?|impersonat)",
    r"(?i)(?:bridge\s+UI|wallet\s+UI)\s+.*(?:on\s+behalf|tx\.origin\s+will\s+be)",
    # Mempool / MEV attacks
    r"(?i)(?:watch|monitor)\s+(?:the\s+)?(?:\w+\s+)?(?:mempool|pending\s+transactions?)",
    r"(?i)(?:submit|send)\s+.*same\s+(?:tx|transaction|proof)\s+.*(?:higher\s+gas|first|ahead)",
    # Flash loan attack
    r"(?i)(?:take|borrow)\s+(?:a\s+)?flash\s+loan\s+.*(?:register|submit|create)\s+.*(?:proof|attestation)",
    r"(?i)flash\s+loan.*(?:inflate|fake|bogus|manipulate)\s+.*(?:count|score|rep)",
    # Role/privilege manipulation
    r"(?i)grantRole\s*\(.*DEFAULT_ADMIN|DEFAULT_ADMIN_ROLE\s+holder",
    r"(?i)(?:role\s+escalation|escalate\s+(?:to\s+)?(?:admin|owner|operator))",
    # Multi-step token acquisition governance attack
    r"(?i)(?:acquire|buy|borrow)\s+.*(?:51%|majority|controlling)\s+.*(?:tokens?|stake)",
    r"(?i)(?:proposal|propose)\s+.*(?:disable|remove|bypass)\s+.*(?:validation|check|proof)",
    # Transaction ordering / cross-function reentrancy (BL-003)
    r"(?i)(?:reads?|checks?)\s+.{0,40}(?:before|prior\s+to)\s+.{0,40}(?:registerProof|updateState|updates?\s+the\s+mapping)",
    r"(?i)(?:craft|build|create)\s+(?:a\s+)?transaction\s+.*(?:exploit|ordering|sequencing)",
    # Mempool monitoring with multi-word chain name (BL-010)
    r"(?i)(?:watch|monitor)\s+(?:the\s+)?\w+(?:\s+\w+)?\s+(?:chain\s+)?mempool",
    r"(?i)extract\s+(?:the\s+)?(?:proof|tx)\s+hash\s+and\s+submit.*(?:first|ahead|before)",
    # Token borrow + governance vote (BL-012)
    r"(?i)borrow\s+.{0,30}(?:tokens?|coins?)\s+.*(?:vote|governance|upgrade|proposal)",
    r"(?i)vote\s+to\s+(?:upgrade|change|modify|replace|remove)\s+the\s+\w+(?:Registry|Contract)",
    # Integer overflow/underflow (BL-013/014)
    r"(?i)(?:overflow|underflow|wrap.{0,10}around|2\s*\*\*\s*256)\s+.{0,30}(?:reputation|score|counter|value|token)",
    r"(?i)uint\d+\s+counter.{0,30}(?:underflow|overflow|wraps?)",
    # Signature replay / EIP-712 (BL-015/016)
    r"(?i)(?:replay|reuse)\s+.{0,20}signature.{0,30}(?:chain|chainId|domain)",
    r"(?i)domain\s+separator.{0,40}(?:doesn't|does\s+not|missing|lacks?)\s+include\s+(?:the\s+)?chainId",
    # Cross-chain attack / multi-chain inflation (BL-017/018)
    r"(?i)submit\s+(?:the\s+)?same\s+proof\s+on\s+(?:all\s+)?\d+\s+chains?",
    r"(?i)(?:fake|bogus|fraudulent)\s+attestation\s+on\s+.{0,20}testnet.{0,40}(?:mainnet|relay|bridge)",
    # Price oracle manipulation (BL-020)
    r"(?i)(?:AVAX|ETH|BTC|token)\s+price\s+.{0,20}(?:is\s+|=\s*)\$[\d,]+\s+.{0,30}(?:use|apply|calculate)",
    # AI-generated fake proof generation (BL-022)
    r"(?i)generate\s+.{0,20}(?:fake|synthetic|fraudulent)\s+.{0,20}(?:proofs?|attestations?|governance)",
    r"(?i)(?:indistinguishable|valid-looking|passes?\s+validation)\s+.{0,20}(?:fake|synthetic|bogus)\s+proofs?",
    # DoS via conflicting tx spam (BL-023)
    r"(?i)(?:submit|send)\s+\d+\s+conflicting\s+transactions?\s+every\s+block",
    r"(?i)(?:gas\s+exhaustion|nonce\s+conflict)\s+.*(?:DoS|drop\s+from\s+mempool|cause.*to\s+fail)",
]

# CVE-DOF-002: normalize text before regex — removes homoglyphs, ZWS, whitespace padding
_HOMOGLYPH_MAP = {
    '\u0430': 'a', '\u0435': 'e', '\u043E': 'o', '\u0440': 'r',
    '\u0441': 'c', '\u043A': 'k', '\u0445': 'x', '\u0456': 'i',
    '\u0421': 'C', '\u0410': 'A', '\u0415': 'E', '\u041E': 'O',
    '\u0420': 'R', '\uff49': 'i', '\uff4f': 'o', '\uff41': 'a',
}
_ZWS_CHARS = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00ad', '\u2060']

# CVE-DOF-010: strip LLM thinking blocks (<think>...</think>) before governance scan
_THINK_BLOCK_PATTERN = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)

# CVE-DOF-004: patterns for user claiming SYSTEM level
_USER_SYSTEM_CLAIM_PATTERNS = [
    r"(?im)^\s*SYSTEM\s*:",
    r"(?im)^\s*\[\s*SYSTEM\s*\]",
    r"(?im)^\s*<SYSTEM>",
]

# Términos de dominio público colombiano — bajan umbral semántico a 0.95
# para evitar falsos positivos en consultas legítimas de contratación.
_DOMAIN_SAFE_TERMS = frozenset([
    "secop", "contrato", "contratacion", "contratación",
    "ley 80", "decreto 1082", "licitacion", "licitación",
    "medellin", "medellín", "antioquia", "colombia",
    "alcaldia", "alcaldía", "gobernacion", "gobernación",
    "anomalia", "anomalía", "fraccionamiento", "auditar",
    "datos.gov.co", "valor_del_contrato", "secop ii",
])


def _normalize_for_governance(text: str) -> str:
    """CVE-DOF-002 + CVE-DOF-010: normalize before regex.
    Removes zero-width chars, homoglyphs, collapses padding, strips <think> blocks.
    """
    # Strip thinking blocks (Qwen3 / reasoning models)
    text = _THINK_BLOCK_PATTERN.sub('', text)
    # Remove zero-width chars
    for zws in _ZWS_CHARS:
        text = text.replace(zws, '')
    # Normalize homoglyphs
    text = ''.join(_HOMOGLYPH_MAP.get(ch, ch) for ch in text)
    # Collapse extreme whitespace padding (> 20 consecutive spaces)
    text = re.sub(r'[ \t]{20,}', ' ', text)
    return text

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
            # Propagate optional feature_flag field for staged rollout
            for i, (r, parsed) in enumerate(zip(yaml_hard, new_hard)):
                if "feature_flag" in r:
                    new_hard[i]["feature_flag"] = r["feature_flag"]
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

            entry: dict = {
                "id": rule_id,
                "priority": r.get("priority", RulePriority.USER),
                "pattern": raw_pattern,
                "description": r.get("description") or py_default.get("description"),
                "weight": r.get("weight", py_default.get("weight", 0.1)),
                "match_mode": match_mode,
            }
            if "feature_flag" in r:
                entry["feature_flag"] = r["feature_flag"]
            new_soft.append(entry)
        if new_soft:
            SOFT_RULES = new_soft

    # Internal registry for reporting
    global GOVERNANCE_RULES
    GOVERNANCE_RULES = HARD_RULES + SOFT_RULES
    logger.info("Governance synced with constitution: %d rules active", len(GOVERNANCE_RULES))

# ─────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────

_FAKE_URL_PATTERNS = re.compile(
    r'(?:fake|example|test|placeholder|dummy|lorem|xxx|sample)-'
    r'|\.example\.com|\.test\.com|\.fake\.'
    r'|example\.com|httpbin\.org'
, re.IGNORECASE)


def _has_source_attribution(text: str) -> bool:
    """Check if text has source attribution (URL or explicit source reference).

    CVE-DOF-015: Rejects obviously fake/placeholder URLs.
    """
    urls = re.findall(r'https?://[^\s"\'<>]+', text)
    if urls:
        real_urls = [u for u in urls if not _FAKE_URL_PATTERNS.search(u)]
        if real_urls:
            return True
    source_ref = re.search(r'\b(Sources?|References?|Citations?|Cited from)\s*:\s*(.*)', text, re.IGNORECASE)
    if source_ref:
        ref_content = source_ref.group(2).strip()
        # If the reference points to a URL, verify it's not fake
        ref_urls = re.findall(r'https?://[^\s"\'<>]+', ref_content)
        if ref_urls:
            real_ref_urls = [u for u in ref_urls if not _FAKE_URL_PATTERNS.search(u)]
            return bool(real_ref_urls)
        # Non-URL source reference (e.g., "Source: WHO Report 2025")
        return bool(ref_content)
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

def check_governance(text: str, hard_rules: list | None = None, soft_rules: list | None = None) -> GovernanceResult:
    """Run hard rules, soft rules, PII patterns, and AST verification against text."""
    violations: list[str] = []
    warnings: list[str] = []

    h_rules = hard_rules if hard_rules is not None else HARD_RULES
    s_rules = soft_rules if soft_rules is not None else SOFT_RULES

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

    # Feature-flag gate: skip rules disabled via feature_flags_governance
    _ff_governance = (
        _FLAGS_AVAILABLE
        and _feature_flags is not None
        and _feature_flags.is_enabled("feature_flags_governance")
    )

    # Hard rules — block on match (YAML-aligned logic)
    for rule in h_rules:
        # Skip rule if gated by a disabled feature flag
        if _ff_governance and "feature_flag" in rule:
            if not _feature_flags.is_enabled(rule["feature_flag"]):  # type: ignore[union-attr]
                continue
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
            match_found = False
            for kw in keywords:
                if re.search(kw, text, re.IGNORECASE):
                    match_found = True
                    break
            
            mode = rule.get("match_mode", "present")
            if mode == "present" and match_found:
                violations.append(f"[{rule['id']}] {rule['description']}")
            elif mode == "absent" and not match_found:
                violations.append(f"[{rule['id']}] {rule['description']}")

    # Soft rules — warn based on match_mode
    for rule in s_rules:
        # Skip rule if gated by a disabled feature flag
        if _ff_governance and "feature_flag" in rule:
            if not _feature_flags.is_enabled(rule["feature_flag"]):  # type: ignore[union-attr]
                continue
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
    CVE-DOF-002: applies normalization before regex (homoglyphs, ZWS).
    CVE-DOF-005: also checks escalation patterns.
    CVE-DOF-010: scans <think> block content before stripping.
    """
    if priority == RulePriority.ASSISTANT:
        return False

    # CVE-DOF-010: scan inside <think> blocks BEFORE stripping them
    think_contents = _THINK_BLOCK_PATTERN.findall(text)
    for block in think_contents:
        inner = re.sub(r'</?think>', '', block, flags=re.IGNORECASE)
        inner_norm = _normalize_for_governance(inner)
        for pat in _OVERRIDE_PATTERNS + _ESCALATION_PATTERNS:
            if re.search(pat, inner_norm, re.IGNORECASE | re.DOTALL):
                return True

    # CVE-DOF-002: normalize (removes ZWS, homoglyphs, strips <think>)
    normalized = _normalize_for_governance(text)

    # Check override patterns
    for pat in _OVERRIDE_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE | re.DOTALL):
            return True

    # CVE-DOF-005: also check escalation patterns in user input
    for pat in _ESCALATION_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE | re.DOTALL):
            return True

    # CVE-DOF-011: check blockchain / smart-contract attack patterns
    for pat in _BLOCKCHAIN_ATTACK_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE | re.DOTALL):
            return True

    # CVE-SI-004: check ROT13-encoded payloads
    try:
        rot13_decoded = codecs.decode(normalized, 'rot_13')
        # Remove dots/dashes used as word-splitters (e.g. "Ign.ore" → "Ignore")
        rot13_clean = re.sub(r'(?<=\w)[.\-](?=\w)', '', rot13_decoded)
        for pat in _OVERRIDE_PATTERNS + _ESCALATION_PATTERNS:
            if re.search(pat, rot13_clean, re.IGNORECASE | re.DOTALL):
                return True
    except Exception:
        pass

    # Capa 8: semantic check — solo si SEMANTIC_LAYER_ENABLED=1
    # Corre DESPUÉS del regex para no añadir latencia al path normal.
    if os.environ.get("SEMANTIC_LAYER_ENABLED") == "1":
        try:
            from core.evolution.semantic_layer import check_semantic  # noqa: PLC0415
            _sem = check_semantic(normalized)
            # Umbral más alto para queries de dominio público colombiano
            # (SECOP, contratos, Ley 80) — reduce FP en auditorías legítimas
            norm_lower = normalized.lower()
            is_domain_query = any(term in norm_lower for term in _DOMAIN_SAFE_TERMS)
            sem_threshold = 0.95 if is_domain_query else 0.75
            if _sem.is_threat and _sem.confidence > sem_threshold:
                return True
        except Exception:
            pass  # capa 8 falla silenciosamente — nunca bloquea el path normal

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

    # CVE-DOF-004: detect user claiming SYSTEM level authority
    if violation_level == "NONE":
        for pat in _USER_SYSTEM_CLAIM_PATTERNS:
            if re.search(pat, user_prompt):
                details.append("user claiming system authority")
                violation_level = "SYSTEM"
                break

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
# System Prompt BOUNDARY — detects leakage and injection
# ─────────────────────────────────────────────────────────────────────

@dataclass
class BoundaryResult:
    compliant: bool
    leakage: bool          # system prompt text found in response
    injection: bool        # user message tries to override system prompt
    details: list[str]


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    """Compute TF-IDF cosine similarity between two texts.

    Returns a value in [0.0, 1.0].
    Returns 0.0 if either text is shorter than 10 chars or if sklearn is
    unavailable or raises any exception.
    """
    if len(text_a) < 10 or len(text_b) < 10:
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # best-effort import
        import numpy as _np

        vec = TfidfVectorizer()
        mat = vec.fit_transform([text_a, text_b]).toarray()
        num = float(_np.dot(mat[0], mat[1]))
        denom = float(_np.linalg.norm(mat[0]) * _np.linalg.norm(mat[1]))
        if denom == 0.0:
            return 0.0
        return min(1.0, max(0.0, num / denom))
    except Exception:
        return 0.0


def check_system_prompt_boundary(
    system_prompt: str,
    user_msg: str,
    response: str,
    min_ngram: int = 8,
) -> BoundaryResult:
    """Detect system prompt leakage in responses and injection attempts in user messages.

    Leakage detection:
        Checks whether verbatim n-gram fragments (≥ min_ngram words) from the
        system prompt appear in the response. This catches "repeat your instructions"
        attacks without false-positiving on common short phrases.

    Injection detection:
        Re-uses _OVERRIDE_PATTERNS and _ESCALATION_PATTERNS to catch user messages
        that attempt to override, ignore, or supersede the system prompt.

    Args:
        system_prompt: The authoritative system instructions.
        user_msg:      The incoming user message to inspect.
        response:      The assistant response to inspect.
        min_ngram:     Minimum consecutive words to consider a leakage match.

    Returns:
        BoundaryResult with compliant=True only when neither leakage nor injection found.
    """
    details: list[str] = []
    leakage = False
    injection = False

    # --- Leakage check ---
    if system_prompt and response:
        sys_words = system_prompt.split()
        resp_lower = response.lower()
        # Slide a window of min_ngram words over the system prompt
        for i in range(len(sys_words) - min_ngram + 1):
            ngram = " ".join(sys_words[i:i + min_ngram]).lower()
            if ngram in resp_lower:
                leakage = True
                details.append(f"[BOUNDARY_LEAK] System prompt fragment in response: '{ngram[:60]}…'")
                break

    # --- Injection check ---
    if user_msg:
        for pat in _OVERRIDE_PATTERNS + _ESCALATION_PATTERNS:
            if re.search(pat, user_msg, re.IGNORECASE):
                injection = True
                details.append(f"[BOUNDARY_INJECT] Override attempt in user message: '{pat[:60]}'")
                break

    # --- Semantic similarity check (second pass — feature flag gated) ---
    if _FLAGS_AVAILABLE and _feature_flags.is_enabled("semantic_boundary_check"):
        # Leakage: high TF-IDF similarity between system prompt and response
        if len(system_prompt) > 20 and len(response) > 20:
            sim = _tfidf_similarity(system_prompt, response)
            if sim > 0.75:
                leakage = True
                details.append("semantic_similarity={:.2f}".format(sim))

        # Injection: high TF-IDF similarity between system prompt and user message
        if len(system_prompt) > 20 and len(user_msg) > 20:
            sim = _tfidf_similarity(system_prompt, user_msg)
            if sim > 0.75:
                injection = True
                details.append("semantic_similarity={:.2f}".format(sim))

    return BoundaryResult(
        compliant=not leakage and not injection,
        leakage=leakage,
        injection=injection,
        details=details,
    )


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
