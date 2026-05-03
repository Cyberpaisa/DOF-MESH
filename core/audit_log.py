"""
DOF Audit Log — Tamper-Proof JSONL with SHA3-256/FIPS Hash Chain
============================================================

Each log entry includes a `chain_hash` that is the SHA3-256 of:
    hash(prev_hash + json(entry_without_chain_hash))

This creates an append-only, tamper-evident chain. Any modification
to any past entry invalidates all subsequent hashes.

Usage:
    log = AuditLog("logs/audit/governance.jsonl")
    log.write({"event": "GOVERNANCE_DECISION", "result": "PASS", "rule": "NO_EMPTY_OUTPUT"})
    log.verify()  # → VerificationResult(valid=True, entries=42, chain_intact=True)
"""

import json
import hashlib
import threading
import time
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("core.audit_log")

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


# ═══════════════════════════════════════════════════
# HASH FUNCTIONS
# ═══════════════════════════════════════════════════

def sha3_256(data: str) -> str:
    """SHA3-256/FIPS audit-chain hash; not EVM/Solidity keccak256."""
    return hashlib.sha3_256(data.encode("utf-8")).hexdigest()


def entry_hash(prev_hash: str, entry_body: Dict) -> str:
    """Compute chain hash for an entry."""
    canonical = json.dumps(entry_body, sort_keys=True, separators=(",", ":"))
    return sha3_256(prev_hash + canonical)


# ═══════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════

@dataclass
class AuditEntry:
    """Single audit log entry with chain hash."""
    seq: int
    timestamp: str
    event: str
    data: Dict[str, Any]
    prev_hash: str
    chain_hash: str

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass
class VerificationResult:
    valid: bool
    entries: int
    chain_intact: bool
    first_broken_seq: Optional[int] = None
    error: Optional[str] = None

    def __str__(self):
        if self.valid:
            return f"VERIFIED — {self.entries} entries, chain intact"
        return f"TAMPERED — broken at seq={self.first_broken_seq}, error={self.error}"


# ═══════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════

class AuditLog:
    """
    Append-only JSONL audit log with an internal SHA3-256/FIPS hash chain.

    Thread-safe. Zero external dependencies.
    """

    _instance = None

    def __new__(cls, path: str = "logs/audit/governance.jsonl"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, path: str = "logs/audit/governance.jsonl"):
        if getattr(self, "_audit_initialized", False):
            return
        self._audit_initialized = True
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq = 0
        self._last_hash = GENESIS_HASH
        self._in_memory_logs: List[str] = []
        self._load_tail()

    # ── Simple log/get_logs interface (for test compatibility) ────────────────

    def log(self, message: str) -> None:
        """Append a string message to the in-memory log. Raises on invalid input."""
        if message is None or not isinstance(message, str):
            raise TypeError(f"message must be a str, got {type(message).__name__}")
        if message == "":
            raise ValueError("message cannot be empty")
        with self._lock:
            self._in_memory_logs.append(message)

    def get_logs(self) -> List[str]:
        """Return in-memory log messages."""
        return list(self._in_memory_logs)

    def _load_tail(self):
        """Resume from last entry if file exists."""
        if not self.path.exists():
            return
        try:
            last_line = None
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
            if last_line:
                entry = json.loads(last_line)
                self._seq = entry.get("seq", 0)
                self._last_hash = entry.get("chain_hash", GENESIS_HASH)
                logger.debug(f"Resumed audit log at seq={self._seq}")
        except Exception as e:
            logger.warning(f"Could not resume audit log: {e}")

    def write(self, event: str, data: Dict[str, Any] = None) -> AuditEntry:
        """Append a tamper-proof entry to the audit log."""
        with self._lock:
            self._seq += 1
            ts = datetime.now(tz=timezone.utc).isoformat()

            body = {
                "seq": self._seq,
                "timestamp": ts,
                "event": event,
                "data": data or {},
                "prev_hash": self._last_hash,
            }

            chain = entry_hash(self._last_hash, body)
            entry = AuditEntry(
                seq=self._seq,
                timestamp=ts,
                event=event,
                data=data or {},
                prev_hash=self._last_hash,
                chain_hash=chain,
            )

            with open(self.path, "a") as f:
                f.write(entry.to_jsonl() + "\n")

            self._last_hash = chain
            return entry

    def verify(self) -> VerificationResult:
        """Verify the integrity of the entire hash chain."""
        if not self.path.exists():
            return VerificationResult(valid=True, entries=0, chain_intact=True)

        prev_hash = GENESIS_HASH
        count = 0

        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    count += 1
                    entry = json.loads(line)

                    # Reconstruct body without chain_hash
                    body = {k: v for k, v in entry.items() if k != "chain_hash"}
                    expected = entry_hash(prev_hash, body)

                    if expected != entry.get("chain_hash"):
                        return VerificationResult(
                            valid=False,
                            entries=count,
                            chain_intact=False,
                            first_broken_seq=entry.get("seq", count),
                            error=f"Hash mismatch at seq={entry.get('seq', count)}"
                        )

                    prev_hash = entry["chain_hash"]

        except Exception as e:
            return VerificationResult(
                valid=False, entries=count, chain_intact=False, error=str(e)
            )

        return VerificationResult(valid=True, entries=count, chain_intact=True)

    def tail(self, n: int = 10) -> List[Dict]:
        """Return last N entries."""
        if not self.path.exists():
            return []
        lines = []
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return lines[-n:]

    def get_head_hash(self) -> str:
        """Return current chain head hash."""
        return self._last_hash

    def entry_count(self) -> int:
        return self._seq


