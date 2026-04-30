"""
Integration tests — DOF-MESH x Conflux Hackathon 2026
python3 -m unittest tests.test_conflux_integration -v
"""
import unittest
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = [pytest.mark.integration, pytest.mark.onchain, pytest.mark.slow]


class TestConfluxChainAdapterDryRun(unittest.TestCase):
    """DOFChainAdapter loads and works with conflux_testnet in dry_run mode."""

    def test_adapter_loads_conflux_testnet(self):
        """from_chain_name('conflux_testnet') must not crash."""
        from core.chain_adapter import DOFChainAdapter
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        self.assertIsNotNone(adapter)

    def test_conflux_testnet_contract_address(self):
        """Chain adapter must point to the deployed DOFProofRegistry."""
        from core.chain_adapter import DOFChainAdapter
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        contract = adapter.config.contract_address
        self.assertIsNotNone(contract, "conflux_testnet must have contract_address in chains_config.json")
        self.assertEqual(contract.lower(), "0x554cca8cebe30df95ceefffbb9ede5ba7c7a9b83")

    def test_publish_attestation_dry_run(self):
        """publish_attestation in dry_run mode must return a dict with tx_hash key."""
        from core.chain_adapter import DOFChainAdapter
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        result = adapter.publish_attestation(
            proof_hash="0xdeadbeef" + "0" * 56,
            agent_id=1687,
            metadata="test-attestation conflux"
        )
        self.assertIsInstance(result, dict)
        self.assertIn("tx_hash", result)


class TestConfluxFullCycleDryRun(unittest.TestCase):
    """Full 6-step governance cycle completes without error in dry_run mode."""

    def test_full_cycle_dry_run(self):
        """Run the full demo cycle (steps 1-5) in dry_run mode — must return status dry_run."""
        # Import steps directly from the demo module
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from conflux_demo import (
            AGENT_OUTPUT, AGENT_TASK,
            step1_constitution, step2_z3, step3_tracer, step4_proof, step5_attest,
        )

        gov = step1_constitution(AGENT_OUTPUT)
        self.assertTrue(gov["passed"], "Constitution must pass for governance-compliant output")
        self.assertGreater(gov["score"], 0.0)

        z3 = step2_z3(AGENT_OUTPUT, AGENT_TASK)
        self.assertEqual(z3["theorems_proven"], z3["total_theorems"], "All Z3 theorems must be PROVEN")

        tracer = step3_tracer(AGENT_OUTPUT, AGENT_TASK)
        self.assertGreater(tracer["total"], 0.0)
        self.assertLessEqual(tracer["total"], 1.0)

        proof = step4_proof(gov, z3, tracer)
        self.assertIn("proof_hash", proof)
        self.assertTrue(proof["proof_hash"].startswith("0x"))

        attest = step5_attest(proof["proof_hash"], proof["payload"], dry_run=True)
        self.assertEqual(attest["status"], "dry_run")
        self.assertIn("tx_hash", attest)
        self.assertIn("conflux", attest["chain"])


if __name__ == "__main__":
    unittest.main()
