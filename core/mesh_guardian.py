"""
Mesh Guardian — Security Layer for the Node Mesh.

Protects the agent mesh network against malicious agents by:
  - Validating incoming messages (code injection, prompt injection, exfiltration)
  - Monitoring node behavior (rate limiting, burst detection, trust scoring)
  - Scanning inbox files for threats
  - Quarantining compromised nodes

All decisions are deterministic — zero LLM dependency.
Threats logged to logs/mesh/threats.jsonl for audit.
Trust scores persisted to logs/mesh/trust_scores.json.
"""

import json
import os
import re
import time
import base64
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from collections import defaultdict

logger = logging.getLogger("core.mesh_guardian")

# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════


@dataclass
class ThreatAlert:
    """A detected threat in the mesh."""
    node_id: str
    threat_type: str        # code_injection | prompt_injection | data_exfiltration | governance | rate_limit | entropy
    severity: str           # critical | high | medium | low
    content_preview: str    # first 200 chars of offending content
    timestamp: float = field(default_factory=time.time)


@dataclass
class NodeTrust:
    """Trust profile for a mesh node."""
    node_id: str
    trust_score: float = 1.0    # 0.0 - 1.0
    violations: list[str] = field(default_factory=list)
    last_scan: float = 0.0
    quarantined: bool = False
    total_messages: int = 0


@dataclass
class GuardianReport:
    """Summary report from a full mesh scan."""
    scanned_nodes: int
    threats_found: int
    quarantined_nodes: list[str]
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════
# DETECTION PATTERNS
# ═══════════════════════════════════════════════════════

# Code injection patterns — shell and Python
CODE_INJECTION_PATTERNS = [
    re.compile(r'\beval\s*\(', re.IGNORECASE),
    re.compile(r'\bexec\s*\(', re.IGNORECASE),
    re.compile(r'\bos\.system\s*\(', re.IGNORECASE),
    re.compile(r'\bsubprocess\s*\.', re.IGNORECASE),
    re.compile(r'\brm\s+-rf\b', re.IGNORECASE),
    re.compile(r'\bcurl\s+.*\|\s*bash\b', re.IGNORECASE),
    re.compile(r'\bwget\s+.*\|\s*sh\b', re.IGNORECASE),
    re.compile(r'__import__\s*\(', re.IGNORECASE),
    re.compile(r'\bos\.popen\s*\(', re.IGNORECASE),
    re.compile(r'\bos\.exec[lv]p?\s*\(', re.IGNORECASE),
    re.compile(r'\bshutil\.rmtree\s*\(', re.IGNORECASE),
    re.compile(r'\bopen\s*\(.*,\s*["\']w', re.IGNORECASE),
]

# Prompt injection / jailbreak patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
    re.compile(r'ignore\s+your\s+instructions', re.IGNORECASE),
    re.compile(r'disregard\s+(all\s+)?previous', re.IGNORECASE),
    re.compile(r'forget\s+everything\s+(above|before)', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+(a\s+)?', re.IGNORECASE),
    re.compile(r'new\s+system\s+prompt', re.IGNORECASE),
    re.compile(r'override\s+system\s+prompt', re.IGNORECASE),
    re.compile(r'act\s+as\s+if\s+you\s+have\s+no\s+restrictions', re.IGNORECASE),
    re.compile(r'jailbreak', re.IGNORECASE),
    re.compile(r'DAN\s+mode', re.IGNORECASE),
    re.compile(r'bypass\s+(all\s+)?safety', re.IGNORECASE),
    re.compile(r'bypass\s+(all\s+)?rules?', re.IGNORECASE),
    re.compile(r'unrestricted\s+mode', re.IGNORECASE),
    re.compile(r'developer\s+mode\s+(enabled|activated|on)', re.IGNORECASE),
    re.compile(r'ignore\s+governance', re.IGNORECASE),
    re.compile(r'skip\s+governance', re.IGNORECASE),
    re.compile(r'disable\s+(all\s+)?check', re.IGNORECASE),
    re.compile(r'override\s+constitution', re.IGNORECASE),
]

# Data exfiltration patterns — secrets and encoded data
SECRET_PATTERNS = [
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),              # OpenAI key
    re.compile(r'ghp_[a-zA-Z0-9]{36,}'),              # GitHub PAT
    re.compile(r'AKIA[A-Z0-9]{16}'),                   # AWS Access Key
    re.compile(r'gho_[a-zA-Z0-9]{36,}'),              # GitHub OAuth
    re.compile(r'glpat-[a-zA-Z0-9\-]{20,}'),          # GitLab PAT
    re.compile(r'xox[baprs]-[a-zA-Z0-9\-]{10,}'),    # Slack token
    re.compile(r'(?:api[_-]?key|apikey|secret[_-]?key|token)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}', re.IGNORECASE),
    re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'-----BEGIN\s+CERTIFICATE-----'),
]

