"""
Tests for core.opsec_shield — OpsecShield operational security module.

Uses temp directories to avoid modifying real files.
Run: python3 -m unittest tests.test_opsec_shield
"""

import json
import os
import shutil
import socket
import stat
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.opsec_shield import (
    OpsecShield, LeakAlert, NetworkReport, PermissionAlert,
    DependencyAlert, MeshSecurityReport, OpsecReport, _redact,
)


class TestRedact(unittest.TestCase):
    """Test the redaction utility."""

    def test_redact_long_string(self):
        result = _redact("gsk_abc123def456")
        self.assertEqual(result, "gsk_****")

    def test_redact_short_string(self):
        result = _redact("ab")
        self.assertEqual(result, "****")

    def test_redact_custom_chars(self):
        result = _redact("sk-1234567890", show_chars=6)
        self.assertEqual(result, "sk-123****")


class TestLeakScan(unittest.TestCase):
    """Test Data Leak Prevention (DLP) scanning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create minimal structure
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_groq_key(self):
        """Detect Groq API key pattern."""
        test_file = os.path.join(self.tmpdir, "config.py")
        with open(test_file, "w") as f:
            f.write('GROQ_KEY = "gsk_abcdefghijklmnopqrstuvwxyz"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        api_alerts = [a for a in alerts if a.category == "API_KEY"]
        self.assertTrue(len(api_alerts) > 0)
        self.assertEqual(api_alerts[0].severity, "CRITICAL")

    def test_detect_openai_key(self):
        """Detect OpenAI API key pattern."""
        test_file = os.path.join(self.tmpdir, "settings.py")
        with open(test_file, "w") as f:
            f.write('OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        api_alerts = [a for a in alerts if a.category == "API_KEY"]
        self.assertTrue(len(api_alerts) > 0)

    def test_detect_aws_key(self):
        """Detect AWS Access Key pattern."""
        test_file = os.path.join(self.tmpdir, "aws.py")
        with open(test_file, "w") as f:
            f.write('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        api_alerts = [a for a in alerts if a.category == "API_KEY"]
        self.assertTrue(len(api_alerts) > 0)

    def test_detect_private_key_header(self):
        """Detect PEM private key header."""
        test_file = os.path.join(self.tmpdir, "key.txt")
        with open(test_file, "w") as f:
            f.write("-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK...\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        pk_alerts = [a for a in alerts if a.category == "PRIVATE_KEY"]
        self.assertTrue(len(pk_alerts) > 0)
        self.assertEqual(pk_alerts[0].severity, "CRITICAL")

    def test_detect_password(self):
        """Detect hardcoded password."""
        test_file = os.path.join(self.tmpdir, "db.py")
        with open(test_file, "w") as f:
            f.write('password = "supersecretpassword123"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        cred_alerts = [a for a in alerts if a.category == "CREDENTIAL"]
        self.assertTrue(len(cred_alerts) > 0)

    def test_detect_database_url(self):
        """Detect database connection URL."""
        test_file = os.path.join(self.tmpdir, "config.py")
        with open(test_file, "w") as f:
            f.write('DB_URL = "postgresql://user:pass@localhost:5432/db"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        db_alerts = [a for a in alerts if a.category == "DATABASE_URL"]
        self.assertTrue(len(db_alerts) > 0)

    def test_detect_jwt_token(self):
        """Detect JWT token (eyJ pattern)."""
        test_file = os.path.join(self.tmpdir, "auth.py")
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        with open(test_file, "w") as f:
            f.write(f'TOKEN = "{jwt}"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        jwt_alerts = [a for a in alerts if "JWT" in a.pattern_matched]
        self.assertTrue(len(jwt_alerts) > 0)

    def test_clean_file_no_alerts(self):
        """Clean file should produce no leak alerts from content scanning."""
        test_file = os.path.join(self.tmpdir, "clean.py")
        with open(test_file, "w") as f:
            f.write('def hello():\n    print("Hello, world!")\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        # Filter out .gitignore alerts — only check content-based alerts
        content_alerts = [a for a in alerts if a.line_number > 0]
        self.assertEqual(len(content_alerts), 0)

    def test_detect_sensitive_filename(self):
        """Detect known sensitive filenames."""
        env_file = os.path.join(self.tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write("SOME_VAR=value\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        file_alerts = [a for a in alerts if "sensitive_file" in a.pattern_matched]
        self.assertTrue(len(file_alerts) > 0)

    def test_detect_oracle_key_json(self):
        """Detect oracle_key.json (known incident)."""
        oracle_file = os.path.join(self.tmpdir, "oracle_key.json")
        with open(oracle_file, "w") as f:
            f.write('{"key": "value"}\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        oracle_alerts = [a for a in alerts if "oracle_key" in a.pattern_matched]
        self.assertTrue(len(oracle_alerts) > 0)
        self.assertEqual(oracle_alerts[0].severity, "CRITICAL")

    def test_skip_binary_files(self):
        """Binary files should be skipped."""
        bin_file = os.path.join(self.tmpdir, "data.png")
        with open(bin_file, "wb") as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'gsk_fakekeyfakekeyfakekey' * 10)
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        bin_alerts = [a for a in alerts if "data.png" in a.file_path]
        self.assertEqual(len(bin_alerts), 0)

    def test_skip_git_directory(self):
        """Files inside .git should be skipped."""
        git_dir = os.path.join(self.tmpdir, ".git", "objects")
        os.makedirs(git_dir, exist_ok=True)
        secret_file = os.path.join(git_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write('gsk_abcdefghijklmnopqrstuvwxyz\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        git_alerts = [a for a in alerts if ".git" in a.file_path]
        self.assertEqual(len(git_alerts), 0)

    def test_env_not_in_gitignore(self):
        """Flag when .env is not in .gitignore."""
        gitignore = os.path.join(self.tmpdir, ".gitignore")
        with open(gitignore, "w") as f:
            f.write("*.pyc\n__pycache__/\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        gi_alerts = [a for a in alerts if ".env not in .gitignore" in a.pattern_matched]
        self.assertTrue(len(gi_alerts) > 0)

    def test_alerts_sorted_by_severity(self):
        """Alerts should be sorted by severity (CRITICAL first)."""
        # Create a file with multiple issues of different severity
        test_file = os.path.join(self.tmpdir, "mixed.py")
        with open(test_file, "w") as f:
            f.write('key = "gsk_abcdefghijklmnopqrstuvwxyz"\n')
            f.write('ip = "192.168.1.100"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_for_leaks()
        content_alerts = [a for a in alerts if a.line_number > 0]
        if len(content_alerts) >= 2:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            for i in range(len(content_alerts) - 1):
                self.assertLessEqual(
                    severity_order.get(content_alerts[i].severity, 4),
                    severity_order.get(content_alerts[i + 1].severity, 4),
                )


class TestGitAudit(unittest.TestCase):
    """Test Git History Audit."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_git_repo_returns_empty(self):
        """Non-git directory should return empty alerts."""
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_git_history()
        self.assertEqual(len(alerts), 0)

    def test_git_audit_with_mock_repo(self):
        """Git audit in a mock repo with clean history."""
        # Create a minimal git repo
        os.makedirs(os.path.join(self.tmpdir, ".git"), exist_ok=True)
        shield = OpsecShield(project_dir=self.tmpdir)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            alerts = shield.audit_git_history()
            # Should have called git commands
            self.assertTrue(mock_run.called)

    def test_git_audit_detects_env_in_history(self):
        """Detect .env file in git history."""
        os.makedirs(os.path.join(self.tmpdir, ".git"), exist_ok=True)
        shield = OpsecShield(project_dir=self.tmpdir)

        call_count = [0]

        def mock_run(cmd, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            if call_count[0] == 1:
                # First call: git log --diff-filter=A
                result.stdout = ".env\noracle_key.json\n"
            else:
                result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            alerts = shield.audit_git_history()
            env_alerts = [a for a in alerts if ".env" in a.file_path
                         or "oracle_key" in a.file_path]
            self.assertTrue(len(env_alerts) > 0)


class TestNetworkScan(unittest.TestCase):
    """Test Network Exposure Scan."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_network_report_structure(self):
        """Network report should have correct structure."""
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.scan_network_exposure()
        self.assertIsInstance(report, NetworkReport)
        self.assertIsInstance(report.open_ports, list)
        self.assertIsInstance(report.firewall_active, bool)
        self.assertIsInstance(report.exposed_services, list)
        self.assertIn(report.risk_level, ("LOW", "MEDIUM", "HIGH", "CRITICAL"))

    def test_network_scan_uses_socket(self):
        """Network scan should use socket, not external tools."""
        shield = OpsecShield(project_dir=self.tmpdir)
        # Patch socket to control the test
        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_socket.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_socket.return_value.__exit__ = MagicMock(return_value=False)
            mock_instance.connect_ex.return_value = 1  # port closed
            report = shield.scan_network_exposure()
            self.assertIsInstance(report, NetworkReport)

    def test_network_scan_with_open_port(self):
        """Test detection of an open port using a real socket server."""
        # Start a temporary server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", 9876))
            server.listen(1)

            shield = OpsecShield(project_dir=self.tmpdir)

            # Monkey-patch the port list temporarily
            import core.opsec_shield as mod
            original = dict(mod._KNOWN_SERVICES)
            mod._KNOWN_SERVICES[9876] = "Test Server"
            try:
                report = shield.scan_network_exposure()
                port_nums = [p["port"] for p in report.open_ports]
                self.assertIn(9876, port_nums)
            finally:
                mod._KNOWN_SERVICES.clear()
                mod._KNOWN_SERVICES.update(original)
        finally:
            server.close()


class TestPermissionAudit(unittest.TestCase):
    """Test File Permission Audit."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_env_wrong_permissions(self):
        """Flag .env file with wrong permissions."""
        env_file = os.path.join(self.tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write("SECRET=value\n")
        os.chmod(env_file, 0o644)
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_permissions()
        env_alerts = [a for a in alerts if ".env" in a.file_path]
        self.assertTrue(len(env_alerts) > 0)
        self.assertEqual(env_alerts[0].recommended, "600")

    def test_env_correct_permissions(self):
        """No alert for .env file with correct permissions."""
        env_file = os.path.join(self.tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write("SECRET=value\n")
        os.chmod(env_file, 0o600)
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_permissions()
        env_alerts = [a for a in alerts if ".env" in a.file_path
                     and a.current_permissions != "600"]
        self.assertEqual(len(env_alerts), 0)

    def test_world_readable_logs(self):
        """Flag world-readable log files."""
        log_file = os.path.join(self.tmpdir, "logs", "test.log")
        with open(log_file, "w") as f:
            f.write("some log data\n")
        os.chmod(log_file, 0o644)
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_permissions()
        log_alerts = [a for a in alerts if "world-readable" in a.reason]
        self.assertTrue(len(log_alerts) > 0)

    def test_no_sensitive_files_no_alerts(self):
        """No alerts when no sensitive files exist."""
        # tmpdir has no .env or key files
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_permissions()
        # May have log alerts but no .env alerts
        env_alerts = [a for a in alerts if ".env" in a.file_path]
        self.assertEqual(len(env_alerts), 0)

    def test_permission_alert_structure(self):
        """PermissionAlert should have correct fields."""
        env_file = os.path.join(self.tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write("KEY=val\n")
        os.chmod(env_file, 0o755)
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.audit_permissions()
        env_alerts = [a for a in alerts if ".env" in a.file_path]
        if env_alerts:
            alert = env_alerts[0]
            self.assertIsInstance(alert, PermissionAlert)
            self.assertTrue(alert.file_path)
            self.assertTrue(alert.current_permissions)
            self.assertTrue(alert.recommended)
            self.assertTrue(alert.reason)


class TestDependencyScan(unittest.TestCase):
    """Test Dependency Vulnerability Scan."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_unpinned_dependency(self):
        """Detect completely unpinned dependency."""
        req_file = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("litellm\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        unpinned = [a for a in alerts if a.issue == "unpinned"]
        self.assertTrue(len(unpinned) > 0)
        self.assertEqual(unpinned[0].package, "litellm")

    def test_detect_range_pinned(self):
        """Detect >= pinned dependency (not exact pin)."""
        req_file = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("flask>=2.0.0\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        range_alerts = [a for a in alerts if a.issue == "unpinned" and a.package == "flask"]
        self.assertTrue(len(range_alerts) > 0)
        self.assertEqual(range_alerts[0].severity, "LOW")

    def test_detect_known_vulnerability(self):
        """Detect known vulnerable version."""
        req_file = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("pyyaml>=5.1\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        vuln_alerts = [a for a in alerts if "known_vuln" in a.issue]
        self.assertTrue(len(vuln_alerts) > 0)

    def test_no_requirements_file(self):
        """No requirements.txt should return empty."""
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        self.assertEqual(len(alerts), 0)

    def test_typosquat_detection(self):
        """Detect potential typosquatting packages."""
        req_file = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("reqeusts>=2.0\n")  # typo of 'requests'
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        typo_alerts = [a for a in alerts if "typosquat" in a.issue]
        self.assertTrue(len(typo_alerts) > 0)

    def test_clean_requirements(self):
        """Properly pinned known packages should have minimal issues."""
        req_file = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("# A comment\nrich>=13.9.0\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        alerts = shield.scan_dependencies()
        # Only range-pinned alert, no vuln or typosquat
        vuln_alerts = [a for a in alerts if "known_vuln" in a.issue]
        typo_alerts = [a for a in alerts if "typosquat" in a.issue]
        self.assertEqual(len(vuln_alerts), 0)
        self.assertEqual(len(typo_alerts), 0)

    def test_version_comparison(self):
        """Test version comparison utility."""
        shield = OpsecShield(project_dir=self.tmpdir)
        self.assertTrue(shield._version_lte("1.0.0", "2.0.0"))
        self.assertTrue(shield._version_lte("1.0.0", "1.0.0"))
        self.assertFalse(shield._version_lte("2.0.0", "1.0.0"))
        self.assertTrue(shield._version_lte("1.0", "1.0.1"))

    def test_typosquat_detection_helper(self):
        """Test typosquatting detection helper."""
        self.assertTrue(OpsecShield._is_typosquat("reqeusts", "requests"))
        self.assertTrue(OpsecShield._is_typosquat("requets", "requests"))
        self.assertFalse(OpsecShield._is_typosquat("requests", "requests"))
        self.assertFalse(OpsecShield._is_typosquat("something_else", "requests"))


class TestMeshSecurityAudit(unittest.TestCase):
    """Test Mesh Communication Security Audit."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mesh_dir = os.path.join(self.tmpdir, "logs", "mesh")
        os.makedirs(self.mesh_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_plaintext_detection(self):
        """Detect plaintext messages in inbox."""
        inbox_dir = os.path.join(self.mesh_dir, "inbox", "node_a")
        os.makedirs(inbox_dir, exist_ok=True)
        msg_file = os.path.join(inbox_dir, "msg_001.json")
        with open(msg_file, "w") as f:
            json.dump({"from_node": "node_b", "content": "Hello there"}, f)
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertTrue(report.plaintext_messages)

    def test_no_auth_detection(self):
        """Detect lack of node authentication."""
        nodes_file = os.path.join(self.mesh_dir, "nodes.json")
        with open(nodes_file, "w") as f:
            json.dump({"node_a": {"status": "active"}}, f)
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertFalse(report.node_authentication)

    def test_unbounded_log_detection(self):
        """Detect large JSONL log files."""
        large_log = os.path.join(self.mesh_dir, "messages.jsonl")
        # Write >1MB of data
        with open(large_log, "w") as f:
            for i in range(50000):
                f.write(json.dumps({"i": i, "msg": "x" * 20}) + "\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertTrue(len(report.unbounded_logs) > 0)

    def test_recommendations_generated(self):
        """Report should generate recommendations."""
        inbox_dir = os.path.join(self.mesh_dir, "inbox", "node_a")
        os.makedirs(inbox_dir, exist_ok=True)
        msg_file = os.path.join(inbox_dir, "msg_001.json")
        with open(msg_file, "w") as f:
            json.dump({"from_node": "b", "content": "test"}, f)
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertTrue(len(report.recommendations) > 0)

    def test_empty_mesh_dir(self):
        """Empty mesh directory should return safe-ish report."""
        # mesh_dir exists but is empty
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertIsInstance(report, MeshSecurityReport)
        self.assertEqual(len(report.permission_issues), 0)

    def test_mesh_report_structure(self):
        """MeshSecurityReport should have all required fields."""
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.audit_mesh_security()
        self.assertIsInstance(report.plaintext_messages, bool)
        self.assertIsInstance(report.node_authentication, bool)
        self.assertIsInstance(report.permission_issues, list)
        self.assertIsInstance(report.unbounded_logs, list)
        self.assertIsInstance(report.recommendations, list)


class TestFullAudit(unittest.TestCase):
    """Test full audit integration."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_full_audit_returns_report(self):
        """Full audit should return OpsecReport."""
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.full_audit()
        self.assertIsInstance(report, OpsecReport)

    def test_full_audit_score_range(self):
        """Overall score should be between 0.0 and 10.0."""
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.full_audit()
        self.assertGreaterEqual(report.overall_score, 0.0)
        self.assertLessEqual(report.overall_score, 10.0)

    def test_full_audit_saves_report(self):
        """Full audit should save report to JSON file."""
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.full_audit()
        report_file = os.path.join(self.tmpdir, "logs", "mesh", "opsec_report.json")
        self.assertTrue(os.path.exists(report_file))
        with open(report_file) as f:
            saved = json.load(f)
        self.assertEqual(saved["overall_score"], report.overall_score)

    def test_full_audit_with_leaks(self):
        """Full audit should detect leaks and lower score."""
        # Create a file with a secret
        test_file = os.path.join(self.tmpdir, "secret.py")
        with open(test_file, "w") as f:
            f.write('KEY = "gsk_abcdefghijklmnopqrstuvwxyz"\n')
        shield = OpsecShield(project_dir=self.tmpdir)
        report = shield.full_audit()
        self.assertGreater(report.leaks_found, 0)
        self.assertLess(report.overall_score, 10.0)
        self.assertTrue(len(report.critical_actions) > 0)


class TestHarden(unittest.TestCase):
    """Test hardening functionality."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_harden_fixes_env_permissions(self):
        """Harden should fix .env file permissions."""
        env_file = os.path.join(self.tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write("SECRET=value\n")
        os.chmod(env_file, 0o644)
        shield = OpsecShield(project_dir=self.tmpdir)
        actions = shield.harden()
        # Check that chmod was applied
        new_mode = os.stat(env_file).st_mode & 0o777
        self.assertEqual(new_mode, 0o600)
        chmod_actions = [a for a in actions if "chmod" in a]
        self.assertTrue(len(chmod_actions) > 0)

    def test_harden_updates_gitignore(self):
        """Harden should add missing entries to .gitignore."""
        gitignore = os.path.join(self.tmpdir, ".gitignore")
        with open(gitignore, "w") as f:
            f.write("*.pyc\n")
        shield = OpsecShield(project_dir=self.tmpdir)
        actions = shield.harden()
        # Read updated .gitignore
        with open(gitignore) as f:
            content = f.read()
        self.assertIn(".env", content)
        self.assertIn("oracle_key.json", content)
        gitignore_actions = [a for a in actions if ".gitignore" in a]
        self.assertTrue(len(gitignore_actions) > 0)

    def test_harden_no_changes_needed(self):
        """Harden with nothing to fix should return empty/minimal actions."""
        shield = OpsecShield(project_dir=self.tmpdir)
        actions = shield.harden()
        # No .env, no .gitignore, no inbox — should have no actions
        self.assertIsInstance(actions, list)


class TestPersistence(unittest.TestCase):
    """Test audit logging and persistence."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "logs", "mesh"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_audit_log_created(self):
        """Audit events should be logged to JSONL."""
        shield = OpsecShield(project_dir=self.tmpdir)
        shield.scan_for_leaks()
        audit_file = os.path.join(self.tmpdir, "logs", "mesh", "opsec_audit.jsonl")
        self.assertTrue(os.path.exists(audit_file))
        with open(audit_file) as f:
            lines = f.readlines()
        self.assertTrue(len(lines) > 0)
        event = json.loads(lines[0])
        self.assertEqual(event["event"], "leak_scan")

    def test_multiple_events_appended(self):
        """Multiple scans should append to the audit log."""
        shield = OpsecShield(project_dir=self.tmpdir)
        shield.scan_for_leaks()
        shield.audit_permissions()
        audit_file = os.path.join(self.tmpdir, "logs", "mesh", "opsec_audit.jsonl")
        with open(audit_file) as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
