"""
Tests for core/oags_bridge.py — OAGS Bridge.

Covers:
  - OAGSIdentity: deterministic BLAKE3 hashing, agent card
  - OAGSPolicyBridge: export/import sekuire.yml, conformance validation
  - OAGSAuditBridge: audit event export, report generation
  - dof/__init__.py exports
"""

import os
import json
import shutil
import tempfile
import unittest
from datetime import datetime

import yaml

from core.oags_bridge import (
    OAGSIdentity,
    OAGSPolicyBridge,
    OAGSAuditBridge,
    BASE_DIR,
)


class TestOAGSIdentity(unittest.TestCase):
    """Tests for OAGSIdentity — deterministic BLAKE3 agent identity."""

    def test_compute_identity_deterministic(self):
        """Same input ALWAYS produces the same identity hash."""
        h1 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool1", "tool2"])
        h2 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool1", "tool2"])
        self.assertEqual(h1, h2)

    def test_compute_identity_tool_order_irrelevant(self):
        """Tools are sorted, so order doesn't matter."""
        h1 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool2", "tool1"])
        h2 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool1", "tool2"])
        self.assertEqual(h1, h2)

    def test_compute_identity_changes_with_model(self):
        """Different model → different identity."""
        h1 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool1"])
        h2 = OAGSIdentity.compute_identity("model-b", "hash123", ["tool1"])
        self.assertNotEqual(h1, h2)

    def test_compute_identity_changes_with_constitution(self):
        """Different constitution hash → different identity."""
        h1 = OAGSIdentity.compute_identity("model-a", "hash123", ["tool1"])
        h2 = OAGSIdentity.compute_identity("model-a", "hash456", ["tool1"])
        self.assertNotEqual(h1, h2)

    def test_compute_constitution_hash_deterministic(self):
        """Same file → same hash."""
        path = os.path.join(BASE_DIR, "dof.constitution.yml")
        if not os.path.exists(path):
            self.skipTest("dof.constitution.yml not found")
        h1 = OAGSIdentity.compute_constitution_hash(path)
        h2 = OAGSIdentity.compute_constitution_hash(path)
        self.assertEqual(h1, h2)
        self.assertTrue(len(h1) == 64)  # BLAKE3 hex digest is 64 chars

    def test_compute_constitution_hash_changes_with_content(self):
        """Different content → different hash."""
        tmpdir = tempfile.mkdtemp()
        try:
            p1 = os.path.join(tmpdir, "c1.yml")
            p2 = os.path.join(tmpdir, "c2.yml")
            with open(p1, "w") as f:
                f.write("rules:\n  hard: []\n")
            with open(p2, "w") as f:
                f.write("rules:\n  hard: [{id: X}]\n")
            h1 = OAGSIdentity.compute_constitution_hash(p1)
            h2 = OAGSIdentity.compute_constitution_hash(p2)
            self.assertNotEqual(h1, h2)
        finally:
            shutil.rmtree(tmpdir)

    def test_agent_card_has_required_fields(self):
        """Agent card must contain all OAGS-required fields."""
        identity = OAGSIdentity(model="test-model", tools=["t1", "t2"])
        card = identity.get_agent_card()
        required = ["identity_hash", "model", "constitution_hash", "tools",
                     "created_at", "framework", "version"]
        for field in required:
            self.assertIn(field, card, f"Missing field: {field}")
        self.assertEqual(card["framework"], "DOF")
        self.assertEqual(card["version"], "0.5.0")
        self.assertEqual(card["model"], "test-model")
        self.assertEqual(card["tools"], ["t1", "t2"])

    def test_agent_card_persisted(self):
        """Agent card should be saved to memory/oags_identity.json."""
        identity = OAGSIdentity(model="persist-test")
        card_path = os.path.join(BASE_DIR, "memory", "oags_identity.json")
        self.assertTrue(os.path.exists(card_path))
        with open(card_path) as f:
            saved = json.load(f)
        self.assertEqual(saved["model"], "persist-test")


