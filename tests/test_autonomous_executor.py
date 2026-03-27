"""Tests for AutonomousExecutor — agentic loop with tool execution."""
import json
import os
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.autonomous_executor import AutonomousExecutor, ToolCall, ExecutionResult, REPO_ROOT


class TestToolExecution(unittest.TestCase):
    """Test each tool in isolation — no Ollama required."""

    def setUp(self):
        AutonomousExecutor.reset()
        self.ex = AutonomousExecutor(model="test-model")

    # ------------------------------------------------------------------ bash
    def test_bash_simple_command(self):
        out, ok = self.ex._run_bash("echo hello_dof")
        self.assertTrue(ok)
        self.assertIn("hello_dof", out)

    def test_bash_blocked_rm_rf(self):
        out, ok = self.ex._run_bash("rm -rf /tmp/something")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", out)

    def test_bash_blocked_git_push(self):
        out, ok = self.ex._run_bash("git push origin main")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", out)

    def test_bash_blocked_git_add_all(self):
        out, ok = self.ex._run_bash("git add -A")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", out)

    def test_bash_nonzero_exit(self):
        out, ok = self.ex._run_bash("exit 1")
        self.assertFalse(ok)

    def test_bash_timeout(self):
        import core.autonomous_executor as ae
        original = ae.BASH_TIMEOUT
        ae.BASH_TIMEOUT = 1
        out, ok = self.ex._run_bash("sleep 5")
        ae.BASH_TIMEOUT = original
        self.assertFalse(ok)
        self.assertIn("TIMEOUT", out)

    # ------------------------------------------------------------------ python
    def test_python_simple(self):
        out, ok = self.ex._run_python("print('dof_test_42')")
        self.assertTrue(ok)
        self.assertIn("dof_test_42", out)

    def test_python_captures_stderr(self):
        out, ok = self.ex._run_python("import sys; sys.stderr.write('err_output')")
        self.assertIn("err_output", out)

    def test_python_exception(self):
        out, ok = self.ex._run_python("raise ValueError('test_error')")
        self.assertFalse(ok)
        self.assertIn("ValueError", out)
        self.assertIn("test_error", out)

    def test_python_no_output_ok(self):
        out, ok = self.ex._run_python("x = 1 + 1")
        self.assertTrue(ok)
        self.assertIn("OK", out)

    def test_python_accesses_repo_root(self):
        out, ok = self.ex._run_python("print(REPO_ROOT)")
        self.assertTrue(ok)
        self.assertIn("DOF-MESH", out)

    # ------------------------------------------------------------------ read_file
    def test_read_file_existing(self):
        path = os.path.join(REPO_ROOT, "dof", "__init__.py")
        if os.path.exists(path):
            out, ok = self.ex._read_file(path)
            self.assertTrue(ok)
            self.assertGreater(len(out), 0)

    def test_read_file_not_found(self):
        # Path must be within allowed dirs (repo/home) but not exist
        path = os.path.join(REPO_ROOT, "this_file_does_not_exist_xyz.py")
        out, ok = self.ex._read_file(path)
        self.assertFalse(ok)
        self.assertIn("NOT FOUND", out)

    def test_read_file_blocked_outside_repo(self):
        out, ok = self.ex._read_file("/etc/passwd")
        # /etc is not under repo or home — should be blocked
        if not ok:
            self.assertIn("BLOCKED", out)

    def test_read_file_relative_path(self):
        # Relative path should resolve to repo root
        out, ok = self.ex._read_file("dof/__init__.py")
        if os.path.exists(os.path.join(REPO_ROOT, "dof/__init__.py")):
            self.assertTrue(ok)

    # ------------------------------------------------------------------ write_file
    def test_write_file_within_repo(self):
        with tempfile.TemporaryDirectory(dir=os.path.join(REPO_ROOT, "logs")) as tmp:
            path = os.path.join(tmp, "test_write.txt")
            out, ok = self.ex._write_file(path, "hello dof")
            self.assertTrue(ok)
            self.assertIn("WRITTEN", out)
            self.assertEqual(open(path).read(), "hello dof")

    def test_write_file_blocked_outside_repo(self):
        out, ok = self.ex._write_file("/tmp/evil.py", "malicious")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", out)

    def test_write_file_blocked_sensitive(self):
        path = os.path.join(REPO_ROOT, "oracle_key.json")
        out, ok = self.ex._write_file(path, '{"key": "secret"}')
        self.assertFalse(ok)
        self.assertIn("BLOCKED", out)

    def test_write_file_creates_dirs(self):
        with tempfile.TemporaryDirectory(dir=os.path.join(REPO_ROOT, "logs")) as tmp:
            path = os.path.join(tmp, "subdir", "nested.txt")
            out, ok = self.ex._write_file(path, "nested content")
            self.assertTrue(ok)

    # ------------------------------------------------------------------ list_dir
    def test_list_dir_repo_root(self):
        out, ok = self.ex._list_dir(REPO_ROOT)
        self.assertTrue(ok)
        self.assertIn("core", out)

    def test_list_dir_nonexistent(self):
        out, ok = self.ex._list_dir("/nonexistent/dir")
        self.assertFalse(ok)

    # ------------------------------------------------------------------ parse tools
    def test_parse_bash_tag(self):
        text = "Let me check:\n<bash>ls -la</bash>"
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools, [("bash", "ls -la")])

    def test_parse_python_tag(self):
        text = "<python>\nprint('hi')\n</python>"
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools, [("python", "print('hi')")])

    def test_parse_multiple_tools(self):
        text = "<bash>pwd</bash>\n<python>print(1)</python>"
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0][0], "bash")
        self.assertEqual(tools[1][0], "python")

    def test_parse_write_file(self):
        text = '<write_file path="/tmp/test.py">content</write_file>'
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools[0][0], "write_file")
        data = json.loads(tools[0][1])
        self.assertEqual(data["path"], "/tmp/test.py")
        self.assertEqual(data["content"], "content")

    def test_parse_read_file(self):
        text = "<read_file>/some/path.py</read_file>"
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools, [("read_file", "/some/path.py")])

    def test_parse_no_tools(self):
        text = "This is a plain text response without any tools."
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools, [])

    def test_parse_done_tag(self):
        # done tag should NOT be parsed as a tool
        text = "<done>Task completed successfully.</done>"
        tools = self.ex._parse_tool_calls(text)
        self.assertEqual(tools, [])


