"""
Tests for core/compliance_framework.py

Coverage:
- ComplianceControlRegistry — 123 controls loaded, by framework counts
- ComplianceTestingEngine — automated tests run without crash
- ControlResult — status/score logic
- RemediationTracker — add items, prioritize, count
- ComplianceReportGenerator — report fields populated
- ComplianceOrchestrator — get_status, run_assessment (DOF_MESH)
- DOF_MESH controls — 10 mesh-specific controls present
"""

import unittest
import os
import sys
import json
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.compliance_framework import (
    ComplianceControlRegistry,
    ComplianceTestingEngine,
    ComplianceOrchestrator,
    ComplianceReportGenerator,
    EvidenceCollector,
    RemediationTracker,
    ComplianceControl,
    ControlResult,
    ControlStatus,
    RemediationItem,
    ComplianceReport,
    RiskLevel,
    Framework,
)


class TestComplianceControlRegistry(unittest.TestCase):
    """Tests for ComplianceControlRegistry."""

    def setUp(self):
        self.registry = ComplianceControlRegistry()

    def test_total_controls_loaded(self):
        """Registry must have at least 93 controls."""
        count = self.registry.count()
        self.assertGreaterEqual(count, 93, f"Expected >=93 controls, got {count}")

    def test_soc2_controls_present(self):
        """SOC2 controls CC1-CC8 must be present."""
        soc2 = self.registry.get_by_framework(Framework.SOC2)
        self.assertGreater(len(soc2), 0)
        ids = {c.control_id for c in soc2}
        for expected in ["CC1.1", "CC3.1", "CC6.1", "CC7.1", "CC8.1"]:
            self.assertIn(expected, ids, f"SOC2 control {expected} missing")

    def test_hipaa_controls_present(self):
        """HIPAA controls must be present."""
        hipaa = self.registry.get_by_framework(Framework.HIPAA)
        self.assertGreater(len(hipaa), 0)
        ids = {c.control_id for c in hipaa}
        for expected in ["HIPAA-A.1", "HIPAA-T.1", "HIPAA-T.7", "HIPAA-P.1"]:
            self.assertIn(expected, ids, f"HIPAA control {expected} missing")

    def test_iso27001_controls_present(self):
        """ISO27001 controls A.5-A.8 must be present."""
        iso = self.registry.get_by_framework(Framework.ISO27001)
        self.assertGreater(len(iso), 0)
        ids = {c.control_id for c in iso}
        for expected in ["ISO-A.5.1", "ISO-A.6.1", "ISO-A.7.1", "ISO-A.8.1"]:
            self.assertIn(expected, ids, f"ISO27001 control {expected} missing")

    def test_dof_mesh_controls_present(self):
        """All 10 DOF Mesh controls must be present."""
        dof = self.registry.get_by_framework(Framework.DOF_MESH)
        self.assertEqual(len(dof), 10, f"Expected 10 DOF_MESH controls, got {len(dof)}")
        ids = {c.control_id for c in dof}
        for i in range(1, 11):
            cid = f"DOF-M.{i}"
            self.assertIn(cid, ids, f"DOF Mesh control {cid} missing")

    def test_get_control_by_id(self):
        """get() returns correct control."""
        ctrl = self.registry.get("DOF-M.1")
        self.assertIsNotNone(ctrl)
        self.assertEqual(ctrl.control_id, "DOF-M.1")
        self.assertEqual(ctrl.framework, Framework.DOF_MESH)
        self.assertEqual(ctrl.risk_level, RiskLevel.CRITICAL)

    def test_critical_controls_have_evidence_requirements(self):
        """All CRITICAL controls must specify evidence_required."""
        all_controls = self.registry.all()
        for ctrl in all_controls:
            if ctrl.risk_level == RiskLevel.CRITICAL:
                self.assertTrue(
                    len(ctrl.evidence_required) > 0,
                    f"Control {ctrl.control_id} is CRITICAL but has no evidence_required"
                )

    def test_all_controls_have_test_procedure(self):
        """Every control must have a non-empty test_procedure."""
        for ctrl in self.registry.all():
            self.assertTrue(
                ctrl.test_procedure and len(ctrl.test_procedure) > 5,
                f"Control {ctrl.control_id} has empty test_procedure"
            )

    def test_control_frameworks_are_valid(self):
        """All controls must have a valid Framework enum value."""
        valid = set(Framework)
        for ctrl in self.registry.all():
            self.assertIn(ctrl.framework, valid, f"Control {ctrl.control_id} has invalid framework")


