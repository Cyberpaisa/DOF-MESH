"""Tests for core/node_mesh.py — NodeMesh, registry, message bus, state."""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from core.node_mesh import MeshMessage, MeshNode, MeshState, NodeMesh


# ─── helpers ────────────────────────────────────────────

def _make_mesh(tmpdir: str) -> NodeMesh:
    """Create a NodeMesh using a temporary directory (no pollution to logs/)."""
    return NodeMesh(
        cwd=tmpdir,
        model="test-model",
        max_budget_usd=1.0,
        mesh_dir=os.path.join(tmpdir, "mesh"),
    )


# ─────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────

class TestDataclasses(unittest.TestCase):

    def test_mesh_node_defaults(self):
        n = MeshNode(node_id="n1", role="tester")
        self.assertEqual(n.node_id, "n1")
        self.assertEqual(n.role, "tester")
        self.assertEqual(n.status, "idle")
        self.assertIsNone(n.session_id)
        self.assertEqual(n.messages_sent, 0)
        self.assertEqual(n.messages_received, 0)
        self.assertIsInstance(n.tools, list)
        self.assertGreater(len(n.tools), 0)

    def test_mesh_message_defaults(self):
        m = MeshMessage(msg_id="m1", from_node="a", to_node="b", content="hi")
        self.assertEqual(m.msg_type, "task")
        self.assertFalse(m.read)
        self.assertIsNone(m.reply_to)
        self.assertGreater(m.timestamp, 0)

    def test_mesh_state_defaults(self):
        s = MeshState()
        self.assertEqual(s.total_nodes, 0)
        self.assertEqual(s.active_nodes, 0)
        self.assertEqual(s.pending_messages, 0)
        self.assertEqual(s.total_messages, 0)


# ─────────────────────────────────────────────────────────
# __init__
# ─────────────────────────────────────────────────────────

class TestInit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_mesh_dir(self):
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "mesh")))

    def test_creates_inbox_dir(self):
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "mesh", "inbox")))

    def test_empty_registry(self):
        self.assertEqual(len(self.mesh._nodes), 0)

    def test_model_stored(self):
        self.assertEqual(self.mesh.model, "test-model")

    def test_budget_stored(self):
        self.assertEqual(self.mesh.max_budget_usd, 1.0)

    def test_start_time_set(self):
        self.assertGreater(self.mesh.start_time, 0)
        self.assertLessEqual(self.mesh.start_time, time.time())


# ─────────────────────────────────────────────────────────
# register_node
# ─────────────────────────────────────────────────────────

