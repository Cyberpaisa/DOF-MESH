"""Tests for core.hyperion_bridge — HyperionBridge singleton facade."""
import threading
import unittest
from unittest.mock import MagicMock, patch


def setUpModule():
    raise unittest.SkipTest("module removed in commit 6cd575e — internal only, pending restoration")


def _mock_sm():
    sm = MagicMock()
    shard = MagicMock()
    shard.id = "shard-0"
    sm.get_shard_for_key.return_value = shard
    sm.status.return_value = {"shards": 3, "machines": 3}
    return sm


def _mock_q():
    q = MagicMock()
    q.status.return_value = {
        "node_id": "hyperion-bridge", "shards": 3,
        "total_queued": 0, "enqueued_total": 0, "dequeued_total": 0, "wal": True,
    }
    q.qsize.return_value = 0
    q.dequeue.return_value = None
    return q


def _patch_deps():
    """Context manager: patches DOFShardManager + DistributedMeshQueue + NodeMesh."""
    return [
        patch("core.hyperion_bridge.DOFShardManager", return_value=_mock_sm()),
        patch("core.hyperion_bridge.DistributedMeshQueue", return_value=_mock_q()),
        patch("core.node_mesh.NodeMesh", side_effect=RuntimeError("no node_mesh in test")),
    ]


class _BridgeBase(unittest.TestCase):
    """Base: patch deps, create bridge, reset after."""

    def setUp(self):
        from core.hyperion_bridge import HyperionBridge
        HyperionBridge.reset()
        self._patches = _patch_deps()
        for p in self._patches:
            p.start()
        HyperionBridge.reset()
        from core.hyperion_bridge import HyperionBridge as HB
        self.bridge = HB(machines=["a", "b", "c"], shard_count=3)

    def tearDown(self):
        from core.hyperion_bridge import HyperionBridge
        HyperionBridge.reset()
        for p in self._patches:
            try:
                p.stop()
            except RuntimeError:
                pass


# ── Singleton ────────────────────────────────────────────────────────────────

