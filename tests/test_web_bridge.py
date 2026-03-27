"""Tests for core.web_bridge — WebBridge (Playwright-based) without launching a browser."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── WEB_TARGETS config ───────────────────────────────────────────────────────

class TestWebTargetsConfig(unittest.TestCase):
    def setUp(self):
        from core.web_bridge import WEB_TARGETS
        self.targets = WEB_TARGETS

    def test_has_core_nodes(self):
        for node in ("gemini", "chatgpt", "minimax", "kimi", "deepseek"):
            self.assertIn(node, self.targets, f"{node} missing from WEB_TARGETS")

    def test_every_target_has_required_keys(self):
        required = ("url", "input_selector", "send_key", "response_selector", "wait_ms")
        for name, cfg in self.targets.items():
            for key in required:
                self.assertIn(key, cfg, f"{name} missing key '{key}'")

    def test_url_starts_with_https(self):
        for name, cfg in self.targets.items():
            self.assertTrue(
                cfg["url"].startswith("https://"),
                f"{name}.url should start with https://"
            )

    def test_wait_ms_is_positive_int(self):
        for name, cfg in self.targets.items():
            self.assertIsInstance(cfg["wait_ms"], int)
            self.assertGreater(cfg["wait_ms"], 0, f"{name}.wait_ms must be > 0")

    def test_send_key_is_nonempty_string(self):
        for name, cfg in self.targets.items():
            self.assertIsInstance(cfg["send_key"], str)
            self.assertTrue(len(cfg["send_key"]) > 0)

    def test_new_chat_url_starts_with_https(self):
        for name, cfg in self.targets.items():
            if "new_chat_url" in cfg:
                self.assertTrue(
                    cfg["new_chat_url"].startswith("https://"),
                    f"{name}.new_chat_url should start with https://"
                )


# ── WebBridge.__init__ ───────────────────────────────────────────────────────

class TestWebBridgeInit(unittest.TestCase):
    def _make_bridge(self, node="gemini", headless=True):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                return WebBridge(node=node, headless=headless)

    def test_valid_nodes_construct_ok(self):
        from core.web_bridge import WEB_TARGETS
        sample_nodes = [k for i, k in enumerate(WEB_TARGETS) if i < 4]
        for node in sample_nodes:
            with self.subTest(node=node):
                b = self._make_bridge(node)
                self.assertEqual(b.node, node)

    def test_invalid_node_raises_value_error(self):
        from core.web_bridge import WebBridge
        with self.assertRaises(ValueError) as ctx:
            WebBridge(node="this-does-not-exist")
        self.assertIn("this-does-not-exist", str(ctx.exception))

    def test_error_message_lists_options(self):
        from core.web_bridge import WebBridge, WEB_TARGETS
        with self.assertRaises(ValueError) as ctx:
            WebBridge(node="bad-node")
        sample = [k for i, k in enumerate(WEB_TARGETS) if i < 2]
        for node in sample:
            self.assertIn(node, str(ctx.exception))

    def test_headless_flag_stored(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini", headless=True)
                self.assertTrue(b.headless)

    def test_headless_false_stored(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="chatgpt", headless=False)
                self.assertFalse(b.headless)

    def test_target_matches_web_targets_entry(self):
        from core.web_bridge import WebBridge, WEB_TARGETS
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
        self.assertEqual(b.target, WEB_TARGETS["gemini"])

    def test_inbox_dir_created(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="deepseek")
            self.assertTrue(b.inbox.exists())

    def test_results_dir_created(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="kimi")
            self.assertTrue(b.results.exists())

    def test_initial_playwright_attrs_are_none(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
        self.assertIsNone(b._pw)
        self.assertIsNone(b._ctx)
        self.assertIsNone(b._page)


# ── WebBridge.stop ───────────────────────────────────────────────────────────

class TestWebBridgeStop(unittest.TestCase):
    def test_stop_without_start_is_safe(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
        b.stop()  # should not raise

    def test_stop_closes_ctx_and_pw(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="chatgpt")
        mock_ctx = MagicMock()
        mock_pw = MagicMock()
        b._ctx = mock_ctx
        b._pw = mock_pw
        b.stop()
        mock_ctx.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_stop_only_ctx_no_pw(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="minimax")
        mock_ctx = MagicMock()
        b._ctx = mock_ctx
        b._pw = None
        b.stop()
        mock_ctx.close.assert_called_once()


# ── WebBridge._navigate_new_chat ─────────────────────────────────────────────

class TestNavigateNewChat(unittest.TestCase):
    def _bridge_with_page(self, node="gemini"):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node=node)
        b._page = MagicMock()
        return b

    def test_calls_goto(self):
        b = self._bridge_with_page("gemini")
        with patch("time.sleep"):
            b._navigate_new_chat()
        b._page.goto.assert_called_once()

    def test_uses_new_chat_url(self):
        from core.web_bridge import WEB_TARGETS
        b = self._bridge_with_page("deepseek")
        with patch("time.sleep"):
            b._navigate_new_chat()
        called_url = b._page.goto.call_args[0][0]
        self.assertEqual(called_url, WEB_TARGETS["deepseek"]["new_chat_url"])

    def test_exception_from_goto_is_handled(self):
        b = self._bridge_with_page("gemini")
        b._page.goto.side_effect = Exception("navigation timeout")
        with patch("time.sleep"):
            b._navigate_new_chat()  # should not raise


# ── WebBridge.process_inbox ───────────────────────────────────────────────────

class TestProcessInbox(unittest.TestCase):
    def _bridge(self, node="chatgpt"):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                return WebBridge(node=node), Path(tmpdir)

    def test_empty_inbox_returns_zero(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="chatgpt")
            count = b.process_inbox()
        self.assertEqual(count, 0)

    def test_processes_task_file(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
                task = {"task_id": "t-001", "prompt": "What is 2+2?"}
                (b.inbox / "task_t001.json").write_text(json.dumps(task))

                with patch.object(b, "send_and_receive", return_value="4"), \
                     patch("time.sleep"):
                    count = b.process_inbox()
        self.assertEqual(count, 1)

    def test_result_saved_on_success(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
            task = {"task_id": "t-002", "prompt": "Hello?"}
            (b.inbox / "task_t002.json").write_text(json.dumps(task))

            with patch.object(b, "send_and_receive", return_value="Hi!"), \
                 patch("time.sleep"), \
                 patch.object(Path, "mkdir", return_value=None):
                b.process_inbox()

            result_files = list(b.results.glob("t-002*.json"))
            self.assertTrue(len(result_files) >= 1)

    def test_no_response_still_counts(self):
        from core.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.web_bridge.REPO_ROOT", Path(tmpdir)):
                b = WebBridge(node="gemini")
            task = {"task_id": "t-003", "prompt": "Q?"}
            (b.inbox / "t3.json").write_text(json.dumps(task))

            with patch.object(b, "send_and_receive", return_value=None), \
                 patch("time.sleep"), \
                 patch.object(Path, "mkdir", return_value=None):
                count = b.process_inbox()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