class TestRegisterNode(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_registers_new_node(self):
        node = self.mesh.register_node("alpha", "researcher")
        self.assertEqual(node.node_id, "alpha")
        self.assertEqual(node.role, "researcher")

    def test_node_in_registry_after_register(self):
        self.mesh.register_node("alpha", "researcher")
        self.assertIn("alpha", self.mesh._nodes)

    def test_updates_existing_node_role(self):
        self.mesh.register_node("alpha", "researcher")
        updated = self.mesh.register_node("alpha", "guardian")
        self.assertEqual(updated.role, "guardian")

    def test_updates_existing_node_tools(self):
        self.mesh.register_node("alpha", "researcher")
        updated = self.mesh.register_node("alpha", "researcher", tools=["Read"])
        self.assertEqual(updated.tools, ["Read"])

    def test_updates_existing_node_model(self):
        self.mesh.register_node("alpha", "researcher")
        updated = self.mesh.register_node("alpha", "researcher", model="new-model")
        self.assertEqual(updated.model, "new-model")

    def test_persists_to_disk(self):
        self.mesh.register_node("alpha", "researcher")
        nodes_file = Path(self.tmpdir) / "mesh" / "nodes.json"
        self.assertTrue(nodes_file.exists())
        data = json.loads(nodes_file.read_text())
        self.assertIn("alpha", data)

    def test_creates_inbox_for_node(self):
        self.mesh.register_node("alpha", "researcher")
        inbox_dir = Path(self.tmpdir) / "mesh" / "inbox" / "alpha"
        self.assertTrue(inbox_dir.is_dir())

    def test_default_tools_assigned(self):
        node = self.mesh.register_node("alpha", "researcher")
        self.assertIn("Read", node.tools)
        self.assertIn("Bash", node.tools)

    def test_custom_tools(self):
        node = self.mesh.register_node("alpha", "researcher", tools=["Grep"])
        self.assertEqual(node.tools, ["Grep"])

    def test_survives_reload(self):
        self.mesh.register_node("alpha", "researcher")
        mesh2 = _make_mesh(self.tmpdir)
        self.assertIn("alpha", mesh2._nodes)
        self.assertEqual(mesh2._nodes["alpha"].role, "researcher")


# ─────────────────────────────────────────────────────────
# get_node
# ─────────────────────────────────────────────────────────

class TestGetNode(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_registered_node(self):
        self.mesh.register_node("alpha", "researcher")
        node = self.mesh.get_node("alpha")
        self.assertIsNotNone(node)
        self.assertEqual(node.node_id, "alpha")

    def test_returns_none_for_missing(self):
        result = self.mesh.get_node("nonexistent")
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────
# list_nodes
# ─────────────────────────────────────────────────────────

class TestListNodes(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_mesh(self):
        self.assertEqual(len(self.mesh.list_nodes()), 0)

    def test_lists_all_nodes(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh.register_node("c", "r3")
        self.assertEqual(len(self.mesh.list_nodes()), 3)

    def test_filter_by_status(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh._nodes["a"].status = "active"
        self.mesh._nodes["b"].status = "idle"
        active = self.mesh.list_nodes(status="active")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].node_id, "a")

    def test_filter_returns_empty_when_no_match(self):
        self.mesh.register_node("a", "r1")
        result = self.mesh.list_nodes(status="error")
        self.assertEqual(len(result), 0)


# ─────────────────────────────────────────────────────────
# remove_node
# ─────────────────────────────────────────────────────────

class TestRemoveNode(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_removes_existing_node(self):
        self.mesh.register_node("alpha", "researcher")
        result = self.mesh.remove_node("alpha")
        self.assertTrue(result)
        self.assertIsNone(self.mesh.get_node("alpha"))

    def test_returns_false_for_missing(self):
        result = self.mesh.remove_node("nonexistent")
        self.assertFalse(result)

    def test_persists_removal(self):
        self.mesh.register_node("alpha", "researcher")
        self.mesh.remove_node("alpha")
        mesh2 = _make_mesh(self.tmpdir)
        self.assertIsNone(mesh2.get_node("alpha"))

    def test_other_nodes_survive(self):
        self.mesh.register_node("alpha", "r1")
        self.mesh.register_node("beta", "r2")
        self.mesh.remove_node("alpha")
        self.assertIsNotNone(self.mesh.get_node("beta"))


# ─────────────────────────────────────────────────────────
# send_message (direct)
# ─────────────────────────────────────────────────────────

class TestSendMessage(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)
        self.mesh.register_node("sender", "r1")
        self.mesh.register_node("receiver", "r2")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_mesh_message(self):
        msg = self.mesh.send_message("sender", "receiver", "hello")
        self.assertIsInstance(msg, MeshMessage)

    def test_message_has_correct_fields(self):
        msg = self.mesh.send_message("sender", "receiver", "hello", msg_type="query")
        self.assertEqual(msg.from_node, "sender")
        self.assertEqual(msg.to_node, "receiver")
        self.assertEqual(msg.content, "hello")
        self.assertEqual(msg.msg_type, "query")
        self.assertFalse(msg.read)
        self.assertIsNotNone(msg.msg_id)
        self.assertGreater(msg.timestamp, 0)

    def test_reply_to_field(self):
        msg = self.mesh.send_message("sender", "receiver", "reply", reply_to="orig123")
        self.assertEqual(msg.reply_to, "orig123")

    def test_message_written_to_global_log(self):
        self.mesh.send_message("sender", "receiver", "hello")
        log_file = Path(self.tmpdir) / "mesh" / "messages.jsonl"
        self.assertTrue(log_file.exists())
        lines = log_file.read_text().strip().split("\n")
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["content"], "hello")

    def test_message_delivered_to_inbox(self):
        self.mesh.send_message("sender", "receiver", "hello")
        inbox_dir = Path(self.tmpdir) / "mesh" / "inbox" / "receiver"
        files = list(inbox_dir.glob("*.json"))
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text())
        self.assertEqual(data["content"], "hello")
        self.assertEqual(data["from_node"], "sender")

    def test_sender_stats_incremented(self):
        self.mesh.send_message("sender", "receiver", "hello")
        self.assertEqual(self.mesh._nodes["sender"].messages_sent, 1)

    def test_multiple_messages_accumulate(self):
        self.mesh.send_message("sender", "receiver", "msg1")
        self.mesh.send_message("sender", "receiver", "msg2")
        inbox_dir = Path(self.tmpdir) / "mesh" / "inbox" / "receiver"
        files = list(inbox_dir.glob("*.json"))
        self.assertEqual(len(files), 2)
        self.assertEqual(self.mesh._nodes["sender"].messages_sent, 2)


# ─────────────────────────────────────────────────────────
# send_message broadcast
# ─────────────────────────────────────────────────────────

class TestBroadcast(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)
        self.mesh.register_node("commander", "orchestrator")
        self.mesh.register_node("alpha", "r1")
        self.mesh.register_node("beta", "r2")
        self.mesh.register_node("gamma", "r3")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_broadcast_delivers_to_all_except_sender(self):
        self.mesh.send_message("commander", "*", "alert!")
        for nid in ("alpha", "beta", "gamma"):
            inbox_dir = Path(self.tmpdir) / "mesh" / "inbox" / nid
            files = list(inbox_dir.glob("*.json"))
            self.assertEqual(len(files), 1, f"Node {nid} should have 1 message")

    def test_broadcast_excludes_sender(self):
        self.mesh.send_message("commander", "*", "alert!")
        inbox_dir = Path(self.tmpdir) / "mesh" / "inbox" / "commander"
        files = list(inbox_dir.glob("*.json"))
        self.assertEqual(len(files), 0)

    def test_broadcast_via_helper(self):
        msg = self.mesh.broadcast("commander", "sync", msg_type="sync")
        self.assertEqual(msg.to_node, "*")
        self.assertEqual(msg.msg_type, "sync")

    def test_broadcast_single_global_log_entry(self):
        self.mesh.send_message("commander", "*", "alert!")
        log_file = Path(self.tmpdir) / "mesh" / "messages.jsonl"
        lines = log_file.read_text().strip().split("\n")
        self.assertEqual(len(lines), 1)


# ─────────────────────────────────────────────────────────
# read_inbox
# ─────────────────────────────────────────────────────────

class TestReadInbox(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)
        self.mesh.register_node("sender", "r1")
        self.mesh.register_node("receiver", "r2")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_inbox(self):
        msgs = self.mesh.read_inbox("receiver")
        self.assertEqual(len(msgs), 0)

    def test_reads_sent_messages(self):
        self.mesh.send_message("sender", "receiver", "hello")
        msgs = self.mesh.read_inbox("receiver")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].content, "hello")

    def test_mark_read_true(self):
        self.mesh.send_message("sender", "receiver", "hello")
        self.mesh.read_inbox("receiver", mark_read=True)
        # Second read should return empty (already marked read)
        msgs = self.mesh.read_inbox("receiver", mark_read=False)
        self.assertEqual(len(msgs), 0)

    def test_mark_read_false(self):
        self.mesh.send_message("sender", "receiver", "hello")
        self.mesh.read_inbox("receiver", mark_read=False)
        # Second read should still return the message
        msgs = self.mesh.read_inbox("receiver", mark_read=False)
        self.assertEqual(len(msgs), 1)

    def test_receiver_stats_incremented(self):
        self.mesh.send_message("sender", "receiver", "hello")
        self.mesh.read_inbox("receiver")
        self.assertEqual(self.mesh._nodes["receiver"].messages_received, 1)

    def test_nonexistent_inbox_returns_empty(self):
        msgs = self.mesh.read_inbox("nonexistent")
        self.assertEqual(len(msgs), 0)

    def test_multiple_messages_read_in_order(self):
        self.mesh.send_message("sender", "receiver", "first")
        self.mesh.send_message("sender", "receiver", "second")
        msgs = self.mesh.read_inbox("receiver")
        self.assertEqual(len(msgs), 2)
        contents = [m.content for m in msgs]
        self.assertIn("first", contents)
        self.assertIn("second", contents)


