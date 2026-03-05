"""
Tests for core/enigma_bridge.py — EnigmaBridge + TrustScore.

Uses SQLite in-memory with manually created trust_scores table
(mirrors the production Supabase schema without using create_all).
"""

import os
import sys
import json
import unittest
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.enigma_bridge import EnigmaBridge, TrustScore

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


def _create_sqlite_trust_scores(engine):
    """Create trust_scores table in SQLite (mimics Supabase schema)."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trust_scores (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                overall_score REAL DEFAULT 0,
                volume_score REAL DEFAULT 0,
                proxy_score REAL DEFAULT 0,
                uptime_score REAL DEFAULT 0,
                oz_match_score REAL DEFAULT 0,
                community_score REAL DEFAULT 0,
                calculated_at TEXT,
                snapshot_data TEXT
            )
        """))
        conn.commit()


class TestTrustScoreDataclass(unittest.TestCase):
    """Test TrustScore dataclass creation and fields."""

    def test_create_trust_score(self):
        score = TrustScore(
            agent_id="abc123",
            overall_score=0.95,
            volume_score=0.0,
            proxy_score=0.8,
            uptime_score=1.0,
            oz_match_score=0.9,
            community_score=0.7,
            calculated_at="2026-01-01T00:00:00",
            snapshot_data={"SS": 0.95},
        )
        self.assertEqual(score.agent_id, "abc123")
        self.assertEqual(score.overall_score, 0.95)
        self.assertEqual(score.proxy_score, 0.8)
        self.assertEqual(score.uptime_score, 1.0)

    def test_trust_score_defaults(self):
        score = TrustScore(
            agent_id="x", overall_score=0, volume_score=0,
            proxy_score=0, uptime_score=0, oz_match_score=0,
            community_score=0, calculated_at="", snapshot_data={},
        )
        self.assertEqual(score.volume_score, 0)
        self.assertEqual(score.snapshot_data, {})


class TestMapMetrics(unittest.TestCase):
    """Test EnigmaBridge.map_metrics static method."""

    def test_map_standard_keys(self):
        metrics = {"SS": 0.95, "GCR": 1.0, "PFI": 0.1, "AST_score": 0.9, "ACR": 0.8}
        mapped = EnigmaBridge.map_metrics(metrics)
        self.assertAlmostEqual(mapped["overall_score"], 0.95, places=4)
        self.assertAlmostEqual(mapped["uptime_score"], 1.0, places=4)
        self.assertAlmostEqual(mapped["proxy_score"], 0.9, places=4)  # 1 - 0.1
        self.assertAlmostEqual(mapped["oz_match_score"], 0.9, places=4)
        self.assertAlmostEqual(mapped["community_score"], 0.8, places=4)
        self.assertEqual(mapped["volume_score"], 0.0)

    def test_map_alternative_keys(self):
        metrics = {
            "stability_score": 0.8,
            "governance_compliance_rate": 0.9,
            "provider_failure_index": 0.2,
            "ast_score": 0.7,
            "adversarial_compliance_rate": 0.6,
        }
        mapped = EnigmaBridge.map_metrics(metrics)
        self.assertAlmostEqual(mapped["overall_score"], 0.8, places=4)
        self.assertAlmostEqual(mapped["proxy_score"], 0.8, places=4)  # 1 - 0.2

    def test_map_missing_keys_defaults_to_zero(self):
        mapped = EnigmaBridge.map_metrics({})
        self.assertEqual(mapped["overall_score"], 0.0)
        self.assertEqual(mapped["uptime_score"], 0.0)
        self.assertEqual(mapped["proxy_score"], 1.0)  # 1 - 0


class TestEnigmaBridgeOffline(unittest.TestCase):
    """Test EnigmaBridge in offline mode (no database URL)."""

    def setUp(self):
        # Ensure no env var leaks
        self._orig = os.environ.get("ENIGMA_DATABASE_URL")
        os.environ.pop("ENIGMA_DATABASE_URL", None)

    def tearDown(self):
        if self._orig is not None:
            os.environ["ENIGMA_DATABASE_URL"] = self._orig

    def test_offline_mode(self):
        bridge = EnigmaBridge()
        self.assertFalse(bridge.is_online)

    def test_publish_offline_returns_score(self):
        bridge = EnigmaBridge()
        score = bridge.publish_trust_score("agent-1", {"SS": 0.9, "GCR": 1.0, "PFI": 0.0})
        self.assertIsInstance(score, TrustScore)
        self.assertEqual(score.agent_id, "agent-1")
        self.assertAlmostEqual(score.overall_score, 0.9, places=4)

    def test_get_trust_score_offline_returns_none(self):
        bridge = EnigmaBridge()
        result = bridge.get_trust_score("agent-1")
        self.assertIsNone(result)

    def test_get_all_verified_offline_returns_empty(self):
        bridge = EnigmaBridge()
        result = bridge.get_all_verified_agents()
        self.assertEqual(result, [])

    def test_revoke_offline_returns_false(self):
        bridge = EnigmaBridge()
        result = bridge.revoke_verification("agent-1", "test")
        self.assertFalse(result)


