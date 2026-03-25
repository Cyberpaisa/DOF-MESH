"""
test_dof_raft_shard.py — Tests RaftShardManager.
"""
import time
import unittest
from core.dof_raft_shard import RaftShardManager


MACHINES = ["machine-a", "machine-b", "machine-c"]


class TestRaftShardManager(unittest.TestCase):

    def setUp(self):
        self.rsm = RaftShardManager(
            MACHINES, shard_count=3, replication_factor=2, raft_nodes_per_shard=3
        )
        self.rsm.start()

    def tearDown(self):
        self.rsm.stop()

    def test_all_shards_elect_leader(self):
        """Todos los shards deben tener leader en <5s."""
        ok = self.rsm.wait_all_leaders(timeout=5.0)
        self.assertTrue(ok, "No todos los shards eligieron leader en 5s")
        s = self.rsm.status()
        self.assertEqual(s["leaders_elected"], 3)

    def test_get_leader_for_shard(self):
        """get_leader(shard_id) retorna el nodo leader."""
        self.rsm.wait_all_leaders(timeout=5.0)
        for shard_id in range(3):
            leader = self.rsm.get_leader(shard_id, timeout=2.0)
            self.assertIsNotNone(leader, f"Shard {shard_id} sin leader")
            self.assertTrue(leader.is_leader())

    def test_get_leader_for_key(self):
        """get_leader_for_key enruta correctamente por clave."""
        self.rsm.wait_all_leaders(timeout=5.0)
        leader = self.rsm.get_leader_for_key("agent-architect")
        self.assertIsNotNone(leader)
        self.assertTrue(leader.is_leader())

    def test_submit_to_shard(self):
        """submit_to_shard envía comando al leader."""
        self.rsm.wait_all_leaders(timeout=5.0)
        idx = self.rsm.submit_to_shard(0, {"task": "analiza DOF Mesh"})
        self.assertIsNotNone(idx)
        self.assertGreater(idx, 0)

    def test_submit_for_key(self):
        """submit_for_key enruta la tarea al shard correcto."""
        self.rsm.wait_all_leaders(timeout=5.0)
        idx = self.rsm.submit_for_key("agent-guardian", {"action": "security audit"})
        self.assertIsNotNone(idx)

    def test_multiple_submits(self):
        """Múltiples submit al mismo shard — sin pérdida."""
        self.rsm.wait_all_leaders(timeout=5.0)
        indices = []
        for i in range(10):
            idx = self.rsm.submit_to_shard(1, f"task-{i}")
            if idx is not None:
                indices.append(idx)
        self.assertGreater(len(indices), 0)
        self.assertEqual(sorted(indices), list(range(1, len(indices) + 1)))

    def test_status_structure(self):
        """status() tiene los campos esperados."""
        s = self.rsm.status()
        for key in ["running", "shard_count", "leaders_elected", "raft_nodes_total", "shards"]:
            self.assertIn(key, s)
        self.assertEqual(s["shard_count"], 3)
        self.assertEqual(s["raft_nodes_total"], 9)  # 3 shards × 3 nodos

    def test_invalid_shard_raises(self):
        """submit_to_shard con shard inválido lanza ValueError."""
        with self.assertRaises(ValueError):
            self.rsm.submit_to_shard(999, "command")

    def test_shard_for_key_consistent(self):
        """La misma clave siempre va al mismo shard."""
        s1 = self.rsm.get_shard_for_key("agent-42")
        s2 = self.rsm.get_shard_for_key("agent-42")
        self.assertEqual(s1.id, s2.id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
