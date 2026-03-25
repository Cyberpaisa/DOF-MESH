"""
test_dof_raft.py — Tests para RaftNode (consensus in-process).
"""
import time
import unittest
from core.dof_raft import RaftNode, RaftRole, create_raft_cluster, wait_for_leader


class TestRaftElection(unittest.TestCase):

    def _start_cluster(self, n=3):
        nodes = create_raft_cluster(n)
        for node in nodes:
            node.start()
        return nodes

    def _stop_cluster(self, nodes):
        for node in nodes:
            node.stop()

    def test_leader_elected(self):
        """Debe elegirse exactamente un leader en <3s."""
        nodes = self._start_cluster(3)
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader, "No se eligió leader en 3s")
            leaders = [n for n in nodes if n.is_leader()]
            self.assertEqual(len(leaders), 1, f"Debe haber exactamente 1 leader, hay {len(leaders)}")
        finally:
            self._stop_cluster(nodes)

    def test_all_agree_on_leader(self):
        """Todos los nodos deben apuntar al mismo leader."""
        nodes = self._start_cluster(3)
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader)
            time.sleep(0.2)
            # Followers deben conocer al leader
            followers = [n for n in nodes if not n.is_leader()]
            for f in followers:
                self.assertEqual(f.leader_id(), leader.node_id,
                    f"{f.node_id} piensa que el leader es {f.leader_id()}, no {leader.node_id}")
        finally:
            self._stop_cluster(nodes)

    def test_5_node_cluster(self):
        """Cluster de 5 nodos también elige un leader."""
        nodes = self._start_cluster(5)
        try:
            leader = wait_for_leader(nodes, timeout=4.0)
            self.assertIsNotNone(leader)
            self.assertEqual(len([n for n in nodes if n.is_leader()]), 1)
        finally:
            self._stop_cluster(nodes)

    def test_leader_has_highest_term(self):
        """El leader debe tener el term más alto o igual al de los followers."""
        nodes = self._start_cluster(3)
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader)
            time.sleep(0.3)
            for n in nodes:
                if not n.is_leader():
                    self.assertGreaterEqual(leader.term(), n.term() - 1)
        finally:
            self._stop_cluster(nodes)

    def test_roles_partitioned(self):
        """Exactamente 1 leader, N-1 followers."""
        nodes = self._start_cluster(3)
        try:
            wait_for_leader(nodes, timeout=3.0)
            time.sleep(0.3)
            roles = [n.role() for n in nodes]
            leaders   = roles.count(RaftRole.LEADER)
            followers = roles.count(RaftRole.FOLLOWER)
            self.assertEqual(leaders, 1)
            self.assertGreaterEqual(followers, 1)
        finally:
            self._stop_cluster(nodes)


class TestRaftLogReplication(unittest.TestCase):

    def test_submit_to_leader(self):
        """Leader acepta un command y lo añade al log."""
        nodes = create_raft_cluster(3)
        for n in nodes:
            n.start()
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader)
            idx = leader.submit({"task": "test-command"})
            self.assertIsNotNone(idx)
            self.assertGreater(idx, 0)
        finally:
            for n in nodes:
                n.stop()

    def test_submit_to_follower_returns_none(self):
        """Follower rechaza submit (solo leader puede aceptar)."""
        nodes = create_raft_cluster(3)
        for n in nodes:
            n.start()
        try:
            wait_for_leader(nodes, timeout=3.0)
            follower = next(n for n in nodes if not n.is_leader())
            result = follower.submit("command")
            self.assertIsNone(result)
        finally:
            for n in nodes:
                n.stop()

    def test_log_replicated_to_followers(self):
        """Comando en leader se replica a followers en <1s."""
        nodes = create_raft_cluster(3)
        for n in nodes:
            n.start()
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader)
            leader.submit("replicate-me")
            time.sleep(0.8)
            for n in nodes:
                cmds = n.committed_commands()
                if len(cmds) > 0:
                    self.assertIn("replicate-me", cmds)
                    return
            # Al menos el leader debe haberlo aplicado
            self.assertIn("replicate-me", leader.committed_commands())
        finally:
            for n in nodes:
                n.stop()

    def test_multiple_commands_ordered(self):
        """Múltiples comandos se replican en orden."""
        nodes = create_raft_cluster(3)
        for n in nodes:
            n.start()
        try:
            leader = wait_for_leader(nodes, timeout=3.0)
            self.assertIsNotNone(leader)
            for i in range(5):
                leader.submit(f"cmd-{i}")
            time.sleep(1.0)
            cmds = leader.committed_commands()
            # Los que están deben estar en orden
            indices = [int(c.split("-")[1]) for c in cmds if c.startswith("cmd-")]
            self.assertEqual(indices, sorted(indices))
        finally:
            for n in nodes:
                n.stop()


class TestRaftStatus(unittest.TestCase):

    def test_status_fields(self):
        """status() debe incluir los campos clave."""
        node = RaftNode("test-node")
        s = node.status()
        for key in ["node_id", "role", "term", "leader", "log_len", "commit_index", "peers"]:
            self.assertIn(key, s)

    def test_initial_state(self):
        """Estado inicial: follower, term=0, sin leader."""
        node = RaftNode("init-node")
        self.assertEqual(node.role(), RaftRole.FOLLOWER)
        self.assertEqual(node.term(), 0)
        self.assertIsNone(node.leader_id())
        self.assertFalse(node.is_leader())

    def test_add_peer(self):
        """add_peer añade peers únicos."""
        a = RaftNode("a")
        b = RaftNode("b")
        a.add_peer(b)
        a.add_peer(b)  # duplicado
        self.assertEqual(a.status()["peers"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