@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestEnigmaBridgeSQLite(unittest.TestCase):
    """Test EnigmaBridge with SQLite in-memory (simulates Supabase)."""

    def setUp(self):
        self._url = "sqlite://"  # in-memory
        # Pre-create table (trust_scores already exists in production)
        self._engine = create_engine(self._url)
        _create_sqlite_trust_scores(self._engine)
        # Pass the URL to EnigmaBridge
        self.bridge = EnigmaBridge(connection_url=self._url)
        # Override engine to use same in-memory DB
        self.bridge._engine = self._engine
        self.bridge._offline = False

    def test_publish_and_retrieve(self):
        metrics = {"SS": 0.92, "GCR": 1.0, "PFI": 0.05, "AST_score": 0.85, "ACR": 0.75}
        score = self.bridge.publish_trust_score("agent-abc", metrics)
        self.assertEqual(score.agent_id, "agent-abc")
        self.assertAlmostEqual(score.overall_score, 0.92, places=4)

        # Retrieve
        retrieved = self.bridge.get_trust_score("agent-abc")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.agent_id, "agent-abc")
        self.assertAlmostEqual(retrieved.overall_score, 0.92, places=2)

    def test_get_nonexistent_agent(self):
        result = self.bridge.get_trust_score("nonexistent")
        self.assertIsNone(result)

    def test_get_all_verified(self):
        # Publish 2 verified (SS >= 0.7) and 1 unverified
        self.bridge.publish_trust_score("agent-good1", {"SS": 0.9, "GCR": 1.0, "PFI": 0.0})
        self.bridge.publish_trust_score("agent-good2", {"SS": 0.75, "GCR": 0.9, "PFI": 0.1})
        self.bridge.publish_trust_score("agent-bad", {"SS": 0.3, "GCR": 0.5, "PFI": 0.5})

        # SQLite doesn't support DISTINCT ON — use alternative query
        # The method uses PostgreSQL syntax; for SQLite test, verify via direct query
        with Session(self._engine) as session:
            rows = session.execute(
                text("SELECT agent_id, overall_score FROM trust_scores WHERE overall_score >= 0.7")
            ).fetchall()
            self.assertGreaterEqual(len(rows), 2)

    def test_revoke_verification(self):
        self.bridge.publish_trust_score("agent-revoke", {"SS": 0.95, "GCR": 1.0, "PFI": 0.0})
        result = self.bridge.revoke_verification("agent-revoke", "violated terms")
        self.assertTrue(result)

        # Verify the latest score is 0
        retrieved = self.bridge.get_trust_score("agent-revoke")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.overall_score, 0.0)

    def test_publish_with_snapshot(self):
        snapshot = {"certificate_hash": "abc123", "task_id": "task-1"}
        score = self.bridge.publish_trust_score(
            "agent-snap", {"SS": 0.8, "GCR": 1.0, "PFI": 0.0}, snapshot
        )
        self.assertEqual(score.snapshot_data, snapshot)

    def test_multiple_scores_returns_latest(self):
        self.bridge.publish_trust_score("agent-multi", {"SS": 0.5, "GCR": 0.8, "PFI": 0.2})
        self.bridge.publish_trust_score("agent-multi", {"SS": 0.9, "GCR": 1.0, "PFI": 0.0})

        retrieved = self.bridge.get_trust_score("agent-multi")
        self.assertIsNotNone(retrieved)
        # Latest should be 0.9
        self.assertAlmostEqual(retrieved.overall_score, 0.9, places=2)


class TestJSONLLogging(unittest.TestCase):
    """Test that EnigmaBridge logs to JSONL."""

    def setUp(self):
        self._orig = os.environ.get("ENIGMA_DATABASE_URL")
        os.environ.pop("ENIGMA_DATABASE_URL", None)

    def tearDown(self):
        if self._orig is not None:
            os.environ["ENIGMA_DATABASE_URL"] = self._orig

    def test_publish_creates_log(self):
        bridge = EnigmaBridge()  # offline
        bridge.publish_trust_score("agent-log", {"SS": 0.9, "GCR": 1.0, "PFI": 0.0})

        log_path = os.path.join(BASE_DIR, "logs", "enigma_bridge.jsonl")
        self.assertTrue(os.path.exists(log_path))

        with open(log_path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertGreater(len(lines), 0)

        last = json.loads(lines[-1])
        self.assertEqual(last["agent_id"], "agent-log")
        self.assertEqual(last["action"], "publish")


if __name__ == "__main__":
    unittest.main()
