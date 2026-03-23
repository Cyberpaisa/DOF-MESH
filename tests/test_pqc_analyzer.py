"""
Tests for core/pqc_analyzer.py — Post-Quantum Cryptography analyzer.

All tests are deterministic, zero LLM, zero network, zero external deps.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pqc_analyzer import (
    ALGORITHMS,
    QUANTUM_THREATS,
    CryptoAlgorithm,
    PQCAnalyzer,
    PQCAssessment,
    SystemAssessment,
    assess_algorithm,
    assess_dof,
)


# ─────────────────────────────────────────────────────────────────────
# ALGORITHMS database integrity
# ─────────────────────────────────────────────────────────────────────

class TestAlgorithmsDatabase(unittest.TestCase):

    VALID_STATUSES   = {"BROKEN", "WEAKENED", "SAFE"}
    VALID_URGENCIES  = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    VALID_CATEGORIES = {"symmetric", "asymmetric", "hash", "signature", "kex"}

    def test_database_non_empty(self):
        self.assertGreater(len(ALGORITHMS), 0)

    def test_all_have_required_fields(self):
        for name, algo in ALGORITHMS.items():
            for attr in ("name", "category", "classical_bits", "quantum_bits",
                         "quantum_status", "migration_target", "migration_urgency"):
                self.assertTrue(
                    getattr(algo, attr, None) is not None,
                    f"{name} missing {attr}"
                )

    def test_quantum_status_valid(self):
        for name, algo in ALGORITHMS.items():
            self.assertIn(algo.quantum_status, self.VALID_STATUSES,
                          f"{name} has invalid status: {algo.quantum_status}")

    def test_urgency_valid(self):
        for name, algo in ALGORITHMS.items():
            self.assertIn(algo.migration_urgency, self.VALID_URGENCIES,
                          f"{name} has invalid urgency: {algo.migration_urgency}")

    def test_category_valid(self):
        for name, algo in ALGORITHMS.items():
            self.assertIn(algo.category, self.VALID_CATEGORIES,
                          f"{name} has invalid category: {algo.category}")

    def test_classical_bits_positive(self):
        for name, algo in ALGORITHMS.items():
            self.assertGreater(algo.classical_bits, 0,
                               f"{name} classical_bits must be > 0")

    def test_quantum_bits_non_negative(self):
        for name, algo in ALGORITHMS.items():
            self.assertGreaterEqual(algo.quantum_bits, 0,
                                    f"{name} quantum_bits must be >= 0")

    def test_broken_algorithms_have_zero_quantum_bits(self):
        for name, algo in ALGORITHMS.items():
            if algo.quantum_status == "BROKEN":
                self.assertEqual(algo.quantum_bits, 0,
                                 f"{name} is BROKEN but quantum_bits != 0")

    def test_broken_algorithms_are_critical(self):
        for name, algo in ALGORITHMS.items():
            if algo.quantum_status == "BROKEN":
                self.assertEqual(algo.migration_urgency, "CRITICAL",
                                 f"{name} is BROKEN but urgency != CRITICAL")

    def test_known_broken_algorithms_present(self):
        for name in ("RSA-2048", "ECC-P256", "Ed25519", "ECDSA-secp256k1"):
            self.assertIn(name, ALGORITHMS, f"Missing known broken algo: {name}")

    def test_known_safe_algorithms_present(self):
        for name in ("AES-256", "SHA-256", "ML-KEM-768", "ML-DSA-65"):
            self.assertIn(name, ALGORITHMS, f"Missing known safe algo: {name}")


# ─────────────────────────────────────────────────────────────────────
# QUANTUM_THREATS database
# ─────────────────────────────────────────────────────────────────────

class TestQuantumThreats(unittest.TestCase):

    def test_shor_present(self):
        self.assertIn("shor", QUANTUM_THREATS)

    def test_grover_present(self):
        self.assertIn("grover", QUANTUM_THREATS)

    def test_shor_fields(self):
        s = QUANTUM_THREATS["shor"]
        for k in ("name", "description", "breaks", "complexity", "qubits_needed_per_bit"):
            self.assertIn(k, s)

    def test_grover_halves_bits(self):
        self.assertEqual(QUANTUM_THREATS["grover"]["effective_bits_factor"], 0.5)

    def test_shor_breaks_ecc(self):
        self.assertIn("ECC", QUANTUM_THREATS["shor"]["breaks"])

    def test_shor_breaks_rsa(self):
        self.assertIn("RSA", QUANTUM_THREATS["shor"]["breaks"])


# ─────────────────────────────────────────────────────────────────────
# assess_algorithm() — known algorithms
# ─────────────────────────────────────────────────────────────────────

class TestAssessAlgorithm(unittest.TestCase):

    def setUp(self):
        self.analyzer = PQCAnalyzer()

    # --- BROKEN algorithms ---

    def test_rsa2048_is_broken(self):
        a = self.analyzer.assess_algorithm("RSA-2048")
        self.assertEqual(a.status, "BROKEN")
        self.assertEqual(a.urgency, "CRITICAL")

    def test_ecc_p256_is_broken(self):
        a = self.analyzer.assess_algorithm("ECC-P256")
        self.assertEqual(a.status, "BROKEN")
        self.assertEqual(a.quantum_bits, 0)

    def test_ed25519_is_broken(self):
        a = self.analyzer.assess_algorithm("Ed25519")
        self.assertEqual(a.status, "BROKEN")
        self.assertEqual(a.threat, "shor")

    def test_ecdsa_secp256k1_is_broken(self):
        a = self.analyzer.assess_algorithm("ECDSA-secp256k1")
        self.assertEqual(a.status, "BROKEN")
        self.assertEqual(a.urgency, "CRITICAL")

    def test_broken_has_qubits_estimate(self):
        a = self.analyzer.assess_algorithm("RSA-2048")
        # ~2 * classical_bits qubits
        self.assertGreater(a.qubits_estimated, 0)
        self.assertEqual(a.qubits_estimated, 112 * 2)

    def test_broken_threat_is_shor(self):
        a = self.analyzer.assess_algorithm("ECC-P256")
        self.assertEqual(a.threat, "shor")

    # --- WEAKENED algorithms ---

    def test_aes128_is_weakened(self):
        a = self.analyzer.assess_algorithm("AES-128")
        self.assertEqual(a.status, "WEAKENED")
        self.assertEqual(a.threat, "grover")
        self.assertEqual(a.urgency, "HIGH")

    def test_weakened_has_nonzero_quantum_bits(self):
        a = self.analyzer.assess_algorithm("AES-128")
        self.assertGreater(a.quantum_bits, 0)

    def test_weakened_qubits_estimate_zero(self):
        # Grover doesn't use qubits the same way — qubits_estimated = 0
        a = self.analyzer.assess_algorithm("AES-128")
        self.assertEqual(a.qubits_estimated, 0)

    # --- SAFE algorithms ---

    def test_aes256_is_safe(self):
        a = self.analyzer.assess_algorithm("AES-256")
        self.assertEqual(a.status, "SAFE")
        self.assertEqual(a.urgency, "LOW")

    def test_sha256_is_safe(self):
        a = self.analyzer.assess_algorithm("SHA-256")
        self.assertEqual(a.status, "SAFE")

    def test_ml_kem_768_is_safe(self):
        a = self.analyzer.assess_algorithm("ML-KEM-768")
        self.assertEqual(a.status, "SAFE")
        self.assertEqual(a.threat, "none")

    def test_safe_threat_is_none(self):
        a = self.analyzer.assess_algorithm("AES-256")
        self.assertEqual(a.threat, "none")

    def test_keccak256_is_safe(self):
        a = self.analyzer.assess_algorithm("keccak256")
        self.assertEqual(a.status, "SAFE")

    # --- Return type ---

    def test_returns_pqc_assessment(self):
        a = self.analyzer.assess_algorithm("AES-256")
        self.assertIsInstance(a, PQCAssessment)

    def test_assessment_has_timestamp(self):
        a = self.analyzer.assess_algorithm("SHA-256")
        self.assertGreater(a.timestamp, 0)

    def test_algorithm_name_preserved(self):
        a = self.analyzer.assess_algorithm("AES-256")
        self.assertEqual(a.algorithm, "AES-256")

    def test_has_migration_target(self):
        a = self.analyzer.assess_algorithm("RSA-2048")
        self.assertIsInstance(a.migration_target, str)
        self.assertGreater(len(a.migration_target), 0)

    def test_has_notes(self):
        a = self.analyzer.assess_algorithm("ECC-P256")
        self.assertIsInstance(a.notes, str)


# ─────────────────────────────────────────────────────────────────────
# assess_algorithm() — unknown / fuzzy
# ─────────────────────────────────────────────────────────────────────

class TestAssessAlgorithmUnknown(unittest.TestCase):

    def setUp(self):
        self.analyzer = PQCAnalyzer()

    def test_unknown_returns_unknown_status(self):
        a = self.analyzer.assess_algorithm("NTRU-Prime-761")
        self.assertEqual(a.status, "UNKNOWN")

    def test_unknown_urgency_medium(self):
        a = self.analyzer.assess_algorithm("CRYSTALS-Kyber")
        self.assertEqual(a.urgency, "MEDIUM")

    def test_unknown_name_preserved(self):
        a = self.analyzer.assess_algorithm("MyCustomAlgo")
        self.assertEqual(a.algorithm, "MyCustomAlgo")

    def test_fuzzy_match_rsa(self):
        # "RSA" should fuzzy-match to RSA-2048 or RSA-4096
        a = self.analyzer.assess_algorithm("RSA")
        self.assertNotEqual(a.status, "UNKNOWN")

    def test_fuzzy_match_case_insensitive(self):
        a = self.analyzer.assess_algorithm("aes-256")
        self.assertNotEqual(a.status, "UNKNOWN")


# ─────────────────────────────────────────────────────────────────────
# assess_system()
# ─────────────────────────────────────────────────────────────────────

class TestAssessSystem(unittest.TestCase):

    def setUp(self):
        self.analyzer = PQCAnalyzer()

    def test_returns_system_assessment(self):
        result = self.analyzer.assess_system(["AES-256", "SHA-256"])
        self.assertIsInstance(result, SystemAssessment)

    def test_all_safe_is_quantum_ready(self):
        result = self.analyzer.assess_system(["AES-256", "SHA-256", "ML-KEM-768"])
        self.assertEqual(result.overall_status, "QUANTUM_READY")
        self.assertEqual(result.critical_count, 0)
        self.assertEqual(result.high_count, 0)

    def test_one_broken_is_vulnerable(self):
        result = self.analyzer.assess_system(["AES-256", "RSA-2048"])
        self.assertEqual(result.overall_status, "VULNERABLE")
        self.assertGreater(result.critical_count, 0)

    def test_weakened_only_is_at_risk(self):
        result = self.analyzer.assess_system(["AES-128"])
        self.assertEqual(result.overall_status, "AT_RISK")
        self.assertEqual(result.critical_count, 0)
        self.assertGreater(result.high_count, 0)

    def test_counts_match_assessments(self):
        algos = ["RSA-2048", "AES-128", "AES-256"]
        result = self.analyzer.assess_system(algos)
        critical = sum(1 for a in result.assessments if a.urgency == "CRITICAL")
        self.assertEqual(result.critical_count, critical)

    def test_safe_count(self):
        result = self.analyzer.assess_system(["AES-256", "SHA-256", "RSA-2048"])
        safe = sum(1 for a in result.assessments if a.status == "SAFE")
        self.assertEqual(result.safe_count, safe)

    def test_algorithms_found_preserved(self):
        algos = ["AES-256", "RSA-2048"]
        result = self.analyzer.assess_system(algos)
        self.assertEqual(result.algorithms_found, algos)

    def test_migration_plan_non_empty_when_critical(self):
        result = self.analyzer.assess_system(["RSA-2048", "ECC-P256"])
        self.assertGreater(len(result.migration_plan), 0)

    def test_migration_plan_empty_when_all_safe(self):
        result = self.analyzer.assess_system(["AES-256", "SHA-256"])
        self.assertEqual(result.migration_plan, [])

    def test_migration_plan_sorted_critical_first(self):
        result = self.analyzer.assess_system(["AES-128", "RSA-2048"])
        # First entry should be CRITICAL
        self.assertTrue(result.migration_plan[0].startswith("[CRITICAL]"))

    def test_empty_algorithm_list(self):
        result = self.analyzer.assess_system([])
        self.assertEqual(result.overall_status, "QUANTUM_READY")
        self.assertEqual(result.critical_count, 0)

    def test_assessments_length_matches_input(self):
        algos = ["AES-256", "RSA-2048", "SHA-256"]
        result = self.analyzer.assess_system(algos)
        self.assertEqual(len(result.assessments), 3)


# ─────────────────────────────────────────────────────────────────────
# assess_dof() — DOF's own stack
# ─────────────────────────────────────────────────────────────────────

class TestAssessDOF(unittest.TestCase):

    def setUp(self):
        self.result = PQCAnalyzer().assess_dof()

    def test_returns_system_assessment(self):
        self.assertIsInstance(self.result, SystemAssessment)

    def test_dof_is_vulnerable(self):
        # DOF uses ECDSA-secp256k1, Ed25519, ECC-P256 — all BROKEN
        self.assertEqual(self.result.overall_status, "VULNERABLE")

    def test_dof_has_three_criticals(self):
        # ECDSA-secp256k1, Ed25519, ECC-P256
        self.assertGreaterEqual(self.result.critical_count, 3)

    def test_dof_has_safe_algorithms(self):
        # keccak256, SHA-256, AES-256 are safe
        self.assertGreater(self.result.safe_count, 0)

    def test_dof_migration_plan_non_empty(self):
        self.assertGreater(len(self.result.migration_plan), 0)

    def test_dof_algorithms_includes_key_ones(self):
        found = self.result.algorithms_found
        for algo in ("ECDSA-secp256k1", "keccak256", "Ed25519"):
            self.assertIn(algo, found)


# ─────────────────────────────────────────────────────────────────────
# q_day_estimate()
# ─────────────────────────────────────────────────────────────────────

class TestQDayEstimate(unittest.TestCase):

    def setUp(self):
        self.estimate = PQCAnalyzer().q_day_estimate()

    def test_returns_dict(self):
        self.assertIsInstance(self.estimate, dict)

    def test_required_keys(self):
        for key in ("optimistic", "moderate", "conservative",
                    "qubits_needed_rsa2048", "qubits_needed_ecc256",
                    "recommendation", "harvest_now_decrypt_later"):
            self.assertIn(key, self.estimate, f"Missing key: {key}")

    def test_harvest_now_is_active_threat(self):
        self.assertIn("ACTIVE", self.estimate["harvest_now_decrypt_later"])

    def test_recommendation_mentions_migration(self):
        self.assertIn("migration", self.estimate["recommendation"].lower())


# ─────────────────────────────────────────────────────────────────────
# report()
# ─────────────────────────────────────────────────────────────────────

class TestReport(unittest.TestCase):

    def setUp(self):
        self.analyzer = PQCAnalyzer()

    def test_report_is_string(self):
        result = self.analyzer.assess_system(["AES-256"])
        self.assertIsInstance(self.analyzer.report(result), str)

    def test_report_contains_status(self):
        result = self.analyzer.assess_system(["AES-256"])
        report = self.analyzer.report(result)
        self.assertIn("QUANTUM_READY", report)

    def test_report_vulnerable_shows_fail(self):
        result = self.analyzer.assess_system(["RSA-2048"])
        report = self.analyzer.report(result)
        self.assertIn("VULNERABLE", report)

    def test_report_shows_migration_plan(self):
        result = self.analyzer.assess_system(["RSA-2048"])
        report = self.analyzer.report(result)
        self.assertIn("Migration Plan", report)

    def test_report_shows_algorithm_names(self):
        result = self.analyzer.assess_system(["AES-256", "RSA-2048"])
        report = self.analyzer.report(result)
        self.assertIn("AES-256", report)
        self.assertIn("RSA-2048", report)

    def test_report_shows_critical_count(self):
        result = self.analyzer.assess_dof()
        report = self.analyzer.report(result)
        self.assertIn("CRITICAL", report)


# ─────────────────────────────────────────────────────────────────────
# Convenience functions
# ─────────────────────────────────────────────────────────────────────

class TestConvenienceFunctions(unittest.TestCase):

    def test_assess_dof_returns_system_assessment(self):
        result = assess_dof()
        self.assertIsInstance(result, SystemAssessment)

    def test_assess_algorithm_returns_pqc_assessment(self):
        result = assess_algorithm("SHA-256")
        self.assertIsInstance(result, PQCAssessment)

    def test_assess_algorithm_correct_status(self):
        self.assertEqual(assess_algorithm("AES-256").status, "SAFE")
        self.assertEqual(assess_algorithm("RSA-2048").status, "BROKEN")


if __name__ == "__main__":
    unittest.main()
