"""
Tests for autonomous mesh — remote node dispatch via free APIs.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.remote_node_adapter import RemoteNodeAdapter, RemoteNodeResponse, REMOTE_NODE_MAPPING
from core.mesh_orchestrator import MeshOrchestrator


class TestRemoteNodeAdapter(unittest.TestCase):
    """Test RemoteNodeAdapter for free API integration."""

    def setUp(self):
        self.adapter = RemoteNodeAdapter()

    def test_remote_node_mapping(self):
        """Test that remote nodes are mapped to providers."""
        expected_nodes = ["gpt-legion", "gemini-web", "kimi-web", "qwen-coder-480b", "minimax"]
        for node in expected_nodes:
            self.assertIn(node, REMOTE_NODE_MAPPING)

    def test_provider_initialization(self):
        """Test that providers are initialized (or fail gracefully)."""
        # Not all providers may be available in test environment
        # Just verify no crash during init
        self.assertIsNotNone(self.adapter.provider_clients)

    def test_build_prompt(self):
        """Test that prompts are built correctly."""
        work_order = {
            "msg_id": "TEST-001",
            "task": {
                "title": "Test Task",
                "description": "A test task",
                "timeline": "Now"
            }
        }
        prompt = self.adapter._build_prompt("test-node", work_order)
        self.assertIn("test-node", prompt)
        self.assertIn("Test Task", prompt)
        self.assertIn("TEST-001", prompt)
        self.assertIn("JSON", prompt)

    def test_extract_code_block(self):
        """Test code block extraction from responses."""
        text = """
Here's the implementation:

```python
def hello():
    return "world"
```

Hope this helps!
        """
        code = self.adapter._extract_code_block(text)
        self.assertIn("def hello", code)
        self.assertIn("return", code)


class TestRemoteNodeResponse(unittest.TestCase):
    """Test RemoteNodeResponse dataclass."""

    def test_response_creation(self):
        """Test creating a response object."""
        resp = RemoteNodeResponse(
            node_id="test-node",
            msg_id="MSG-001",
            status="COMPLETED",
            response_text="Task completed successfully",
        )
        self.assertEqual(resp.node_id, "test-node")
        self.assertEqual(resp.status, "COMPLETED")
        self.assertGreater(resp.timestamp, 0)

    def test_response_to_dict(self):
        """Test converting response to dict."""
        from dataclasses import asdict
        resp = RemoteNodeResponse(
            node_id="test-node",
            msg_id="MSG-001",
            status="COMPLETED",
            response_text="Done",
        )
        d = asdict(resp)
        self.assertEqual(d["node_id"], "test-node")
        self.assertEqual(d["status"], "COMPLETED")


class TestMeshOrchestrator(unittest.TestCase):
    """Test MeshOrchestrator autonomous dispatch."""

    def setUp(self):
        MeshOrchestrator.reset()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mesh_dir = Path(self.temp_dir.name)
        self.orchestrator = MeshOrchestrator(mesh_dir=str(self.mesh_dir))

    def tearDown(self):
        MeshOrchestrator.reset()
        self.temp_dir.cleanup()

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        self.assertEqual(self.orchestrator.work_orders_processed, 0)
        self.assertEqual(self.orchestrator.cycle_count, 0)
        self.assertTrue((self.mesh_dir / "inbox" / "commander").exists())

    def test_discover_work_orders(self):
        """Test discovering work orders in inbox."""
        # Create a test work order
        inbox = self.mesh_dir / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)

        order_file = inbox / "PHASE2-TEST-001.json"
        order_data = {
            "msg_id": "PHASE2-TEST-001",
            "to_node": "kimi-web",
            "task": {"title": "Test", "description": "Test task"}
        }
        order_file.write_text(json.dumps(order_data))

        # Discover
        discovered = self.orchestrator._discover_work_orders()
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0][1]["msg_id"], "PHASE2-TEST-001")

    def test_save_response(self):
        """Test saving response to disk."""
        inbox = self.mesh_dir / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)

        order_file = inbox / "PHASE2-TEST-001.json"
        order_file.write_text(json.dumps({"msg_id": "PHASE2-TEST-001"}))

        result = RemoteNodeResponse(
            node_id="kimi-web",
            msg_id="PHASE2-TEST-001",
            status="COMPLETED",
            response_text="Task completed",
            code="def task(): pass",
        )

        self.orchestrator._save_response(order_file, result)

        response_file = inbox / "PHASE2-TEST-001-RESPONSE.json"
        self.assertTrue(response_file.exists())

        with open(response_file) as f:
            data = json.load(f)

        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["from_node"], "kimi-web")

    def test_save_failure(self):
        """Test saving failure record."""
        inbox = self.mesh_dir / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)

        order_file = inbox / "PHASE2-TEST-001.json"
        order_file.write_text(json.dumps({"msg_id": "PHASE2-TEST-001"}))

        result = RemoteNodeResponse(
            node_id="kimi-web",
            msg_id="PHASE2-TEST-001",
            status="FAILED",
            response_text="",
            error="Provider not initialized",
        )

        self.orchestrator._save_failure(order_file, result)

        failed_file = inbox / "PHASE2-TEST-001-FAILED.json"
        self.assertTrue(failed_file.exists())

        with open(failed_file) as f:
            data = json.load(f)

        self.assertEqual(data["status"], "FAILED")

    def test_get_status(self):
        """Test getting orchestrator status."""
        self.orchestrator.work_orders_processed = 5
        self.orchestrator.work_orders_completed = 3

        status = self.orchestrator.get_status()
        self.assertEqual(status["work_orders_processed"], 5)
        self.assertEqual(status["work_orders_completed"], 3)
        self.assertAlmostEqual(status["completion_rate"], 0.6, places=1)


class TestNodeMeshRemoteIntegration(unittest.TestCase):
    """Test NodeMesh integration with remote adapter."""

    def test_remote_adapter_imported(self):
        """Test that RemoteNodeAdapter is available in node_mesh."""
        from core.node_mesh import RemoteNodeAdapter as ImportedAdapter
        self.assertIsNotNone(ImportedAdapter)

    def test_node_mesh_has_remote_adapter(self):
        """Test that NodeMesh initializes remote adapter."""
        from core.node_mesh import NodeMesh

        with tempfile.TemporaryDirectory() as tmpdir:
            mesh = NodeMesh(mesh_dir=str(Path(tmpdir) / "mesh"))
            # May be None if RemoteNodeAdapter init failed
            # Just check it doesn't crash
            self.assertTrue(hasattr(mesh, "_remote_adapter"))

    def test_dispatch_work_order_method_exists(self):
        """Test that dispatch_work_order method exists in NodeMesh."""
        from core.node_mesh import NodeMesh

        with tempfile.TemporaryDirectory() as tmpdir:
            mesh = NodeMesh(mesh_dir=str(Path(tmpdir) / "mesh"))
            self.assertTrue(hasattr(mesh, "dispatch_work_order"))
            self.assertTrue(callable(mesh.dispatch_work_order))


if __name__ == "__main__":
    unittest.main()
