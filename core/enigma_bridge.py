"""
Enigma Bridge — DOF attestations → dof_trust_scores in enigma-dev Supabase.

Writes to dof_trust_scores (DOF's own table), NOT trust_scores (El Centinela).
This avoids semantic collision: El Centinela calculates on-chain metrics
(volume, proxy detection, heartbeat uptime) while DOF tracks governance
attestation metrics (GCR, SS, AST, ACR, PFI, RP, SSR).

Schema (dof_trust_scores):
    agent_id            → agents.address (FK, resolved by token_id)
    governance_score    → GCR (governance compliance rate)
    stability_score     → SS  (stability score)
    ast_score           → AST verifier score
    adversarial_score   → ACR (adversarial compliance rate)
    provider_fragility  → PFI (provider failure index)
    retry_pressure      → RP  (retry pressure)
    supervisor_strictness → SSR (supervisor strictness ratio)
    certificate_hash    → attestation certificate hash
    on_chain_tx         → Avalanche TX hash
    on_chain_block      → Avalanche block number
    z3_verified         → Z3 formal verification pass
    z3_theorems_passed  → number of Z3 theorems verified
    governance_status   → COMPLIANT / NON_COMPLIANT / UNKNOWN
    snapshot_data       → full attestation JSON for audit

Usage:
    from core.enigma_bridge import EnigmaBridge

    bridge = EnigmaBridge()
    bridge.publish_trust_score(
        attestation={
            'metrics': {'SS': 0.92, 'GCR': 1.0, 'PFI': 0.15, ...},
            'governance_status': 'COMPLIANT',
            'certificate_hash': '0xabc...',
            'z3_verified': True,
            'ast_score': 1.0,
            'on_chain_tx': '0xdef...',
            'on_chain_block': 79657379,
        },
        oags_identity='1687',  # token_id — resolved to agents.address
    )
    score = bridge.get_trust_score(agent_id)
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger("core.enigma_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# SQLAlchemy is optional — graceful fallback
try:
    from sqlalchemy import (
        create_engine, Column, String, Float, DateTime, JSON,
        Table, MetaData, text,
    )
    from sqlalchemy.orm import Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


# ─────────────────────────────────────────────────────────────────────
# DOFTrustScore dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DOFTrustScore:
    """Mirrors the dof_trust_scores table in enigma-dev Supabase."""
    agent_id: str
    governance_score: float      # GCR
    stability_score: float       # SS
    ast_score: float             # AST verifier
    adversarial_score: float     # ACR
    provider_fragility: float    # PFI
    retry_pressure: float        # RP
    supervisor_strictness: float # SSR
    certificate_hash: str
    on_chain_tx: str
    on_chain_block: int
    z3_verified: bool
    z3_theorems_passed: int
    governance_status: str
    calculated_at: str           # ISO format
    snapshot_data: dict          # Full attestation for audit


# Backward compat alias
TrustScore = DOFTrustScore


# ─────────────────────────────────────────────────────────────────────
# EnigmaBridge
# ─────────────────────────────────────────────────────────────────────

class EnigmaBridge:
    """Bridge between DOF attestations and dof_trust_scores in enigma-dev.

    Reads ENIGMA_DATABASE_URL from environment. If unavailable, operates
    in offline mode (logs to JSONL only, no database writes).
    """

    def __init__(self, connection_url: str = None):
        self._url = connection_url or os.environ.get("ENIGMA_DATABASE_URL", "")
        self._engine = None
        self._offline = True

        if self._url and HAS_SQLALCHEMY:
            try:
                self._engine = create_engine(self._url, echo=False)
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                self._offline = False
                logger.info("EnigmaBridge connected to Enigma database")
            except Exception as e:
                logger.warning(f"EnigmaBridge offline — cannot connect: {e}")
                self._engine = None
        elif not self._url:
            logger.info("EnigmaBridge offline — ENIGMA_DATABASE_URL not set")
        elif not HAS_SQLALCHEMY:
            logger.info("EnigmaBridge offline — sqlalchemy not installed")

    @property
    def is_online(self) -> bool:
        return not self._offline

    def resolve_agent_address(self, token_id) -> str | None:
        """Resolve agents.address from token_id (trust_scores FK target)."""
        if self._offline or self._engine is None:
            return None
        try:
            with Session(self._engine) as session:
                row = session.execute(
                    text("SELECT address FROM agents WHERE token_id = :tid"),
                    {"tid": int(token_id)},
                ).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def publish_trust_score(self, attestation: dict = None,
                            oags_identity: str = None,
                            **kwargs) -> DOFTrustScore:
        """Publish DOF attestation to dof_trust_scores.

        Args:
            attestation: Dict with metrics, governance_status, certificate_hash,
                         z3_verified, ast_score, on_chain_tx, on_chain_block.
            oags_identity: Token ID string — resolved to agents.address.
            **kwargs: Legacy support (agent_id, metrics, snapshot_data).

        Returns:
            DOFTrustScore dataclass with published values.
        """
        # ── Legacy API support (agent_id, metrics, snapshot_data) ──
        if attestation is None and "agent_id" in kwargs:
            return self._publish_legacy(**kwargs)

        if attestation is None:
            attestation = {}

        metrics = attestation.get("metrics", {})

        # Resolve agent address from token_id
        agent_id = None
        if oags_identity and self.is_online:
            agent_id = self.resolve_agent_address(oags_identity)
        if not agent_id:
            agent_id = f"token_{oags_identity}" if oags_identity else "unknown"

        now = datetime.now(timezone.utc).isoformat()

        z3_ok = bool(attestation.get("z3_verified", False))

        score = DOFTrustScore(
            agent_id=agent_id,
            governance_score=round(float(metrics.get("GCR", 0.0)), 4),
            stability_score=round(float(metrics.get("SS", 0.0)), 4),
            ast_score=round(float(attestation.get("ast_score", 0.0)), 4),
            adversarial_score=round(float(metrics.get("ACR", 0.0)), 4),
            provider_fragility=round(float(metrics.get("PFI", 0.0)), 4),
            retry_pressure=round(float(metrics.get("RP", 0.0)), 4),
            supervisor_strictness=round(float(metrics.get("SSR", 0.0)), 4),
            certificate_hash=attestation.get("certificate_hash", ""),
            on_chain_tx=attestation.get("on_chain_tx", ""),
            on_chain_block=int(attestation.get("on_chain_block", 0)),
            z3_verified=z3_ok,
            z3_theorems_passed=4 if z3_ok else 0,
            governance_status=attestation.get("governance_status", "UNKNOWN"),
            calculated_at=now,
            snapshot_data=attestation,
        )

        self._log_score(score, "publish")

        if not self._offline and self._engine is not None:
            try:
                self._insert_dof_score(score)
                logger.info(f"Published DOF score for {agent_id[:16]}...")
            except Exception as e:
                logger.error(f"Failed to publish DOF score: {e}")
                raise

        return score

    def _publish_legacy(self, agent_id: str, metrics: dict = None,
                        snapshot_data: dict = None) -> DOFTrustScore:
        """Legacy API: publish_trust_score(agent_id, metrics, snapshot_data)."""
        metrics = metrics or {}
        now = datetime.now(timezone.utc).isoformat()

        score = DOFTrustScore(
            agent_id=agent_id,
            governance_score=round(float(metrics.get("GCR", 0.0)), 4),
            stability_score=round(float(metrics.get("SS", 0.0)), 4),
            ast_score=round(float(metrics.get("AST_score", metrics.get("ast_score", 0.0))), 4),
            adversarial_score=round(float(metrics.get("ACR", 0.0)), 4),
            provider_fragility=round(float(metrics.get("PFI", 0.0)), 4),
            retry_pressure=round(float(metrics.get("RP", 0.0)), 4),
            supervisor_strictness=round(float(metrics.get("SSR", 0.0)), 4),
            certificate_hash="",
            on_chain_tx="",
            on_chain_block=0,
            z3_verified=False,
            z3_theorems_passed=0,
            governance_status="UNKNOWN",
            calculated_at=now,
            snapshot_data=snapshot_data or metrics,
        )

        self._log_score(score, "publish")

        if not self._offline and self._engine is not None:
            try:
                self._insert_dof_score(score)
                logger.info(f"Published DOF score for {agent_id[:16]}...")
            except Exception as e:
                logger.error(f"Failed to publish DOF score: {e}")
                raise

        return score

    def get_trust_score(self, agent_id: str) -> DOFTrustScore | None:
        """Retrieve the latest DOF trust score for an agent."""
        if self._offline or self._engine is None:
            logger.warning("Cannot query DOF scores in offline mode")
            return None

        try:
            with Session(self._engine) as session:
                row = session.execute(
                    text(
                        "SELECT agent_id, governance_score, stability_score, "
                        "ast_score, adversarial_score, provider_fragility, "
                        "retry_pressure, supervisor_strictness, certificate_hash, "
                        "on_chain_tx, on_chain_block, z3_verified, "
                        "z3_theorems_passed, governance_status, calculated_at, "
                        "snapshot_data "
                        "FROM dof_trust_scores "
                        "WHERE agent_id = :aid "
                        "ORDER BY calculated_at DESC LIMIT 1"
                    ),
                    {"aid": agent_id},
                ).fetchone()

                if row is None:
                    return None

                return self._row_to_score(row)
        except Exception as e:
            logger.error(f"Failed to get DOF score: {e}")
            return None

    def get_all_verified_agents(self) -> list[DOFTrustScore]:
        """Retrieve latest score for agents with governance_score == 1.0."""
        if self._offline or self._engine is None:
            return []

        try:
            with Session(self._engine) as session:
                # Subquery for latest per agent, then filter
                rows = session.execute(
                    text(
                        "SELECT DISTINCT ON (agent_id) "
                        "agent_id, governance_score, stability_score, "
                        "ast_score, adversarial_score, provider_fragility, "
                        "retry_pressure, supervisor_strictness, certificate_hash, "
                        "on_chain_tx, on_chain_block, z3_verified, "
                        "z3_theorems_passed, governance_status, calculated_at, "
                        "snapshot_data "
                        "FROM dof_trust_scores "
                        "WHERE governance_score = 1.0 "
                        "ORDER BY agent_id, calculated_at DESC"
                    )
                ).fetchall()

                return [self._row_to_score(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get verified agents: {e}")
            return []

    def get_history(self, agent_id: str) -> list[DOFTrustScore]:
        """Retrieve full score history for an agent (newest first)."""
        if self._offline or self._engine is None:
            return []

        try:
            with Session(self._engine) as session:
                rows = session.execute(
                    text(
                        "SELECT agent_id, governance_score, stability_score, "
                        "ast_score, adversarial_score, provider_fragility, "
                        "retry_pressure, supervisor_strictness, certificate_hash, "
                        "on_chain_tx, on_chain_block, z3_verified, "
                        "z3_theorems_passed, governance_status, calculated_at, "
                        "snapshot_data "
                        "FROM dof_trust_scores "
                        "WHERE agent_id = :aid "
                        "ORDER BY calculated_at DESC"
                    ),
                    {"aid": agent_id},
                ).fetchall()

                return [self._row_to_score(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def get_latest_scores(self) -> list[DOFTrustScore]:
        """Retrieve latest DOF score for every agent."""
        if self._offline or self._engine is None:
            return []

        try:
            with Session(self._engine) as session:
                rows = session.execute(
                    text(
                        "SELECT DISTINCT ON (agent_id) "
                        "agent_id, governance_score, stability_score, "
                        "ast_score, adversarial_score, provider_fragility, "
                        "retry_pressure, supervisor_strictness, certificate_hash, "
                        "on_chain_tx, on_chain_block, z3_verified, "
                        "z3_theorems_passed, governance_status, calculated_at, "
                        "snapshot_data "
                        "FROM dof_trust_scores "
                        "ORDER BY agent_id, calculated_at DESC"
                    )
                ).fetchall()

                return [self._row_to_score(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get latest scores: {e}")
            return []

    def revoke_verification(self, agent_id: str, reason: str = "") -> bool:
        """Insert a zero-score row to revoke trust for an agent."""
        if self._offline or self._engine is None:
            logger.warning("Cannot revoke in offline mode")
            return False

        try:
            now = datetime.now(timezone.utc).isoformat()
            score = DOFTrustScore(
                agent_id=agent_id,
                governance_score=0, stability_score=0, ast_score=0,
                adversarial_score=0, provider_fragility=1.0,
                retry_pressure=1.0, supervisor_strictness=1.0,
                certificate_hash="", on_chain_tx="", on_chain_block=0,
                z3_verified=False, z3_theorems_passed=0,
                governance_status="REVOKED",
                calculated_at=now,
                snapshot_data={"revoked": True, "reason": reason},
            )
            self._insert_dof_score(score)
            self._log_score(score, "revoke")
            logger.info(f"Revoked verification for {agent_id[:16]}... reason={reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke verification: {e}")
            return False

    # ─── Internals ──────────────────────────────────────────────────

    def _insert_dof_score(self, score: DOFTrustScore):
        """INSERT into dof_trust_scores (append-only history)."""
        with Session(self._engine) as session:
            session.execute(
                text(
                    "INSERT INTO dof_trust_scores "
                    "(id, agent_id, governance_score, stability_score, "
                    "ast_score, adversarial_score, provider_fragility, "
                    "retry_pressure, supervisor_strictness, certificate_hash, "
                    "on_chain_tx, on_chain_block, z3_verified, "
                    "z3_theorems_passed, governance_status, calculated_at, "
                    "snapshot_data) "
                    "VALUES (:id, :aid, :gcr, :ss, :ast, :acr, :pfi, "
                    ":rp, :ssr, :cert, :tx, :blk, :z3, :z3n, :gs, :ts, :snap)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "aid": score.agent_id,
                    "gcr": score.governance_score,
                    "ss": score.stability_score,
                    "ast": score.ast_score,
                    "acr": score.adversarial_score,
                    "pfi": score.provider_fragility,
                    "rp": score.retry_pressure,
                    "ssr": score.supervisor_strictness,
                    "cert": score.certificate_hash,
                    "tx": score.on_chain_tx,
                    "blk": score.on_chain_block,
                    "z3": score.z3_verified,
                    "z3n": score.z3_theorems_passed,
                    "gs": score.governance_status,
                    "ts": score.calculated_at,
                    "snap": json.dumps(score.snapshot_data, default=str),
                },
            )
            session.commit()

    @staticmethod
    def _row_to_score(row) -> DOFTrustScore:
        """Convert a DB row tuple to DOFTrustScore."""
        snapshot = row[15] if row[15] else {}
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = {}

        return DOFTrustScore(
            agent_id=row[0],
            governance_score=float(row[1] or 0),
            stability_score=float(row[2] or 0),
            ast_score=float(row[3] or 0),
            adversarial_score=float(row[4] or 0),
            provider_fragility=float(row[5] or 0),
            retry_pressure=float(row[6] or 0),
            supervisor_strictness=float(row[7] or 0),
            certificate_hash=str(row[8] or ""),
            on_chain_tx=str(row[9] or ""),
            on_chain_block=int(row[10] or 0),
            z3_verified=bool(row[11]),
            z3_theorems_passed=int(row[12] or 0),
            governance_status=str(row[13] or "UNKNOWN"),
            calculated_at=str(row[14] or ""),
            snapshot_data=snapshot,
        )

    def _log_score(self, score: DOFTrustScore, action: str):
        """Log DOF trust score event to logs/enigma_bridge.jsonl."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "enigma_bridge.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "agent_id": score.agent_id,
            "governance_score": score.governance_score,
            "stability_score": score.stability_score,
            "ast_score": score.ast_score,
            "adversarial_score": score.adversarial_score,
            "z3_verified": score.z3_verified,
            "governance_status": score.governance_status,
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log enigma bridge event: {e}")

    # ─── Legacy compat ──────────────────────────────────────────────

    @staticmethod
    def map_metrics(metrics: dict) -> dict:
        """Legacy: Map DOF metrics to old trust_scores columns.

        Kept for backward compatibility with scripts that call map_metrics().
        """
        ss = metrics.get("SS", metrics.get("stability_score", 0.0))
        gcr = metrics.get("GCR", metrics.get("governance_compliance_rate", 0.0))
        pfi = metrics.get("PFI", metrics.get("provider_failure_index", 0.0))
        ast = metrics.get("AST_score", metrics.get("ast_score", 0.0))
        acr = metrics.get("ACR", metrics.get("adversarial_compliance_rate", 0.0))

        return {
            "overall_score": round(float(ss), 4),
            "volume_score": 0.0,
            "proxy_score": round(1.0 - float(pfi), 4),
            "uptime_score": round(float(gcr), 4),
            "oz_match_score": round(float(ast), 4),
            "community_score": round(float(acr), 4),
        }