# ═══════════════════════════════════════════════════
# GLOBAL AUDIT LOGS — DOF MESH
# ═══════════════════════════════════════════════════

class DOFAuditLogs:
    """
    Central registry of all DOF audit logs.
    One log per domain, all hash-chained.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.governance = AuditLog("logs/audit/governance.jsonl")
        self.mesh       = AuditLog("logs/audit/mesh.jsonl")
        self.security   = AuditLog("logs/audit/security.jsonl")
        self.compliance = AuditLog("logs/audit/compliance.jsonl")
        self.remote     = AuditLog("logs/audit/remote_nodes.jsonl")

    @classmethod
    def get(cls) -> "DOFAuditLogs":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def verify_all(self) -> Dict[str, VerificationResult]:
        return {
            "governance": self.governance.verify(),
            "mesh":       self.mesh.verify(),
            "security":   self.security.verify(),
            "compliance": self.compliance.verify(),
            "remote":     self.remote.verify(),
        }

    def status(self) -> Dict:
        return {
            log_name: {
                "entries": log.entry_count(),
                "head_hash": log.get_head_hash()[:16] + "...",
                "path": str(log.path),
            }
            for log_name, log in {
                "governance": self.governance,
                "mesh":       self.mesh,
                "security":   self.security,
                "compliance": self.compliance,
                "remote":     self.remote,
            }.items()
        }


# Convenience functions
def audit_governance(event: str, data: Dict = None) -> AuditEntry:
    return DOFAuditLogs.get().governance.write(event, data)

def audit_mesh(event: str, data: Dict = None) -> AuditEntry:
    return DOFAuditLogs.get().mesh.write(event, data)

def audit_security(event: str, data: Dict = None) -> AuditEntry:
    return DOFAuditLogs.get().security.write(event, data)

def audit_compliance(event: str, data: Dict = None) -> AuditEntry:
    return DOFAuditLogs.get().compliance.write(event, data)

def audit_remote(event: str, data: Dict = None) -> AuditEntry:
    return DOFAuditLogs.get().remote.write(event, data)


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    logs = DOFAuditLogs.get()

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        print("\n=== DOF AUDIT LOG VERIFICATION ===")
        results = logs.verify_all()
        all_valid = True
        for name, result in results.items():
            status = "✅ VERIFIED" if result.valid else "❌ TAMPERED"
            print(f"  {name:12s} {status}  {result.entries} entries")
            if not result.valid:
                all_valid = False
                print(f"              Error: {result.error}")
        print(f"\n{'ALL CHAINS INTACT' if all_valid else 'TAMPERING DETECTED'}")

    else:
        # Demo: write and verify
        print("Writing demo entries...")
        for i in range(5):
            audit_governance("DEMO_EVENT", {"index": i, "value": f"test_{i}"})

        result = logs.governance.verify()
        print(f"Governance chain: {result}")
        print(f"Head hash: {logs.governance.get_head_hash()[:32]}...")
        print(f"\nStatus: {json.dumps(logs.status(), indent=2)}")
