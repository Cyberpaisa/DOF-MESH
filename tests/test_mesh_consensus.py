import unittest
from unittest.mock import Mock, patch
from core.mesh_consensus import ConsensusNode, ConsensusState, get_consensus_node


class TestMeshConsensus(unittest.TestCase):
    def test_node_created_with_correct_id(self):
        """Test that a node is created with the specified node_id."""
        node = ConsensusNode(node_id="test_node_1")
        self.assertEqual(node.node_id, "test_node_1")

    def test_initial_state_is_follower(self):
        """Test that a new node's initial state is FOLLOWER."""
        node = ConsensusNode(node_id="test_node_2")
        self.assertEqual(node.state, ConsensusState.FOLLOWER)

    def test_initial_term_is_zero(self):
        """Test that a new node's term starts at 0."""
        node = ConsensusNode(node_id="test_node_3")
        self.assertEqual(node.current_term, 0)

    def test_vote_returns_bool(self):
        """Test that the vote method returns a boolean."""
        node = ConsensusNode(node_id="test_node_4")
        result = node.vote(candidate_id="candidate_1", term=1)
        self.assertIsInstance(result, bool)

    def test_vote_accepts_higher_term(self):
        """Test that a node votes for a candidate with a higher term."""
        node = ConsensusNode(node_id="test_node_5")
        node.current_term = 1
        self.assertTrue(node.vote(candidate_id="candidate_2", term=2))
        self.assertEqual(node.voted_for, "candidate_2")
        self.assertEqual(node.current_term, 2)

    def test_vote_rejects_lower_term(self):
        """Test that a node rejects a vote request with a lower term."""
        node = ConsensusNode(node_id="test_node_6")
        node.current_term = 5
        self.assertFalse(node.vote(candidate_id="candidate_3", term=3))
        self.assertNotEqual(node.voted_for, "candidate_3")
        self.assertEqual(node.current_term, 5)

    def test_vote_rejects_same_term_if_already_voted(self):
        """Test that a node rejects a vote request in the same term if it already voted."""
        node = ConsensusNode(node_id="test_node_7")
        node.current_term = 4
        node.voted_for = "candidate_4"
        self.assertFalse(node.vote(candidate_id="candidate_5", term=4))
        self.assertEqual(node.voted_for, "candidate_4")

    def test_propose_returns_bool(self):
        """Test that the propose method returns a boolean."""
        node = ConsensusNode(node_id="test_node_8")
        result = node.propose(term=1)
        self.assertIsInstance(result, bool)

    def test_propose_accepts_higher_term(self):
        """Test that a node accepts a proposal with a higher term and becomes FOLLOWER."""
        node = ConsensusNode(node_id="test_node_9")
        node.current_term = 2
        node.state = ConsensusState.CANDIDATE
        self.assertTrue(node.propose(term=5))
        self.assertEqual(node.current_term, 5)
        self.assertEqual(node.state, ConsensusState.FOLLOWER)

    def test_propose_rejects_lower_term(self):
        """Test that a node rejects a proposal with a lower term."""
        node = ConsensusNode(node_id="test_node_10")
        node.current_term = 10
        node.state = ConsensusState.LEADER
        self.assertFalse(node.propose(term=8))
        self.assertEqual(node.current_term, 10)
        self.assertEqual(node.state, ConsensusState.LEADER)

    def test_append_entry_returns_bool(self):
        """Test that append_entry returns a boolean."""
        node = ConsensusNode(node_id="test_node_11")
        result = node.append_entry(term=1, entry_data="test")
        self.assertIsInstance(result, bool)

    def test_append_entry_accepts_higher_or_equal_term(self):
        """Test that append_entry succeeds if the entry term is >= current term."""
        node = ConsensusNode(node_id="test_node_12")
        node.current_term = 3
        self.assertTrue(node.append_entry(term=3, entry_data="data1"))
        self.assertTrue(node.append_entry(term=5, entry_data="data2"))
        self.assertEqual(node.current_term, 5)

    def test_append_entry_rejects_lower_term(self):
        """Test that append_entry fails if the entry term is lower than current term."""
        node = ConsensusNode(node_id="test_node_13")
        node.current_term = 7
        self.assertFalse(node.append_entry(term=4, entry_data="data3"))
        self.assertEqual(node.current_term, 7)

    def test_get_state_returns_consensus_state_enum(self):
        """Test that get_state returns a ConsensusState enum."""
        node = ConsensusNode(node_id="test_node_14")
        state = node.get_state()
        self.assertIsInstance(state, ConsensusState)

    def test_two_nodes_have_independent_state(self):
        """Test that two different nodes maintain independent state."""
        node1 = ConsensusNode(node_id="node_a")
        node2 = ConsensusNode(node_id="node_b")
        node1.current_term = 100
        node1.state = ConsensusState.LEADER
        self.assertEqual(node1.current_term, 100)
        self.assertEqual(node1.state, ConsensusState.LEADER)
        self.assertEqual(node2.current_term, 0)
        self.assertEqual(node2.state, ConsensusState.FOLLOWER)

    def test_singleton_per_node_id_returns_same_instance(self):
        """Test that get_consensus_node returns the same instance for the same node_id."""
        node1 = get_consensus_node(node_id="singleton_node")
        node2 = get_consensus_node(node_id="singleton_node")
        self.assertIs(node1, node2)

    def test_singleton_different_node_id_returns_different_instance(self):
        """Test that get_consensus_node returns different instances for different node_ids."""
        node1 = get_consensus_node(node_id="singleton_node_1")
        node2 = get_consensus_node(node_id="singleton_node_2")
        self.assertIsNot(node1, node2)

    def test_state_transition_follower_to_candidate(self):
        """Test that a node can transition from FOLLOWER to CANDIDATE."""
        node = ConsensusNode(node_id="test_node_15")
        node.become_candidate()
        self.assertEqual(node.state, ConsensusState.CANDIDATE)
        self.assertEqual(node.current_term, 1)

    def test_state_transition_candidate_to_leader(self):
        """Test that a node can transition from CANDIDATE to LEADER."""
        node = ConsensusNode(node_id="test_node_16")
        node.become_candidate()
        node.become_leader()
        self.assertEqual(node.state, ConsensusState.LEADER)

    def test_state_transition_leader_to_follower_on_higher_proposal(self):
        """Test that a LEADER becomes FOLLOWER on receiving a proposal with higher term."""
        node = ConsensusNode(node_id="test_node_17")
        node.become_candidate()
        node.become_leader()
        node.propose(term=10)
        self.assertEqual(node.state, ConsensusState.FOLLOWER)
        self.assertEqual(node.current_term, 10)

    def test_log_initialized_empty(self):
        """Test that the log is initialized as an empty list."""
        node = ConsensusNode(node_id="test_node_18")
        self.assertEqual(node.log, [])

    def test_append_entry_adds_to_log(self):
        """Test that a successful append_entry adds the entry to the log."""
        node = ConsensusNode(node_id="test_node_19")
        node.append_entry(term=1, entry_data="entry1")
        self.assertEqual(len(node.log), 1)
        self.assertEqual(node.log[0]['term'], 1)
        self.assertEqual(node.log[0]['data'], "entry1")

    def test_reset_vote_on_term_change(self):
        """Test that voted_for is reset when term changes."""
        node = ConsensusNode(node_id="test_node_20")
        node.vote(candidate_id="candidate_x", term=5)
        self.assertEqual(node.voted_for, "candidate_x")
        node.vote(candidate_id="candidate_y", term=8)
        self.assertEqual(node.voted_for, "candidate_y")


if __name__ == '__main__':
    unittest.main()
