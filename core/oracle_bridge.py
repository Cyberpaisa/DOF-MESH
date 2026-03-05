"""
Oracle Bridge — ERC-8004 on-chain attestation of governance metrics.

Bridge between DOF off-chain governance and ERC-8004 Validation Registry
on Avalanche C-Chain. Generates attestation structures off-chain, signs
them with HMAC-SHA256, and prepares transactions for on-chain publishing.

No blockchain dependency for testing — transaction preparation only.
All operations logged to JSONL for audit trail.

Usage:
    from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationRegistry
    from core.oags_bridge import OAGSIdentity

    signer = CertificateSigner()
    identity = OAGSIdentity()
    bridge = OracleBridge(signer, identity)

    cert = bridge.create_attestation("task-001", {"SS": 0.95, "GCR": 1.0, ...})
    if bridge.should_publish(cert):
        tx = bridge.prepare_transaction(cert)
"""

import os
import json
import hmac
import hashlib
import secrets
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger("core.oracle_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
KEYS_DIR = os.path.join(BASE_DIR, "keys")

# Reuse _hash_bytes from oags_bridge for BLAKE3/SHA256 fallback
try:
    import blake3 as _blake3

    def _hash_bytes(data: bytes) -> str:
        return _blake3.blake3(data).hexdigest()
except ImportError:
    def _hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ─────────────────────────────────────────────────────────────────────
# AttestationCertificate
# ─────────────────────────────────────────────────────────────────────

@dataclass
class AttestationCertificate:
    """Signed governance metrics attestation for ERC-8004."""
    agent_identity: str
    task_id: str
    timestamp: str  # ISO format
    metrics: dict  # SS, GCR, PFI, RP, SSR
    governance_status: str  # "COMPLIANT" or "NON_COMPLIANT"
    z3_verified: bool
    signature: str
    certificate_hash: str
    published: bool = False  # True after on-chain publishing


# ─────────────────────────────────────────────────────────────────────
# CertificateSigner — HMAC-SHA256 (zero external deps)
# ─────────────────────────────────────────────────────────────────────

class CertificateSigner:
    """HMAC-SHA256 signing for attestation certificates.

    Generates a random secret key if none exists, persists to keys/oracle_key.json.
    """

    def __init__(self, key_path: str = ""):
        self._key_path = key_path or os.path.join(KEYS_DIR, "oracle_key.json")
        self._secret_key = b""
        self._load_or_generate_key()

    def _load_or_generate_key(self):
        """Load key from file or generate new one."""
        if os.path.exists(self._key_path):
            try:
                with open(self._key_path, "r") as f:
                    data = json.load(f)
                self._secret_key = bytes.fromhex(data["secret_key_hex"])
                logger.info(f"Loaded signing key from {self._key_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load key: {e} — generating new one")

        # Generate new key
        self._secret_key = secrets.token_bytes(32)
        os.makedirs(os.path.dirname(self._key_path), exist_ok=True)
        with open(self._key_path, "w") as f:
            json.dump({
                "secret_key_hex": self._secret_key.hex(),
                "created_at": datetime.now().isoformat(),
                "algorithm": "HMAC-SHA256",
            }, f, indent=2)
        logger.info(f"Generated new signing key: {self._key_path}")

    def sign(self, data: bytes) -> str:
        """Sign data with HMAC-SHA256. Returns hex signature."""
        return hmac.new(self._secret_key, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        expected = hmac.new(self._secret_key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def get_public_id(self) -> str:
        """Return BLAKE3/SHA256 hash of the key as public identifier."""
        return _hash_bytes(self._secret_key)


# ─────────────────────────────────────────────────────────────────────
# OracleBridge — Attestation creation and transaction preparation
# ─────────────────────────────────────────────────────────────────────

class OracleBridge:
    """Bridge between DOF off-chain governance and ERC-8004 on-chain attestation."""

    def __init__(self, signer: CertificateSigner, oags):
        """Initialize with signer and OAGSIdentity instance."""
        self._signer = signer
        self._oags = oags
        self._agent_identity = ""
        if oags:
            card = oags.get_agent_card()
            self._agent_identity = card.get("identity_hash", "")

    def create_attestation(self, task_id: str, metrics: dict,
                           z3_results: list | None = None) -> AttestationCertificate:
        """Create a signed attestation certificate from execution metrics.

        Args:
            task_id: Unique task identifier.
            metrics: Dict with SS, GCR, PFI, RP, SSR values.
            z3_results: Optional list of ProofResult-like dicts. All must have
                        result=="VERIFIED" for z3_verified=True.

        Returns:
            Signed AttestationCertificate.
        """
        # Determine governance status
        gcr = metrics.get("GCR", metrics.get("governance_compliance_rate", 0.0))
        governance_status = "COMPLIANT" if gcr == 1.0 else "NON_COMPLIANT"

        # Determine Z3 verification status
        z3_verified = False
        if z3_results:
            z3_verified = all(
                r.get("result") == "VERIFIED" or getattr(r, "result", None) == "VERIFIED"
                for r in z3_results
            )

        timestamp = datetime.now().isoformat()

        # Serialize for signing
        payload = json.dumps({
            "agent_identity": self._agent_identity,
            "task_id": task_id,
            "timestamp": timestamp,
            "metrics": metrics,
            "governance_status": governance_status,
            "z3_verified": z3_verified,
        }, sort_keys=True, default=str).encode("utf-8")

        # Sign
        signature = self._signer.sign(payload)

        # Certificate hash
        certificate_hash = _hash_bytes(payload + signature.encode("utf-8"))

        cert = AttestationCertificate(
            agent_identity=self._agent_identity,
            task_id=task_id,
            timestamp=timestamp,
            metrics=metrics,
            governance_status=governance_status,
            z3_verified=z3_verified,
            signature=signature,
            certificate_hash=certificate_hash,
        )

        self._log_attestation(cert, "created")
        return cert

    def should_publish(self, cert: AttestationCertificate) -> bool:
        """Determine if attestation should be published on-chain.

        Only COMPLIANT attestations are published.
        SS < 0.5 publishes with warning (still returns True).
        """
        if cert.governance_status != "COMPLIANT":
            return False

        ss = cert.metrics.get("SS", cert.metrics.get("stability_score", 1.0))
        if ss < 0.5:
            logger.warning(
                f"Attestation {cert.certificate_hash[:16]} has low SS={ss} — "
                f"publishing with warning"
            )

        return True

    def prepare_transaction(self, cert: AttestationCertificate) -> dict:
        """Prepare an ERC-8004 compatible transaction structure.

        Does NOT send the transaction — only prepares it.
        """
        return {
            "to": "0x0000000000000000000000000000000000000000",
            "data": {
                "agent_id": cert.agent_identity,
                "validation_signal": cert.governance_status,
                "metrics_hash": cert.certificate_hash,
                "timestamp": cert.timestamp,
                "signature": cert.signature,
            },
            "chain": "avalanche-c-chain",
            "gas_estimate": None,
        }

    def batch_attestations(self, certs: list[AttestationCertificate]) -> dict:
        """Group multiple attestations into a single batch transaction.

        Gas optimization: one tx for N attestations.
        """
        batch_id = str(uuid.uuid4())
        transaction_data = []
        for cert in certs:
            transaction_data.append({
                "agent_id": cert.agent_identity,
                "validation_signal": cert.governance_status,
                "metrics_hash": cert.certificate_hash,
                "timestamp": cert.timestamp,
                "signature": cert.signature,
            })

        return {
            "batch_id": batch_id,
            "certificates": len(certs),
            "transaction_data": transaction_data,
        }

    def verify_attestation(self, cert: AttestationCertificate) -> bool:
        """Verify attestation integrity: recalculate hash and verify signature."""
        # Reconstruct payload
        payload = json.dumps({
            "agent_identity": cert.agent_identity,
            "task_id": cert.task_id,
            "timestamp": cert.timestamp,
            "metrics": cert.metrics,
            "governance_status": cert.governance_status,
            "z3_verified": cert.z3_verified,
        }, sort_keys=True, default=str).encode("utf-8")

        # Verify signature
        if not self._signer.verify(payload, cert.signature):
            return False

        # Verify certificate hash
        expected_hash = _hash_bytes(payload + cert.signature.encode("utf-8"))
        return expected_hash == cert.certificate_hash

    def publish_to_enigma(self, cert: AttestationCertificate,
                          ast_score: float = 0.0,
                          acr: float = 0.0) -> dict:
        """Publish attestation metrics to Enigma Scanner trust_scores.

        Requires ENIGMA_DATABASE_URL in environment.

        Args:
            cert: Signed attestation certificate.
            ast_score: AST verifier score (0.0-1.0).
            acr: Adversarial compliance rate (0.0-1.0).

        Returns:
            Dict with published TrustScore or error.
        """
        try:
            from core.enigma_bridge import EnigmaBridge

            bridge = EnigmaBridge()
            metrics = {
                "SS": cert.metrics.get("SS", cert.metrics.get("stability_score", 0.0)),
                "GCR": cert.metrics.get("GCR", cert.metrics.get("governance_compliance_rate", 0.0)),
                "PFI": cert.metrics.get("PFI", cert.metrics.get("provider_failure_index", 0.0)),
                "AST_score": ast_score,
                "ACR": acr,
            }
            snapshot = {
                "certificate_hash": cert.certificate_hash,
                "task_id": cert.task_id,
                "governance_status": cert.governance_status,
                "z3_verified": cert.z3_verified,
                "full_metrics": cert.metrics,
            }
            score = bridge.publish_trust_score(
                agent_id=cert.agent_identity,
                metrics=metrics,
                snapshot_data=snapshot,
            )
            self._log_attestation(cert, "published_to_enigma")
            return {"status": "published", "trust_score": score.__dict__}
        except Exception as e:
            logger.warning(f"Failed to publish to Enigma: {e}")
            return {"status": "error", "error": str(e)}

    def _log_attestation(self, cert: AttestationCertificate, action: str):
        """Log attestation event to logs/oracle_bridge.jsonl."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "oracle_bridge.jsonl")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "certificate_hash": cert.certificate_hash,
            "task_id": cert.task_id,
            "governance_status": cert.governance_status,
            "z3_verified": cert.z3_verified,
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log attestation: {e}")


# ─────────────────────────────────────────────────────────────────────
# AttestationRegistry — Off-chain local persistence
# ─────────────────────────────────────────────────────────────────────

class AttestationRegistry:
    """Off-chain local registry for attestation certificates.

    Persists to logs/attestations.jsonl.
    Optional: StorageBackend (PostgreSQL) for production persistence.
    """

    def __init__(self, _storage_backend=None):
        os.makedirs(LOGS_DIR, exist_ok=True)
        self._store_path = os.path.join(LOGS_DIR, "attestations.jsonl")
        self._certs: list[AttestationCertificate] = []
        self._backend = _storage_backend
        self._load()

    def _load(self):
        """Load existing attestations from JSONL."""
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        cert = AttestationCertificate(**data)
                        self._certs.append(cert)
                    except (json.JSONDecodeError, TypeError):
                        continue
        except Exception as e:
            logger.warning(f"Error loading attestations: {e}")

    def _save(self):
        """Persist all attestations to JSONL."""
        with open(self._store_path, "w") as f:
            for cert in self._certs:
                f.write(json.dumps(asdict(cert), default=str) + "\n")

    def add(self, cert: AttestationCertificate):
        """Add attestation to registry and persist."""
        self._certs.append(cert)
        self._save()
        # Dual-write to storage backend if available
        if self._backend is not None:
            try:
                self._backend.save_attestation(asdict(cert))
            except Exception as exc:
                logger.warning(f"Backend save_attestation failed: {exc}")

    def get_attestation(self, certificate_hash: str) -> AttestationCertificate | None:
        """Look up attestation by certificate hash."""
        for cert in self._certs:
            if cert.certificate_hash == certificate_hash:
                return cert
        return None

    def get_agent_history(self, agent_identity: str) -> list[AttestationCertificate]:
        """Return all attestations for a given agent identity."""
        return [c for c in self._certs if c.agent_identity == agent_identity]

    def get_compliance_rate(self) -> float:
        """Calculate compliance rate: COMPLIANT / total."""
        if not self._certs:
            return 0.0
        compliant = sum(1 for c in self._certs if c.governance_status == "COMPLIANT")
        return compliant / len(self._certs)

    def export_for_chain(self) -> list[dict]:
        """Return unpublished COMPLIANT attestations ready for on-chain publishing."""
        pending = [c for c in self._certs
                   if c.governance_status == "COMPLIANT" and not c.published]
        return [asdict(c) for c in pending]

    def mark_published(self, certificate_hash: str):
        """Mark attestation as published on-chain."""
        for cert in self._certs:
            if cert.certificate_hash == certificate_hash:
                cert.published = True
                self._save()
                return
