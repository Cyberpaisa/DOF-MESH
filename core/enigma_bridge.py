"""
Enigma Bridge — DOF attestations → erc-8004scan.xyz trust_scores via Supabase.

Maps DOF governance metrics to the Enigma Scanner trust_scores table:
    SS  → overall_score     (stability score)
    GCR → uptime_score      (governance compliance rate)
    1-PFI → proxy_score     (inverted provider failure index)
    AST → oz_match_score    (AST verifier score)
    ACR → community_score   (adversarial compliance rate)

IMPORTANT: trust_scores table already exists in enigma-dev.
           Never use create_all() in production — only INSERT/UPDATE.
           Connection strings come from ENIGMA_DATABASE_URL env var.

Usage:
    from core.enigma_bridge import EnigmaBridge

    bridge = EnigmaBridge()
    bridge.publish_trust_score(agent_id, metrics, snapshot_data)
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
# TrustScore dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TrustScore:
    """Mirrors the trust_scores table in enigma-dev Supabase."""
    agent_id: str
    overall_score: float     # SS
    volume_score: float      # 0.0 (not mapped from DOF)
    proxy_score: float       # 1 - PFI
    uptime_score: float      # GCR
    oz_match_score: float    # AST verifier score
    community_score: float   # ACR (adversarial compliance rate)
    calculated_at: str       # ISO format
    snapshot_data: dict      # Full metrics snapshot for audit


# ─────────────────────────────────────────────────────────────────────
# EnigmaBridge
# ─────────────────────────────────────────────────────────────────────

class EnigmaBridge:
    """Bridge between DOF attestations and erc-8004scan.xyz trust_scores.

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
                # Test connection
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

    @staticmethod
    def map_metrics(metrics: dict) -> dict:
        """Map DOF metrics to trust_scores columns.

        Args:
            metrics: Dict with keys SS, GCR, PFI, plus optional AST_score, ACR.

        Returns:
            Dict with trust_scores column names and values.
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

    def publish_trust_score(self, agent_id: str, metrics: dict,
                            snapshot_data: dict = None) -> TrustScore:
        """Publish DOF metrics as a trust score to Enigma database.

        Args:
            agent_id: Agent identity hash (from OAGSIdentity).
            metrics: DOF metrics dict (SS, GCR, PFI, AST_score, ACR).
            snapshot_data: Optional full metrics snapshot for audit.

        Returns:
            TrustScore dataclass with published values.
        """
        mapped = self.map_metrics(metrics)
        now = datetime.now(timezone.utc).isoformat()

        score = TrustScore(
            agent_id=agent_id,
            overall_score=mapped["overall_score"],
            volume_score=mapped["volume_score"],
            proxy_score=mapped["proxy_score"],
            uptime_score=mapped["uptime_score"],
            oz_match_score=mapped["oz_match_score"],
            community_score=mapped["community_score"],
            calculated_at=now,
            snapshot_data=snapshot_data or metrics,
        )

        # Always log to JSONL
        self._log_score(score, "publish")

        # Write to database if online
        if not self._offline and self._engine is not None:
            try:
                self._upsert_trust_score(score)
                logger.info(f"Published trust score for {agent_id[:16]}...")
            except Exception as e:
                logger.error(f"Failed to publish trust score: {e}")
                raise

        return score

    def get_trust_score(self, agent_id: str) -> TrustScore | None:
        """Retrieve the latest trust score for an agent.

        Args:
            agent_id: Agent identity hash.

        Returns:
            TrustScore or None if not found.
        """
        if self._offline or self._engine is None:
            logger.warning("Cannot query trust scores in offline mode")
            return None

        try:
            with Session(self._engine) as session:
                row = session.execute(
                    text(
                        "SELECT agent_id, overall_score, volume_score, proxy_score, "
                        "uptime_score, oz_match_score, community_score, "
                        "calculated_at, snapshot_data "
                        "FROM trust_scores "
                        "WHERE agent_id = :aid "
                        "ORDER BY calculated_at DESC LIMIT 1"
                    ),
                    {"aid": agent_id},
                ).fetchone()

                if row is None:
                    return None

                snapshot = row[8] if row[8] else {}
                if isinstance(snapshot, str):
                    try:
                        snapshot = json.loads(snapshot)
                    except (json.JSONDecodeError, TypeError):
                        snapshot = {}

                return TrustScore(
                    agent_id=row[0],
                    overall_score=float(row[1] or 0),
                    volume_score=float(row[2] or 0),
                    proxy_score=float(row[3] or 0),
                    uptime_score=float(row[4] or 0),
                    oz_match_score=float(row[5] or 0),
                    community_score=float(row[6] or 0),
                    calculated_at=str(row[7] or ""),
                    snapshot_data=snapshot,
                )
        except Exception as e:
            logger.error(f"Failed to get trust score: {e}")
            return None

    def get_all_verified_agents(self) -> list[TrustScore]:
        """Retrieve all agents with overall_score >= 0.7.

        Returns:
            List of TrustScore for verified agents.
        """
        if self._offline or self._engine is None:
            logger.warning("Cannot query trust scores in offline mode")
            return []

        try:
            with Session(self._engine) as session:
                rows = session.execute(
                    text(
                        "SELECT DISTINCT ON (agent_id) "
                        "agent_id, overall_score, volume_score, proxy_score, "
                        "uptime_score, oz_match_score, community_score, "
                        "calculated_at, snapshot_data "
                        "FROM trust_scores "
                        "WHERE overall_score >= 0.7 "
                        "ORDER BY agent_id, calculated_at DESC"
                    )
                ).fetchall()

                results = []
                for row in rows:
                    snapshot = row[8] if row[8] else {}
                    if isinstance(snapshot, str):
                        try:
                            snapshot = json.loads(snapshot)
                        except (json.JSONDecodeError, TypeError):
                            snapshot = {}
                    results.append(TrustScore(
                        agent_id=row[0],
                        overall_score=float(row[1] or 0),
                        volume_score=float(row[2] or 0),
                        proxy_score=float(row[3] or 0),
                        uptime_score=float(row[4] or 0),
                        oz_match_score=float(row[5] or 0),
                        community_score=float(row[6] or 0),
                        calculated_at=str(row[7] or ""),
                        snapshot_data=snapshot,
                    ))
                return results
        except Exception as e:
            logger.error(f"Failed to get verified agents: {e}")
            return []

    def revoke_verification(self, agent_id: str, reason: str = "") -> bool:
        """Set all scores to 0 for an agent (revoke trust).

        Args:
            agent_id: Agent identity hash.
            reason: Reason for revocation (logged).

        Returns:
            True if revoked, False on failure or offline.
        """
        if self._offline or self._engine is None:
            logger.warning("Cannot revoke in offline mode")
            return False

        try:
            now = datetime.now(timezone.utc).isoformat()
            with Session(self._engine) as session:
                session.execute(
                    text(
                        "INSERT INTO trust_scores "
                        "(id, agent_id, overall_score, volume_score, proxy_score, "
                        "uptime_score, oz_match_score, community_score, "
                        "calculated_at, snapshot_data) "
                        "VALUES (:id, :aid, 0, 0, 0, 0, 0, 0, :ts, :snap)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "aid": agent_id,
                        "ts": now,
                        "snap": json.dumps({"revoked": True, "reason": reason}),
                    },
                )
                session.commit()

            self._log_score(
                TrustScore(
                    agent_id=agent_id,
                    overall_score=0, volume_score=0, proxy_score=0,
                    uptime_score=0, oz_match_score=0, community_score=0,
                    calculated_at=now,
                    snapshot_data={"revoked": True, "reason": reason},
                ),
                "revoke",
            )
            logger.info(f"Revoked verification for {agent_id[:16]}... reason={reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke verification: {e}")
            return False

    def _upsert_trust_score(self, score: TrustScore):
        """INSERT a new trust_scores row (append-only history)."""
        with Session(self._engine) as session:
            session.execute(
                text(
                    "INSERT INTO trust_scores "
                    "(id, agent_id, overall_score, volume_score, proxy_score, "
                    "uptime_score, oz_match_score, community_score, "
                    "calculated_at, snapshot_data) "
                    "VALUES (:id, :aid, :os, :vs, :ps, :us, :ozs, :cs, :ts, :snap)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "aid": score.agent_id,
                    "os": score.overall_score,
                    "vs": score.volume_score,
                    "ps": score.proxy_score,
                    "us": score.uptime_score,
                    "ozs": score.oz_match_score,
                    "cs": score.community_score,
                    "ts": score.calculated_at,
                    "snap": json.dumps(score.snapshot_data, default=str),
                },
            )
            session.commit()

    def _log_score(self, score: TrustScore, action: str):
        """Log trust score event to logs/enigma_bridge.jsonl."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "enigma_bridge.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "agent_id": score.agent_id,
            "overall_score": score.overall_score,
            "proxy_score": score.proxy_score,
            "uptime_score": score.uptime_score,
            "oz_match_score": score.oz_match_score,
            "community_score": score.community_score,
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log enigma bridge event: {e}")
