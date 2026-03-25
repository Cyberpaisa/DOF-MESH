"""Tests for HyperionHTTPServer and HyperionClient."""
import json
import threading
import time
import unittest
import urllib.request
from core.hyperion_http import HyperionHTTPServer, HyperionClient
from core.hyperion_bridge import HyperionBridge


def start_test_server(port=18765):
    srv = HyperionHTTPServer(host="127.0.0.1", port=port, shard_count=5)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    time.sleep(0.3)
    return srv


class TestHyperionHTTP(unittest.TestCase):
    PORT = 18765

    @classmethod
    def setUpClass(cls):
        cls.srv = start_test_server(cls.PORT)
        cls.client = HyperionClient(f"http://127.0.0.1:{cls.PORT}")

    def test_health(self):
        self.assertTrue(self.client.health())

    def test_status(self):
        s = self.client.status()
        self.assertIn("queue", s)
        self.assertIn("uptime_s", s)

    def test_enqueue(self):
        r = self.client.enqueue("t-http-1", "agent-0", "test prompt")
        self.assertEqual(r["task_id"], "t-http-1")
        self.assertIn("shard", r)

    def test_enqueue_and_dequeue(self):
        self.client.enqueue("t-http-2", "agent-1", "hello")
        time.sleep(0.1)
        task = self.client.dequeue()
        self.assertIsNotNone(task)

    def test_dequeue_empty(self):
        # Drain first
        for _ in range(20):
            self.client.dequeue()
        task = self.client.dequeue()
        self.assertIsNone(task)

    def test_broadcast(self):
        r = self.client.broadcast("analiza DOF Mesh", agents=["a", "b", "c"])
        self.assertEqual(r["enqueued"], 3)
        self.assertEqual(len(r["task_ids"]), 3)

    def test_dequeue_by_shard(self):
        self.client.enqueue("t-shard-1", "agent-5", "shard test")
        time.sleep(0.1)
        # Try all shards to find it
        found = False
        for shard in range(5):
            task = self.client.dequeue(shard_id=shard)
            if task:
                found = True
                break
        self.assertTrue(found)

    def test_enqueue_auto_id(self):
        r = self.client.enqueue("", "agent-7", "auto id test")
        self.assertTrue(len(r["task_id"]) > 0)

    def test_request_count(self):
        before = self.client.status()["requests_total"]
        self.client.health()
        after = self.client.status()["requests_total"]
        self.assertGreater(after, before)


class TestHyperionBridge(unittest.TestCase):

    def setUp(self):
        HyperionBridge.reset()

    def test_send_message(self):
        h = HyperionBridge(machines=["m-a", "m-b", "m-c"], shard_count=5)
        tid = h.send_message("supervisor", "architect", {"task": "build"}, "swarm_task")
        self.assertIn("architect", tid)

    def test_queue_size_increases(self):
        h = HyperionBridge(machines=["m-a", "m-b"], shard_count=5)
        h.send_message("s", "agent-1", "task1")
        h.send_message("s", "agent-2", "task2")
        self.assertGreaterEqual(h.queue_size(), 2)

    def test_broadcast(self):
        h = HyperionBridge(machines=["m-a", "m-b", "m-c"], shard_count=5)
        ids = h.broadcast("supervisor", "analiza", nodes=["a", "b", "c"])
        self.assertEqual(len(ids), 3)

    def test_singleton(self):
        h1 = HyperionBridge(machines=["m-a"], shard_count=5)
        h2 = HyperionBridge()
        self.assertIs(h1, h2)

    def test_status(self):
        h = HyperionBridge(machines=["m-a", "m-b"], shard_count=5)
        h.send_message("s", "agent-x", "task")
        s = h.status()
        self.assertIn("queue", s)
        self.assertIn("dispatched_by_node", s)


if __name__ == "__main__":
    unittest.main()
