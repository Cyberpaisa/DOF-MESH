"""
Tests para core/cross_chain_identity.py
Cross-Chain Identity Bridge — unittest
"""

import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cross_chain_identity import (
    CrossChainIdentity,
    BridgedIdentity,
    IdentityRegistration,
    SUPPORTED_CHAINS,
)


class TestCrossChainIdentity(unittest.TestCase):
    """Tests para CrossChainIdentity."""

    def setUp(self):
        self.bridge = CrossChainIdentity()
        self.agent = "0xABCDef1234567890abcdef1234567890ABCDEF12"
        self.avax_chain = 43114
        self.base_chain = 8453
        self.tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    def test_register_identity(self):
        """Registrar identidad en una chain soportada."""
        reg = self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        self.assertIsInstance(reg, IdentityRegistration)
        self.assertEqual(reg.agent_address, self.agent.lower())
        self.assertEqual(reg.chain_id, self.avax_chain)
        self.assertEqual(reg.registration_tx, self.tx_hash)
        self.assertEqual(reg.timestamp, 1000000.0)
        self.assertIsNotNone(reg.proof_hash)
        self.assertEqual(len(reg.proof_hash), 64)  # sha256 hex

    def test_register_identity_default_timestamp(self):
        """Registrar identidad sin timestamp usa time.time()."""
        reg = self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash
        )
        self.assertGreater(reg.timestamp, 0)

    def test_bridge_avalanche_to_base(self):
        """Bridgear identidad de Avalanche a Base."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        bridged = self.bridge.bridge_identity(
            self.agent, self.avax_chain, self.base_chain
        )
        self.assertIsInstance(bridged, BridgedIdentity)
        self.assertEqual(bridged.agent_address, self.agent.lower())
        self.assertEqual(bridged.origin_chain, self.avax_chain)
        self.assertEqual(bridged.target_chain, self.base_chain)
        self.assertIsNotNone(bridged.proof_hash)
        self.assertIsNotNone(bridged.bridged_at)

    def test_verify_bridged_identity(self):
        """Verificar una identidad bridgeada valida."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        bridged = self.bridge.bridge_identity(
            self.agent, self.avax_chain, self.base_chain
        )
        result = self.bridge.verify_bridged_identity(
            bridged.proof_hash, self.base_chain
        )
        self.assertTrue(result)

    def test_verify_wrong_chain_fails(self):
        """Verificar con chain incorrecta retorna False."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        bridged = self.bridge.bridge_identity(
            self.agent, self.avax_chain, self.base_chain
        )
        # Verificar con chain equivocada (Celo en vez de Base)
        result = self.bridge.verify_bridged_identity(
            bridged.proof_hash, 42220
        )
        self.assertFalse(result)

    def test_invalid_chain_rejected(self):
        """Chain no soportada lanza ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.bridge.register_identity(self.agent, 99999, self.tx_hash)
        self.assertIn("99999", str(ctx.exception))
        self.assertIn("no soportada", str(ctx.exception))

    def test_invalid_target_chain_rejected(self):
        """Chain destino no soportada lanza ValueError."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash
        )
        with self.assertRaises(ValueError):
            self.bridge.bridge_identity(self.agent, self.avax_chain, 99999)

    def test_bridge_same_chain_rejected(self):
        """Bridge a la misma chain lanza ValueError."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash
        )
        with self.assertRaises(ValueError) as ctx:
            self.bridge.bridge_identity(
                self.agent, self.avax_chain, self.avax_chain
            )
        self.assertIn("diferentes", str(ctx.exception))

    def test_proof_tamper_detection(self):
        """Proof manipulado no pasa verificacion."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        bridged = self.bridge.bridge_identity(
            self.agent, self.avax_chain, self.base_chain
        )
        # Manipular el proof hash
        tampered_proof = "a" * 64
        result = self.bridge.verify_bridged_identity(tampered_proof, self.base_chain)
        self.assertFalse(result)

    def test_multiple_bridges_same_identity(self):
        """Un agente puede bridgear a multiples chains."""
        self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )

        b1 = self.bridge.bridge_identity(self.agent, self.avax_chain, self.base_chain)
        b2 = self.bridge.bridge_identity(self.agent, self.avax_chain, 42220)  # Celo
        b3 = self.bridge.bridge_identity(self.agent, self.avax_chain, 1)     # Ethereum

        # Todos deben tener proofs diferentes
        proofs = {b1.proof_hash, b2.proof_hash, b3.proof_hash}
        self.assertEqual(len(proofs), 3)

        # Todos deben verificar en su chain correspondiente
        self.assertTrue(self.bridge.verify_bridged_identity(b1.proof_hash, self.base_chain))
        self.assertTrue(self.bridge.verify_bridged_identity(b2.proof_hash, 42220))
        self.assertTrue(self.bridge.verify_bridged_identity(b3.proof_hash, 1))

        # Listar bridges del agente
        bridges = self.bridge.get_bridges_for_agent(self.agent)
        self.assertEqual(len(bridges), 3)

    def test_bridge_without_registration_fails(self):
        """Bridge sin registro previo lanza ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.bridge.bridge_identity(self.agent, self.avax_chain, self.base_chain)
        self.assertIn("No hay registro", str(ctx.exception))

    def test_proof_hash_deterministic(self):
        """El proof hash es determinista para los mismos inputs."""
        reg1 = self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        # Crear otra instancia y registrar con los mismos datos
        bridge2 = CrossChainIdentity()
        reg2 = bridge2.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        self.assertEqual(reg1.proof_hash, reg2.proof_hash)

    def test_supported_chains_list(self):
        """Lista de chains soportadas es correcta."""
        chains = self.bridge.list_supported_chains()
        self.assertIn("avalanche", chains)
        self.assertIn("base", chains)
        self.assertIn("celo", chains)
        self.assertIn("ethereum", chains)
        self.assertEqual(chains["avalanche"], 43114)

    def test_to_dict_serialization(self):
        """Los dataclasses se serializan correctamente."""
        reg = self.bridge.register_identity(
            self.agent, self.avax_chain, self.tx_hash, timestamp=1000000.0
        )
        d = reg.to_dict()
        self.assertIn("agent_address", d)
        self.assertIn("proof_hash", d)
        self.assertIsInstance(d, dict)

        bridged = self.bridge.bridge_identity(
            self.agent, self.avax_chain, self.base_chain
        )
        bd = bridged.to_dict()
        self.assertIn("origin_chain", bd)
        self.assertIn("target_chain", bd)


if __name__ == "__main__":
    unittest.main()