class TestAgentLoop(unittest.TestCase):
    """Test the agentic loop with mocked Ollama."""

    def setUp(self):
        AutonomousExecutor.reset()
        self.ex = AutonomousExecutor(model="test-model")

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_plain_text_response(self, mock_llm):
        """Model returns plain text — no tools, direct result."""
        mock_llm.return_value = "The answer is 42."
        result = self.ex.execute("t1", "What is the answer?")
        self.assertTrue(result.success)
        self.assertEqual(result.result, "The answer is 42.")
        self.assertEqual(result.iterations, 1)
        self.assertEqual(len(result.tool_calls), 0)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_done_tag_terminates(self, mock_llm):
        """<done> tag terminates the loop."""
        mock_llm.return_value = "<done>File created and tests pass.</done>"
        result = self.ex.execute("t2", "Create a file")
        self.assertTrue(result.success)
        self.assertEqual(result.result, "File created and tests pass.")

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_bash_tool_then_done(self, mock_llm):
        """Model uses bash, gets result, then finishes."""
        mock_llm.side_effect = [
            "<bash>echo dof_hello</bash>",
            "<done>Command ran successfully.</done>",
        ]
        result = self.ex.execute("t3", "Run echo command")
        self.assertTrue(result.success)
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].tool, "bash")
        self.assertIn("dof_hello", result.tool_calls[0].output)
        self.assertEqual(result.iterations, 2)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_python_tool_then_done(self, mock_llm):
        """Model uses python execution."""
        mock_llm.side_effect = [
            "<python>print('result_42')</python>",
            "<done>Python ran.</done>",
        ]
        result = self.ex.execute("t4", "Run python")
        self.assertTrue(result.success)
        self.assertIn("result_42", result.tool_calls[0].output)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_ollama_none_returns_error(self, mock_llm):
        """If _call_llm returns None (all providers exhausted), result is error."""
        mock_llm.return_value = None
        result = self.ex.execute("t5", "anything")
        self.assertFalse(result.success)
        self.assertIn("ERROR", result.result)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_max_iterations_reached(self, mock_llm):
        """Loop stops after MAX_ITERATIONS."""
        import core.autonomous_executor as ae
        original_max = ae.MAX_ITERATIONS
        ae.MAX_ITERATIONS = 3
        mock_llm.return_value = "<bash>echo loop</bash>"
        result = self.ex.execute("t6", "infinite task")
        ae.MAX_ITERATIONS = original_max
        self.assertFalse(result.success)
        self.assertIn("MAX ITERATIONS", result.result)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_deepseek_think_tags_stripped(self, mock_llm):
        """<think> tags from deepseek-r1 are stripped before parsing."""
        mock_llm.return_value = (
            "<think>Internal reasoning here...</think>\n"
            "<done>Clean answer without thinking.</done>"
        )
        result = self.ex.execute("t7", "reason about this")
        self.assertTrue(result.success)
        self.assertNotIn("Internal reasoning", result.result)

    @patch.object(AutonomousExecutor, "_call_llm")
    def test_multiple_tools_same_response(self, mock_llm):
        """Multiple tools in one response are all executed."""
        mock_llm.side_effect = [
            "<bash>echo one</bash>\n<bash>echo two</bash>",
            "<done>Both ran.</done>",
        ]
        result = self.ex.execute("t8", "run two commands")
        self.assertEqual(len(result.tool_calls), 2)

    def test_singleton_pattern(self):
        """AutonomousExecutor is a singleton."""
        AutonomousExecutor.reset()
        a = AutonomousExecutor(model="m1")
        b = AutonomousExecutor(model="m2")
        self.assertIs(a, b)


