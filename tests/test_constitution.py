"""
Test Constitution — Validates dof.constitution.yml schema and
confirms parity with core/governance.py rules.
"""

import os
import sys
import unittest

import yaml

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

CONSTITUTION_PATH = os.path.join(PROJECT_ROOT, "dof.constitution.yml")


class TestConstitutionSchema(unittest.TestCase):
    """Validate dof.constitution.yml structure and required fields."""

    @classmethod
    def setUpClass(cls):
        with open(CONSTITUTION_PATH, "r", encoding="utf-8") as f:
            cls.doc = yaml.safe_load(f)

    # ── Top-level sections ──────────────────────────────────────────

    def test_has_metadata(self):
        meta = self.doc.get("metadata", {})
        self.assertEqual(meta.get("spec_version"), "1.0")
        self.assertEqual(meta.get("project"), "deterministic-observability-framework")
        self.assertIn("author", meta)

    def test_has_identity(self):
        identity = self.doc.get("identity", {})
        self.assertIn("model", identity)
        self.assertIsInstance(identity.get("providers"), list)
        self.assertGreater(len(identity["providers"]), 0)

    def test_has_rules(self):
        rules = self.doc.get("rules", {})
        self.assertIn("hard", rules)
        self.assertIn("soft", rules)
        self.assertGreater(len(rules["hard"]), 0)
        self.assertGreater(len(rules["soft"]), 0)

    def test_has_metrics(self):
        metrics = self.doc.get("metrics")
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 5)

    def test_has_thresholds(self):
        th = self.doc.get("thresholds", {})
        self.assertIn("supervisor", th)
        self.assertIn("crew_runner", th)

    # ── Rule schema ─────────────────────────────────────────────────

    def test_hard_rules_schema(self):
        for rule in self.doc["rules"]["hard"]:
            self.assertIn("id", rule, f"Missing 'id' in hard rule: {rule}")
            self.assertIn("rule_key", rule, f"Missing 'rule_key' in: {rule['id']}")
            self.assertEqual(rule["severity"], "block", f"Hard rule {rule['id']} severity must be 'block'")
            self.assertEqual(rule["action"], "block", f"Hard rule {rule['id']} action must be 'block'")
            self.assertIn("pattern", rule, f"Missing 'pattern' in: {rule['id']}")
            self.assertIn("evidence", rule, f"Missing 'evidence' in: {rule['id']}")

    def test_soft_rules_schema(self):
        for rule in self.doc["rules"]["soft"]:
            self.assertIn("id", rule, f"Missing 'id' in soft rule: {rule}")
            self.assertIn("rule_key", rule, f"Missing 'rule_key' in: {rule['id']}")
            self.assertEqual(rule["severity"], "warn", f"Soft rule {rule['id']} severity must be 'warn'")
            self.assertEqual(rule["action"], "warn", f"Soft rule {rule['id']} action must be 'warn'")
            self.assertIn("weight", rule, f"Missing 'weight' in: {rule['id']}")
            self.assertIn("pattern", rule, f"Missing 'pattern' in: {rule['id']}")
            self.assertIn("evidence", rule, f"Missing 'evidence' in: {rule['id']}")

    def test_hard_rule_ids_sequential(self):
        ids = [r["id"] for r in self.doc["rules"]["hard"]]
        for i, rid in enumerate(ids, 1):
            self.assertEqual(rid, f"HARD-{i:03d}", f"Expected HARD-{i:03d}, got {rid}")

    def test_soft_rule_ids_sequential(self):
        ids = [r["id"] for r in self.doc["rules"]["soft"]]
        for i, rid in enumerate(ids, 1):
            self.assertEqual(rid, f"SOFT-{i:03d}", f"Expected SOFT-{i:03d}, got {rid}")

    # ── Metrics schema ──────────────────────────────────────────────

    def test_metrics_schema(self):
        expected_ids = {"SS", "PFI", "RP", "GCR", "SSR"}
        actual_ids = {m["id"] for m in self.doc["metrics"]}
        self.assertEqual(actual_ids, expected_ids)
        for m in self.doc["metrics"]:
            self.assertIn("name", m, f"Missing 'name' in metric {m['id']}")
            self.assertIn("domain", m, f"Missing 'domain' in metric {m['id']}")
            self.assertIn("description", m, f"Missing 'description' in metric {m['id']}")

    def test_gcr_invariant(self):
        gcr = next(m for m in self.doc["metrics"] if m["id"] == "GCR")
        self.assertEqual(gcr.get("invariant"), 1.0)

    # ── Thresholds ──────────────────────────────────────────────────

    def test_supervisor_thresholds(self):
        sup = self.doc["thresholds"]["supervisor"]
        self.assertEqual(sup["accept"], 7.0)
        self.assertEqual(sup["retry"], 5.0)
        self.assertEqual(sup["max_retries"], 2)
        weights = sup["weights"]
        self.assertAlmostEqual(
            sum(weights.values()), 1.0, places=2,
            msg="Supervisor weights must sum to 1.0",
        )

    def test_crew_runner_thresholds(self):
        cr = self.doc["thresholds"]["crew_runner"]
        self.assertEqual(cr["max_retries"], 3)


class TestConstitutionGovernanceParity(unittest.TestCase):
    """Confirm every in-code HARD_RULE/SOFT_RULE has a YAML entry."""

    @classmethod
    def setUpClass(cls):
        with open(CONSTITUTION_PATH, "r", encoding="utf-8") as f:
            cls.doc = yaml.safe_load(f)
        from core.governance import HARD_RULES, SOFT_RULES
        cls.hard_rules = HARD_RULES
        cls.soft_rules = SOFT_RULES

    def test_all_hard_rules_in_yaml(self):
        yaml_keys = {r["rule_key"] for r in self.doc["rules"]["hard"]}
        for rule in self.hard_rules:
            self.assertIn(
                rule["id"], yaml_keys,
                f"HARD_RULE '{rule['id']}' missing from dof.constitution.yml",
            )

    def test_all_soft_rules_in_yaml(self):
        yaml_keys = {r["rule_key"] for r in self.doc["rules"]["soft"]}
        for rule in self.soft_rules:
            self.assertIn(
                rule["id"], yaml_keys,
                f"SOFT_RULE '{rule['id']}' missing from dof.constitution.yml",
            )

    def test_soft_weights_match(self):
        yaml_weights = {r["rule_key"]: r["weight"] for r in self.doc["rules"]["soft"]}
        for rule in self.soft_rules:
            code_weight = rule.get("weight", 0.25)
            yaml_weight = yaml_weights.get(rule["id"])
            self.assertIsNotNone(yaml_weight, f"No YAML weight for {rule['id']}")
            self.assertAlmostEqual(
                code_weight, yaml_weight, places=2,
                msg=f"Weight mismatch for {rule['id']}: code={code_weight}, yaml={yaml_weight}",
            )

    def test_yaml_hard_count_matches_code(self):
        self.assertEqual(
            len(self.doc["rules"]["hard"]),
            len(self.hard_rules),
            "YAML hard rule count does not match code",
        )

    def test_yaml_soft_count_matches_code(self):
        self.assertEqual(
            len(self.doc["rules"]["soft"]),
            len(self.soft_rules),
            "YAML soft rule count does not match code",
        )


if __name__ == "__main__":
    unittest.main()
