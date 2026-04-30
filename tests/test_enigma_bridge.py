"""
Tests for core/enigma_bridge.py — EnigmaBridge + DOFTrustScore.

Uses SQLite in-memory with manually created dof_trust_scores table
(mirrors the production Supabase schema without using create_all).
"""

import os
import sys
import json
import unittest
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

pytestmark = pytest.mark.optional

from core.enigma_bridge import EnigmaBridge, DOFTrustScore, TrustScore

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


def _create_sqlite_dof_tables(engine):
    """Create dof_trust_scores table in SQLite (mimics Supabase schema)."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dof_trust_scores (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                governance_score REAL DEFAULT 0,
                stability_score REAL DEFAULT 0,
                ast_score REAL DEFAULT 0,
                adversarial_score REAL DEFAULT 0,
                provider_fragility REAL DEFAULT 0,
                retry_pressure REAL DEFAULT 0,
                supervisor_strictness REAL DEFAULT 0,
                certificate_hash TEXT DEFAULT '',
                on_chain_tx TEXT DEFAULT '',
                on_chain_block INTEGER DEFAULT 0,
                z3_verified BOOLEAN DEFAULT 0,
                z3_theorems_passed INTEGER DEFAULT 0,
                governance_status TEXT DEFAULT 'UNKNOWN',
                calculated_at TEXT,
                snapshot_data TEXT
            )
        """))
        # For resolve_agent_address tests
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                address TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_id INTEGER,
                status TEXT DEFAULT 'VERIFIED'
            )
        """))
        conn.commit()


class TestDOFTrustScoreDataclass(unittest.TestCase):
    """Test DOFTrustScore dataclass creation and fields."""

    def test_create_dof_trust_score(self):
        score = DOFTrustScore(
            agent_id="0xabc123",
            governance_score=1.0,
            stability_score=0.92,
            ast_score=1.0,
            adversarial_score=0.85,
            provider_fragility=0.15,
            retry_pressure=0.10,
            supervisor_strictness=0.0,
            certificate_hash="0xcert",
            on_chain_tx="0xtx",
            on_chain_block=79657379,
            z3_verified=True,
            z3_theorems_passed=4,
            governance_status="COMPLIANT",
            calculated_at="2026-01-01T00:00:00",
            snapshot_data={"test": True},
        )
        self.assertEqual(score.agent_id, "0xabc123")
        self.assertEqual(score.governance_score, 1.0)
        self.assertEqual(score.stability_score, 0.92)
        self.assertTrue(score.z3_verified)
        self.assertEqual(score.z3_theorems_passed, 4)
        self.assertEqual(score.governance_status, "COMPLIANT")

    def test_backward_compat_alias(self):
        """TrustScore is an alias for DOFTrustScore."""
        self.assertIs(TrustScore, DOFTrustScore)

    def test_defaults_all_zero(self):
        score = DOFTrustScore(
            agent_id="x", governance_score=0, stability_score=0,
            ast_score=0, adversarial_score=0, provider_fragility=0,
            retry_pressure=0, supervisor_strictness=0,
            certificate_hash="", on_chain_tx="", on_chain_block=0,
            z3_verified=False, z3_theorems_passed=0,
            governance_status="UNKNOWN", calculated_at="",
            snapshot_data={},
        )
        self.assertEqual(score.governance_score, 0)
        self.assertFalse(score.z3_verified)
        self.assertEqual(score.snapshot_data, {})


class TestMapMetrics(unittest.TestCase):
    """Test EnigmaBridge.map_metrics legacy static method."""

    def test_map_standard_keys(self):
        metrics = {"SS": 0.95, "GCR": 1.0, "PFI": 0.1, "AST_score": 0.9, "ACR": 0.8}
        mapped = EnigmaBridge.map_metrics(metrics)
        self.assertAlmostEqual(mapped["overall_score"], 0.95, places=4)
        self.assertAlmostEqual(mapped["uptime_score"], 1.0, places=4)
        self.assertAlmostEqual(mapped["proxy_score"], 0.9, places=4)
        self.assertAlmostEqual(mapped["oz_match_score"], 0.9, places=4)
        self.assertAlmostEqual(mapped["community_score"], 0.8, places=4)
        self.assertEqual(mapped["volume_score"], 0.0)

    def test_map_missing_keys_defaults_to_zero(self):
        mapped = EnigmaBridge.map_metrics({})
        self.assertEqual(mapped["overall_score"], 0.0)
        self.assertEqual(mapped["proxy_score"], 1.0)  # 1 - 0


class TestEnigmaBridgeOffline(unittest.TestCase):
    """Test EnigmaBridge in offline mode (no database URL)."""

    def setUp(self):
        self._orig = os.environ.get("ENIGMA_DATABASE_URL")
        os.environ.pop("ENIGMA_DATABASE_URL", None)

    def tearDown(self):
        if self._orig is not None:
            os.environ["ENIGMA_DATABASE_URL"] = self._orig

    def test_offline_mode(self):
        bridge = EnigmaBridge()
        self.assertFalse(bridge.is_online)

    def test_publish_offline_new_api(self):
        bridge = EnigmaBridge()
        score = bridge.publish_trust_score(
            attestation={
                "metrics": {"SS": 0.92, "GCR": 1.0, "PFI": 0.15},
                "governance_status": "COMPLIANT",
                "z3_verified": True,
                "ast_score": 1.0,
            },
            oags_identity="1687",
        )
        self.assertIsInstance(score, DOFTrustScore)
        self.assertEqual(score.governance_score, 1.0)
        self.assertEqual(score.stability_score, 0.92)
        self.assertTrue(score.z3_verified)
        self.assertEqual(score.z3_theorems_passed, 4)
        self.assertEqual(score.governance_status, "COMPLIANT")
        # Offline: agent_id falls back to token_<id>
        self.assertEqual(score.agent_id, "token_1687")

    def test_publish_offline_legacy_api(self):
        bridge = EnigmaBridge()
        score = bridge.publish_trust_score(
            agent_id="agent-1",
            metrics={"SS": 0.9, "GCR": 1.0, "PFI": 0.0},
        )
        self.assertIsInstance(score, DOFTrustScore)
        self.assertEqual(score.agent_id, "agent-1")
        self.assertAlmostEqual(score.stability_score, 0.9, places=4)
        self.assertAlmostEqual(score.governance_score, 1.0, places=4)

    def test_get_trust_score_offline_returns_none(self):
        bridge = EnigmaBridge()
        result = bridge.get_trust_score("agent-1")
        self.assertIsNone(result)

    def test_get_all_verified_offline_returns_empty(self):
        bridge = EnigmaBridge()
        result = bridge.get_all_verified_agents()
        self.assertEqual(result, [])

    def test_get_history_offline_returns_empty(self):
        bridge = EnigmaBridge()
        result = bridge.get_history("agent-1")
        self.assertEqual(result, [])

    def test_get_latest_scores_offline_returns_empty(self):
        bridge = EnigmaBridge()
        result = bridge.get_latest_scores()
        self.assertEqual(result, [])

    def test_revoke_offline_returns_false(self):
        bridge = EnigmaBridge()
        result = bridge.revoke_verification("agent-1", "test")
        self.assertFalse(result)


@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestEnigmaBridgeSQLite(unittest.TestCase):
    """Test EnigmaBridge with SQLite in-memory (simulates Supabase)."""

    def setUp(self):
        self._url = "sqlite://"
        self._engine = create_engine(self._url)
        _create_sqlite_dof_tables(self._engine)
        self.bridge = EnigmaBridge(connection_url=self._url)
        self.bridge._engine = self._engine
        self.bridge._offline = False

    def test_publish_new_api_and_retrieve(self):
        score = self.bridge.publish_trust_score(
            attestation={
                "metrics": {"SS": 0.92, "GCR": 1.0, "PFI": 0.05, "ACR": 0.85, "RP": 0.1, "SSR": 0.0},
                "governance_status": "COMPLIANT",
                "certificate_hash": "0xcert123",
                "z3_verified": True,
                "ast_score": 1.0,
                "on_chain_tx": "0xtx456",
                "on_chain_block": 79657379,
            },
            oags_identity="1687",
        )
        # Offline SQLite won't have agents table with token_id 1687
        self.assertIn("1687", score.agent_id)
        self.assertAlmostEqual(score.governance_score, 1.0, places=4)
        self.assertAlmostEqual(score.stability_score, 0.92, places=4)
        self.assertTrue(score.z3_verified)

        retrieved = self.bridge.get_trust_score(score.agent_id)
        self.assertIsNotNone(retrieved)
        self.assertAlmostEqual(retrieved.governance_score, 1.0, places=2)
        self.assertEqual(retrieved.governance_status, "COMPLIANT")

    def test_publish_legacy_api_and_retrieve(self):
        score = self.bridge.publish_trust_score(
            agent_id="agent-abc",
            metrics={"SS": 0.88, "GCR": 1.0, "PFI": 0.22, "ACR": 0.9},
        )
        self.assertEqual(score.agent_id, "agent-abc")
        self.assertAlmostEqual(score.stability_score, 0.88, places=4)

        retrieved = self.bridge.get_trust_score("agent-abc")
        self.assertIsNotNone(retrieved)
        self.assertAlmostEqual(retrieved.stability_score, 0.88, places=2)

    def test_resolve_agent_address(self):
        """Test token_id → agents.address resolution."""
        with Session(self._engine) as session:
            session.execute(text(
                "INSERT INTO agents (address, name, token_id) "
                "VALUES ('0xfc6f71502d24f04e0463452947cc152a0eb4de3c', 'Apex', 1687)"
            ))
            session.commit()

        addr = self.bridge.resolve_agent_address(1687)
        self.assertEqual(addr, "0xfc6f71502d24f04e0463452947cc152a0eb4de3c")

        addr_none = self.bridge.resolve_agent_address(9999)
        self.assertIsNone(addr_none)

    def test_publish_resolves_address(self):
        """Publish with oags_identity resolves to agents.address."""
        with Session(self._engine) as session:
            session.execute(text(
                "INSERT INTO agents (address, name, token_id) "
                "VALUES ('0x9b59db8e7534924e34baa67a86454125cb02206d', 'AvaBuilder', 1686)"
            ))
            session.commit()

        score = self.bridge.publish_trust_score(
            attestation={
                "metrics": {"SS": 0.88, "GCR": 1.0, "PFI": 0.22},
                "governance_status": "COMPLIANT",
                "z3_verified": True,
                "ast_score": 1.0,
            },
            oags_identity="1686",
        )
        self.assertEqual(score.agent_id, "0x9b59db8e7534924e34baa67a86454125cb02206d")

    def test_get_nonexistent_agent(self):
        result = self.bridge.get_trust_score("nonexistent")
        self.assertIsNone(result)

    def test_history_multiple_inserts(self):
        """Multiple publishes for same agent → full history."""
        self.bridge.publish_trust_score(
            agent_id="agent-hist", metrics={"SS": 0.5, "GCR": 0.8, "PFI": 0.2}
        )
        self.bridge.publish_trust_score(
            agent_id="agent-hist", metrics={"SS": 0.9, "GCR": 1.0, "PFI": 0.0}
        )
        self.bridge.publish_trust_score(
            agent_id="agent-hist", metrics={"SS": 0.7, "GCR": 0.9, "PFI": 0.1}
        )

        history = self.bridge.get_history("agent-hist")
        self.assertEqual(len(history), 3)
        # Latest first
        self.assertAlmostEqual(history[0].stability_score, 0.7, places=2)

        # get_trust_score returns only latest
        latest = self.bridge.get_trust_score("agent-hist")
        self.assertAlmostEqual(latest.stability_score, 0.7, places=2)

    def test_revoke_verification(self):
        self.bridge.publish_trust_score(
            agent_id="agent-revoke",
            metrics={"SS": 0.95, "GCR": 1.0, "PFI": 0.0},
        )
        result = self.bridge.revoke_verification("agent-revoke", "violated terms")
        self.assertTrue(result)

        retrieved = self.bridge.get_trust_score("agent-revoke")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.governance_score, 0.0)
        self.assertEqual(retrieved.governance_status, "REVOKED")

    def test_publish_with_on_chain_data(self):
        score = self.bridge.publish_trust_score(
            attestation={
                "metrics": {"SS": 0.92, "GCR": 1.0, "PFI": 0.0},
                "governance_status": "COMPLIANT",
                "certificate_hash": "0xb031d562",
                "z3_verified": True,
                "ast_score": 1.0,
                "on_chain_tx": "0xb031d56244434fac",
                "on_chain_block": 79657379,
            },
            oags_identity="1687",
        )
        self.assertEqual(score.certificate_hash, "0xb031d562")
        self.assertEqual(score.on_chain_tx, "0xb031d56244434fac")
        self.assertEqual(score.on_chain_block, 79657379)

    def test_z3_theorems_auto_set(self):
        """z3_theorems_passed = 4 if z3_verified, else 0."""
        score_ok = self.bridge.publish_trust_score(
            attestation={"metrics": {}, "z3_verified": True},
            oags_identity="1",
        )
        self.assertEqual(score_ok.z3_theorems_passed, 4)

        score_fail = self.bridge.publish_trust_score(
            attestation={"metrics": {}, "z3_verified": False},
            oags_identity="2",
        )
        self.assertEqual(score_fail.z3_theorems_passed, 0)

    def test_multiple_scores_returns_latest(self):
        self.bridge.publish_trust_score(
            agent_id="agent-multi", metrics={"SS": 0.5, "GCR": 0.8, "PFI": 0.2}
        )
        self.bridge.publish_trust_score(
            agent_id="agent-multi", metrics={"SS": 0.9, "GCR": 1.0, "PFI": 0.0}
        )

        retrieved = self.bridge.get_trust_score("agent-multi")
        self.assertIsNotNone(retrieved)
        self.assertAlmostEqual(retrieved.stability_score, 0.9, places=2)


class TestJSONLLogging(unittest.TestCase):
    """Test that EnigmaBridge logs to JSONL."""

    def setUp(self):
        self._orig = os.environ.get("ENIGMA_DATABASE_URL")
        os.environ.pop("ENIGMA_DATABASE_URL", None)

    def tearDown(self):
        if self._orig is not None:
            os.environ["ENIGMA_DATABASE_URL"] = self._orig

    def test_publish_creates_log(self):
        bridge = EnigmaBridge()
        bridge.publish_trust_score(
            attestation={
                "metrics": {"SS": 0.9, "GCR": 1.0, "PFI": 0.0},
                "governance_status": "COMPLIANT",
                "z3_verified": True,
                "ast_score": 1.0,
            },
            oags_identity="9999",
        )

        log_path = os.path.join(BASE_DIR, "logs", "enigma_bridge.jsonl")
        self.assertTrue(os.path.exists(log_path))

        with open(log_path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertGreater(len(lines), 0)

        last = json.loads(lines[-1])
        self.assertIn("9999", last["agent_id"])
        self.assertEqual(last["action"], "publish")
        self.assertEqual(last["governance_score"], 1.0)

    def test_legacy_publish_creates_log(self):
        bridge = EnigmaBridge()
        bridge.publish_trust_score(
            agent_id="agent-log-legacy",
            metrics={"SS": 0.9, "GCR": 1.0, "PFI": 0.0},
        )

        log_path = os.path.join(BASE_DIR, "logs", "enigma_bridge.jsonl")
        with open(log_path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]

        last = json.loads(lines[-1])
        self.assertEqual(last["agent_id"], "agent-log-legacy")
        self.assertEqual(last["action"], "publish")


if __name__ == "__main__":
    unittest.main()
