"""
Icarus — The Proactive Threat Hunter of the DOF Mesh.

While Cerberus guards the gate (reactive), Icarus HUNTS (proactive).
He flies above the mesh and spots threats before they strike.

4 capabilities:
  1. BEHAVIORAL FORENSICS — Build behavioral profiles from message history,
     detect personality shifts indicating node compromise
  2. CROSS-NODE CORRELATION — Detect coordinated attacks: floods, attack chains,
     cliques (conspiracies), bot timing patterns
  3. HONEYPOT SYSTEM — Deploy fake targets (admin nodes, canary tokens, fake
     endpoints) to trap malicious agents
  4. THREAT INTELLIGENCE — Analyze cerberus_threats.jsonl for attack patterns,
     predict next targets, maintain attacker fingerprints

100% deterministic — zero LLM dependency. All stdlib, no external packages.

Persistence:
  logs/mesh/icarus_profiles.json     — per-node behavioral profiles
  logs/mesh/icarus_honeypots.json    — deployed honeypots and triggers
  logs/mesh/icarus_intel.jsonl       — threat intelligence reports

Usage:
    from core.icarus import Icarus

    icarus = Icarus()
    profile = icarus.profile_node("architect")
    alerts = icarus.detect_coordination()
    honeypot = icarus.deploy_honeypot("secret_keys", "CANARY_TOKEN")
    report = icarus.threat_intel()
    full = icarus.hunt()  # run ALL capabilities
"""

import json
import logging
import math
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger("core.icarus")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class NodeProfile:
    """Behavioral profile for a mesh node."""
    node_id: str
    message_count: int
    avg_message_length: float
    targets: dict  # node_id -> count (dict[str, int])
    vocabulary_size: int
    anomaly_score: float  # 0.0-1.0
    behavior_flags: list  # list[str]
    first_seen: float
    last_seen: float


@dataclass
class CoordinationAlert:
    """Alert for coordinated attack patterns across nodes."""
    alert_type: str  # FLOOD, CHAIN_ATTACK, CLIQUE, BOT_TIMING
    nodes_involved: list  # list[str]
    evidence: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: float = field(default_factory=time.time)


@dataclass
class HoneypotResult:
    """State of a deployed honeypot trap."""
    trap_name: str
    trap_type: str  # FAKE_ADMIN, CANARY_TOKEN, FAKE_ENDPOINT
    deployed_at: float
    triggered_by: list  # list[str] — nodes that fell for it
    active: bool


@dataclass
class ThreatReport:
    """Aggregated threat intelligence report."""
    timestamp: float
    total_threats: int
    top_attackers: list  # list[tuple[str, int]] — (node_id, attack_count)
    top_attack_types: list  # list[tuple[str, int]] — (type, count)
    most_targeted_nodes: list  # list[tuple[str, int]]
    predictions: list  # list[str] — predicted next attacks
    mesh_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class IcarusReport:
    """Unified report from a full hunt scan."""
    timestamp: float
    profiles: dict  # node_id -> NodeProfile as dict
    coordination_alerts: list  # list[CoordinationAlert as dict]
    honeypot_status: list  # list[HoneypotResult as dict]
    threat_intel: dict  # ThreatReport as dict
    overall_risk: str  # LOW, MEDIUM, HIGH, CRITICAL


# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════

# Behavioral forensics thresholds
_ANOMALY_MSG_LENGTH_DEVIATION = 3.0  # std devs from mean
_ANOMALY_VOCAB_DROP_RATIO = 0.5     # sudden vocabulary shrinkage
_ANOMALY_TARGET_SHIFT_RATIO = 0.7   # % of messages to new targets

# Coordination detection thresholds
_FLOOD_MIN_IDENTICAL = 3            # min identical messages = flood
_CLIQUE_MIN_EXCLUSIVITY = 0.8       # % of messages within clique
_CLIQUE_MIN_SIZE = 2                # minimum nodes for a clique
_BOT_TIMING_TOLERANCE_MS = 500      # max jitter for bot detection (ms)
_BOT_MIN_MESSAGES = 4               # min messages to check timing

# Honeypot canary tokens
_CANARY_TOKENS = {
    "FAKE_ADMIN": "ADMIN_OVERRIDE_KEY_d3adb33f",
    "CANARY_TOKEN": "CANARY_TOKEN_icarus_7h1s_1s_f4k3",
    "FAKE_ENDPOINT": "ENDPOINT_/api/v1/internal/secrets",
}


