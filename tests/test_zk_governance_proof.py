"""
Tests unitarios para ZK Governance Proof y Batch Prover.

Verifica generación, verificación, tamper detection, Merkle batching,
inclusion proofs, y formato de attestation payload.
"""

import unittest
import os
import json
import tempfile
import shutil

from core.zk_governance_proof import (
    GovernanceProof,
    GovernanceProofGenerator,
    _keccak256,
    _canonical_json,
    _hash_governance_input,
)
from core.zk_batch_prover import GovernanceBatchProver, BatchExport


class TestKeccak256(unittest.TestCase):
    """Tests para la función de hash keccak256."""

    def test_deterministic_hash(self):
        """El mismo input siempre produce el mismo hash."""
        data = b"governance decision"
        h1 = _keccak256(data)
        h2 = _keccak256(data)
        self.assertEqual(h1, h2)

    def test_different_inputs_different_hashes(self):
        """Inputs diferentes producen hashes diferentes."""
        h1 = _keccak256(b"input_a")
        h2 = _keccak256(b"input_b")
        self.assertNotEqual(h1, h2)

    def test_hash_length(self):
        """SHA3-256 produce un hash de 64 caracteres hex."""
        h = _keccak256(b"test")
        self.assertEqual(len(h), 64)


class TestCanonicalJson(unittest.TestCase):
    """Tests para serialización JSON canónica."""

    def test_sorted_keys(self):
        """Las claves se ordenan alfabéticamente."""
        d1 = {"b": 1, "a": 2}
        d2 = {"a": 2, "b": 1}
        self.assertEqual(_canonical_json(d1), _canonical_json(d2))

    def test_no_spaces(self):
        """No hay espacios extra en la serialización."""
        result = _canonical_json({"key": "value"})
        self.assertNotIn(" ", result)