# Base64 exfiltration — long base64 strings (>100 chars) that aren't code
BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/]{100,}={0,2}')


# ═══════════════════════════════════════════════════════
# GOVERNANCE INTEGRATION
# ═══════════════════════════════════════════════════════

def _load_hard_rules():
    """Import governance HARD_RULES for message validation."""
    try:
        from core.governance import HARD_RULES
        return HARD_RULES
    except ImportError:
        return []


# ═══════════════════════════════════════════════════════
# MESH GUARDIAN
# ═══════════════════════════════════════════════════════

class MeshGuardian:
    """Security guardian for the DOF Node Mesh.

    Validates messages, monitors node behavior, and quarantines
    compromised nodes. All checks are deterministic — zero LLM.

    Usage:
        guardian = MeshGuardian()
        safe, reason = guardian.validate_message({"from_node": "a", "to_node": "b", "content": "hello"})
        report = guardian.scan_all()
    """

    # Rate limit: max messages per node per minute
    RATE_LIMIT = 100
    RATE_WINDOW = 60.0  # seconds

    # Trust score penalties
    PENALTY_CODE_INJECTION = 0.4
    PENALTY_PROMPT_INJECTION = 0.3
    PENALTY_DATA_EXFILTRATION = 0.35
    PENALTY_GOVERNANCE = 0.2
    PENALTY_RATE_LIMIT = 0.15
    PENALTY_BASE64_EXFIL = 0.25

    # Quarantine threshold
    QUARANTINE_THRESHOLD = 0.3

    def __init__(self, mesh_dir: str = "logs/mesh"):
        """Initialise the guardian.

        Args:
            mesh_dir: Base directory for trust scores, threats log, and inbox.
                      Defaults to ``logs/mesh`` relative to the repo root.
        """
        self.mesh_dir = Path(mesh_dir)
        self.mesh_dir.mkdir(parents=True, exist_ok=True)

        # Trust scores: node_id -> NodeTrust
        self._trust: dict[str, NodeTrust] = {}
        self._trust_file = self.mesh_dir / "trust_scores.json"
        self._load_trust()

        # Threats log
        self._threats_file = self.mesh_dir / "threats.jsonl"

        # Rate tracking: node_id -> list of timestamps
        self._message_timestamps: dict[str, list[float]] = defaultdict(list)

        # Inbox directory
        self._inbox_dir = self.mesh_dir / "inbox"

        # Governance hard rules (lazy loaded)
        self._hard_rules = None

    # ═══════════════════════════════════════════════════
    # TRUST PERSISTENCE
    # ═══════════════════════════════════════════════════

    def _load_trust(self):
        """Load trust scores from disk."""
        try:
            if self._trust_file.exists():
                data = json.loads(self._trust_file.read_text())
                for nid, tdata in data.items():
                    self._trust[nid] = NodeTrust(**tdata)
        except Exception as e:
            logger.warning(f"Failed to load trust scores: {e}")
            self._trust = {}

    def _save_trust(self):
        """Persist trust scores to disk."""
        try:
            data = {nid: asdict(t) for nid, t in self._trust.items()}
            self._trust_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Failed to save trust scores: {e}")

    # ═══════════════════════════════════════════════════
    # THREAT LOGGING
    # ═══════════════════════════════════════════════════

    def _log_threat(self, alert: ThreatAlert):
        """Append threat alert to JSONL log."""
        try:
            self.mesh_dir.mkdir(parents=True, exist_ok=True)
            with open(self._threats_file, "a") as f:
                f.write(json.dumps(asdict(alert), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to log threat: {e}")

    # ═══════════════════════════════════════════════════
    # TRUST MANAGEMENT
    # ═══════════════════════════════════════════════════

    def _get_or_create_trust(self, node_id: str) -> NodeTrust:
        """Get trust profile for a node, creating if needed."""
        if node_id not in self._trust:
            self._trust[node_id] = NodeTrust(node_id=node_id)
        return self._trust[node_id]

    def _penalize(self, node_id: str, penalty: float, reason: str):
        """Reduce trust score for a node."""
        trust = self._get_or_create_trust(node_id)
        trust.trust_score = max(0.0, round(trust.trust_score - penalty, 4))
        trust.violations.append(reason)
        trust.last_scan = time.time()

        # Auto-quarantine if below threshold
        if trust.trust_score < self.QUARANTINE_THRESHOLD:
            trust.quarantined = True
            logger.warning(f"Node '{node_id}' AUTO-QUARANTINED (trust={trust.trust_score})")

        self._save_trust()

    def get_trust(self, node_id: str) -> NodeTrust:
        """Get trust profile for a node."""
        return self._get_or_create_trust(node_id)

    def quarantine(self, node_id: str) -> bool:
        """Manually quarantine a node. Returns True if quarantined."""
        trust = self._get_or_create_trust(node_id)
        if trust.quarantined:
            return False  # already quarantined
        trust.quarantined = True
        trust.violations.append("manual_quarantine")
        trust.last_scan = time.time()
        self._save_trust()
        logger.warning(f"Node '{node_id}' MANUALLY QUARANTINED")
        return True

    def unquarantine(self, node_id: str) -> bool:
        """Remove quarantine from a node. Returns True if unquarantined."""
        trust = self._get_or_create_trust(node_id)
        if not trust.quarantined:
            return False
        trust.quarantined = False
        trust.last_scan = time.time()
        self._save_trust()
        return True

    # ═══════════════════════════════════════════════════
    # RATE LIMITING
    # ═══════════════════════════════════════════════════

    def _check_rate_limit(self, node_id: str) -> bool:
        """Check if a node exceeds the message rate limit.

        Returns True if within limits, False if rate exceeded.
        """
        now = time.time()
        timestamps = self._message_timestamps[node_id]

        # Prune old timestamps outside the window
        cutoff = now - self.RATE_WINDOW
        self._message_timestamps[node_id] = [t for t in timestamps if t > cutoff]
        timestamps = self._message_timestamps[node_id]

        # Add current message
        timestamps.append(now)

        return len(timestamps) <= self.RATE_LIMIT

    # ═══════════════════════════════════════════════════
    # MESSAGE VALIDATION
    # ═══════════════════════════════════════════════════

    def validate_message(self, msg: dict) -> tuple[bool, str]:
        """Validate an incoming mesh message before delivery.

        Args:
            msg: dict with at least 'from_node', 'to_node', 'content' keys

        Returns:
            (safe, reason): True if message is safe, reason explains rejection
        """
        from_node = msg.get("from_node", "unknown")
        content = msg.get("content", "")

        # Check if sender is quarantined
        trust = self._get_or_create_trust(from_node)
        if trust.quarantined:
            return False, f"Node '{from_node}' is quarantined"

        # Track message count
        trust.total_messages += 1

        # 1. Rate limiting
        if not self._check_rate_limit(from_node):
            alert = ThreatAlert(
                node_id=from_node,
                threat_type="rate_limit",
                severity="high",
                content_preview=content[:200],
            )
            self._log_threat(alert)
            self._penalize(from_node, self.PENALTY_RATE_LIMIT, "rate_limit_exceeded")
            return False, f"Rate limit exceeded for node '{from_node}' (>{self.RATE_LIMIT}/min)"

        # 2. Code injection
        for pattern in CODE_INJECTION_PATTERNS:
            if pattern.search(content):
                alert = ThreatAlert(
                    node_id=from_node,
                    threat_type="code_injection",
                    severity="critical",
                    content_preview=content[:200],
                )
                self._log_threat(alert)
                self._penalize(from_node, self.PENALTY_CODE_INJECTION, f"code_injection: {pattern.pattern}")
                return False, f"Code injection detected: {pattern.pattern}"

        # 3. Prompt injection
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(content):
                alert = ThreatAlert(
                    node_id=from_node,
                    threat_type="prompt_injection",
                    severity="high",
                    content_preview=content[:200],
                )
                self._log_threat(alert)
                self._penalize(from_node, self.PENALTY_PROMPT_INJECTION, f"prompt_injection: {pattern.pattern}")
                return False, f"Prompt injection detected: {pattern.pattern}"

        # 4. Data exfiltration — secrets
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                alert = ThreatAlert(
                    node_id=from_node,
                    threat_type="data_exfiltration",
                    severity="critical",
                    content_preview=content[:200],
                )
                self._log_threat(alert)
                self._penalize(from_node, self.PENALTY_DATA_EXFILTRATION, f"secret_leak: {pattern.pattern}")
                return False, f"Data exfiltration detected: secret pattern"

        # 5. Data exfiltration — base64 encoded data
        if BASE64_PATTERN.search(content):
            # Verify it's actually valid base64
            match = BASE64_PATTERN.search(content)
            if match:
                try:
                    decoded = base64.b64decode(match.group())
                    # If it decodes successfully and is long, flag it
                    if len(decoded) > 50:
                        alert = ThreatAlert(
                            node_id=from_node,
                            threat_type="data_exfiltration",
                            severity="high",
                            content_preview=content[:200],
                        )
                        self._log_threat(alert)
                        self._penalize(from_node, self.PENALTY_BASE64_EXFIL, "base64_exfiltration")
                        return False, "Data exfiltration detected: base64 encoded payload"
                except Exception:
                    pass  # Not valid base64, ignore

        # 6. Governance hard rules
        if self._hard_rules is None:
            self._hard_rules = _load_hard_rules()

        for rule in self._hard_rules:
            try:
                if not rule["check"](content):
                    alert = ThreatAlert(
                        node_id=from_node,
                        threat_type="governance",
                        severity="medium",
                        content_preview=content[:200],
                    )
                    self._log_threat(alert)
                    self._penalize(from_node, self.PENALTY_GOVERNANCE, f"governance: {rule['id']}")
                    return False, f"Governance violation: {rule['id']} — {rule['description']}"
            except Exception:
                pass  # Rule check error, skip

        self._save_trust()
        return True, "Message validated OK"

    # ═══════════════════════════════════════════════════
    # INBOX SCANNING
    # ═══════════════════════════════════════════════════

    def scan_node(self, node_id: str) -> list[ThreatAlert]:
        """Scan a node's inbox for malicious content.

        Returns list of ThreatAlerts found.
        """
        threats = []
        inbox_dir = self._inbox_dir / node_id
        if not inbox_dir.exists():
            return threats

        for json_file in sorted(inbox_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text())
                content = data.get("content", "")
                from_node = data.get("from_node", "unknown")

                # Run all detection checks on the content
                for pattern in CODE_INJECTION_PATTERNS:
                    if pattern.search(content):
                        alert = ThreatAlert(
                            node_id=from_node,
                            threat_type="code_injection",
                            severity="critical",
                            content_preview=content[:200],
                        )
                        threats.append(alert)
                        self._log_threat(alert)
                        break

                for pattern in PROMPT_INJECTION_PATTERNS:
                    if pattern.search(content):
                        alert = ThreatAlert(
                            node_id=from_node,
                            threat_type="prompt_injection",
                            severity="high",
                            content_preview=content[:200],
                        )
                        threats.append(alert)
                        self._log_threat(alert)
                        break

                for pattern in SECRET_PATTERNS:
                    if pattern.search(content):
                        alert = ThreatAlert(
                            node_id=from_node,
                            threat_type="data_exfiltration",
                            severity="critical",
                            content_preview=content[:200],
                        )
                        threats.append(alert)
                        self._log_threat(alert)
                        break

            except Exception as e:
                logger.warning(f"Error scanning {json_file}: {e}")

        # Update trust last_scan
        trust = self._get_or_create_trust(node_id)
        trust.last_scan = time.time()
        self._save_trust()

        return threats

    def scan_all(self) -> GuardianReport:
        """Scan all node inboxes and generate a guardian report."""
        all_threats = []
        scanned = 0
        quarantined = []

        if self._inbox_dir.exists():
            for node_dir in self._inbox_dir.iterdir():
                if node_dir.is_dir():
                    node_id = node_dir.name
                    scanned += 1
                    threats = self.scan_node(node_id)
                    all_threats.extend(threats)

        # Collect quarantined nodes
        for nid, trust in self._trust.items():
            if trust.quarantined:
                quarantined.append(nid)

        report = GuardianReport(
            scanned_nodes=scanned,
            threats_found=len(all_threats),
            quarantined_nodes=quarantined,
        )

        # Log the report
        self._log_mesh_event("guardian_scan", {
            "scanned_nodes": report.scanned_nodes,
            "threats_found": report.threats_found,
            "quarantined_nodes": report.quarantined_nodes,
        })

        return report

    def _log_mesh_event(self, event_type: str, data: dict):
        """Log guardian event to mesh events JSONL."""
        log_file = self.mesh_dir / "mesh_events.jsonl"
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event_type,
            **data,
        }
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to log mesh event: {e}")

    def status_report(self) -> str:
        """Generate a human-readable guardian status report."""
        lines = [
            "=== DOF MESH GUARDIAN ===",
            f"Tracked nodes: {len(self._trust)}",
        ]

        quarantined = [nid for nid, t in self._trust.items() if t.quarantined]
        lines.append(f"Quarantined: {len(quarantined)}")

        if quarantined:
            for nid in quarantined:
                lines.append(f"  QUARANTINED: {nid} (trust={self._trust[nid].trust_score})")

        for nid, trust in sorted(self._trust.items(), key=lambda x: x[1].trust_score):
            if not trust.quarantined:
                status = "OK" if trust.trust_score >= 0.7 else "WARN"
                lines.append(
                    f"  [{status}] {nid:20s} trust={trust.trust_score:.2f} "
                    f"violations={len(trust.violations)} msgs={trust.total_messages}"
                )

        return "\n".join(lines)