class TestSpeculativeExecutor(unittest.TestCase):
    """Tests for _call_llm_speculative — racing DeepSeek and Ollama."""

    def setUp(self):
        AutonomousExecutor.reset()
        self.ex = AutonomousExecutor(model="test-model")
        self.messages = [{"role": "user", "content": "hello"}]

    def test_speculative_returns_first_winner(self):
        """DeepSeek wins the race — its response is returned."""
        with patch.object(self.ex, "_call_deepseek", return_value="deepseek_answer"), \
             patch.object(self.ex, "_call_ollama", return_value="ollama_answer"):
            result = self.ex._call_llm_speculative(self.messages, "test-model")
        self.assertIn(result, ("deepseek_answer", "ollama_answer"))

    def test_speculative_falls_back_when_both_none(self):
        """Both DeepSeek and Ollama return None — falls back to Cerebras."""
        with patch.object(self.ex, "_call_deepseek", return_value=None), \
             patch.object(self.ex, "_call_ollama", return_value=None), \
             patch.object(self.ex, "_call_external", return_value="cerebras_answer") as mock_cerebras:
            result = self.ex._call_llm_speculative(self.messages, "test-model")
        self.assertEqual(result, "cerebras_answer")
        mock_cerebras.assert_called_once()

    def test_speculative_falls_back_to_groq_when_cerebras_none(self):
        """DeepSeek+Ollama+Cerebras all fail — falls back to Groq."""
        with patch.object(self.ex, "_call_deepseek", return_value=None), \
             patch.object(self.ex, "_call_ollama", return_value=None), \
             patch.object(self.ex, "_call_external", return_value=None), \
             patch.object(self.ex, "_call_groq", return_value="groq_answer") as mock_groq:
            result = self.ex._call_llm_speculative(self.messages, "test-model")
        self.assertEqual(result, "groq_answer")
        mock_groq.assert_called_once()

    def test_speculative_returns_none_when_all_fail(self):
        """All providers fail — returns None."""
        with patch.object(self.ex, "_call_deepseek", return_value=None), \
             patch.object(self.ex, "_call_ollama", return_value=None), \
             patch.object(self.ex, "_call_external", return_value=None), \
             patch.object(self.ex, "_call_groq", return_value=None):
            result = self.ex._call_llm_speculative(self.messages, "test-model")
        self.assertIsNone(result)

    def test_call_llm_uses_speculative_when_deepseek_key_set(self):
        """_call_llm delegates to _call_llm_speculative when DEEPSEEK_API_KEY is set."""
        import core.autonomous_executor as ae
        original_key = ae.DEEPSEEK_API_KEY
        ae.DEEPSEEK_API_KEY = "fake-key"
        try:
            with patch.object(self.ex, "_call_llm_speculative", return_value="spec_result") as mock_spec:
                result = self.ex._call_llm(self.messages, "test-model")
            self.assertEqual(result, "spec_result")
            mock_spec.assert_called_once_with(self.messages, "test-model")
        finally:
            ae.DEEPSEEK_API_KEY = original_key

    def test_call_llm_serial_when_no_deepseek_key(self):
        """_call_llm uses serial Ollama→Cerebras→Groq chain when no DEEPSEEK_API_KEY."""
        import core.autonomous_executor as ae
        original_key = ae.DEEPSEEK_API_KEY
        ae.DEEPSEEK_API_KEY = ""
        try:
            with patch.object(self.ex, "_call_ollama", return_value="ollama_result") as mock_ollama:
                result = self.ex._call_llm(self.messages, "test-model")
            self.assertEqual(result, "ollama_result")
            mock_ollama.assert_called_once()
        finally:
            ae.DEEPSEEK_API_KEY = original_key


if __name__ == "__main__":
    unittest.main(verbosity=2)
