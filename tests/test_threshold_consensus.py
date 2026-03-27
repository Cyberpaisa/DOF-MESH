"""
Tests para core/threshold_consensus.py
Threshold Consensus para DOF Mesh — unittest
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.threshold_consensus import (
    ThresholdConsensus,
    Proposal,
    Vote,
)


class TestThresholdConsensus(unittest.TestCase):
    """Tests para ThresholdConsensus."""

    def setUp(self):
        self.tc = ThresholdConsensus(threshold=2 / 3)
        self.tc.register_node("node-1")
        self.tc.register_node("node-2")
        self.tc.register_node("node-3")

    def _make_sig(self, node_id: str, proposal_id: str) -> str:
        """Genera una signature determinista para testing."""
        return hashlib.sha256(f"{node_id}:{proposal_id}".encode()).hexdigest()

    def test_register_nodes(self):
        """Registrar nodos correctamente."""
        tc = ThresholdConsensus()
        self.assertTrue(tc.register_node("a"))
        self.assertTrue(tc.register_node("b"))
        self.assertFalse(tc.register_node("a"))  # duplicado
        self.assertEqual(tc.node_count, 2)

    def test_propose_decision(self):
        """Crear una propuesta genera un Proposal valido."""
        proposal = self.tc.propose("upgrade-v2", proposer="node-1")
        self.assertIsInstance(proposal, Proposal)
        self.assertEqual(proposal.decision, "upgrade-v2")
        self.assertEqual(proposal.proposer, "node-1")
        self.assertEqual(proposal.result, "PENDING")
        self.assertIsNotNone(proposal.id)
        self.assertEqual(len(proposal.votes), 0)

    def test_propose_unregistered_node_fails(self):
        """Propuesta de nodo no registrado lanza ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.tc.propose("test", proposer="ghost-node")
        self.assertIn("no esta registrado", str(ctx.exception))

    def test_vote_approve(self):
        """Votar aprobacion registra el voto correctamente."""
        proposal = self.tc.propose("test-decision", proposer="node-1")
        sig = self._make_sig("node-1", proposal.id)
        vote = self.tc.vote("node-1", proposal.id, True, sig)

        self.assertIsInstance(vote, Vote)
        self.assertEqual(vote.node_id, "node-1")
        self.assertTrue(vote.approve)
        self.assertEqual(vote.signature, sig)

    def test_vote_reject(self):
        """Votar rechazo registra el voto correctamente."""
        proposal = self.tc.propose("test-decision", proposer="node-1")
        sig = self._make_sig("node-2", proposal.id)
        vote = self.tc.vote("node-2", proposal.id, False, sig)

        self.assertFalse(vote.approve)
        self.assertEqual(vote.node_id, "node-2")

    def test_threshold_reached_approved(self):
        """Propuesta aprobada cuando se alcanza el threshold (2/3)."""
        proposal = self.tc.propose("deploy-contract", proposer="node-1")

        # 2 de 3 votan si -> 66.7% >= 66.7% -> APPROVED
        self.tc.vote("node-1", proposal.id, True, self._make_sig("node-1", proposal.id))
        self.tc.vote("node-2", proposal.id, True, self._make_sig("node-2", proposal.id))

        result = self.tc.tally(proposal.id)
        self.assertEqual(result, "APPROVED")
        self.assertEqual(proposal.result, "APPROVED")
        self.assertIsNotNone(proposal.resolved_at)

    def test_threshold_not_reached_pending(self):
        """Propuesta queda PENDING si no se alcanza threshold."""
        proposal = self.tc.propose("risky-change", proposer="node-1")

        # Solo 1 de 3 vota si -> 33% < 66.7%
        self.tc.vote("node-1", proposal.id, True, self._make_sig("node-1", proposal.id))

        result = self.tc.tally(proposal.id)
        self.assertEqual(result, "PENDING")

    def test_majority_reject(self):
        """Propuesta rechazada cuando mayoria vota no."""
        proposal = self.tc.propose("bad-idea", proposer="node-1")

        # 2 de 3 votan no -> imposible alcanzar 2/3 aprobacion
        self.tc.vote("node-1", proposal.id, False, self._make_sig("node-1", proposal.id))
        self.tc.vote("node-2", proposal.id, False, self._make_sig("node-2", proposal.id))

        result = self.tc.tally(proposal.id)
        self.assertEqual(result, "REJECTED")

    def test_collective_signature(self):
        """Firma colectiva combina signatures aprobadas."""
        proposal = self.tc.propose("sign-this", proposer="node-1")

        sig1 = self._make_sig("node-1", proposal.id)
        sig2 = self._make_sig("node-2", proposal.id)
        self.tc.vote("node-1", proposal.id, True, sig1)
        self.tc.vote("node-2", proposal.id, True, sig2)
        # node-3 vota no
        self.tc.vote("node-3", proposal.id, False, self._make_sig("node-3", proposal.id))

        collective = self.tc.get_collective_signature(proposal.id)
        self.assertIsNotNone(collective)
        self.assertEqual(len(collective), 64)  # sha256 hex

        # Verificar que es determinista
        expected_sigs = sorted([sig1, sig2])
        expected = hashlib.sha256(":".join(expected_sigs).encode()).hexdigest()
        self.assertEqual(collective, expected)

    def test_collective_signature_no_approvals(self):
        """Firma colectiva es None si no hay aprobaciones."""
        proposal = self.tc.propose("nothing", proposer="node-1")
        self.tc.vote("node-1", proposal.id, False, "sig")

        collective = self.tc.get_collective_signature(proposal.id)
        self.assertIsNone(collective)

    def test_verify_threshold(self):
        """Verificar threshold con y sin votos suficientes."""
        proposal = self.tc.propose("check-threshold", proposer="node-1")

        self.tc.vote("node-1", proposal.id, True, self._make_sig("node-1", proposal.id))
        # 1/3 < 2/3 -> False
        self.assertFalse(self.tc.verify_threshold(proposal.id))

        self.tc.vote("node-2", proposal.id, True, self._make_sig("node-2", proposal.id))
        # 2/3 >= 2/3 -> True
        self.assertTrue(self.tc.verify_threshold(proposal.id))

    def test_verify_threshold_custom(self):
        """Verificar con threshold customizado."""
        proposal = self.tc.propose("custom-threshold", proposer="node-1")
        self.tc.vote("node-1", proposal.id, True, self._make_sig("node-1", proposal.id))

        # 1/3 >= 0.3 -> True
        self.assertTrue(self.tc.verify_threshold(proposal.id, threshold=0.3))
        # 1/3 >= 0.5 -> False
        self.assertFalse(self.tc.verify_threshold(proposal.id, threshold=0.5))

    def test_duplicate_vote_rejected(self):
        """Voto duplicado del mismo nodo lanza ValueError."""
        proposal = self.tc.propose("double-vote", proposer="node-1")
        self.tc.vote("node-1", proposal.id, True, "sig1")

        with self.assertRaises(ValueError) as ctx:
            self.tc.vote("node-1", proposal.id, False, "sig2")
        self.assertIn("ya voto", str(ctx.exception))

    def test_vote_unregistered_node_fails(self):
        """Voto de nodo no registrado lanza ValueError."""
        proposal = self.tc.propose("test", proposer="node-1")
        with self.assertRaises(ValueError):
            self.tc.vote("ghost", proposal.id, True, "sig")

    def test_vote_nonexistent_proposal_fails(self):
        """Voto en propuesta inexistente lanza ValueError."""
        with self.assertRaises(ValueError):
            self.tc.vote("node-1", "fake-id", True, "sig")

    def test_vote_on_resolved_proposal_fails(self):
        """Voto en propuesta ya resuelta lanza ValueError."""
        proposal = self.tc.propose("resolved", proposer="node-1")
        self.tc.vote("node-1", proposal.id, True, self._make_sig("node-1", proposal.id))
        self.tc.vote("node-2", proposal.id, True, self._make_sig("node-2", proposal.id))
        self.tc.tally(proposal.id)  # APPROVED

        with self.assertRaises(ValueError) as ctx:
            self.tc.vote("node-3", proposal.id, True, "sig3")
        self.assertIn("ya fue resuelta", str(ctx.exception))

    def test_tally_nonexistent_proposal_fails(self):
        """Tally de propuesta inexistente lanza ValueError."""
        with self.assertRaises(ValueError):
            self.tc.tally("fake-id")

    def test_invalid_threshold_rejected(self):
        """Threshold fuera de rango lanza ValueError."""
        with self.assertRaises(ValueError):
            ThresholdConsensus(threshold=0.0)
        with self.assertRaises(ValueError):
            ThresholdConsensus(threshold=1.5)

    def test_list_proposals(self):
        """Listar propuestas retorna todas."""
        self.tc.propose("p1", proposer="node-1")
        self.tc.propose("p2", proposer="node-2")
        proposals = self.tc.list_proposals()
        self.assertEqual(len(proposals), 2)

    def test_proposal_to_dict(self):
        """Propuesta se serializa correctamente."""
        proposal = self.tc.propose("serialize-test", proposer="node-1")
        self.tc.vote("node-1", proposal.id, True, "sig1")
        d = proposal.to_dict()
        self.assertIn("id", d)
        self.assertIn("decision", d)
        self.assertIn("votes", d)
        self.assertIsInstance(d["votes"], dict)


if __name__ == "__main__":
    unittest.main()