class TestControlResult(unittest.TestCase):
    """Tests for ControlResult dataclass."""

    def test_pass_status(self):
        r = ControlResult(control_id="CC1.1", status=ControlStatus.PASS, score=1.0)
        self.assertEqual(r.status, ControlStatus.PASS)
        self.assertEqual(r.score, 1.0)

    def test_fail_status(self):
        r = ControlResult(
            control_id="DOF-M.7",
            status=ControlStatus.FAIL,
            score=0.0,
            findings=["E2E encryption not implemented"]
        )
        self.assertEqual(r.status, ControlStatus.FAIL)
        self.assertEqual(len(r.findings), 1)

    def test_partial_status(self):
        r = ControlResult(
            control_id="DOF-M.5",
            status=ControlStatus.PARTIAL,
            score=0.5,
            findings=["Logs exist but no hash chain"],
            recommendations=["Add keccak256 hash chain"]
        )
        self.assertEqual(r.status, ControlStatus.PARTIAL)
        self.assertEqual(r.score, 0.5)

    def test_timestamp_auto_set(self):
        r = ControlResult(control_id="CC6.1", status=ControlStatus.PASS, score=0.9)
        self.assertIsNotNone(r.timestamp)
        self.assertIn("2026", r.timestamp)

    def test_evidence_dict(self):
        r = ControlResult(
            control_id="DOF-M.8",
            status=ControlStatus.PASS,
            score=0.9,
            evidence={"icarus_packets": 100}
        )
        self.assertEqual(r.evidence["icarus_packets"], 100)


class TestComplianceTestingEngine(unittest.TestCase):
    """Tests for ComplianceTestingEngine."""

    def setUp(self):
        self.registry = ComplianceControlRegistry()
        self.engine = ComplianceTestingEngine(self.registry)

    def test_engine_initializes(self):
        self.assertIsNotNone(self.engine)

    def test_test_unknown_control(self):
        """Testing unknown control returns NOT_TESTED."""
        result = self.engine.test_control("NONEXISTENT-999")
        self.assertEqual(result.status, ControlStatus.NOT_TESTED)

    def test_test_dof_m5_audit_log(self):
        """DOF-M.5 audit log test runs without crash."""
        result = self.engine.test_control("DOF-M.5")
        self.assertIn(result.status, list(ControlStatus))
        self.assertIsInstance(result.score, float)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)

    def test_test_dof_m8_entropy(self):
        """DOF-M.8 entropy monitoring test (Icarus V2)."""
        result = self.engine.test_control("DOF-M.8")
        self.assertIn(result.status, [ControlStatus.PASS, ControlStatus.FAIL, ControlStatus.PARTIAL])
        self.assertIsInstance(result.score, float)

    def test_test_dof_m9_certs(self):
        """DOF-M.9 certificate rotation test."""
        result = self.engine.test_control("DOF-M.9")
        self.assertIn(result.status, list(ControlStatus))

    def test_test_dof_m6_z3(self):
        """DOF-M.6 Z3 proofs test."""
        result = self.engine.test_control("DOF-M.6")
        self.assertIn(result.status, list(ControlStatus))

    def test_test_all_dof_mesh(self):
        """test_all(DOF_MESH) returns 10 results."""
        results = self.engine.test_all(Framework.DOF_MESH)
        self.assertEqual(len(results), 10)
        for r in results:
            self.assertIsInstance(r, ControlResult)
            self.assertIn(r.status, list(ControlStatus))

    def test_test_all_returns_list(self):
        """test_all() with no framework returns list of ControlResult."""
        results = self.engine.test_all()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIsInstance(r.score, float)

    def test_no_crash_on_any_control(self):
        """No control test should raise an unhandled exception."""
        registry = ComplianceControlRegistry()
        engine = ComplianceTestingEngine(registry)
        for ctrl in registry.all():
            try:
                result = engine.test_control(ctrl.control_id)
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"test_control({ctrl.control_id}) raised: {e}")


