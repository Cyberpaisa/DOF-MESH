"""Tests for MCP Server — DOF governance as Model Context Protocol tools."""

import json
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

from mcp_server import (
    TOOLS,
    RESOURCES,
    handle_request,
    handle_initialize,
    handle_tools_list,
    handle_tools_call,
    handle_resources_list,
    handle_resources_read,
    tool_verify_governance,
    tool_verify_ast,
    tool_run_z3,
    tool_memory_add,
    tool_memory_query,
    tool_memory_snapshot,
    tool_get_metrics,
    tool_create_attestation,
    tool_oags_identity,
    tool_conformance_check,
    resource_constitution,
    resource_metrics_latest,
    resource_memory_stats,
)


class TestMCPToolRegistry(unittest.TestCase):
    """Test that the tool registry is correct."""

    def test_has_15_tools(self):
        self.assertEqual(len(TOOLS), 15)

    def test_has_3_resources(self):
        self.assertEqual(len(RESOURCES), 3)

    def test_tool_names(self):
        expected = {
            "dof_verify_governance",
            "dof_verify_ast",
            "dof_run_z3",
            "dof_memory_add",
            "dof_memory_query",
            "dof_memory_snapshot",
            "dof_get_metrics",
            "dof_create_attestation",
            "dof_oags_identity",
            "dof_conformance_check",
            "mesh_send_task",
            "mesh_broadcast",
            "mesh_route_smart",
            "mesh_read_inbox",
            "mesh_consensus",
        }
        self.assertEqual(set(TOOLS.keys()), expected)

    def test_resource_uris(self):
        expected = {"dof://constitution", "dof://metrics/latest", "dof://memory/stats"}
        self.assertEqual(set(RESOURCES.keys()), expected)

    def test_each_tool_has_schema(self):
        for name, spec in TOOLS.items():
            self.assertIn("description", spec, f"{name} missing description")
            self.assertIn("inputSchema", spec, f"{name} missing inputSchema")
            self.assertIn("handler", spec, f"{name} missing handler")
            self.assertTrue(callable(spec["handler"]), f"{name} handler not callable")

    def test_each_resource_has_fields(self):
        for uri, spec in RESOURCES.items():
            self.assertIn("name", spec, f"{uri} missing name")
            self.assertIn("description", spec, f"{uri} missing description")
            self.assertIn("mimeType", spec, f"{uri} missing mimeType")
            self.assertIn("handler", spec, f"{uri} missing handler")


class TestMCPProtocol(unittest.TestCase):
    """Test JSON-RPC 2.0 protocol handling."""

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = handle_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        result = resp["result"]
        self.assertIn("protocolVersion", result)
        self.assertIn("capabilities", result)
        self.assertIn("serverInfo", result)
        self.assertEqual(result["serverInfo"]["name"], "dof-governance")

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = handle_request(req)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 15)
        names = {t["name"] for t in tools}
        self.assertIn("dof_verify_governance", names)
        self.assertIn("dof_run_z3", names)
        self.assertIn("mesh_send_task", names)
        self.assertIn("mesh_consensus", names)

    def test_resources_list(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
        resp = handle_request(req)
        resources = resp["result"]["resources"]
        self.assertEqual(len(resources), 3)

    def test_notification_returns_none(self):
        req = {"method": "notifications/initialized", "params": {}}
        resp = handle_request(req)
        self.assertIsNone(resp)

    def test_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "unknown/method", "params": {}}
        resp = handle_request(req)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_tool(self):
        req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = handle_request(req)
        result = resp["result"]
        self.assertTrue(result["isError"])

    def test_unknown_resource(self):
        req = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "resources/read",
            "params": {"uri": "dof://nonexistent"},
        }
        resp = handle_request(req)
        contents = resp["result"]["contents"]
        self.assertIn("error", json.loads(contents[0]["text"]))


class TestMCPToolGovernance(unittest.TestCase):
    """Test dof_verify_governance tool."""

    def test_clean_output_passes(self):
        result = tool_verify_governance({
            "output_text": "The research shows that Python adoption grew 15% in 2024. "
                           "Sources: Stack Overflow Survey 2024."
        })
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["score"], 0)

    def test_empty_output_fails(self):
        result = tool_verify_governance({"output_text": ""})
        self.assertEqual(result["status"], "fail")
        self.assertTrue(len(result["hard_violations"]) > 0)

    def test_via_jsonrpc(self):
        req = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "dof_verify_governance",
                "arguments": {"output_text": "Valid output with sources. Sources: test."},
            },
        }
        resp = handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("status", data)


class TestMCPToolAST(unittest.TestCase):
    """Test dof_verify_ast tool."""

    def test_clean_code_passes(self):
        result = tool_verify_ast({"code": "def add(a, b):\n    return a + b\n"})
        self.assertEqual(result["score"], 1.0)
        self.assertTrue(result["passed"])

    def test_eval_detected(self):
        result = tool_verify_ast({"code": "x = eval('1+1')\n"})
        self.assertLess(result["score"], 1.0)
        self.assertTrue(len(result["violations"]) > 0)

    def test_blocked_import_detected(self):
        result = tool_verify_ast({"code": "import subprocess\nsubprocess.call('rm -rf /')\n"})
        self.assertFalse(result["passed"])


