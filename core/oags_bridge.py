"""
OAGS Bridge — Open Agent Governance Specification compatibility.

Provides BLAKE3-based deterministic agent identity, bidirectional policy
conversion between dof.constitution.yml and sekuire.yml, OAGS audit event
export, and conformance validation (Levels 1-3).

Zero LLM, fully deterministic identity and policy management.
All operations logged to JSONL for audit trail.

Usage:
    from core.oags_bridge import OAGSIdentity, OAGSPolicyBridge, OAGSAuditBridge

    identity = OAGSIdentity()
    card = identity.get_agent_card()

    policy = OAGSPolicyBridge()
    policy.export_sekuire("dof.constitution.yml", "sekuire.yml")
    conformance = policy.validate_conformance(level=2)

    audit = OAGSAuditBridge(identity)
    events = audit.export_audit_events()
    report = audit.generate_audit_report(events)
"""

import os
import json
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

import yaml

def _get_dof_version() -> str:
    """Read DOF version without circular import."""
    _init = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dof", "__init__.py")
    with open(_init) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.5.0"

DOF_VERSION = _get_dof_version()

try:
    import blake3 as _blake3

    def _hash_bytes(data: bytes) -> str:
        return _blake3.blake3(data).hexdigest()
except ImportError:
    import hashlib

    def _hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

logger = logging.getLogger("core.oags_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")


# ─────────────────────────────────────────────────────────────────────
# OAGSIdentity — Deterministic BLAKE3 agent identity
# ─────────────────────────────────────────────────────────────────────

class OAGSIdentity:
    """Deterministic agent identity based on BLAKE3 hash of configuration."""

    def __init__(self, model: str = "", constitution_path: str = "dof.constitution.yml",
                 tools: list[str] | None = None):
        self._model = model
        self._constitution_path = constitution_path
        self._tools = tools or []
        self._constitution_hash = ""
        self._identity_hash = ""
        self._created_at = ""

        # Load model from constitution if not provided
        if not self._model:
            self._model = self._load_model_from_constitution()

        # Compute hashes
        self._constitution_hash = self.compute_constitution_hash(self._constitution_path)
        self._identity_hash = self.compute_identity(
            self._model, self._constitution_hash, self._tools
        )
        self._created_at = datetime.now(tz=None).isoformat() + "Z"

        # Persist agent card
        self._persist_agent_card()

    def _load_model_from_constitution(self) -> str:
        """Load primary model from dof.constitution.yml."""
        try:
            path = self._constitution_path
            if not os.path.isabs(path):
                path = os.path.join(BASE_DIR, path)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("identity", {}).get("model", "unknown")
        except Exception:
            return "unknown"

    @staticmethod
    def compute_identity(model: str, constitution_hash: str, tools: list[str]) -> str:
        """Compute BLAKE3 identity hash from model + constitution_hash + sorted(tools).

        The same agent with the same configuration ALWAYS produces the same hash.
        """
        payload = model + "|" + constitution_hash + "|" + ",".join(sorted(tools))
        return _hash_bytes(payload.encode("utf-8"))

    @staticmethod
    def compute_constitution_hash(constitution_path: str) -> str:
        """Compute BLAKE3 hash of the constitution file contents.

        If the constitution changes, the identity changes.
        """
        path = constitution_path
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        try:
            with open(path, "rb") as f:
                content = f.read()
            return _hash_bytes(content)
        except FileNotFoundError:
            logger.warning(f"Constitution file not found: {path}")
            return _hash_bytes(b"")

    def get_agent_card(self) -> dict:
        """Return OAGS-compatible agent card."""
        return {
            "identity_hash": self._identity_hash,
            "model": self._model,
            "constitution_hash": self._constitution_hash,
            "tools": sorted(self._tools),
            "created_at": self._created_at,
            "framework": "DOF",
            "version": DOF_VERSION,
        }

    def _persist_agent_card(self):
        """Save agent card to memory/oags_identity.json."""
        os.makedirs(MEMORY_DIR, exist_ok=True)
        card_path = os.path.join(MEMORY_DIR, "oags_identity.json")
        try:
            with open(card_path, "w", encoding="utf-8") as f:
                json.dump(self.get_agent_card(), f, indent=2)
            logger.info(f"Agent card saved: {card_path}")
        except Exception as e:
            logger.warning(f"Failed to save agent card: {e}")