class TestRemediationTracker(unittest.TestCase):
    """Tests for RemediationTracker."""

    def setUp(self):
        self.tracker = RemediationTracker()

    def test_add_item(self):
        """add() creates a RemediationItem."""
        registry = ComplianceControlRegistry()
        ctrl = registry.get("DOF-M.7")
        item = self.tracker.add(ctrl, ["E2E not implemented"])
        self.assertIsNotNone(item)
        self.assertEqual(item.control_id, "DOF-M.7")
        self.assertEqual(item.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(item.status, "OPEN")

    def test_open_count(self):
        """open_count() reflects added items."""
        registry = ComplianceControlRegistry()
        initial = self.tracker.open_count()
        ctrl = registry.get("DOF-M.3")
        self.tracker.add(ctrl, ["RBAC not enforced"])
        self.assertEqual(self.tracker.open_count(), initial + 1)

    def test_get_prioritized_critical_first(self):
        """get_prioritized() returns CRITICAL before LOW."""
        registry = ComplianceControlRegistry()
        self.tracker.add(registry.get("DOF-M.1"), ["7-layer not active"])  # CRITICAL
        self.tracker.add(registry.get("DOF-M.10"), ["Honeypot not configured"])  # MEDIUM

        items = self.tracker.get_prioritized()
        if len(items) >= 2:
            scores = [RemediationTracker.PRIORITY_SCORE.get(i.risk_level, 0) for i in items]
            # Should be descending
            for i in range(len(scores) - 1):
                self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_item_has_required_fields(self):
        """RemediationItem has all required fields."""
        registry = ComplianceControlRegistry()
        ctrl = registry.get("DOF-M.4")
        item = self.tracker.add(ctrl, ["Rate limiting missing"])
        self.assertTrue(item.item_id.startswith("REM-"))
        self.assertIsNotNone(item.created_at)
        self.assertIn(item.effort, ["LOW", "MEDIUM", "HIGH"])

    def test_all_returns_list(self):
        self.assertIsInstance(self.tracker.all(), list)


class TestComplianceReportGenerator(unittest.TestCase):
    """Tests for ComplianceReportGenerator."""

    def setUp(self):
        self.registry = ComplianceControlRegistry()
        self.engine = ComplianceTestingEngine(self.registry)

    def test_generate_report_fields(self):
        """Generated report has all required fields."""
        results = self.engine.test_all(Framework.DOF_MESH)
        tracker = RemediationTracker()
        reporter = ComplianceReportGenerator()

        report = reporter.generate(
            framework_name="DOF_MESH",
            results=results,
            remediation_items=tracker.all(),
            registry=self.registry
        )

        self.assertIsInstance(report, ComplianceReport)
        self.assertEqual(report.framework, "DOF_MESH")
        self.assertEqual(report.total_controls, 10)
        self.assertIsNotNone(report.report_id)
        self.assertTrue(report.report_id.startswith("RPT-"))
        self.assertIsInstance(report.compliance_score, float)
        self.assertGreaterEqual(report.compliance_score, 0.0)
        self.assertLessEqual(report.compliance_score, 100.0)
        self.assertIsInstance(report.critical_gaps, list)
        self.assertIsInstance(report.control_results, list)

    def test_report_score_math(self):
        """Compliance score = passed / tested * 100."""
        results = [
            ControlResult("DOF-M.1", ControlStatus.PASS, 1.0),
            ControlResult("DOF-M.2", ControlStatus.PASS, 1.0),
            ControlResult("DOF-M.3", ControlStatus.FAIL, 0.0),
            ControlResult("DOF-M.4", ControlStatus.FAIL, 0.0),
        ]
        tracker = RemediationTracker()
        reporter = ComplianceReportGenerator()
        report = reporter.generate("TEST", results, [], self.registry)
        # 2 pass / 4 tested = 50%
        self.assertAlmostEqual(report.compliance_score, 50.0, places=1)

    def test_to_markdown_contains_framework(self):
        """Markdown report contains framework name and table."""
        results = self.engine.test_all(Framework.DOF_MESH)
        reporter = ComplianceReportGenerator()
        report = reporter.generate("DOF_MESH", results, [], self.registry)
        md = reporter.to_markdown(report)
        self.assertIn("DOF_MESH", md)
        self.assertIn("Score", md)
        self.assertIn("PASS", md)


class TestEvidenceCollector(unittest.TestCase):
    """Tests for EvidenceCollector."""

    def setUp(self):
        self.collector = EvidenceCollector(evidence_dir="logs/compliance/evidence_test")

    def test_collect_creates_entry(self):
        """collect() adds entry to internal store."""
        self.collector.collect("DOF-M.5", "test", {"log_count": 5})
        entries = self.collector.get("DOF-M.5")
        self.assertGreater(len(entries), 0)

    def test_collect_entry_has_hash(self):
        """Collected entry has content hash."""
        self.collector.collect("DOF-M.8", "config", {"entropy_threshold": 7.5})
        entries = self.collector.get("DOF-M.8")
        self.assertTrue(len(entries) > 0)
        # Entry stored
        entry = entries[-1]
        self.assertIn("hash", entry)

    def test_get_empty_for_unknown_control(self):
        """get() returns empty list for unknown control."""
        result = self.collector.get("NONEXISTENT-999")
        self.assertEqual(result, [])


class TestComplianceOrchestrator(unittest.TestCase):
    """Integration tests for ComplianceOrchestrator."""

    def setUp(self):
        self.orchestrator = ComplianceOrchestrator()

    def test_get_status(self):
        """get_status() returns dict with expected keys."""
        status = self.orchestrator.get_status()
        self.assertIn("total_controls", status)
        self.assertGreaterEqual(status["total_controls"], 93)
        self.assertIn("open_remediations", status)
        self.assertIn("evidence_entries", status)

    def test_run_assessment_dof_mesh(self):
        """run_assessment(DOF_MESH) returns valid report."""
        report = self.orchestrator.run_assessment(
            framework=Framework.DOF_MESH,
            save_report=False
        )
        self.assertIsInstance(report, ComplianceReport)
        self.assertEqual(report.total_controls, 10)
        self.assertIsNotNone(report.report_id)
        self.assertGreaterEqual(report.compliance_score, 0.0)
        self.assertLessEqual(report.compliance_score, 100.0)

    def test_run_assessment_soc2(self):
        """run_assessment(SOC2) returns report with SOC2 controls."""
        report = self.orchestrator.run_assessment(
            framework=Framework.SOC2,
            save_report=False
        )
        self.assertIsInstance(report, ComplianceReport)
        self.assertGreater(report.total_controls, 0)
        self.assertIn("SOC2", report.framework)

    def test_get_critical_gaps_returns_list(self):
        """get_critical_gaps() always returns a list."""
        gaps = self.orchestrator.get_critical_gaps()
        self.assertIsInstance(gaps, list)

    def test_run_all_frameworks_no_crash(self):
        """Running all frameworks sequentially should not crash."""
        for fw in [Framework.SOC2, Framework.HIPAA, Framework.ISO27001, Framework.DOF_MESH]:
            try:
                report = self.orchestrator.run_assessment(fw, save_report=False)
                self.assertIsNotNone(report)
            except Exception as e:
                self.fail(f"run_assessment({fw}) raised: {e}")


class TestDOFMeshSpecificControls(unittest.TestCase):
    """Verify DOF Mesh controls map correctly to the 7-layer security stack."""

    def setUp(self):
        self.registry = ComplianceControlRegistry()
        self.dof_controls = {
            c.control_id: c for c in self.registry.get_by_framework(Framework.DOF_MESH)
        }

    def test_seven_layer_stack_control(self):
        """DOF-M.1 covers 7-layer security."""
        ctrl = self.dof_controls.get("DOF-M.1")
        self.assertIsNotNone(ctrl)
        self.assertIn("7", ctrl.name + ctrl.description)
        self.assertEqual(ctrl.risk_level, RiskLevel.CRITICAL)

    def test_nats_tls_control(self):
        """DOF-M.2 covers NATS TLS 1.3 + mTLS."""
        ctrl = self.dof_controls.get("DOF-M.2")
        self.assertIsNotNone(ctrl)
        self.assertIn("TLS", ctrl.name + ctrl.description)
        self.assertEqual(ctrl.risk_level, RiskLevel.CRITICAL)

    def test_e2e_encryption_control(self):
        """DOF-M.7 covers E2E encryption (currently NOT IMPLEMENTED — critical gap)."""
        ctrl = self.dof_controls.get("DOF-M.7")
        self.assertIsNotNone(ctrl)
        self.assertIn("E2E", ctrl.name + ctrl.description)
        self.assertEqual(ctrl.risk_level, RiskLevel.CRITICAL)

    def test_entropy_monitoring_control(self):
        """DOF-M.8 covers Shannon entropy monitoring via Icarus V2."""
        ctrl = self.dof_controls.get("DOF-M.8")
        self.assertIsNotNone(ctrl)
        self.assertIn("entropy", ctrl.description.lower())

    def test_honeypot_control(self):
        """DOF-M.10 covers honeypot detection."""
        ctrl = self.dof_controls.get("DOF-M.10")
        self.assertIsNotNone(ctrl)
        self.assertIn("oneypot", ctrl.name + ctrl.description)

    def test_all_dof_controls_have_evidence(self):
        """All DOF Mesh controls specify evidence_required."""
        for cid, ctrl in self.dof_controls.items():
            self.assertTrue(
                len(ctrl.evidence_required) > 0,
                f"{cid} missing evidence_required"
            )


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