class TestMCPToolZ3(unittest.TestCase):
    """Test dof_run_z3 tool."""

    def test_z3_verifies_all(self):
        result = tool_run_z3({})
        self.assertTrue(result["all_verified"])
        self.assertGreaterEqual(result["count"], 4)
        for t in result["theorems"]:
            self.assertEqual(t["result"], "VERIFIED")
            self.assertIn("theorem_name", t)


class TestMCPToolMemory(unittest.TestCase):
    """Test memory tools with temp directory."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        import core.memory_governance as mg
        self._orig_store = mg.STORE_FILE
        self._orig_log = mg.LOG_FILE
        self._orig_decay = mg.DECAY_LOG_FILE
        mg.STORE_FILE = os.path.join(self._tmpdir, "store.jsonl")
        mg.LOG_FILE = os.path.join(self._tmpdir, "log.jsonl")
        mg.DECAY_LOG_FILE = os.path.join(self._tmpdir, "decay.jsonl")

    def tearDown(self):
        import core.memory_governance as mg
        mg.STORE_FILE = self._orig_store
        mg.LOG_FILE = self._orig_log
        mg.DECAY_LOG_FILE = self._orig_decay
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_memory_add(self):
        result = tool_memory_add({
            "content": "DOF achieves 98% governance compliance rate",
            "category": "knowledge",
        })
        self.assertIn("memory_id", result)
        self.assertIn(result["status"], ("approved", "warning", "rejected"))
        self.assertEqual(result["category"], "knowledge")

    def test_memory_query(self):
        tool_memory_add({"content": "Test memory entry for query", "category": "context"})
        result = tool_memory_query({"query": "test", "category": "context"})
        self.assertIn("results", result)
        self.assertIn("count", result)

    def test_memory_snapshot(self):
        tool_memory_add({"content": "Snapshot test entry", "category": "decisions"})
        result = tool_memory_snapshot({})
        self.assertIn("memories", result)
        self.assertIn("as_of", result)


class TestMCPToolMetrics(unittest.TestCase):
    """Test dof_get_metrics tool."""

    def test_default_metrics(self):
        result = tool_get_metrics({})
        for key in ("SS", "GCR", "PFI", "RP", "SSR"):
            self.assertIn(key, result)
        self.assertEqual(result["GCR"], 1.0)

    def test_nonexistent_trace_returns_defaults(self):
        result = tool_get_metrics({"run_trace_path": "/nonexistent/trace.json"})
        self.assertIn("SS", result)


class TestMCPToolAttestation(unittest.TestCase):
    """Test dof_create_attestation tool."""

    def test_create_attestation(self):
        result = tool_create_attestation({
            "task_id": "mcp-test-001",
            "metrics": {"SS": 0.95, "GCR": 1.0, "PFI": 0.02, "RP": 0.85, "SSR": 0.92},
        })
        self.assertIn("certificate_hash", result)
        self.assertIn("governance_status", result)
        self.assertIn("z3_verified", result)
        self.assertIn("agent_identity", result)
        self.assertIsInstance(result["should_publish"], bool)


class TestMCPToolOAGS(unittest.TestCase):
    """Test OAGS identity and conformance tools."""

    def test_oags_identity_deterministic(self):
        r1 = tool_oags_identity({"model": "test-model", "tools": ["tool1", "tool2"]})
        r2 = tool_oags_identity({"model": "test-model", "tools": ["tool1", "tool2"]})
        self.assertEqual(r1["identity_hash"], r2["identity_hash"])
        self.assertIn("agent_card", r1)

    def test_conformance_check(self):
        result = tool_conformance_check({})
        self.assertIn("level_1", result)
        self.assertIn("level_2", result)
        self.assertIn("level_3", result)
        self.assertIn("max_level", result)
        self.assertGreaterEqual(result["max_level"], 3)


class TestMCPResources(unittest.TestCase):
    """Test resource handlers."""

    def test_constitution_resource(self):
        result = resource_constitution()
        self.assertEqual(result["uri"], "dof://constitution")
        # Should have data or error
        self.assertTrue("data" in result or "error" in result)

    def test_metrics_resource(self):
        result = resource_metrics_latest()
        self.assertEqual(result["uri"], "dof://metrics/latest")
        self.assertIn("data", result)
        self.assertIn("SS", result["data"])

    def test_memory_stats_resource(self):
        result = resource_memory_stats()
        self.assertEqual(result["uri"], "dof://memory/stats")
        self.assertTrue("data" in result or "error" in result)

    def test_resources_via_jsonrpc(self):
        req = {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "resources/read",
            "params": {"uri": "dof://metrics/latest"},
        }
        resp = handle_request(req)
        contents = resp["result"]["contents"]
        self.assertEqual(len(contents), 1)
        data = json.loads(contents[0]["text"])
        self.assertIn("SS", data)


if __name__ == "__main__":
    unittest.main()