class TestSingleton(_BridgeBase):
    def test_same_instance_on_second_call(self):
        from core.hyperion_bridge import HyperionBridge
        second = HyperionBridge()
        self.assertIs(self.bridge, second)

    def test_reset_produces_new_instance(self):
        from core.hyperion_bridge import HyperionBridge
        first = self.bridge
        HyperionBridge.reset()
        # Need fresh patches for the second construction
        for p in _patch_deps():
            p.start()
        second = HyperionBridge(machines=["a", "b", "c"], shard_count=3)
        self.assertIsNot(first, second)

    def test_thread_safe_same_instance(self):
        from core.hyperion_bridge import HyperionBridge
        results = []

        def _get():
            results.append(HyperionBridge())

        threads = [threading.Thread(target=_get) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(all(r is results[0] for r in results))

    def test_node_mesh_inactive_when_unavailable(self):
        self.assertIsNone(self.bridge._node_mesh)
        self.assertFalse(self.bridge.status()["node_mesh_active"])


# ── send_message ─────────────────────────────────────────────────────────────

class TestSendMessage(_BridgeBase):
    def test_returns_nonempty_string(self):
        tid = self.bridge.send_message("src", "dst", "hello")
        self.assertIsInstance(tid, str)
        self.assertTrue(len(tid) > 0)

    def test_task_id_contains_target_node(self):
        tid = self.bridge.send_message("a", "my-target", "data")
        self.assertIn("my-target", tid)

    def test_enqueues_to_distributed_queue(self):
        self.bridge.send_message("a", "b", "msg", "task")
        self.assertTrue(self.bridge._queue.enqueue.called)

    def test_tracks_dispatched_count(self):
        self.bridge.send_message("a", "node-x", "m1")
        self.bridge.send_message("a", "node-x", "m2")
        self.assertEqual(len(self.bridge._dispatched.get("node-x", [])), 2)

    def test_dict_content_converted_to_prompt(self):
        """Dict content should not raise."""
        tid = self.bridge.send_message("a", "b", {"task": "build it"}, "build")
        self.assertIsInstance(tid, str)

    def test_urgent_msg_type_sets_priority_zero(self):
        self.bridge.send_message("a", "b", "urgent!", "urgent")
        call_arg = self.bridge._queue.enqueue.call_args[0][0]
        self.assertEqual(call_arg.priority, 0)

    def test_normal_msg_type_sets_priority_one(self):
        self.bridge.send_message("a", "b", "regular", "task")
        call_arg = self.bridge._queue.enqueue.call_args[0][0]
        self.assertEqual(call_arg.priority, 1)

    def test_multiple_sends_accumulate_dispatched(self):
        for i in range(5):
            self.bridge.send_message("src", f"node-{i}", "data")
        self.assertEqual(len(self.bridge._dispatched), 5)


# ── broadcast ────────────────────────────────────────────────────────────────

class TestBroadcast(_BridgeBase):
    def test_returns_list(self):
        result = self.bridge.broadcast("src", "hello")
        self.assertIsInstance(result, list)

    def test_default_targets_count(self):
        # Default: architect, researcher, guardian, verifier, narrator, devops
        result = self.bridge.broadcast("src", "msg")
        self.assertEqual(len(result), 6)

    def test_custom_nodes(self):
        result = self.bridge.broadcast("src", "msg", nodes=["alpha", "beta"])
        self.assertEqual(len(result), 2)

    def test_all_task_ids_are_strings(self):
        result = self.bridge.broadcast("src", "data")
        self.assertTrue(all(isinstance(t, str) for t in result))

    def test_zero_nodes(self):
        result = self.bridge.broadcast("src", "msg", nodes=[])
        self.assertEqual(result, [])


# ── spawn_node ───────────────────────────────────────────────────────────────

class TestSpawnNode(_BridgeBase):
    def test_returns_task_id_string(self):
        tid = self.bridge.spawn_node("worker-1", "do something")
        self.assertIsInstance(tid, str)

    def test_calls_assign_agent(self):
        self.bridge.spawn_node("worker-2", "task")
        self.bridge._sm.assign_agent.assert_called_once_with("worker-2")

    def test_dispatches_spawn_message(self):
        self.bridge.spawn_node("worker-3", "task")
        call_arg = self.bridge._queue.enqueue.call_args[0][0]
        self.assertIn("spawn", call_arg.metadata.get("type", ""))


# ── status + queue_size ──────────────────────────────────────────────────────

class TestStatus(_BridgeBase):
    def test_returns_dict(self):
        self.assertIsInstance(self.bridge.status(), dict)

    def test_has_required_keys(self):
        s = self.bridge.status()
        for key in ("queue", "shards", "dispatched_by_node", "node_mesh_active"):
            self.assertIn(key, s)

    def test_dispatched_by_node_counts_sends(self):
        self.bridge.send_message("a", "target", "m1")
        self.bridge.send_message("a", "target", "m2")
        s = self.bridge.status()
        self.assertEqual(s["dispatched_by_node"].get("target"), 2)

    def test_queue_size_returns_int(self):
        self.assertIsInstance(self.bridge.queue_size(), int)

    def test_queue_size_starts_at_zero(self):
        self.assertEqual(self.bridge.queue_size(), 0)


# ── read_inbox ───────────────────────────────────────────────────────────────

class TestReadInbox(_BridgeBase):
    def test_returns_none_when_empty(self):
        result = self.bridge.read_inbox("some-node", timeout=0.01)
        self.assertIsNone(result)

    def test_calls_dequeue_with_shard(self):
        self.bridge.read_inbox("my-node", timeout=0.01)
        self.assertTrue(self.bridge._queue.dequeue.called)


if __name__ == "__main__":
    unittest.main()