class TestProofGeneration(unittest.TestCase):
    """Tests para generación de GovernanceProof."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmp_dir, "test_proofs.jsonl")
        self.gen = GovernanceProofGenerator(log_path=self.log_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_proof_generation_pass(self):
        """Genera un proof PASS cuando no hay violaciones."""
        proof = self.gen.generate_proof(
            violations=[],
            warnings=["[HAS_SOURCES] Should include source URLs"],
            score=1.0,
            rule_ids=["HAS_SOURCES"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.assertIsInstance(proof, GovernanceProof)
        self.assertEqual(proof.verdict, "PASS")
        self.assertEqual(proof.violations_count, 0)
        self.assertEqual(proof.warnings_count, 1)
        self.assertEqual(proof.score, 1.0)
        self.assertEqual(len(proof.proof_hash), 64)
        self.assertEqual(len(proof.input_hash), 64)

    def test_proof_generation_fail(self):
        """Genera un proof FAIL cuando hay violaciones."""
        proof = self.gen.generate_proof(
            violations=["[NO_EMPTY_OUTPUT] Output cannot be empty"],
            warnings=[],
            score=0.0,
            rule_ids=["NO_EMPTY_OUTPUT"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.assertEqual(proof.verdict, "FAIL")
        self.assertEqual(proof.violations_count, 1)
        self.assertEqual(proof.score, 0.0)

    def test_proof_structure_complete(self):
        """El proof tiene todos los campos requeridos."""
        proof = self.gen.generate_proof(
            violations=[],
            warnings=[],
            score=1.0,
            rule_ids=["NO_HALLUCINATION_CLAIM", "LANGUAGE_COMPLIANCE"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        d = proof.to_dict()
        required_keys = {
            "proof_hash", "input_hash", "timestamp", "verdict",
            "rule_ids", "violations_count", "warnings_count", "score",
        }
        self.assertEqual(set(d.keys()), required_keys)

    def test_proof_deterministic(self):
        """Mismo input produce mismo proof_hash."""
        kwargs = dict(
            violations=["[X] fail"],
            warnings=["[Y] warn"],
            score=0.5,
            rule_ids=["X", "Y"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        p1 = self.gen.generate_proof(**kwargs)
        p2 = self.gen.generate_proof(**kwargs)
        self.assertEqual(p1.proof_hash, p2.proof_hash)
        self.assertEqual(p1.input_hash, p2.input_hash)

    def test_proof_logged_to_jsonl(self):
        """El proof se persiste en JSONL."""
        self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.assertTrue(os.path.exists(self.log_path))
        with open(self.log_path) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertIn("proof_hash", entry)
        self.assertIn("verdict", entry)


class TestProofVerification(unittest.TestCase):
    """Tests para verificación de proofs."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_proof_verification_valid(self):
        """Un proof generado se verifica correctamente."""
        violations = ["[NO_EMPTY_OUTPUT] Output cannot be empty"]
        warnings = ["[HAS_SOURCES] Should include source URLs"]
        score = 0.0

        proof = self.gen.generate_proof(
            violations=violations,
            warnings=warnings,
            score=score,
            rule_ids=["NO_EMPTY_OUTPUT", "HAS_SOURCES"],
            timestamp="2026-03-27T12:00:00+00:00",
        )

        result = self.gen.verify_proof(proof, violations, warnings, score)
        self.assertTrue(result)

    def test_proof_verification_wrong_violations(self):
        """Verificación falla si las violations cambian."""
        violations = ["[X] original violation"]
        proof = self.gen.generate_proof(
            violations=violations, warnings=[], score=0.0,
            rule_ids=["X"],
            timestamp="2026-03-27T12:00:00+00:00",
        )

        tampered = ["[X] tampered violation"]
        result = self.gen.verify_proof(proof, tampered, [], 0.0)
        self.assertFalse(result)

    def test_proof_verification_wrong_score(self):
        """Verificación falla si el score cambia."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=[],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        result = self.gen.verify_proof(proof, [], [], 0.5)
        self.assertFalse(result)

    def test_proof_verification_wrong_warnings(self):
        """Verificación falla si los warnings cambian."""
        warnings = ["[W1] original"]
        proof = self.gen.generate_proof(
            violations=[], warnings=warnings, score=1.0,
            rule_ids=["W1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        result = self.gen.verify_proof(proof, [], ["[W1] modified"], 1.0)
        self.assertFalse(result)


class TestTamperDetection(unittest.TestCase):
    """Tests para detección de manipulación."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_tamper_proof_hash(self):
        """Detecta si proof_hash fue alterado."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        # Crear proof con hash alterado
        tampered = GovernanceProof(
            proof_hash="a" * 64,  # hash falso
            input_hash=proof.input_hash,
            timestamp=proof.timestamp,
            verdict=proof.verdict,
            rule_ids=proof.rule_ids,
            violations_count=proof.violations_count,
            warnings_count=proof.warnings_count,
            score=proof.score,
        )
        result = self.gen.verify_proof(tampered, [], [], 1.0)
        self.assertFalse(result)

    def test_tamper_input_hash(self):
        """Detecta si input_hash fue alterado."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        tampered = GovernanceProof(
            proof_hash=proof.proof_hash,
            input_hash="b" * 64,  # hash falso
            timestamp=proof.timestamp,
            verdict=proof.verdict,
            rule_ids=proof.rule_ids,
        )
        result = self.gen.verify_proof(tampered, [], [], 1.0)
        self.assertFalse(result)

    def test_tamper_verdict(self):
        """Detecta si el verdict fue alterado (PASS->FAIL)."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        tampered = GovernanceProof(
            proof_hash=proof.proof_hash,
            input_hash=proof.input_hash,
            timestamp=proof.timestamp,
            verdict="FAIL",  # alterado
            rule_ids=proof.rule_ids,
        )
        result = self.gen.verify_proof(tampered, [], [], 1.0)
        self.assertFalse(result)


class TestBatchMerkleRoot(unittest.TestCase):
    """Tests para batch prover con Merkle tree."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )
        self.prover = GovernanceBatchProver(
            log_path=os.path.join(self.tmp_dir, "batches.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_batch_root(self):
        """Batch vacío retorna root vacío."""
        root = self.prover.get_merkle_root()
        self.assertEqual(root, "")

    def test_single_proof_root(self):
        """Batch con un solo proof genera root válido."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.prover.add_proof(proof)
        root = self.prover.get_merkle_root()
        self.assertIsInstance(root, str)
        self.assertTrue(len(root) > 0)

    def test_multiple_proofs_root(self):
        """Batch con múltiples proofs genera Merkle root."""
        for i in range(5):
            proof = self.gen.generate_proof(
                violations=[] if i % 2 == 0 else [f"[R{i}] violation"],
                warnings=[],
                score=1.0 if i % 2 == 0 else 0.0,
                rule_ids=[f"R{i}"],
                timestamp=f"2026-03-27T12:0{i}:00+00:00",
            )
            self.prover.add_proof(proof)

        root = self.prover.get_merkle_root()
        self.assertEqual(len(root), 64)
        self.assertEqual(self.prover.proof_count, 5)

    def test_merkle_root_deterministic(self):
        """El mismo set de proofs produce el mismo Merkle root."""
        proofs = []
        for i in range(3):
            p = self.gen.generate_proof(
                violations=[], warnings=[], score=1.0,
                rule_ids=[f"R{i}"],
                timestamp=f"2026-03-27T12:0{i}:00+00:00",
            )
            proofs.append(p)

        prover1 = GovernanceBatchProver(
            log_path=os.path.join(self.tmp_dir, "b1.jsonl")
        )
        prover2 = GovernanceBatchProver(
            log_path=os.path.join(self.tmp_dir, "b2.jsonl")
        )
        for p in proofs:
            prover1.add_proof(p)
            prover2.add_proof(p)

        self.assertEqual(prover1.get_merkle_root(), prover2.get_merkle_root())


class TestInclusionProof(unittest.TestCase):
    """Tests para verificación de inclusión en Merkle tree."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )
        self.prover = GovernanceBatchProver(
            log_path=os.path.join(self.tmp_dir, "batches.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_inclusion_proof_valid(self):
        """Un proof incluido se verifica correctamente."""
        proofs = []
        for i in range(4):
            p = self.gen.generate_proof(
                violations=[], warnings=[], score=1.0,
                rule_ids=[f"R{i}"],
                timestamp=f"2026-03-27T12:0{i}:00+00:00",
            )
            proofs.append(p)
            self.prover.add_proof(p)

        root = self.prover.get_merkle_root()
        for p in proofs:
            self.assertTrue(self.prover.verify_inclusion(p, root))

    def test_inclusion_proof_invalid(self):
        """Un proof no incluido falla la verificación."""
        for i in range(3):
            p = self.gen.generate_proof(
                violations=[], warnings=[], score=1.0,
                rule_ids=[f"R{i}"],
                timestamp=f"2026-03-27T12:0{i}:00+00:00",
            )
            self.prover.add_proof(p)

        # Proof externo no incluido en el batch
        external = self.gen.generate_proof(
            violations=["[X] external"],
            warnings=[], score=0.0,
            rule_ids=["X"],
            timestamp="2026-03-27T13:00:00+00:00",
        )

        root = self.prover.get_merkle_root()
        self.assertFalse(self.prover.verify_inclusion(external, root))

    def test_get_inclusion_proof_raises(self):
        """get_inclusion_proof lanza ValueError para proof no incluido."""
        p = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.prover.add_proof(p)

        external = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R2"],
            timestamp="2026-03-27T13:00:00+00:00",
        )

        with self.assertRaises(ValueError):
            self.prover.get_inclusion_proof(external)


class TestAttestationPayload(unittest.TestCase):
    """Tests para formato de attestation payload on-chain."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_attestation_payload_structure(self):
        """El payload tiene la estructura correcta para web3.py."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["NO_HALLUCINATION_CLAIM", "LANGUAGE_COMPLIANCE"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        payload = proof.to_attestation_payload()

        self.assertIn("method", payload)
        self.assertEqual(payload["method"], "submitGovernanceProof")
        self.assertIn("params", payload)
        self.assertIn("abi_types", payload)
        self.assertEqual(payload["chain_id"], 43114)

        params = payload["params"]
        self.assertTrue(params["proofHash"].startswith("0x"))
        self.assertTrue(params["inputHash"].startswith("0x"))
        self.assertIsInstance(params["verdict"], bool)
        self.assertTrue(params["verdict"])  # PASS
        self.assertIsInstance(params["timestamp"], int)
        self.assertEqual(params["ruleCount"], 2)
        self.assertEqual(params["score"], 10000)  # 1.0 * 10000

    def test_attestation_payload_fail_verdict(self):
        """Payload con verdict FAIL tiene verdict=false."""
        proof = self.gen.generate_proof(
            violations=["[X] failure"],
            warnings=[], score=0.0,
            rule_ids=["X"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        payload = proof.to_attestation_payload()
        self.assertFalse(payload["params"]["verdict"])
        self.assertEqual(payload["params"]["score"], 0)

    def test_attestation_payload_hash_length(self):
        """Los hashes en el payload tienen longitud correcta (0x + 64)."""
        proof = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        payload = proof.to_attestation_payload()
        self.assertEqual(len(payload["params"]["proofHash"]), 66)  # 0x + 64
        self.assertEqual(len(payload["params"]["inputHash"]), 66)


class TestBatchExport(unittest.TestCase):
    """Tests para exportación de batch con payload on-chain."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )
        self.prover = GovernanceBatchProver(
            log_path=os.path.join(self.tmp_dir, "batches.jsonl")
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_export_batch_structure(self):
        """El batch exportado tiene estructura completa."""
        for i in range(3):
            p = self.gen.generate_proof(
                violations=[] if i != 1 else ["[R1] fail"],
                warnings=[], score=1.0 if i != 1 else 0.0,
                rule_ids=[f"R{i}"],
                timestamp=f"2026-03-27T12:0{i}:00+00:00",
            )
            self.prover.add_proof(p)

        export = self.prover.export_batch("test-batch-001")

        self.assertIsInstance(export, BatchExport)
        self.assertEqual(export.batch_id, "test-batch-001")
        self.assertEqual(export.proof_count, 3)
        self.assertEqual(len(export.proof_hashes), 3)
        self.assertEqual(export.verdicts["PASS"], 2)
        self.assertEqual(export.verdicts["FAIL"], 1)
        self.assertTrue(len(export.merkle_root) > 0)

    def test_export_chain_payload(self):
        """El chain payload del batch es válido para web3.py."""
        p = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.prover.add_proof(p)

        export = self.prover.export_batch("batch-001")
        cp = export.chain_payload

        self.assertEqual(cp["method"], "submitBatchAttestation")
        self.assertEqual(cp["chain_id"], 43114)
        self.assertEqual(cp["params"]["batchId"], "batch-001")
        self.assertTrue(cp["params"]["merkleRoot"].startswith("0x"))
        self.assertEqual(cp["params"]["proofCount"], 1)

    def test_export_logged_to_jsonl(self):
        """El batch se persiste en JSONL."""
        p = self.gen.generate_proof(
            violations=[], warnings=[], score=1.0,
            rule_ids=["R1"],
            timestamp="2026-03-27T12:00:00+00:00",
        )
        self.prover.add_proof(p)
        self.prover.export_batch("batch-log-test")

        log_path = os.path.join(self.tmp_dir, "batches.jsonl")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["batch_id"], "batch-log-test")


class TestEnforceWithProof(unittest.TestCase):
    """Tests para integración enforce_with_proof()."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_enforce_with_proof_pass(self):
        """enforce_with_proof genera proof PASS para texto compliant."""
        from core.zk_governance_proof import GovernanceProofGenerator
        from core.governance import check_governance

        gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )

        text = (
            "The recommendation is to implement the following steps for "
            "improving system reliability and performance monitoring across "
            "all nodes in the mesh network. Next step: deploy to production."
        )

        result = check_governance(text)
        proof = gen.generate_proof_from_result(result)

        self.assertEqual(proof.verdict, "PASS")
        self.assertTrue(
            gen.verify_proof_from_result(proof, result)
        )

    def test_enforce_with_proof_fail(self):
        """enforce_with_proof genera proof FAIL para texto non-compliant."""
        from core.zk_governance_proof import GovernanceProofGenerator
        from core.governance import check_governance

        gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl")
        )

        text = ""  # empty -> violation

        result = check_governance(text)
        proof = gen.generate_proof_from_result(result)

        self.assertEqual(proof.verdict, "FAIL")
        self.assertTrue(
            gen.verify_proof_from_result(proof, result)
        )


class TestEnforceWithProofIntegration(unittest.TestCase):
    """Tests para la función enforce_with_proof integrada en governance."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_enforce_with_proof_function(self):
        """La función enforce_with_proof retorna resultado + proof."""
        from core.governance import enforce_with_proof

        text = (
            "The analysis shows that the system is performing well with "
            "recommendations for next step improvements in security and "
            "reliability across the distributed agent network."
        )

        result, proof = enforce_with_proof(
            text,
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl"),
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(proof)
        self.assertEqual(proof.verdict, "PASS" if result.passed else "FAIL")

    def test_enforce_with_proof_verifiable(self):
        """El proof generado por enforce_with_proof es verificable."""
        from core.governance import enforce_with_proof
        from core.zk_governance_proof import GovernanceProofGenerator

        text = (
            "This is a well-structured analysis with actionable recommendations. "
            "Next step: implement the proposed changes. "
            "Source: https://example.com/report"
        )

        result, proof = enforce_with_proof(
            text,
            log_path=os.path.join(self.tmp_dir, "proofs.jsonl"),
        )

        gen = GovernanceProofGenerator(
            log_path=os.path.join(self.tmp_dir, "verify.jsonl")
        )
        self.assertTrue(gen.verify_proof_from_result(proof, result))


if __name__ == "__main__":
    unittest.main()
