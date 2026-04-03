"""
EnigmaBridge — DOF-MESH → Enigma Trust Score Publisher.

Publishes DOF verification results to the Enigma Scanner database
(Supabase/PostgreSQL in production, SQLite for tests, offline mode as fallback).

Offline mode activates automatically when ENIGMA_DATABASE_URL is not set.
All operations are logged to logs/enigma_bridge.jsonl for audit.

Usage:
    bridge = EnigmaBridge()

    # New API (attestation dict from OracleBridge):
    score = bridge.publish_trust_score(
        attestation={"metrics": {"SS": 0.92, "GCR": 1.0, "PFI": 0.05},
                     "governance_status": "COMPLIANT", "z3_verified": True},
        oags_identity="1687",
    )

    # Legacy API (metrics dict + agent_id):
    score = bridge.publish_trust_score(
        agent_id="apex-1687",
        metrics={"SS": 0.92, "GCR": 1.0, "PFI": 0.05},
    )
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("dof.enigma_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_LOG = os.path.join(BASE_DIR, "logs", "enigma_bridge.jsonl")


# ── DOFTrustScore dataclass ───────────────────────────────────────────────────

@dataclass
class DOFTrustScore:
    """DOF-derived trust score record sent to Enigma Scanner."""
    agent_id: str
    governance_score: float
    stability_score: float
    ast_score: float
    adversarial_score: float
    provider_fragility: float
    retry_pressure: float
    supervisor_strictness: float
    certificate_hash: str
    on_chain_tx: str
    on_chain_block: int
    z3_verified: bool
    z3_theorems_passed: int
    governance_status: str
    calculated_at: str
    snapshot_data: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# Backward-compat alias
TrustScore = DOFTrustScore


# ── Audit logger ──────────────────────────────────────────────────────────────

def _log(entry: dict) -> None:
    os.makedirs(os.path.dirname(JSONL_LOG), exist_ok=True)
    try:
        with open(JSONL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.error(f"enigma_bridge audit write failed: {e}")


# ── EnigmaBridge ──────────────────────────────────────────────────────────────

class EnigmaBridge:
    """
    Publishes DOF trust scores to Enigma Scanner.

    Modes:
      - Online  (connection_url or ENIGMA_DATABASE_URL set): reads/writes SQLAlchemy
      - Offline (no DB URL): in-memory only, returns computed score, logs to JSONL
    """

    def __init__(self, connection_url: Optional[str] = None):
        url = connection_url or os.environ.get("ENIGMA_DATABASE_URL", "")
        self._offline = not bool(url)
        self._engine = None

        if not self._offline:
            try:
                from sqlalchemy import create_engine
                self._engine = create_engine(url)
            except Exception as e:
                logger.warning(f"EnigmaBridge DB init failed: {e} — falling back to offline")
                self._offline = True

    @property
    def is_online(self) -> bool:
        return not self._offline

    # ── map_metrics ───────────────────────────────────────────────────────────

    @staticmethod
    def map_metrics(metrics: dict) -> dict:
        """
        Map DOF metric keys (SS, GCR, PFI, ACR, AST_score) to Enigma schema fields.

        Mapping:
            SS         → overall_score
            GCR        → uptime_score
            1 - PFI    → proxy_score      (lower fragility = higher proxy reliability)
            AST_score  → oz_match_score
            ACR        → community_score
            (default)  → volume_score = 0.0
        """
        return {
            "overall_score":    metrics.get("SS", 0.0),
            "uptime_score":     metrics.get("GCR", 0.0),
            "proxy_score":      1.0 - metrics.get("PFI", 0.0),
            "oz_match_score":   metrics.get("AST_score", 0.0),
            "community_score":  metrics.get("ACR", 0.0),
            "volume_score":     metrics.get("volume_score", 0.0),
        }

    # ── publish_trust_score ───────────────────────────────────────────────────

    def publish_trust_score(
        self,
        attestation: Optional[dict] = None,
        oags_identity: Optional[str] = None,
        agent_id: Optional[str] = None,
        metrics: Optional[dict] = None,
    ) -> DOFTrustScore:
        """
        Publish a DOF trust score to Enigma Scanner.

        Supports two calling conventions:
          New API:    publish_trust_score(attestation={...}, oags_identity="1687")
          Legacy API: publish_trust_score(agent_id="apex", metrics={...})
        """
        # ── Normalise inputs ──────────────────────────────────────────────────
        if attestation is not None:
            # New API — unpack attestation dict
            raw_metrics = attestation.get("metrics", {})
            governance_status = attestation.get("governance_status", "UNKNOWN")
            z3_verified = bool(attestation.get("z3_verified", False))
            ast_score = float(attestation.get("ast_score", 0.0))
            certificate_hash = attestation.get("certificate_hash", "")
            on_chain_tx = attestation.get("on_chain_tx", "")
            on_chain_block = int(attestation.get("on_chain_block", 0))
        else:
            # Legacy API — plain metrics dict
            raw_metrics = metrics or {}
            governance_status = "UNKNOWN"
            z3_verified = False
            ast_score = raw_metrics.get("AST_score", 0.0)
            certificate_hash = ""
            on_chain_tx = ""
            on_chain_block = 0

        # Resolve agent_id: oags_identity → DB lookup → fallback
        resolved_id = self._resolve_agent_id(agent_id, oags_identity)

        # Build score
        score = DOFTrustScore(
            agent_id=resolved_id,
            governance_score=float(raw_metrics.get("GCR", 0.0)),
            stability_score=float(raw_metrics.get("SS", 0.0)),
            ast_score=ast_score,
            adversarial_score=float(raw_metrics.get("ACR", 0.0)),
            provider_fragility=float(raw_metrics.get("PFI", 0.0)),
            retry_pressure=float(raw_metrics.get("RP", 0.0)),
            supervisor_strictness=float(raw_metrics.get("SSR", 0.0)),
            certificate_hash=certificate_hash,
            on_chain_tx=on_chain_tx,
            on_chain_block=on_chain_block,
            z3_verified=z3_verified,
            z3_theorems_passed=4 if z3_verified else 0,
            governance_status=governance_status,
            calculated_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            snapshot_data=raw_metrics,
        )

        # Persist
        if not self._offline and self._engine is not None:
            self._save_to_db(score)
        else:
            logger.info(f"[offline] EnigmaBridge: score computed for {resolved_id}")

        # JSONL audit
        _log({
            "ts":               time.time(),
            "iso":              score.calculated_at,
            "action":           "publish",
            "agent_id":         score.agent_id,
            "governance_score": score.governance_score,
            "stability_score":  score.stability_score,
            "governance_status": score.governance_status,
            "z3_verified":      score.z3_verified,
            "certificate_hash": score.certificate_hash,
        })

        return score

    # ── read operations ───────────────────────────────────────────────────────

    def get_trust_score(self, agent_id: str) -> Optional[DOFTrustScore]:
        """Return the latest trust score for agent_id, or None if not found."""
        if self._offline or self._engine is None:
            return None
        return self._fetch_latest(agent_id)

    def get_history(self, agent_id: str) -> list[DOFTrustScore]:
        """Return all trust score records for agent_id, latest first."""
        if self._offline or self._engine is None:
            return []
        return self._fetch_history(agent_id)

    def get_all_verified_agents(self) -> list[DOFTrustScore]:
        """Return latest score for each agent, filtered to COMPLIANT."""
        if self._offline or self._engine is None:
            return []
        return self._fetch_all_verified()

    def get_latest_scores(self) -> list[DOFTrustScore]:
        """Return the most recent score entry per unique agent_id."""
        if self._offline or self._engine is None:
            return []
        return self._fetch_latest_scores()

    def revoke_verification(self, agent_id: str, reason: str) -> bool:
        """Mark agent as REVOKED (governance_score=0, status=REVOKED)."""
        if self._offline or self._engine is None:
            return False
        return self._revoke(agent_id, reason)

    def resolve_agent_address(self, token_id: int) -> Optional[str]:
        """Look up EVM address for an ERC-8004 token_id from agents table."""
        if self._offline or self._engine is None:
            return None
        return self._resolve_address(token_id)

    # ── internal DB helpers ───────────────────────────────────────────────────

    def _resolve_agent_id(self, agent_id: Optional[str], oags_identity: Optional[str]) -> str:
        if agent_id:
            return agent_id
        if oags_identity:
            # Try DB lookup first
            try:
                token_id = int(oags_identity)
                addr = self.resolve_agent_address(token_id)
                if addr:
                    return addr
            except (ValueError, Exception):
                pass
            return f"token_{oags_identity}"
        return f"agent_{uuid.uuid4().hex[:8]}"

    def _save_to_db(self, score: DOFTrustScore) -> None:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            session.execute(text("""
                INSERT INTO dof_trust_scores (
                    id, agent_id, governance_score, stability_score, ast_score,
                    adversarial_score, provider_fragility, retry_pressure,
                    supervisor_strictness, certificate_hash, on_chain_tx,
                    on_chain_block, z3_verified, z3_theorems_passed,
                    governance_status, calculated_at, snapshot_data
                ) VALUES (
                    :id, :agent_id, :governance_score, :stability_score, :ast_score,
                    :adversarial_score, :provider_fragility, :retry_pressure,
                    :supervisor_strictness, :certificate_hash, :on_chain_tx,
                    :on_chain_block, :z3_verified, :z3_theorems_passed,
                    :governance_status, :calculated_at, :snapshot_data
                )
            """), {
                "id":                   score.id,
                "agent_id":             score.agent_id,
                "governance_score":     score.governance_score,
                "stability_score":      score.stability_score,
                "ast_score":            score.ast_score,
                "adversarial_score":    score.adversarial_score,
                "provider_fragility":   score.provider_fragility,
                "retry_pressure":       score.retry_pressure,
                "supervisor_strictness": score.supervisor_strictness,
                "certificate_hash":     score.certificate_hash,
                "on_chain_tx":          score.on_chain_tx,
                "on_chain_block":       score.on_chain_block,
                "z3_verified":          int(score.z3_verified),
                "z3_theorems_passed":   score.z3_theorems_passed,
                "governance_status":    score.governance_status,
                "calculated_at":        score.calculated_at,
                "snapshot_data":        json.dumps(score.snapshot_data),
            })
            session.commit()

    def _row_to_score(self, row) -> DOFTrustScore:
        snap = row.snapshot_data
        if isinstance(snap, str):
            try:
                snap = json.loads(snap)
            except Exception:
                snap = {}
        return DOFTrustScore(
            id=row.id,
            agent_id=row.agent_id,
            governance_score=float(row.governance_score or 0),
            stability_score=float(row.stability_score or 0),
            ast_score=float(row.ast_score or 0),
            adversarial_score=float(row.adversarial_score or 0),
            provider_fragility=float(row.provider_fragility or 0),
            retry_pressure=float(row.retry_pressure or 0),
            supervisor_strictness=float(row.supervisor_strictness or 0),
            certificate_hash=row.certificate_hash or "",
            on_chain_tx=row.on_chain_tx or "",
            on_chain_block=int(row.on_chain_block or 0),
            z3_verified=bool(row.z3_verified),
            z3_theorems_passed=int(row.z3_theorems_passed or 0),
            governance_status=row.governance_status or "UNKNOWN",
            calculated_at=row.calculated_at or "",
            snapshot_data=snap,
        )

    def _fetch_latest(self, agent_id: str) -> Optional[DOFTrustScore]:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            row = session.execute(text(
                "SELECT * FROM dof_trust_scores WHERE agent_id = :aid "
                "ORDER BY calculated_at DESC LIMIT 1"
            ), {"aid": agent_id}).fetchone()
        return self._row_to_score(row) if row else None

    def _fetch_history(self, agent_id: str) -> list[DOFTrustScore]:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            rows = session.execute(text(
                "SELECT * FROM dof_trust_scores WHERE agent_id = :aid "
                "ORDER BY calculated_at DESC"
            ), {"aid": agent_id}).fetchall()
        return [self._row_to_score(r) for r in rows]

    def _fetch_all_verified(self) -> list[DOFTrustScore]:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            rows = session.execute(text(
                "SELECT * FROM dof_trust_scores WHERE governance_status = 'COMPLIANT' "
                "ORDER BY calculated_at DESC"
            )).fetchall()
        return [self._row_to_score(r) for r in rows]

    def _fetch_latest_scores(self) -> list[DOFTrustScore]:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            rows = session.execute(text(
                "SELECT * FROM dof_trust_scores ORDER BY calculated_at DESC"
            )).fetchall()
        # One per agent_id
        seen: set[str] = set()
        result = []
        for r in rows:
            if r.agent_id not in seen:
                seen.add(r.agent_id)
                result.append(self._row_to_score(r))
        return result

    def _revoke(self, agent_id: str, reason: str) -> bool:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        try:
            ts = time.strftime("%Y-%m-%dT%H:%M:%S")
            with Session(self._engine) as session:
                session.execute(text(
                    "UPDATE dof_trust_scores SET governance_score = 0.0, "
                    "governance_status = 'REVOKED', calculated_at = :ts "
                    "WHERE agent_id = :aid"
                ), {"ts": ts, "aid": agent_id})
                session.commit()
            _log({"ts": time.time(), "action": "revoke", "agent_id": agent_id, "reason": reason})
            return True
        except Exception as e:
            logger.error(f"revoke_verification failed: {e}")
            return False

    def _resolve_address(self, token_id: int) -> Optional[str]:
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        try:
            with Session(self._engine) as session:
                row = session.execute(text(
                    "SELECT address FROM agents WHERE token_id = :tid"
                ), {"tid": token_id}).fetchone()
            return row.address if row else None
        except Exception as e:
            logger.debug(f"resolve_agent_address({token_id}) failed: {e}")
            return None