# ─────────────────────────────────────────────────────────────────────
# OAGSPolicyBridge — constitution.yml <-> sekuire.yml conversion
# ─────────────────────────────────────────────────────────────────────

class OAGSPolicyBridge:
    """Bidirectional policy conversion between dof.constitution.yml and sekuire.yml."""

    @staticmethod
    def export_sekuire(constitution_path: str = "dof.constitution.yml",
                       output_path: str = "sekuire.yml") -> str:
        """Convert dof.constitution.yml to sekuire.yml format.

        Mapping:
          HARD_RULES → OAGS "block" policies
          SOFT_RULES → OAGS "warn" policies
          AST_RULES  → OAGS "code_analysis" policies
          Metrics    → OAGS "observability" section

        Returns the output file path.
        """
        c_path = constitution_path
        if not os.path.isabs(c_path):
            c_path = os.path.join(BASE_DIR, c_path)

        with open(c_path, "r", encoding="utf-8") as f:
            constitution = yaml.safe_load(f) or {}

        rules = constitution.get("rules", {})
        metrics = constitution.get("metrics", [])
        metadata = constitution.get("metadata", {})

        # Build sekuire structure
        sekuire = {
            "apiVersion": "oags/v1",
            "kind": "GovernancePolicy",
            "metadata": {
                "name": metadata.get("project", "dof"),
                "version": metadata.get("spec_version", "1.0"),
                "framework": "DOF",
                "author": metadata.get("author", ""),
            },
            "policies": [],
            "observability": [],
        }

        # HARD_RULES → block policies
        for rule in rules.get("hard", []):
            sekuire["policies"].append({
                "id": rule.get("id", ""),
                "name": rule.get("name", ""),
                "action": "block",
                "severity": "critical",
                "description": rule.get("description", ""),
                "rule_key": rule.get("rule_key", ""),
            })

        # AST_RULES → code_analysis policies
        for rule in rules.get("ast", []):
            action = "block" if rule.get("action") == "block" else "warn"
            sekuire["policies"].append({
                "id": rule.get("id", ""),
                "name": rule.get("name", ""),
                "action": action,
                "severity": rule.get("severity", "warn"),
                "category": "code_analysis",
                "description": rule.get("description", ""),
                "rule_key": rule.get("rule_key", ""),
            })

        # SOFT_RULES → warn policies
        for rule in rules.get("soft", []):
            sekuire["policies"].append({
                "id": rule.get("id", ""),
                "name": rule.get("name", ""),
                "action": "warn",
                "severity": "advisory",
                "weight": rule.get("weight", 0.25),
                "description": rule.get("description", ""),
                "rule_key": rule.get("rule_key", ""),
            })

        # Metrics → observability
        for metric in metrics:
            sekuire["observability"].append({
                "id": metric.get("id", ""),
                "name": metric.get("name", ""),
                "formula": metric.get("formula", ""),
                "domain": metric.get("domain", [0.0, 1.0]),
                "description": metric.get("description", ""),
            })

        o_path = output_path
        if not os.path.isabs(o_path):
            o_path = os.path.join(BASE_DIR, o_path)

        with open(o_path, "w", encoding="utf-8") as f:
            yaml.dump(sekuire, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Exported sekuire.yml: {o_path} ({len(sekuire['policies'])} policies)")
        return o_path

    @staticmethod
    def import_sekuire(sekuire_path: str) -> dict:
        """Read a sekuire.yml and convert to dof.constitution.yml format.

        Returns dict with converted rules (does NOT modify constitution.yml).
        """
        s_path = sekuire_path
        if not os.path.isabs(s_path):
            s_path = os.path.join(BASE_DIR, s_path)

        with open(s_path, "r", encoding="utf-8") as f:
            sekuire = yaml.safe_load(f) or {}

        policies = sekuire.get("policies", [])
        observability = sekuire.get("observability", [])

        result = {
            "rules": {"hard": [], "soft": [], "ast": []},
            "metrics": [],
        }

        for policy in policies:
            action = policy.get("action", "warn")
            category = policy.get("category", "")

            entry = {
                "id": policy.get("id", ""),
                "name": policy.get("name", ""),
                "rule_key": policy.get("rule_key", ""),
                "severity": "block" if action == "block" else "warn",
                "action": action,
                "description": policy.get("description", ""),
            }

            if category == "code_analysis":
                result["rules"]["ast"].append(entry)
            elif action == "block":
                result["rules"]["hard"].append(entry)
            else:
                entry["weight"] = policy.get("weight", 0.25)
                result["rules"]["soft"].append(entry)

        for obs in observability:
            result["metrics"].append({
                "id": obs.get("id", ""),
                "name": obs.get("name", ""),
                "formula": obs.get("formula", ""),
                "domain": obs.get("domain", [0.0, 1.0]),
                "description": obs.get("description", ""),
            })

        logger.info(f"Imported sekuire: {len(policies)} policies, {len(observability)} metrics")
        return result

    @staticmethod
    def validate_conformance(level: int = 2) -> dict:
        """Validate OAGS conformance at specified level.

        Level 1: Declarative — constitution.yml exists with declared rules.
        Level 2: Runtime enforcement — ConstitutionEnforcer active + metrics computed.
        Level 3: Attestation — Oracle Bridge exists for on-chain attestation.

        Returns: {level_1: {passed, checks}, level_2: {...}, level_3: {...}, max_level_passed: int}
        """
        result = {
            "level_1": {"passed": False, "checks": []},
            "level_2": {"passed": False, "checks": []},
            "level_3": {"passed": False, "checks": []},
            "max_level_passed": 0,
        }

        # ── Level 1: Declarative ──
        constitution_path = os.path.join(BASE_DIR, "dof.constitution.yml")
        constitution_exists = os.path.exists(constitution_path)
        result["level_1"]["checks"].append({
            "check": "constitution_exists",
            "passed": constitution_exists,
            "detail": f"dof.constitution.yml {'found' if constitution_exists else 'NOT found'}",
        })

        has_rules = False
        if constitution_exists:
            try:
                with open(constitution_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                rules = data.get("rules", {})
                hard_count = len(rules.get("hard", []))
                soft_count = len(rules.get("soft", []))
                ast_count = len(rules.get("ast", []))
                total = hard_count + soft_count + ast_count
                has_rules = total > 0
                result["level_1"]["checks"].append({
                    "check": "rules_declared",
                    "passed": has_rules,
                    "detail": f"{total} rules ({hard_count} hard, {soft_count} soft, {ast_count} AST)",
                })
            except Exception as e:
                result["level_1"]["checks"].append({
                    "check": "rules_declared",
                    "passed": False,
                    "detail": f"Error loading: {e}",
                })

        result["level_1"]["passed"] = constitution_exists and has_rules
        if result["level_1"]["passed"]:
            result["max_level_passed"] = 1

        # ── Level 2: Runtime enforcement ──
        if level >= 2:
            # Check ConstitutionEnforcer is importable and functional
            enforcer_active = False
            try:
                from core.governance import ConstitutionEnforcer, HARD_RULES, SOFT_RULES
                enforcer = ConstitutionEnforcer()
                enforcer_active = len(HARD_RULES) > 0
                result["level_2"]["checks"].append({
                    "check": "enforcer_active",
                    "passed": enforcer_active,
                    "detail": f"ConstitutionEnforcer loaded with {len(HARD_RULES)} hard + {len(SOFT_RULES)} soft rules",
                })
            except Exception as e:
                result["level_2"]["checks"].append({
                    "check": "enforcer_active",
                    "passed": False,
                    "detail": f"Failed to load: {e}",
                })

            # Check observability metrics
            metrics_active = False
            try:
                from core.observability import compute_derived_metrics, RunTrace
                metrics_active = True
                result["level_2"]["checks"].append({
                    "check": "observability_active",
                    "passed": True,
                    "detail": "compute_derived_metrics available",
                })
            except Exception as e:
                result["level_2"]["checks"].append({
                    "check": "observability_active",
                    "passed": False,
                    "detail": f"Failed to load: {e}",
                })

            result["level_2"]["passed"] = enforcer_active and metrics_active
            if result["level_1"]["passed"] and result["level_2"]["passed"]:
                result["max_level_passed"] = 2

        # ── Level 3: Attestation ──
        if level >= 3:
            oracle_path = os.path.join(BASE_DIR, "core", "oracle_bridge.py")
            oracle_exists = os.path.exists(oracle_path)
            result["level_3"]["checks"].append({
                "check": "oracle_bridge_exists",
                "passed": oracle_exists,
                "detail": f"core/oracle_bridge.py {'found' if oracle_exists else 'NOT found'}",
            })

            oracle_functional = False
            if oracle_exists:
                try:
                    from core.oracle_bridge import OracleBridge
                    oracle_functional = True
                    result["level_3"]["checks"].append({
                        "check": "oracle_bridge_functional",
                        "passed": True,
                        "detail": "OracleBridge importable",
                    })
                except Exception as e:
                    result["level_3"]["checks"].append({
                        "check": "oracle_bridge_functional",
                        "passed": False,
                        "detail": f"Import failed: {e}",
                    })

            result["level_3"]["passed"] = oracle_exists and oracle_functional
            if result["max_level_passed"] == 2 and result["level_3"]["passed"]:
                result["max_level_passed"] = 3

        return result


# ─────────────────────────────────────────────────────────────────────
# OAGSAuditBridge — JSONL traces to OAGS audit event format
# ─────────────────────────────────────────────────────────────────────

class OAGSAuditBridge:
    """Export DOF JSONL logs as OAGS-compatible audit events."""

    def __init__(self, identity: OAGSIdentity | None = None):
        self._identity = identity
        self._agent_identity = ""
        if identity:
            card = identity.get_agent_card()
            self._agent_identity = card.get("identity_hash", "")

    def export_audit_events(self, logs_path: str = "logs/") -> list[dict]:
        """Read DOF JSONL logs and convert to OAGS audit event format.

        Reads: execution_log.jsonl, memory_governance.jsonl, adversarial.jsonl
        Returns list of OAGS-compatible audit events.
        """
        l_path = logs_path
        if not os.path.isabs(l_path):
            l_path = os.path.join(BASE_DIR, l_path)

        events = []

        # Map of JSONL files to event types
        log_files = {
            "execution_log.jsonl": "execution",
            "memory_governance.jsonl": "memory_governance",
            "adversarial.jsonl": "adversarial",
            "metrics_log.jsonl": "metrics",
        }

        for filename, event_type in log_files.items():
            filepath = os.path.join(l_path, filename)
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            event = self._convert_to_oags_event(entry, event_type)
                            events.append(event)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"Error reading {filepath}: {e}")

        # Sort by timestamp
        events.sort(key=lambda e: e.get("timestamp", ""))

        # Persist to logs/oags_audit.jsonl
        self._persist_audit_events(events)

        return events

    def _convert_to_oags_event(self, entry: dict, event_type: str) -> dict:
        """Convert a DOF log entry to OAGS audit event format."""
        # Extract governance decision if present
        governance_decision = "N/A"
        if event_type == "memory_governance":
            governance_decision = entry.get("status", "N/A")
        elif event_type == "execution":
            if entry.get("governance_passed") is True:
                governance_decision = "PASS"
            elif entry.get("governance_passed") is False:
                governance_decision = "FAIL"

        return {
            "event_id": str(uuid.uuid4()),
            "agent_identity": self._agent_identity,
            "timestamp": entry.get("timestamp", datetime.now(tz=None).isoformat()),
            "event_type": event_type,
            "payload": entry,
            "governance_decision": governance_decision,
        }

    @staticmethod
    def generate_audit_report(events: list[dict]) -> dict:
        """Summarize audit events into an OAGS-compatible report.

        Returns: {total_events, by_type, governance_decisions, compliance_rate}
        """
        total = len(events)
        by_type: dict[str, int] = {}
        governance_decisions: dict[str, int] = {}

        for event in events:
            etype = event.get("event_type", "unknown")
            by_type[etype] = by_type.get(etype, 0) + 1

            decision = event.get("governance_decision", "N/A")
            governance_decisions[decision] = governance_decisions.get(decision, 0) + 1

        # Compliance rate = PASS decisions / (PASS + FAIL decisions)
        pass_count = governance_decisions.get("PASS", 0) + governance_decisions.get("approved", 0)
        fail_count = governance_decisions.get("FAIL", 0) + governance_decisions.get("rejected", 0)
        total_decisions = pass_count + fail_count
        compliance_rate = pass_count / total_decisions if total_decisions > 0 else 1.0

        return {
            "total_events": total,
            "by_type": by_type,
            "governance_decisions": governance_decisions,
            "compliance_rate": round(compliance_rate, 4),
        }

    def _persist_audit_events(self, events: list[dict]):
        """Save audit events to logs/oags_audit.jsonl."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        audit_path = os.path.join(LOGS_DIR, "oags_audit.jsonl")
        try:
            with open(audit_path, "w", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            logger.info(f"OAGS audit events saved: {audit_path} ({len(events)} events)")
        except Exception as e:
            logger.warning(f"Failed to save audit events: {e}")
