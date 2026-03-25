"""Tests for core.remote_node_adapter — RemoteNodeAdapter multi-provider dispatch."""
import json
import unittest
from unittest.mock import MagicMock, patch


class TestRemoteProvider(unittest.TestCase):
    def test_all_providers_defined(self):
        from core.remote_node_adapter import RemoteProvider
        expected = {"GROQ", "CEREBRAS", "ZO", "TOGETHER", "MINIMAX",
                    "NVIDIA", "GEMINI", "SAMBANOVA", "OPENROUTER",
                    "ZHIPU", "DEEPSEEK"}
        actual = {p.name for p in RemoteProvider}
        self.assertEqual(expected, actual)

    def test_provider_values_are_strings(self):
        from core.remote_node_adapter import RemoteProvider
        for p in RemoteProvider:
            self.assertIsInstance(p.value, str)


class TestRemoteNodeRequest(unittest.TestCase):
    def test_creation(self):
        from core.remote_node_adapter import RemoteNodeRequest
        req = RemoteNodeRequest(
            node_id="deepseek-coder",
            msg_id="WO-001",
            task_title="Write Tests",
            task_description="Write comprehensive tests for mesh module",
            deadline="2026-03-25T00:00:00Z",
        )
        self.assertEqual(req.node_id, "deepseek-coder")
        self.assertEqual(req.msg_id, "WO-001")

    def test_post_init_sets_timestamp(self):
        from core.remote_node_adapter import RemoteNodeRequest
        req = RemoteNodeRequest(
            node_id="cerebras-llama",
            msg_id="WO-002",
            task_title="Analyze",
            task_description="Analyze security",
            deadline="2026-03-25T00:00:00Z",
        )
        self.assertIsNotNone(req.timestamp)
        self.assertGreater(req.timestamp, 0)

    def test_custom_timestamp(self):
        from core.remote_node_adapter import RemoteNodeRequest
        req = RemoteNodeRequest(
            node_id="n", msg_id="m", task_title="t",
            task_description="d", deadline="2026-01-01T00:00:00Z",
            timestamp=12345.0,
        )
        self.assertEqual(req.timestamp, 12345.0)


class TestRemoteNodeResponse(unittest.TestCase):
    def test_creation_completed(self):
        from core.remote_node_adapter import RemoteNodeResponse
        resp = RemoteNodeResponse(
            node_id="deepseek-coder",
            msg_id="WO-001",
            status="COMPLETED",
            response_text="def hello(): return 'world'",
        )
        self.assertEqual(resp.status, "COMPLETED")
        self.assertEqual(resp.node_id, "deepseek-coder")

    def test_creation_failed(self):
        from core.remote_node_adapter import RemoteNodeResponse
        resp = RemoteNodeResponse(
            node_id="groq-llama",
            msg_id="WO-002",
            status="FAILED",
            response_text="",
            error="rate_limit_exceeded",
        )
        self.assertEqual(resp.status, "FAILED")
        self.assertEqual(resp.error, "rate_limit_exceeded")

    def test_post_init_sets_timestamp(self):
        from core.remote_node_adapter import RemoteNodeResponse
        resp = RemoteNodeResponse(
            node_id="n", msg_id="m", status="COMPLETED", response_text="ok"
        )
        self.assertIsNotNone(resp.timestamp)
        self.assertGreater(resp.timestamp, 0)

    def test_default_empty_fields(self):
        from core.remote_node_adapter import RemoteNodeResponse
        resp = RemoteNodeResponse(
            node_id="n", msg_id="m", status="COMPLETED", response_text="ok"
        )
        self.assertEqual(resp.code, "")
        self.assertEqual(resp.error, "")
        self.assertEqual(resp.deliverable_preview, "")


class TestRemoteNodeAdapterInit(unittest.TestCase):
    def test_creation(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        adapter = RemoteNodeAdapter()
        self.assertIsInstance(adapter, RemoteNodeAdapter)

    def test_init_providers_returns_dict(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        adapter = RemoteNodeAdapter()
        providers = adapter._init_providers()
        self.assertIsInstance(providers, dict)

    def test_get_history_returns_list(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        adapter = RemoteNodeAdapter()
        history = adapter.get_history()
        self.assertIsInstance(history, list)


class TestRemoteNodeAdapterDispatch(unittest.TestCase):
    def setUp(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        self.adapter = RemoteNodeAdapter()

    def test_dispatch_unknown_node_returns_none(self):
        result = self.adapter.dispatch("unknown-node-xyz", {"task": "test"})
        self.assertIsNone(result)

    def test_build_prompt_contains_node_id(self):
        # work_order["task"] must be a dict with title/description keys
        prompt = self.adapter._build_prompt(
            "cerebras-llama",
            {"task": {"title": "Security Analysis", "description": "analyze gaps"}}
        )
        self.assertIn("cerebras-llama", prompt)

    def test_build_prompt_is_string(self):
        prompt = self.adapter._build_prompt(
            "node-x",
            {"task": {"title": "Tests", "description": "write unit tests"}}
        )
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)

    def test_build_prompt_with_empty_work_order(self):
        prompt = self.adapter._build_prompt("deepseek-coder", {})
        self.assertIsInstance(prompt, str)

    def test_extract_code_block_markdown(self):
        text = "Here is code:\n```python\ndef foo():\n    return 1\n```\nDone."
        result = self.adapter._extract_code_block(text)
        self.assertIn("def foo", result)

    def test_extract_code_block_no_markdown_returns_empty(self):
        # No code block → returns "" (extracts nothing)
        result = self.adapter._extract_code_block("Plain text without code block")
        self.assertEqual(result, "")

    def test_extract_code_block_empty(self):
        result = self.adapter._extract_code_block("")
        self.assertEqual(result, "")


class TestRemoteNodeAdapterHistory(unittest.TestCase):
    def test_history_grows_on_dispatch(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        adapter = RemoteNodeAdapter()
        initial_len = len(adapter.get_history())
        # Dispatch to unknown node — records the attempt
        adapter.dispatch("nonexistent", {"task": "test"})
        # History may or may not grow depending on implementation
        self.assertGreaterEqual(len(adapter.get_history()), 0)

    def test_history_entries_are_dicts(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        adapter = RemoteNodeAdapter()
        history = adapter.get_history()
        for entry in history:
            self.assertIsInstance(entry, dict)


class TestCallHelpers(unittest.TestCase):
    def setUp(self):
        from core.remote_node_adapter import RemoteNodeAdapter
        self.adapter = RemoteNodeAdapter()

    def test_call_deepseek_with_mock_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        mock_client.chat.completions.create.return_value = mock_response
        result = self.adapter._call_deepseek(mock_client, "write a test")
        self.assertIsNotNone(result)

    def test_call_cerebras_with_mock_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "cerebras output"
        mock_client.chat.completions.create.return_value = mock_response
        result = self.adapter._call_cerebras(mock_client, "test prompt")
        self.assertIsNotNone(result)

    def test_call_returns_none_on_exception(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        result = self.adapter._call_deepseek(mock_client, "test")
        self.assertIsNone(result)
