import unittest

from constitution.update_coordinator import (
    ConstitutionUpdateCoordinator,
    InsufficientQuorumError,
)


class TestConstitutionUpdateCoordinator(unittest.TestCase):

    def setUp(self):
        self.nodes = ["node-A", "node-B", "node-C"]
        self.coordinator = ConstitutionUpdateCoordinator(self.nodes)
        self.rules = {"max_actions": 10, "allow_external": False}

    def test_propose_creates_proposal(self):
        vh = self.coordinator.propose_update(self.rules, "node-A")
        proposal = self.coordinator.get_proposal(vh)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.version_hash, vh)
        self.assertEqual(proposal.proposed_by, "node-A")
        self.assertFalse(proposal.committed)

    def test_vote_registered(self):
        vh = self.coordinator.propose_update(self.rules, "node-A")
        self.coordinator.cast_vote(vh, "node-B")
        proposal = self.coordinator.get_proposal(vh)
        self.assertIn("node-B", proposal.votes)

    def test_commit_fails_without_quorum(self):
        vh = self.coordinator.propose_update(self.rules, "node-A")
        self.coordinator.cast_vote(vh, "node-A")
        with self.assertRaises(InsufficientQuorumError):
            self.coordinator.try_commit(vh)

    def test_commit_succeeds_with_quorum(self):
        vh = self.coordinator.propose_update(self.rules, "node-A")
        self.coordinator.cast_vote(vh, "node-A")
        self.coordinator.cast_vote(vh, "node-B")
        self.coordinator.cast_vote(vh, "node-C")
        result = self.coordinator.try_commit(vh)
        self.assertTrue(result)

    def test_commit_exact_quorum(self):
        # 2/3 = 0.6667, use quorum=0.66 so 2/3 nodes is exactly enough
        coord = ConstitutionUpdateCoordinator(self.nodes, quorum=0.66)
        vh = coord.propose_update(self.rules, "node-A")
        coord.cast_vote(vh, "node-A")
        coord.cast_vote(vh, "node-B")
        result = coord.try_commit(vh)
        self.assertTrue(result)

    def test_committed_count_increments(self):
        self.assertEqual(self.coordinator.committed_count, 0)
        vh = self.coordinator.propose_update(self.rules, "node-A")
        self.coordinator.cast_vote(vh, "node-A")
        self.coordinator.cast_vote(vh, "node-B")
        self.coordinator.cast_vote(vh, "node-C")
        self.coordinator.try_commit(vh)
        self.assertEqual(self.coordinator.committed_count, 1)

    def test_duplicate_vote_ignored(self):
        vh = self.coordinator.propose_update(self.rules, "node-A")
        self.coordinator.cast_vote(vh, "node-A")
        self.coordinator.cast_vote(vh, "node-A")
        proposal = self.coordinator.get_proposal(vh)
        self.assertEqual(len(proposal.votes), 1)

    def test_proposal_hash_deterministic(self):
        vh1 = self.coordinator.propose_update(self.rules, "node-A")
        coord2 = ConstitutionUpdateCoordinator(self.nodes)
        vh2 = coord2.propose_update(self.rules, "node-B")
        self.assertEqual(vh1, vh2)


if __name__ == "__main__":
    unittest.main()