# ─────────────────────────────────────────────────────────
# get_state
# ─────────────────────────────────────────────────────────

class TestGetState(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_state(self):
        state = self.mesh.get_state()
        self.assertIsInstance(state, MeshState)
        self.assertEqual(state.total_nodes, 0)
        self.assertEqual(state.active_nodes, 0)
        self.assertEqual(state.pending_messages, 0)
        self.assertEqual(state.total_messages, 0)

    def test_counts_nodes(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        state = self.mesh.get_state()
        self.assertEqual(state.total_nodes, 2)

    def test_counts_active_nodes(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh._nodes["a"].status = "active"
        state = self.mesh.get_state()
        self.assertEqual(state.active_nodes, 1)

    def test_counts_total_messages(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh.send_message("a", "b", "m1")
        self.mesh.send_message("a", "b", "m2")
        state = self.mesh.get_state()
        self.assertEqual(state.total_messages, 2)

    def test_counts_pending_messages(self):
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh.send_message("a", "b", "unread")
        state = self.mesh.get_state()
        self.assertEqual(state.pending_messages, 1)

    def test_uptime_positive(self):
        state = self.mesh.get_state()
        self.assertGreaterEqual(state.uptime_seconds, 0)


# ─────────────────────────────────────────────────────────
# _gen_msg_id
# ─────────────────────────────────────────────────────────

class TestGenMsgId(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_string(self):
        mid = self.mesh._gen_msg_id()
        self.assertIsInstance(mid, str)

    def test_length_12(self):
        mid = self.mesh._gen_msg_id()
        self.assertEqual(len(mid), 12)

    def test_hex_characters(self):
        mid = self.mesh._gen_msg_id()
        int(mid, 16)  # raises ValueError if not valid hex

    def test_100_unique_ids(self):
        ids = [self.mesh._gen_msg_id() for _ in range(100)]
        self.assertEqual(len(set(ids)), 100)


# ─────────────────────────────────────────────────────────
# get_conversation
# ─────────────────────────────────────────────────────────

class TestGetConversation(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)
        self.mesh.register_node("a", "r1")
        self.mesh.register_node("b", "r2")
        self.mesh.register_node("c", "r3")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_conversation(self):
        msgs = self.mesh.get_conversation("a", "b")
        self.assertEqual(len(msgs), 0)

    def test_returns_messages_between_two_nodes(self):
        self.mesh.send_message("a", "b", "hi")
        self.mesh.send_message("b", "a", "hey")
        self.mesh.send_message("a", "c", "other")
        msgs = self.mesh.get_conversation("a", "b")
        self.assertEqual(len(msgs), 2)

    def test_limit_parameter(self):
        for i in range(5):
            self.mesh.send_message("a", "b", f"msg{i}")
        msgs = self.mesh.get_conversation("a", "b", limit=3)
        self.assertEqual(len(msgs), 3)


# ─────────────────────────────────────────────────────────
# _log_mesh_event
# ─────────────────────────────────────────────────────────

class TestLogMeshEvent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh = _make_mesh(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_event_log(self):
        self.mesh._log_mesh_event("test", {"key": "value"})
        log_file = Path(self.tmpdir) / "mesh" / "mesh_events.jsonl"
        self.assertTrue(log_file.exists())

    def test_event_has_required_fields(self):
        self.mesh._log_mesh_event("spawn", {"node_id": "alpha"})
        log_file = Path(self.tmpdir) / "mesh" / "mesh_events.jsonl"
        data = json.loads(log_file.read_text().strip())
        self.assertIn("timestamp", data)
        self.assertIn("iso", data)
        self.assertEqual(data["event"], "spawn")
        self.assertEqual(data["node_id"], "alpha")


if __name__ == "__main__":
    unittest.main()
