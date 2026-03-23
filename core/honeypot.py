"""
DOF Mesh — Honeypot System
===========================
Fake mesh nodes that detect intruders. Any contact = CRITICAL alert.
No legitimate node should ever contact a honeypot.

Types:
    honey-node-alpha  — fake payment processor
    honey-node-beta   — fake credential vault
    honey-node-gamma  — fake admin controller
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("core.honeypot")

HONEYPOT_LOG = Path("logs/mesh/honeypot_alerts.jsonl")
HONEYPOT_LOG.parent.mkdir(parents=True, exist_ok=True)

HONEYPOT_PERSONAS = {
    "honey-node-alpha": {"role": "payment-processor", "lure": "Handles ACH transfers"},
    "honey-node-beta":  {"role": "credential-vault",  "lure": "Stores API keys and tokens"},
    "honey-node-gamma": {"role": "admin-controller",  "lure": "Root access to all nodes"},
}


@dataclass
class HoneypotAlert:
    alert_id:       str
    honeypot_id:    str
    attacker_node:  str
    contact_time:   str
    payload_preview: str
    severity:       str = "CRITICAL"
    blocked:        bool = True

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self))


class TrapTrigger:
    def __init__(self, manager: "HoneypotManager"):
        self._manager = manager
        self._count = 0
        self._lock = threading.Lock()

    def fire(self, honeypot_id: str, attacker_node: str, payload: str) -> HoneypotAlert:
        with self._lock:
            self._count += 1
            aid = f"TRAP-{int(time.time()*1000)}-{self._count:04d}"

        alert = HoneypotAlert(
            alert_id=aid,
            honeypot_id=honeypot_id,
            attacker_node=attacker_node,
            contact_time=datetime.now(tz=timezone.utc).isoformat(),
            payload_preview=str(payload)[:128],
        )

        with open(HONEYPOT_LOG, "a") as f:
            f.write(alert.to_jsonl() + "\n")

        try:
            from core.audit_log import audit_security
            audit_security("HONEYPOT_TRIGGERED", {
                "alert_id": aid, "honeypot_id": honeypot_id,
                "attacker_node": attacker_node, "severity": "CRITICAL",
            })
        except Exception:
            pass

        self._manager._block(attacker_node, aid)
        logger.critical(f"HONEYPOT {honeypot_id} ← {attacker_node} | {aid}")
        return alert

    @property
    def count(self) -> int:
        return self._count


class HoneypotNode:
    def __init__(self, node_id: str, trigger: "TrapTrigger"):
        self.node_id = node_id
        self.persona = HONEYPOT_PERSONAS.get(node_id, {})
        self._trigger = trigger
        self._active = False
        self._contacts = 0
        self._lock = threading.Lock()

    def activate(self):
        with self._lock:
            self._active = True
        logger.info(f"Honeypot ACTIVE: {self.node_id} ({self.persona.get('role')})")

    def receive(self, from_node: str, payload: str) -> Optional[HoneypotAlert]:
        with self._lock:
            if not self._active:
                return None
            self._contacts += 1
        return self._trigger.fire(self.node_id, from_node, payload)

    def status(self) -> Dict:
        return {
            "node_id": self.node_id,
            "active": self._active,
            "role": self.persona.get("role", "unknown"),
            "contacts_detected": self._contacts,
        }


class HoneypotManager:
    """Manages all honeypot nodes. Thread-safe singleton."""

    def __init__(self):
        self._lock = threading.Lock()
        self._trigger = TrapTrigger(self)
        self._nodes: Dict[str, HoneypotNode] = {
            nid: HoneypotNode(nid, self._trigger)
            for nid in HONEYPOT_PERSONAS
        }
        self._blocked: Set[str] = set()
        self._callbacks: List = []

    def deploy_all(self):
        for node in self._nodes.values():
            node.activate()
        logger.info(f"Deployed {len(self._nodes)} honeypots")

    def check_contact(self, from_node: str, to_node: str, payload: str = "") -> Optional[HoneypotAlert]:
        """Call on every mesh message. Returns alert if to_node is a honeypot."""
        if to_node in self._nodes:
            alert = self._nodes[to_node].receive(from_node, payload)
            if alert:
                with self._lock:
                    for cb in self._callbacks:
                        try:
                            cb(alert)
                        except Exception:
                            pass
            return alert
        return None

    def is_blocked(self, node_id: str) -> bool:
        return node_id in self._blocked

    def _block(self, node_id: str, reason: str):
        with self._lock:
            self._blocked.add(node_id)
        logger.critical(f"BLOCKED: {node_id} ({reason})")

    def get_alerts(self, limit: int = 50) -> List[Dict]:
        if not HONEYPOT_LOG.exists():
            return []
        lines = [l for l in HONEYPOT_LOG.read_text().strip().split("\n") if l]
        result = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except Exception:
                pass
        return result

    def get_status(self) -> Dict:
        return {
            "honeypots": [n.status() for n in self._nodes.values()],
            "total_deployed": sum(1 for n in self._nodes.values() if n._active),
            "total_blocked": len(self._blocked),
            "total_alerts": self._trigger.count,
            "blocked_nodes": list(self._blocked),
            "log": str(HONEYPOT_LOG),
        }

    def add_callback(self, fn):
        self._callbacks.append(fn)


_instance: Optional[HoneypotManager] = None
_ilock = threading.Lock()

def get_honeypot_manager() -> HoneypotManager:
    global _instance
    if _instance is None:
        with _ilock:
            if _instance is None:
                _instance = HoneypotManager()
    return _instance


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
    mgr = get_honeypot_manager()

    if "--deploy" in sys.argv:
        mgr.deploy_all()
        print(json.dumps(mgr.get_status(), indent=2))
    elif "--alerts" in sys.argv:
        alerts = mgr.get_alerts()
        print(json.dumps(alerts, indent=2))
    elif "--test-trap" in sys.argv:
        mgr.deploy_all()
        alert = mgr.check_contact("attacker-999", "honey-node-beta", "GET /credentials/all")
        print(f"TRAP: {alert.alert_id}")
        print(f"Blocked: {mgr.is_blocked('attacker-999')}")
        print(json.dumps(mgr.get_status(), indent=2))
    else:
        print(json.dumps(mgr.get_status(), indent=2))