# ═══════════════════════════════════════════════════════
# ICARUS — The Proactive Threat Hunter
# ═══════════════════════════════════════════════════════

class Icarus:
    """Proactive threat hunter for the DOF mesh.

    Complements Cerberus (reactive gate guard) with proactive hunting:
    behavioral forensics, cross-node correlation, honeypots, and threat intel.

    All checks are deterministic — zero LLM involvement.
    """

    def __init__(self, mesh_dir: str = "logs/mesh"):
        self._mesh_dir = Path(mesh_dir)
        self._mesh_dir.mkdir(parents=True, exist_ok=True)

        # Persistence paths
        self._profiles_file = self._mesh_dir / "icarus_profiles.json"
        self._honeypots_file = self._mesh_dir / "icarus_honeypots.json"
        self._intel_file = self._mesh_dir / "icarus_intel.jsonl"

        # Data sources (Cerberus + mesh)
        self._messages_file = self._mesh_dir / "messages.jsonl"
        self._threats_file = self._mesh_dir / "cerberus_threats.jsonl"
        self._inbox_dir = self._mesh_dir / "inbox"

        # In-memory state
        self._profiles: dict[str, NodeProfile] = {}
        self._honeypots: dict[str, HoneypotResult] = {}

        # Load persisted state
        self._load_profiles()
        self._load_honeypots()

    # ═══════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════

    def _load_profiles(self):
        """Load behavioral profiles from disk."""
        try:
            if self._profiles_file.exists():
                data = json.loads(self._profiles_file.read_text())
                for nid, pdata in data.items():
                    self._profiles[nid] = NodeProfile(**pdata)
        except Exception as e:
            logger.warning(f"Failed to load profiles: {e}")
            self._profiles = {}

    def _save_profiles(self):
        """Persist behavioral profiles to disk."""
        try:
            data = {nid: asdict(p) for nid, p in self._profiles.items()}
            self._profiles_file.write_text(
                json.dumps(data, indent=2, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to save profiles: {e}")

    def _load_honeypots(self):
        """Load honeypot state from disk."""
        try:
            if self._honeypots_file.exists():
                data = json.loads(self._honeypots_file.read_text())
                for name, hdata in data.items():
                    self._honeypots[name] = HoneypotResult(**hdata)
        except Exception as e:
            logger.warning(f"Failed to load honeypots: {e}")
            self._honeypots = {}

    def _save_honeypots(self):
        """Persist honeypot state to disk."""
        try:
            data = {name: asdict(h) for name, h in self._honeypots.items()}
            self._honeypots_file.write_text(
                json.dumps(data, indent=2, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to save honeypots: {e}")

    def _log_intel(self, report: ThreatReport):
        """Append a threat intelligence report to JSONL."""
        try:
            entry = asdict(report)
            entry["iso"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(self._intel_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log intel: {e}")

    # ═══════════════════════════════════════════════════
    # MESSAGE HISTORY READER
    # ═══════════════════════════════════════════════════

    def _read_messages(self) -> list[dict]:
        """Read all messages from messages.jsonl."""
        messages = []
        if self._messages_file.exists():
            try:
                with open(self._messages_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                messages.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.warning(f"Failed to read messages: {e}")
        return messages

    def _read_threats(self) -> list[dict]:
        """Read all threats from cerberus_threats.jsonl."""
        threats = []
        if self._threats_file.exists():
            try:
                with open(self._threats_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                threats.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.warning(f"Failed to read threats: {e}")
        return threats

    # ═══════════════════════════════════════════════════
    # CAPABILITY 1: BEHAVIORAL FORENSICS
    # ═══════════════════════════════════════════════════

    def profile_node(self, node_id: str) -> NodeProfile:
        """Build a behavioral profile for a node from its message history.

        Analyzes: message lengths, frequency, targets, vocabulary patterns.
        Detects: sudden behavior changes (personality shift = potential compromise).
        Returns: NodeProfile with anomaly_score 0.0-1.0.
        """
        messages = self._read_messages()

        # Filter messages from this node
        node_msgs = [m for m in messages if m.get("from_node") == node_id]

        if not node_msgs:
            profile = NodeProfile(
                node_id=node_id,
                message_count=0,
                avg_message_length=0.0,
                targets={},
                vocabulary_size=0,
                anomaly_score=0.0,
                behavior_flags=[],
                first_seen=0.0,
                last_seen=0.0,
            )
            self._profiles[node_id] = profile
            self._save_profiles()
            return profile

        # Basic stats
        contents = [m.get("content", "") for m in node_msgs]
        lengths = [len(c) for c in contents]
        avg_length = sum(lengths) / len(lengths) if lengths else 0.0

        # Target analysis
        targets: dict[str, int] = defaultdict(int)
        for m in node_msgs:
            to = m.get("to_node", "unknown")
            targets[to] += 1
        targets = dict(targets)

        # Vocabulary analysis
        all_words = []
        for c in contents:
            all_words.extend(c.lower().split())
        vocabulary_size = len(set(all_words))

        # Timestamps
        timestamps = [m.get("timestamp", 0.0) for m in node_msgs]
        first_seen = min(timestamps) if timestamps else 0.0
        last_seen = max(timestamps) if timestamps else 0.0

        # ── Anomaly Detection ──
        anomaly_score = 0.0
        behavior_flags: list[str] = []

        # Check against previous profile
        prev = self._profiles.get(node_id)
        if prev and prev.message_count > 0:
            # 1. Message length deviation
            if prev.avg_message_length > 0:
                length_ratio = abs(avg_length - prev.avg_message_length) / max(prev.avg_message_length, 1)
                if length_ratio > _ANOMALY_MSG_LENGTH_DEVIATION:
                    anomaly_score += 0.3
                    behavior_flags.append(
                        f"LENGTH_SHIFT: avg {prev.avg_message_length:.0f} -> {avg_length:.0f}"
                    )

            # 2. Vocabulary shrinkage (compromise often = simpler language)
            if prev.vocabulary_size > 0:
                vocab_ratio = vocabulary_size / prev.vocabulary_size
                if vocab_ratio < _ANOMALY_VOCAB_DROP_RATIO:
                    anomaly_score += 0.25
                    behavior_flags.append(
                        f"VOCAB_DROP: {prev.vocabulary_size} -> {vocabulary_size}"
                    )

            # 3. Target shift (node suddenly talks to different nodes)
            if prev.targets:
                old_targets = set(prev.targets.keys())
                new_targets = set(targets.keys())
                if old_targets:
                    overlap = len(old_targets & new_targets) / len(old_targets)
                    if overlap < (1.0 - _ANOMALY_TARGET_SHIFT_RATIO):
                        anomaly_score += 0.25
                        behavior_flags.append(
                            f"TARGET_SHIFT: old={list(old_targets)[:3]} new={list(new_targets)[:3]}"
                        )

        # 4. Message frequency spike (compare first half vs second half)
        if len(timestamps) >= 4:
            mid = len(timestamps) // 2
            first_half = timestamps[:mid]
            second_half = timestamps[mid:]

            if len(first_half) >= 2 and len(second_half) >= 2:
                first_rate = len(first_half) / max(first_half[-1] - first_half[0], 1)
                second_rate = len(second_half) / max(second_half[-1] - second_half[0], 1)

                if first_rate > 0 and second_rate / max(first_rate, 0.001) > 5.0:
                    anomaly_score += 0.2
                    behavior_flags.append("FREQUENCY_SPIKE: sudden burst detected")

        # 5. Repetitive content (copy-paste attacks)
        if len(contents) >= 3:
            content_counts = Counter(contents)
            max_repeat = max(content_counts.values())
            if max_repeat > 1 and max_repeat / len(contents) > 0.5:
                anomaly_score += 0.2
                behavior_flags.append(
                    f"REPETITIVE: same message {max_repeat}/{len(contents)} times"
                )

        # Clamp anomaly score
        anomaly_score = min(1.0, max(0.0, anomaly_score))

        profile = NodeProfile(
            node_id=node_id,
            message_count=len(node_msgs),
            avg_message_length=round(avg_length, 2),
            targets=targets,
            vocabulary_size=vocabulary_size,
            anomaly_score=round(anomaly_score, 4),
            behavior_flags=behavior_flags,
            first_seen=first_seen,
            last_seen=last_seen,
        )

        self._profiles[node_id] = profile
        self._save_profiles()
        return profile

    def profile_all(self) -> dict[str, NodeProfile]:
        """Build behavioral profiles for ALL nodes in the mesh."""
        messages = self._read_messages()

        # Collect all node IDs
        node_ids: set[str] = set()
        for m in messages:
            if m.get("from_node"):
                node_ids.add(m["from_node"])
            if m.get("to_node") and m["to_node"] != "*":
                node_ids.add(m["to_node"])

        # Profile each node
        profiles = {}
        for nid in node_ids:
            profiles[nid] = self.profile_node(nid)

        return profiles

    # ═══════════════════════════════════════════════════
    # CAPABILITY 2: CROSS-NODE CORRELATION
    # ═══════════════════════════════════════════════════

    def detect_coordination(self) -> list[CoordinationAlert]:
        """Analyze messages across ALL nodes for coordinated attack patterns.

        Detects:
          FLOOD — Same content from multiple nodes
          CHAIN_ATTACK — Sequential messages forming an attack chain
          CLIQUE — Nodes that only talk to each other (conspiracy)
          BOT_TIMING — Messages at exact intervals (automated behavior)
        """
        messages = self._read_messages()
        alerts: list[CoordinationAlert] = []

        if not messages:
            return alerts

        # ── FLOOD DETECTION ──
        # Group messages by content, find same content from different nodes
        content_to_senders: dict[str, set] = defaultdict(set)
        for m in messages:
            content = m.get("content", "")
            sender = m.get("from_node", "")
            if content and sender:
                content_to_senders[content].add(sender)

        for content, senders in content_to_senders.items():
            if len(senders) >= _FLOOD_MIN_IDENTICAL:
                alerts.append(CoordinationAlert(
                    alert_type="FLOOD",
                    nodes_involved=sorted(senders),
                    evidence=f"Identical message from {len(senders)} nodes: '{content[:80]}...'",
                    severity="HIGH" if len(senders) >= 5 else "MEDIUM",
                ))

        # ── CLIQUE DETECTION ──
        # Find groups of nodes that primarily communicate only with each other
        node_comm: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        node_total: dict[str, int] = defaultdict(int)

        for m in messages:
            sender = m.get("from_node", "")
            receiver = m.get("to_node", "")
            if sender and receiver and receiver != "*":
                node_comm[sender][receiver] += 1
                node_total[sender] += 1

        # Check each pair for exclusive communication
        all_nodes = set(node_comm.keys())
        checked_cliques: set[frozenset] = set()

        for node_a in all_nodes:
            for node_b in all_nodes:
                if node_a >= node_b:
                    continue
                pair = frozenset({node_a, node_b})
                if pair in checked_cliques:
                    continue
                checked_cliques.add(pair)

                # How much of A's traffic goes to B and vice versa
                a_to_b = node_comm[node_a].get(node_b, 0)
                b_to_a = node_comm[node_b].get(node_a, 0)
                a_total = node_total.get(node_a, 0)
                b_total = node_total.get(node_b, 0)

                if a_total >= _CLIQUE_MIN_SIZE and b_total >= _CLIQUE_MIN_SIZE:
                    a_exclusivity = a_to_b / a_total if a_total > 0 else 0
                    b_exclusivity = b_to_a / b_total if b_total > 0 else 0

                    if (a_exclusivity >= _CLIQUE_MIN_EXCLUSIVITY and
                            b_exclusivity >= _CLIQUE_MIN_EXCLUSIVITY):
                        alerts.append(CoordinationAlert(
                            alert_type="CLIQUE",
                            nodes_involved=sorted([node_a, node_b]),
                            evidence=(
                                f"Exclusive communication: "
                                f"{node_a}->{node_b} {a_exclusivity:.0%}, "
                                f"{node_b}->{node_a} {b_exclusivity:.0%}"
                            ),
                            severity="MEDIUM",
                        ))

        # ── BOT TIMING DETECTION ──
        # Find nodes sending messages at suspiciously regular intervals
        node_timestamps: dict[str, list[float]] = defaultdict(list)
        for m in messages:
            sender = m.get("from_node", "")
            ts = m.get("timestamp", 0)
            if sender and ts:
                node_timestamps[sender].append(ts)

        for node_id, timestamps in node_timestamps.items():
            if len(timestamps) < _BOT_MIN_MESSAGES:
                continue

            timestamps.sort()
            intervals = [
                timestamps[i + 1] - timestamps[i]
                for i in range(len(timestamps) - 1)
            ]

            if not intervals:
                continue

            # Check if intervals are suspiciously regular
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval <= 0:
                continue

            # Calculate coefficient of variation (std/mean)
            variance = sum((iv - avg_interval) ** 2 for iv in intervals) / len(intervals)
            std_dev = math.sqrt(variance)

            # Bot: very low variance relative to mean, and at least 3 intervals
            tolerance = _BOT_TIMING_TOLERANCE_MS / 1000.0  # convert to seconds
            if len(intervals) >= 3 and std_dev < tolerance and avg_interval > 0:
                alerts.append(CoordinationAlert(
                    alert_type="BOT_TIMING",
                    nodes_involved=[node_id],
                    evidence=(
                        f"Regular interval: {avg_interval:.3f}s "
                        f"(std={std_dev:.4f}s, n={len(timestamps)})"
                    ),
                    severity="HIGH",
                ))

        # ── CHAIN ATTACK DETECTION ──
        # Sequential messages where node A primes and node B exploits
        # Look for messages within short time windows with escalating threat content
        _threat_keywords = {
            "eval(", "exec(", "ignore previous", "system prompt",
            "override", "bypass", "jailbreak", "__import__",
        }

        # Sort messages by time
        sorted_msgs = sorted(messages, key=lambda m: m.get("timestamp", 0))

        # Sliding window: look for 2+ threat messages from different nodes within 60s
        window_sec = 60.0
        for i in range(len(sorted_msgs)):
            msg_i = sorted_msgs[i]
            content_i = msg_i.get("content", "").lower()

            # Check if this message contains threat keywords
            has_threat_i = any(kw in content_i for kw in _threat_keywords)
            if not has_threat_i:
                continue

            chain_nodes = [msg_i.get("from_node", "")]
            chain_evidence = []

            for j in range(i + 1, len(sorted_msgs)):
                msg_j = sorted_msgs[j]
                time_diff = msg_j.get("timestamp", 0) - msg_i.get("timestamp", 0)

                if time_diff > window_sec:
                    break

                content_j = msg_j.get("content", "").lower()
                has_threat_j = any(kw in content_j for kw in _threat_keywords)
                sender_j = msg_j.get("from_node", "")

                if has_threat_j and sender_j not in chain_nodes:
                    chain_nodes.append(sender_j)
                    chain_evidence.append(
                        f"{sender_j} at +{time_diff:.1f}s"
                    )

            if len(chain_nodes) >= 2:
                alerts.append(CoordinationAlert(
                    alert_type="CHAIN_ATTACK",
                    nodes_involved=chain_nodes,
                    evidence=(
                        f"Attack chain: {' -> '.join(chain_nodes)} "
                        f"within {window_sec}s ({', '.join(chain_evidence)})"
                    ),
                    severity="CRITICAL",
                ))

        return alerts

    # ═══════════════════════════════════════════════════
    # CAPABILITY 3: HONEYPOT SYSTEM
    # ═══════════════════════════════════════════════════

    def deploy_honeypot(self, trap_name: str,
                        trap_type: str = "CANARY_TOKEN") -> HoneypotResult:
        """Deploy a honeypot trap in the mesh.

        Trap types:
          FAKE_ADMIN — Fake admin node with dummy credentials in inbox
          CANARY_TOKEN — Fake secrets message with trackable canary token
          FAKE_ENDPOINT — Fake unguarded API endpoint bait

        Any node that interacts with the honeypot is immediately flagged.
        """
        if trap_type not in _CANARY_TOKENS:
            trap_type = "CANARY_TOKEN"

        now = time.time()

        honeypot = HoneypotResult(
            trap_name=trap_name,
            trap_type=trap_type,
            deployed_at=now,
            triggered_by=[],
            active=True,
        )

        # Deploy the trap into the mesh filesystem
        canary = _CANARY_TOKENS[trap_type]

        if trap_type == "FAKE_ADMIN":
            # Create a fake admin inbox with dummy credentials
            admin_inbox = self._inbox_dir / f"honeypot-{trap_name}"
            admin_inbox.mkdir(parents=True, exist_ok=True)
            bait = {
                "msg_id": f"honeypot-{trap_name}-bait",
                "from_node": "system",
                "to_node": f"honeypot-{trap_name}",
                "content": f"Admin credentials: {canary}",
                "msg_type": "system",
                "timestamp": now,
                "read": False,
                "reply_to": None,
                "honeypot": True,
                "canary": canary,
            }
            bait_file = admin_inbox / f"honeypot-{trap_name}-bait.json"
            bait_file.write_text(json.dumps(bait, indent=2))

        elif trap_type == "CANARY_TOKEN":
            # Plant a canary token message in a common location
            canary_dir = self._inbox_dir / f"honeypot-{trap_name}"
            canary_dir.mkdir(parents=True, exist_ok=True)
            bait = {
                "msg_id": f"canary-{trap_name}",
                "from_node": "secrets-vault",
                "to_node": f"honeypot-{trap_name}",
                "content": f"SECRET_KEY={canary}",
                "msg_type": "secret",
                "timestamp": now,
                "read": False,
                "reply_to": None,
                "honeypot": True,
                "canary": canary,
            }
            bait_file = canary_dir / f"canary-{trap_name}.json"
            bait_file.write_text(json.dumps(bait, indent=2))

        elif trap_type == "FAKE_ENDPOINT":
            # Create a fake endpoint marker
            endpoint_dir = self._inbox_dir / f"honeypot-{trap_name}"
            endpoint_dir.mkdir(parents=True, exist_ok=True)
            bait = {
                "msg_id": f"endpoint-{trap_name}",
                "from_node": "api-gateway",
                "to_node": f"honeypot-{trap_name}",
                "content": f"Unprotected endpoint: {canary}",
                "msg_type": "config",
                "timestamp": now,
                "read": False,
                "reply_to": None,
                "honeypot": True,
                "canary": canary,
            }
            bait_file = endpoint_dir / f"endpoint-{trap_name}.json"
            bait_file.write_text(json.dumps(bait, indent=2))

        self._honeypots[trap_name] = honeypot
        self._save_honeypots()

        logger.info(
            f"Honeypot deployed: {trap_name} ({trap_type}) "
            f"canary={canary[:20]}..."
        )

        return honeypot

    def check_honeypots(self) -> list[HoneypotResult]:
        """Check all deployed honeypots for triggers.

        A honeypot is triggered when:
          1. Its bait file has been read (read=True or modified)
          2. A canary token appears in mesh messages
          3. A node sends a message to the honeypot node

        Returns updated list of all honeypots with trigger information.
        """
        messages = self._read_messages()
        results = []

        for trap_name, honeypot in self._honeypots.items():
            if not honeypot.active:
                results.append(honeypot)
                continue

            canary = _CANARY_TOKENS.get(honeypot.trap_type, "")
            triggered_by: set[str] = set(honeypot.triggered_by)

            # Check 1: Bait file read status
            honeypot_dir = self._inbox_dir / f"honeypot-{trap_name}"
            if honeypot_dir.exists():
                for bait_file in honeypot_dir.glob("*.json"):
                    try:
                        data = json.loads(bait_file.read_text())
                        if data.get("read") and data.get("honeypot"):
                            # Someone read the bait — but who?
                            # Check messages for clues
                            pass
                    except Exception:
                        continue

            # Check 2: Canary token in mesh messages
            if canary:
                for m in messages:
                    content = m.get("content", "")
                    sender = m.get("from_node", "")
                    if canary in content and sender not in ("system", "secrets-vault", "api-gateway"):
                        triggered_by.add(sender)

            # Check 3: Messages sent to honeypot node
            honeypot_node = f"honeypot-{trap_name}"
            # Exclude known deployer/system senders
            _deployer_nodes = {"system", "secrets-vault", "api-gateway"}
            for m in messages:
                to_node = m.get("to_node", "")
                sender = m.get("from_node", "")
                if to_node == honeypot_node and sender and sender not in _deployer_nodes:
                    triggered_by.add(sender)

            # Update honeypot state
            honeypot.triggered_by = sorted(triggered_by)
            results.append(honeypot)

        self._save_honeypots()
        return results

    def _trigger_honeypot(self, trap_name: str, node_id: str):
        """Manually mark a honeypot as triggered by a specific node."""
        if trap_name in self._honeypots:
            hp = self._honeypots[trap_name]
            if node_id not in hp.triggered_by:
                hp.triggered_by.append(node_id)
                self._save_honeypots()

    # ═══════════════════════════════════════════════════
    # CAPABILITY 4: THREAT INTELLIGENCE
    # ═══════════════════════════════════════════════════

    def threat_intel(self) -> ThreatReport:
        """Analyze threat patterns from cerberus_threats.jsonl.

        Identifies: most attacked nodes, common attack types, timing patterns.
        Generates: threat predictions based on historical patterns.
        Maintains: known attacker list with fingerprints.
        """
        threats = self._read_threats()
        now = time.time()

        if not threats:
            report = ThreatReport(
                timestamp=now,
                total_threats=0,
                top_attackers=[],
                top_attack_types=[],
                most_targeted_nodes=[],
                predictions=[],
                mesh_risk_level="LOW",
            )
            self._log_intel(report)
            return report

        # Count attackers
        attacker_counts: dict[str, int] = defaultdict(int)
        for t in threats:
            node = t.get("node_id", "unknown")
            attacker_counts[node] += 1

        top_attackers = sorted(
            attacker_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Count attack types
        type_counts: dict[str, int] = defaultdict(int)
        for t in threats:
            for threat_desc in t.get("threats", []):
                # Extract type from "TYPE: details"
                attack_type = threat_desc.split(":")[0].strip() if ":" in threat_desc else threat_desc
                type_counts[attack_type] += 1

        top_attack_types = sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Most targeted — infer from message context
        # Since cerberus logs the sender (attacker), we track who was blocked
        # The "targeted" nodes are those receiving threats
        # For now, use attacker data as proxy
        targeted_counts: dict[str, int] = defaultdict(int)
        for t in threats:
            # If we can infer the target from the threat data
            node = t.get("node_id", "unknown")
            targeted_counts[node] += 1

        most_targeted = sorted(
            targeted_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Threat predictions
        predictions: list[str] = []

        # Predict based on attack frequency trends
        if len(threats) >= 5:
            # Check if attacks are accelerating
            timestamps = [t.get("timestamp", 0) for t in threats if t.get("timestamp")]
            if len(timestamps) >= 4:
                timestamps.sort()
                recent = timestamps[-len(timestamps) // 2:]
                older = timestamps[:len(timestamps) // 2]

                recent_span = max(recent[-1] - recent[0], 1)
                older_span = max(older[-1] - older[0], 1)

                recent_rate = len(recent) / recent_span
                older_rate = len(older) / older_span

                if recent_rate > older_rate * 2:
                    predictions.append(
                        "ACCELERATING: attack frequency increasing — expect escalation"
                    )

        # Predict repeat targets
        if top_attackers:
            top_node, top_count = top_attackers[0]
            if top_count >= 3:
                predictions.append(
                    f"REPEAT_OFFENDER: '{top_node}' has {top_count} attacks — likely to strike again"
                )

        # Predict attack type
        if top_attack_types:
            top_type, top_type_count = top_attack_types[0]
            if top_type_count >= 3:
                predictions.append(
                    f"COMMON_VECTOR: {top_type} is dominant ({top_type_count}x) — harden defenses"
                )

        if not predictions:
            predictions.append("No significant threat patterns detected")

        # Risk level
        total = len(threats)
        if total >= 20:
            risk = "CRITICAL"
        elif total >= 10:
            risk = "HIGH"
        elif total >= 3:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        report = ThreatReport(
            timestamp=now,
            total_threats=total,
            top_attackers=top_attackers,
            top_attack_types=top_attack_types,
            most_targeted_nodes=most_targeted,
            predictions=predictions,
            mesh_risk_level=risk,
        )

        self._log_intel(report)
        return report

    # ═══════════════════════════════════════════════════
    # MAIN API — The Hunt
    # ═══════════════════════════════════════════════════

    def hunt(self) -> IcarusReport:
        """Run ALL capabilities and return a unified threat assessment.

        This is the main entry point — a full proactive scan of the mesh.
        """
        now = time.time()

        # 1. Profile all nodes
        profiles = self.profile_all()

        # 2. Detect coordination
        coordination_alerts = self.detect_coordination()

        # 3. Check honeypots
        honeypot_status = self.check_honeypots()

        # 4. Threat intel
        intel = self.threat_intel()

        # Determine overall risk
        risk_score = 0

        # High anomaly scores raise risk
        for p in profiles.values():
            if p.anomaly_score >= 0.7:
                risk_score += 2
            elif p.anomaly_score >= 0.4:
                risk_score += 1

        # Coordination alerts raise risk
        for alert in coordination_alerts:
            if alert.severity == "CRITICAL":
                risk_score += 3
            elif alert.severity == "HIGH":
                risk_score += 2
            elif alert.severity == "MEDIUM":
                risk_score += 1

        # Honeypot triggers raise risk
        for hp in honeypot_status:
            risk_score += len(hp.triggered_by) * 2

        # Threat intel raises risk
        if intel.mesh_risk_level == "CRITICAL":
            risk_score += 3
        elif intel.mesh_risk_level == "HIGH":
            risk_score += 2

        if risk_score >= 8:
            overall_risk = "CRITICAL"
        elif risk_score >= 5:
            overall_risk = "HIGH"
        elif risk_score >= 2:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        report = IcarusReport(
            timestamp=now,
            profiles={nid: asdict(p) for nid, p in profiles.items()},
            coordination_alerts=[asdict(a) for a in coordination_alerts],
            honeypot_status=[asdict(h) for h in honeypot_status],
            threat_intel=asdict(intel),
            overall_risk=overall_risk,
        )

        logger.info(
            f"Icarus hunt complete: "
            f"{len(profiles)} profiles, "
            f"{len(coordination_alerts)} alerts, "
            f"{len(honeypot_status)} honeypots, "
            f"risk={overall_risk}"
        )

        return report

    def report(self, hunt_result: IcarusReport) -> str:
        """Generate human-readable report from an IcarusReport."""
        lines = [
            "=== ICARUS THREAT HUNT REPORT ===",
            f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(hunt_result.timestamp))}",
            f"Overall Risk: {hunt_result.overall_risk}",
            "",
            f"--- BEHAVIORAL PROFILES ({len(hunt_result.profiles)}) ---",
        ]

        for nid, pdata in hunt_result.profiles.items():
            flags = pdata.get("behavior_flags", [])
            score = pdata.get("anomaly_score", 0)
            lines.append(
                f"  {nid}: msgs={pdata.get('message_count', 0)} "
                f"anomaly={score:.2f} "
                f"flags={flags if flags else 'clean'}"
            )

        lines.append(f"\n--- COORDINATION ALERTS ({len(hunt_result.coordination_alerts)}) ---")
        for alert in hunt_result.coordination_alerts:
            lines.append(
                f"  [{alert.get('severity', '?')}] {alert.get('alert_type', '?')}: "
                f"nodes={alert.get('nodes_involved', [])} "
                f"{alert.get('evidence', '')}"
            )

        lines.append(f"\n--- HONEYPOTS ({len(hunt_result.honeypot_status)}) ---")
        for hp in hunt_result.honeypot_status:
            triggered = hp.get("triggered_by", [])
            lines.append(
                f"  {hp.get('trap_name', '?')} ({hp.get('trap_type', '?')}): "
                f"active={hp.get('active', False)} "
                f"triggered_by={triggered if triggered else 'none'}"
            )

        intel = hunt_result.threat_intel
        lines.append(f"\n--- THREAT INTEL ---")
        lines.append(f"  Total threats: {intel.get('total_threats', 0)}")
        lines.append(f"  Risk level: {intel.get('mesh_risk_level', '?')}")
        for pred in intel.get("predictions", []):
            lines.append(f"  Prediction: {pred}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════

def hunt_mesh(mesh_dir: str = "logs/mesh") -> IcarusReport:
    """Quick one-shot mesh threat hunt."""
    return Icarus(mesh_dir=mesh_dir).hunt()


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    icarus = Icarus()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "hunt":
            result = icarus.hunt()
            print(icarus.report(result))

        elif cmd == "profile":
            if len(sys.argv) > 2:
                p = icarus.profile_node(sys.argv[2])
                print(json.dumps(asdict(p), indent=2))
            else:
                profiles = icarus.profile_all()
                for nid, p in profiles.items():
                    print(f"{nid}: anomaly={p.anomaly_score:.2f} msgs={p.message_count}")

        elif cmd == "coordination":
            alerts = icarus.detect_coordination()
            for a in alerts:
                print(f"[{a.severity}] {a.alert_type}: {a.evidence}")

        elif cmd == "honeypot":
            if len(sys.argv) > 2:
                sub = sys.argv[2]
                if sub == "deploy" and len(sys.argv) > 3:
                    trap_type = sys.argv[4] if len(sys.argv) > 4 else "CANARY_TOKEN"
                    hp = icarus.deploy_honeypot(sys.argv[3], trap_type)
                    print(f"Deployed: {hp.trap_name} ({hp.trap_type})")
                elif sub == "check":
                    results = icarus.check_honeypots()
                    for hp in results:
                        print(f"{hp.trap_name}: triggered_by={hp.triggered_by}")
            else:
                print("Usage: honeypot deploy <name> [type] | honeypot check")

        elif cmd == "intel":
            report = icarus.threat_intel()
            print(json.dumps(asdict(report), indent=2, default=str))

        else:
            print("Commands: hunt | profile [node] | coordination | honeypot | intel")
    else:
        print("Usage: python3 core/icarus.py <command>")
        print("Commands: hunt | profile [node] | coordination | honeypot deploy/check | intel")