class TestOAGSPolicyBridge(unittest.TestCase):
    """Tests for OAGSPolicyBridge — sekuire.yml export/import."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def test_export_sekuire_generates_valid_yaml(self):
        """Export produces a valid YAML file with expected structure."""
        output = os.path.join(self._tmpdir, "sekuire.yml")
        path = OAGSPolicyBridge.export_sekuire(output_path=output)
        self.assertTrue(os.path.exists(path))

        with open(path) as f:
            data = yaml.safe_load(f)

        self.assertEqual(data["apiVersion"], "oags/v1")
        self.assertEqual(data["kind"], "GovernancePolicy")
        self.assertIn("policies", data)
        self.assertIn("observability", data)
        self.assertIsInstance(data["policies"], list)
        self.assertTrue(len(data["policies"]) > 0, "Should have at least one policy")

    def test_import_sekuire_reads_format(self):
        """Import reads sekuire.yml and returns DOF-compatible rules."""
        output = os.path.join(self._tmpdir, "sekuire.yml")
        OAGSPolicyBridge.export_sekuire(output_path=output)
        result = OAGSPolicyBridge.import_sekuire(output)

        self.assertIn("rules", result)
        self.assertIn("metrics", result)
        self.assertIn("hard", result["rules"])
        self.assertIn("soft", result["rules"])
        self.assertIn("ast", result["rules"])

    def test_export_import_roundtrip_preserves_rules(self):
        """Export → import roundtrip preserves rule counts and keys."""
        output = os.path.join(self._tmpdir, "sekuire.yml")
        OAGSPolicyBridge.export_sekuire(output_path=output)

        # Read original constitution
        c_path = os.path.join(BASE_DIR, "dof.constitution.yml")
        with open(c_path) as f:
            original = yaml.safe_load(f) or {}
        orig_rules = original.get("rules", {})
        orig_hard = len(orig_rules.get("hard", []))
        orig_soft = len(orig_rules.get("soft", []))
        orig_ast = len(orig_rules.get("ast", []))
        orig_metrics = len(original.get("metrics", []))

        # Import back
        result = OAGSPolicyBridge.import_sekuire(output)
        self.assertEqual(len(result["rules"]["hard"]), orig_hard)
        self.assertEqual(len(result["rules"]["soft"]), orig_soft)
        self.assertEqual(len(result["rules"]["ast"]), orig_ast)
        self.assertEqual(len(result["metrics"]), orig_metrics)

        # Check rule keys preserved
        orig_hard_keys = {r["rule_key"] for r in orig_rules.get("hard", [])}
        imported_hard_keys = {r["rule_key"] for r in result["rules"]["hard"]}
        self.assertEqual(orig_hard_keys, imported_hard_keys)

    def test_validate_conformance_level_1_passes(self):
        """Level 1 passes — we have constitution.yml with rules."""
        result = OAGSPolicyBridge.validate_conformance(level=1)
        self.assertTrue(result["level_1"]["passed"])
        self.assertGreaterEqual(result["max_level_passed"], 1)

    def test_validate_conformance_level_2_passes(self):
        """Level 2 passes — ConstitutionEnforcer active + metrics available."""
        result = OAGSPolicyBridge.validate_conformance(level=2)
        self.assertTrue(result["level_2"]["passed"])
        self.assertGreaterEqual(result["max_level_passed"], 2)

    def test_validate_conformance_level_3_fails(self):
        """Level 3 fails — Oracle Bridge doesn't exist yet."""
        oracle_path = os.path.join(BASE_DIR, "core", "oracle_bridge.py")
        if os.path.exists(oracle_path):
            self.skipTest("oracle_bridge.py exists — Level 3 would pass")
        result = OAGSPolicyBridge.validate_conformance(level=3)
        self.assertFalse(result["level_3"]["passed"])
        self.assertEqual(result["max_level_passed"], 2)


class TestOAGSAuditBridge(unittest.TestCase):
    """Tests for OAGSAuditBridge — audit event export and reporting."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._logs_dir = os.path.join(self._tmpdir, "logs")
        os.makedirs(self._logs_dir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def test_export_audit_events_format(self):
        """Exported events have required OAGS fields."""
        # Write a sample execution log
        log_path = os.path.join(self._logs_dir, "execution_log.jsonl")
        entry = {
            "timestamp": "2026-03-01T10:00:00",
            "crew": "research",
            "status": "success",
            "governance_passed": True,
        }
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        identity = OAGSIdentity(model="test-audit")
        audit = OAGSAuditBridge(identity)
        events = audit.export_audit_events(logs_path=self._logs_dir)

        self.assertEqual(len(events), 1)
        event = events[0]
        required_fields = ["event_id", "agent_identity", "timestamp",
                           "event_type", "payload", "governance_decision"]
        for field in required_fields:
            self.assertIn(field, event, f"Missing OAGS field: {field}")

        self.assertEqual(event["event_type"], "execution")
        self.assertEqual(event["governance_decision"], "PASS")

    def test_generate_audit_report(self):
        """Report summarizes events correctly."""
        events = [
            {"event_type": "execution", "governance_decision": "PASS"},
            {"event_type": "execution", "governance_decision": "PASS"},
            {"event_type": "memory_governance", "governance_decision": "approved"},
            {"event_type": "execution", "governance_decision": "FAIL"},
        ]
        report = OAGSAuditBridge.generate_audit_report(events)

        self.assertEqual(report["total_events"], 4)
        self.assertEqual(report["by_type"]["execution"], 3)
        self.assertEqual(report["by_type"]["memory_governance"], 1)
        # compliance: (2 PASS + 1 approved) / (2 PASS + 1 approved + 1 FAIL) = 3/4
        self.assertAlmostEqual(report["compliance_rate"], 0.75, places=2)

    def test_export_empty_logs(self):
        """Empty logs directory → empty events list."""
        audit = OAGSAuditBridge()
        events = audit.export_audit_events(logs_path=self._logs_dir)
        self.assertEqual(len(events), 0)


class TestDofOAGSExports(unittest.TestCase):
    """Test that OAGS bridge is properly exported from dof/__init__.py."""

    def test_import_oags_identity(self):
        from dof import OAGSIdentity as OI
        self.assertIsNotNone(OI)

    def test_import_oags_policy_bridge(self):
        from dof import OAGSPolicyBridge as OPB
        self.assertIsNotNone(OPB)

    def test_import_oags_audit_bridge(self):
        from dof import OAGSAuditBridge as OAB
        self.assertIsNotNone(OAB)


if __name__ == "__main__":
    unittest.main()
