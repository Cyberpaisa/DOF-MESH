"""
OpsecShield — Operational Security Module for DOF Mesh Infrastructure.

DEFENSIVE security techniques protecting our own infrastructure:
  1. Data Leak Prevention (DLP) — scan for accidentally exposed secrets
  2. Git History Audit — detect secrets in commit history
  3. Network Exposure Scan — check open ports and service bindings
  4. File Permission Audit — verify sensitive files are locked down
  5. Dependency Vulnerability Scan — flag unpinned or suspicious packages
  6. Mesh Communication Security — audit mesh message storage and auth

100% deterministic — zero LLM dependency. All stdlib, no external packages.

Persistence:
  logs/mesh/opsec_audit.jsonl    — audit event log
  logs/mesh/opsec_report.json   — last full report

Usage:
    from core.opsec_shield import OpsecShield

    shield = OpsecShield()
    leaks = shield.scan_for_leaks()
    report = shield.full_audit()
    actions = shield.harden()
"""

import json
import logging
import os
import re
import socket
import stat
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger("core.opsec_shield")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ===================================================================
# DATA CLASSES
# ===================================================================

@dataclass
class LeakAlert:
    """A detected data leak in the project."""
    severity: str       # CRITICAL, HIGH, MEDIUM, LOW
    category: str       # API_KEY, PRIVATE_KEY, DATABASE_URL, CREDENTIAL, PII
    file_path: str
    line_number: int
    pattern_matched: str
    preview: str        # redacted preview (first 20 chars + ****)
    recommendation: str


@dataclass
class NetworkReport:
    """Result of a network exposure scan."""
    open_ports: list     # list[dict] — {port, service, binding, exposed}
    firewall_active: bool
    exposed_services: list  # list[str]
    risk_level: str      # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class PermissionAlert:
    """A file permission issue."""
    file_path: str
    current_permissions: str   # e.g., "644"
    recommended: str           # e.g., "600"
    reason: str


@dataclass
class DependencyAlert:
    """A dependency issue."""
    package: str
    version: str
    issue: str       # unpinned, known_vuln, typosquat_risk
    severity: str    # CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class MeshSecurityReport:
    """Mesh communication security audit."""
    plaintext_messages: bool
    node_authentication: bool
    permission_issues: list     # list[str]
    unbounded_logs: list        # list[str]
    recommendations: list       # list[str]


@dataclass
class OpsecReport:
    """Full operational security audit report."""
    timestamp: float
    leaks_found: int
    network_risk: str
    permission_issues: int
    dependency_issues: int
    mesh_security_issues: int
    overall_score: float        # 0.0 to 10.0 (10 = fully hardened)
    critical_actions: list      # list[str] — what to fix NOW


# ===================================================================
# LEAK DETECTION PATTERNS
# ===================================================================

_API_KEY_PATTERNS = [
    ("API_KEY", "Groq API key",        re.compile(r'gsk_[a-zA-Z0-9]{20,}')),
    ("API_KEY", "OpenAI API key",      re.compile(r'sk-[a-zA-Z0-9]{20,}')),
    ("API_KEY", "Google API key",      re.compile(r'AIza[a-zA-Z0-9_-]{30,}')),
    ("API_KEY", "NVIDIA API key",      re.compile(r'nvapi-[a-zA-Z0-9_-]{20,}')),
    ("API_KEY", "GitHub PAT",          re.compile(r'ghp_[a-zA-Z0-9]{36,}')),
    ("API_KEY", "AWS Access Key",      re.compile(r'AKIA[A-Z0-9]{16}')),
    ("CREDENTIAL", "Bearer token",     re.compile(r'Bearer\s+[a-zA-Z0-9_\-.]{20,}')),
    ("CREDENTIAL", "Inline token",     re.compile(r'token\s*=\s*["\'][a-zA-Z0-9_\-.]{16,}')),
    ("CREDENTIAL", "Inline password",  re.compile(r'password\s*=\s*["\'][^\'"]{8,}')),
]

_PRIVATE_KEY_PATTERN = re.compile(r'-----BEGIN\s+[\w\s]*PRIVATE\s+KEY-----')

_WALLET_KEY_PATTERN = re.compile(r'\b[0-9a-fA-F]{64}\b')

_DATABASE_URL_PATTERNS = [
    ("DATABASE_URL", "PostgreSQL URL",  re.compile(r'postgresql://[^\s"\']+', re.IGNORECASE)),
    ("DATABASE_URL", "MySQL URL",       re.compile(r'mysql://[^\s"\']+', re.IGNORECASE)),
    ("DATABASE_URL", "MongoDB URL",     re.compile(r'mongodb://[^\s"\']+', re.IGNORECASE)),
    ("DATABASE_URL", "MongoDB+srv URL", re.compile(r'mongodb\+srv://[^\s"\']+', re.IGNORECASE)),
]

_JWT_PATTERN = re.compile(r'eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}')

_INTERNAL_IP_PATTERN = re.compile(
    r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|'
    r'192\.168\.\d{1,3}\.\d{1,3})\b'
)

# Files to skip during scanning
_SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.bin',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.bmp',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.xlsb',
    '.woff', '.woff2', '.ttf', '.eot',
    '.db', '.sqlite', '.sqlite3',
}

_SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    '.mypy_cache', '.pytest_cache', '.tox', 'dist', 'build',
    'egg-info', '.eggs',
}

# Known sensitive filenames
_SENSITIVE_FILES = {
    '.env', '.env.local', '.env.production', '.env.staging',
    'oracle_key.json', 'credentials.json', 'service_account.json',
    'id_rsa', 'id_ed25519', 'id_ecdsa',
}

# Known vulnerable package versions (basic list, no network needed)
_KNOWN_VULNS = {
    'requests': [('2.19.1', 'CVE-2018-18074: Session redirect vulnerability')],
    'urllib3': [('1.24.1', 'CVE-2019-11324: Certificate verification bypass')],
    'pyyaml': [('5.3', 'CVE-2020-14343: Arbitrary code execution via yaml.load')],
    'jinja2': [('2.11.2', 'CVE-2020-28493: ReDoS vulnerability')],
    'flask': [('1.0', 'CVE-2019-1010083: DoS vulnerability')],
    'django': [('3.0', 'Multiple CVEs in Django <3.1')],
    'pillow': [('8.3.2', 'CVE-2021-34552: Buffer overflow')],
    'cryptography': [('3.3', 'CVE-2020-36242: Integer overflow')],
}

# Typosquatting patterns — packages with names suspiciously similar to popular ones
_POPULAR_PACKAGES = {
    'requests', 'flask', 'django', 'numpy', 'pandas', 'scipy',
    'tensorflow', 'torch', 'boto3', 'sqlalchemy', 'celery',
    'redis', 'pillow', 'cryptography', 'paramiko', 'pyyaml',
}

# Ports commonly used by DOF services
_KNOWN_SERVICES = {
    8000: "A2A Server",
    8501: "Streamlit Dashboard",
    7899: "Peers Broker",
    5000: "Flask Dev Server",
    3000: "Node.js Dev Server",
    6379: "Redis",
    5432: "PostgreSQL",
    27017: "MongoDB",
}


# ===================================================================
# REDACTION UTILITY
# ===================================================================

def _redact(value: str, show_chars: int = 4) -> str:
    """Redact a sensitive value, showing only first N chars."""
    if len(value) <= show_chars:
        return "****"
    return value[:show_chars] + "****"


# ===================================================================
# OPSEC SHIELD
# ===================================================================

class OpsecShield:
    """Operational Security Shield — infrastructure protection for the DOF mesh.

    All checks are DEFENSIVE — protecting our own infrastructure.
    Zero LLM dependency. All stdlib.

    Usage:
        shield = OpsecShield()
        leaks = shield.scan_for_leaks()
        report = shield.full_audit()
        actions = shield.harden()
    """

    def __init__(self, project_dir: str = "."):
        self._project_dir = Path(project_dir).resolve()
        self._log_dir = self._project_dir / "logs" / "mesh"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._audit_file = self._log_dir / "opsec_audit.jsonl"
        self._report_file = self._log_dir / "opsec_report.json"

    # ===============================================================
    # PERSISTENCE
    # ===============================================================

    def _log_event(self, event_type: str, data: dict):
        """Append audit event to JSONL log."""
        try:
            entry = {
                "timestamp": time.time(),
                "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "event": event_type,
                **data,
            }
            with open(self._audit_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log opsec event: {e}")

    def _save_report(self, report: OpsecReport):
        """Save the last full report to JSON."""
        try:
            self._report_file.write_text(
                json.dumps(asdict(report), indent=2, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to save opsec report: {e}")

    # ===============================================================
    # 1. DATA LEAK PREVENTION (DLP)
    # ===============================================================

    def scan_for_leaks(self, directory: str = ".") -> list[LeakAlert]:
        """Scan the project directory for accidentally exposed sensitive data.

        Checks for: API keys, private keys, wallet keys, database URLs,
        .env files, oracle_key.json, SSH keys, hardcoded IPs, JWT tokens.

        Returns severity-ranked list of findings.
        """
        scan_dir = Path(directory).resolve() if directory != "." else self._project_dir
        alerts: list[LeakAlert] = []

        for root, dirs, files in os.walk(scan_dir):
            # Skip irrelevant directories
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]

            root_path = Path(root)

            for filename in files:
                file_path = root_path / filename
                ext = file_path.suffix.lower()

                # Skip binary/media files
                if ext in _SKIP_EXTENSIONS:
                    continue

                # Check for known sensitive filenames
                if filename in _SENSITIVE_FILES:
                    alerts.append(LeakAlert(
                        severity="CRITICAL" if filename in ('.env', 'oracle_key.json') else "HIGH",
                        category="CREDENTIAL",
                        file_path=str(file_path),
                        line_number=0,
                        pattern_matched=f"sensitive_file:{filename}",
                        preview=f"{filename} (sensitive file)",
                        recommendation=f"Ensure {filename} is in .gitignore and has permissions 600",
                    ))

                # Check for SSH keys in unexpected locations
                if filename.startswith("id_") and not filename.endswith(".pub"):
                    rel = file_path.relative_to(scan_dir) if file_path.is_relative_to(scan_dir) else file_path
                    if ".ssh" not in str(rel):
                        alerts.append(LeakAlert(
                            severity="CRITICAL",
                            category="PRIVATE_KEY",
                            file_path=str(file_path),
                            line_number=0,
                            pattern_matched=f"ssh_key_outside_ssh_dir:{filename}",
                            preview=f"{filename} (SSH key outside ~/.ssh)",
                            recommendation="Move SSH keys to ~/.ssh/ and set permissions 600",
                        ))

                # Scan file contents
                try:
                    # Skip large files (>1MB)
                    if file_path.stat().st_size > 1_000_000:
                        continue
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except (OSError, UnicodeDecodeError):
                    continue

                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    # API key patterns
                    for category, desc, pattern in _API_KEY_PATTERNS:
                        match = pattern.search(line)
                        if match:
                            alerts.append(LeakAlert(
                                severity="CRITICAL",
                                category=category,
                                file_path=str(file_path),
                                line_number=line_num,
                                pattern_matched=desc,
                                preview=_redact(match.group()),
                                recommendation=f"Remove {desc} from source code; use environment variables",
                            ))

                    # Private key headers
                    if _PRIVATE_KEY_PATTERN.search(line):
                        alerts.append(LeakAlert(
                            severity="CRITICAL",
                            category="PRIVATE_KEY",
                            file_path=str(file_path),
                            line_number=line_num,
                            pattern_matched="PEM private key header",
                            preview=_redact(line.strip()),
                            recommendation="Never store private keys in source code",
                        ))

                    # Wallet private keys (64-char hex)
                    if _WALLET_KEY_PATTERN.search(line):
                        # Avoid false positives: skip lines that look like hashes in context
                        stripped = line.strip()
                        if len(stripped) <= 70 and not stripped.startswith("#"):
                            alerts.append(LeakAlert(
                                severity="HIGH",
                                category="PRIVATE_KEY",
                                file_path=str(file_path),
                                line_number=line_num,
                                pattern_matched="64-char hex (potential wallet private key)",
                                preview=_redact(stripped),
                                recommendation="Verify this is not a private key; if so, remove immediately",
                            ))

                    # Database URLs
                    for category, desc, pattern in _DATABASE_URL_PATTERNS:
                        match = pattern.search(line)
                        if match:
                            alerts.append(LeakAlert(
                                severity="HIGH",
                                category=category,
                                file_path=str(file_path),
                                line_number=line_num,
                                pattern_matched=desc,
                                preview=_redact(match.group()),
                                recommendation="Use environment variables for database connection strings",
                            ))

                    # JWT tokens
                    if _JWT_PATTERN.search(line):
                        match = _JWT_PATTERN.search(line)
                        if match:
                            alerts.append(LeakAlert(
                                severity="MEDIUM",
                                category="CREDENTIAL",
                                file_path=str(file_path),
                                line_number=line_num,
                                pattern_matched="JWT token (eyJ pattern)",
                                preview=_redact(match.group()),
                                recommendation="Do not hardcode JWT tokens; use secure token storage",
                            ))

                    # Hardcoded internal IPs
                    if _INTERNAL_IP_PATTERN.search(line):
                        match = _INTERNAL_IP_PATTERN.search(line)
                        if match:
                            alerts.append(LeakAlert(
                                severity="LOW",
                                category="PII",
                                file_path=str(file_path),
                                line_number=line_num,
                                pattern_matched="hardcoded internal IP",
                                preview=match.group(),
                                recommendation="Use configuration variables for internal IP addresses",
                            ))

        # Check .env in .gitignore
        gitignore_path = self._project_dir / ".gitignore"
        if gitignore_path.exists():
            try:
                gitignore_content = gitignore_path.read_text()
                if ".env" not in gitignore_content:
                    alerts.append(LeakAlert(
                        severity="HIGH",
                        category="CREDENTIAL",
                        file_path=str(gitignore_path),
                        line_number=0,
                        pattern_matched=".env not in .gitignore",
                        preview=".gitignore missing .env entry",
                        recommendation="Add .env to .gitignore immediately",
                    ))
            except OSError:
                pass

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 4))

        self._log_event("leak_scan", {
            "directory": str(scan_dir),
            "alerts_found": len(alerts),
            "critical": sum(1 for a in alerts if a.severity == "CRITICAL"),
        })

        return alerts

    # ===============================================================
    # 2. GIT HISTORY AUDIT
    # ===============================================================

    def audit_git_history(self, max_commits: int = 100) -> list[LeakAlert]:
        """Scan recent git diffs for accidentally committed secrets.

        Checks: secrets in diffs, .env/.key files ever tracked, large binaries,
        force pushes / history rewrites.
        """
        alerts: list[LeakAlert] = []

        # Check if we're in a git repo
        git_dir = self._project_dir / ".git"
        if not git_dir.exists():
            return alerts

        try:
            # Check if .env was ever tracked
            result = subprocess.run(
                ["git", "log", "--all", "--diff-filter=A", "--name-only",
                 "--pretty=format:", "--", ".env", "oracle_key.json",
                 "*.pem", "*.key", "id_rsa", "id_ed25519"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self._project_dir),
            )
            if result.stdout.strip():
                for tracked_file in result.stdout.strip().split("\n"):
                    tracked_file = tracked_file.strip()
                    if tracked_file:
                        alerts.append(LeakAlert(
                            severity="CRITICAL",
                            category="CREDENTIAL",
                            file_path=tracked_file,
                            line_number=0,
                            pattern_matched="sensitive_file_in_git_history",
                            preview=f"{tracked_file} was committed to git",
                            recommendation=f"Use git filter-branch or BFG to remove {tracked_file} from history",
                        ))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        try:
            # Scan recent commit diffs for secrets
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--diff-filter=AM",
                 "-p", "--no-color", "--pretty=format:COMMIT:%H"],
                capture_output=True, text=True, timeout=60,
                cwd=str(self._project_dir),
            )
            if result.returncode == 0:
                current_commit = "unknown"
                for line in result.stdout.split("\n"):
                    if line.startswith("COMMIT:"):
                        current_commit = line[7:15]  # short hash
                        continue
                    if not line.startswith("+"):
                        continue
                    # Skip diff headers
                    if line.startswith("+++"):
                        continue

                    diff_line = line[1:]  # remove leading +

                    # Check for API keys in diffs
                    for _cat, desc, pattern in _API_KEY_PATTERNS:
                        match = pattern.search(diff_line)
                        if match:
                            alerts.append(LeakAlert(
                                severity="CRITICAL",
                                category="API_KEY",
                                file_path=f"git:commit:{current_commit}",
                                line_number=0,
                                pattern_matched=f"{desc} in git diff",
                                preview=_redact(match.group()),
                                recommendation=f"Secret found in commit {current_commit}; rotate the key and purge from history",
                            ))
                            break

                    # Check for private keys
                    if _PRIVATE_KEY_PATTERN.search(diff_line):
                        alerts.append(LeakAlert(
                            severity="CRITICAL",
                            category="PRIVATE_KEY",
                            file_path=f"git:commit:{current_commit}",
                            line_number=0,
                            pattern_matched="PEM private key in git diff",
                            preview=_redact(diff_line.strip()),
                            recommendation=f"Private key in commit {current_commit}; rotate and purge from history",
                        ))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        try:
            # Check for large binary files
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--diff-filter=A",
                 "--name-only", "--pretty=format:"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self._project_dir),
            )
            if result.returncode == 0:
                binary_exts = {'.bin', '.exe', '.dll', '.so', '.dylib',
                               '.zip', '.tar', '.gz', '.rar', '.7z',
                               '.db', '.sqlite', '.sqlite3'}
                for fname in result.stdout.strip().split("\n"):
                    fname = fname.strip()
                    if fname and Path(fname).suffix.lower() in binary_exts:
                        alerts.append(LeakAlert(
                            severity="MEDIUM",
                            category="CREDENTIAL",
                            file_path=fname,
                            line_number=0,
                            pattern_matched="binary_in_git",
                            preview=f"Binary file: {fname}",
                            recommendation=f"Consider removing {fname} from git; use .gitignore or Git LFS",
                        ))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        try:
            # Detect force pushes / reflog anomalies
            result = subprocess.run(
                ["git", "reflog", "--format=%gd %gs", "-20"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._project_dir),
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if any(kw in line.lower() for kw in ("reset:", "rebase", "force")):
                        alerts.append(LeakAlert(
                            severity="MEDIUM",
                            category="CREDENTIAL",
                            file_path="git:reflog",
                            line_number=0,
                            pattern_matched="history_rewrite",
                            preview=_redact(line, 40),
                            recommendation="History rewrite detected; verify no secrets were exposed before rewrite",
                        ))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 4))

        self._log_event("git_audit", {
            "max_commits": max_commits,
            "alerts_found": len(alerts),
        })

        return alerts

    # ===============================================================
    # 3. NETWORK EXPOSURE SCAN
    # ===============================================================

    def scan_network_exposure(self) -> NetworkReport:
        """Check what ports are open on localhost and service bindings.

        Uses socket only (no nmap or external tools).
        """
        open_ports: list[dict] = []
        exposed_services: list[str] = []

        # Scan common ports used by DOF and dev services
        ports_to_check = list(_KNOWN_SERVICES.keys()) + [
            80, 443, 8080, 8443, 9090, 4000, 5555, 6006, 8888,
        ]

        for port in sorted(set(ports_to_check)):
            service_name = _KNOWN_SERVICES.get(port, f"port-{port}")

            # Check if port is open on localhost
            is_open = False
            binding = "unknown"

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    result = s.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        is_open = True
                        binding = "127.0.0.1"
            except (OSError, socket.error):
                pass

            if is_open:
                # Check if also bound to 0.0.0.0 (exposed to network)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.3)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        # Try binding — if it fails, something else is already bound
                        try:
                            s.bind(("0.0.0.0", port))
                            # If we CAN bind to 0.0.0.0, the existing service is on 127.0.0.1
                            binding = "127.0.0.1"
                        except OSError:
                            # Can't bind — service might be on 0.0.0.0
                            binding = "0.0.0.0"
                            exposed_services.append(f"{service_name} on port {port}")
                except (OSError, socket.error):
                    pass

                open_ports.append({
                    "port": port,
                    "service": service_name,
                    "binding": binding,
                    "exposed": binding == "0.0.0.0",
                })

        # Check firewall status (macOS pf)
        firewall_active = False
        try:
            result = subprocess.run(
                ["pfctl", "-s", "info"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and "Status: Enabled" in result.stdout:
                firewall_active = True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

        # Also try macOS application firewall
        if not firewall_active:
            try:
                result = subprocess.run(
                    ["/usr/libexec/ApplicationFirewall/socketfilterfw",
                     "--getglobalstate"],
                    capture_output=True, text=True, timeout=5,
                )
                if "enabled" in result.stdout.lower():
                    firewall_active = True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass

        # Determine risk level
        if exposed_services and not firewall_active:
            risk_level = "HIGH"
        elif exposed_services:
            risk_level = "MEDIUM"
        elif open_ports and not firewall_active:
            risk_level = "LOW"
        else:
            risk_level = "LOW"

        report = NetworkReport(
            open_ports=open_ports,
            firewall_active=firewall_active,
            exposed_services=exposed_services,
            risk_level=risk_level,
        )

        self._log_event("network_scan", {
            "open_ports": len(open_ports),
            "exposed_services": len(exposed_services),
            "firewall_active": firewall_active,
            "risk_level": risk_level,
        })

        return report

    # ===============================================================
    # 4. FILE PERMISSION AUDIT
    # ===============================================================

    def audit_permissions(self) -> list[PermissionAlert]:
        """Check file permissions on sensitive files.

        Flags: .env files, key files, log files with world-readable perms,
        mesh inbox files.
        """
        alerts: list[PermissionAlert] = []

        # Sensitive files that should be 600 (owner read/write only)
        sensitive_patterns = [
            (".env", "600", "Contains API keys and secrets"),
            (".env.local", "600", "Contains local secrets"),
            (".env.production", "600", "Contains production secrets"),
            ("oracle_key.json", "600", "Known leaked credential file"),
            ("credentials.json", "600", "Contains service credentials"),
        ]

        for filename, recommended, reason in sensitive_patterns:
            file_path = self._project_dir / filename
            if file_path.exists():
                try:
                    mode = file_path.stat().st_mode
                    perms = oct(mode & 0o777)[2:]
                    if perms != recommended:
                        alerts.append(PermissionAlert(
                            file_path=str(file_path),
                            current_permissions=perms,
                            recommended=recommended,
                            reason=reason,
                        ))
                except OSError:
                    pass

        # Check logs directory for world-readable files with potential secrets
        logs_dir = self._project_dir / "logs"
        if logs_dir.exists():
            for root, _dirs, files in os.walk(logs_dir):
                for filename in files:
                    file_path = Path(root) / filename
                    try:
                        mode = file_path.stat().st_mode
                        perms = oct(mode & 0o777)[2:]
                        # Check if world-readable (others can read)
                        if mode & stat.S_IROTH:
                            alerts.append(PermissionAlert(
                                file_path=str(file_path),
                                current_permissions=perms,
                                recommended="640",
                                reason="Log file is world-readable; may contain sensitive data",
                            ))
                    except OSError:
                        pass

        # Check mesh inbox permissions
        inbox_dir = self._project_dir / "logs" / "mesh" / "inbox"
        if inbox_dir.exists():
            try:
                mode = inbox_dir.stat().st_mode
                perms = oct(mode & 0o777)[2:]
                if mode & stat.S_IWOTH:
                    alerts.append(PermissionAlert(
                        file_path=str(inbox_dir),
                        current_permissions=perms,
                        recommended="750",
                        reason="Mesh inbox directory is world-writable; any process can inject messages",
                    ))
            except OSError:
                pass

        self._log_event("permission_audit", {
            "issues_found": len(alerts),
        })

        return alerts

    # ===============================================================
    # 5. DEPENDENCY VULNERABILITY SCAN
    # ===============================================================

    def scan_dependencies(self) -> list[DependencyAlert]:
        """Scan requirements.txt for dependency issues.

        Checks: unpinned versions, known vulnerable versions, typosquatting.
        No network required.
        """
        alerts: list[DependencyAlert] = []

        req_file = self._project_dir / "requirements.txt"
        if not req_file.exists():
            return alerts

        try:
            content = req_file.read_text()
        except OSError:
            return alerts

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse package name and version spec
            # Handle: package, package>=1.0, package==1.0, package[extras]>=1.0
            match = re.match(
                r'^([a-zA-Z0-9_-]+)(?:\[[^\]]*\])?\s*([><=!~]+\s*[\d.]+)?',
                line
            )
            if not match:
                continue

            package = match.group(1).lower().replace("-", "_")
            version_spec = match.group(2) or ""

            # Check for unpinned dependencies
            if not version_spec:
                alerts.append(DependencyAlert(
                    package=match.group(1),
                    version="unpinned",
                    issue="unpinned",
                    severity="MEDIUM",
                ))
            elif ">=" in version_spec and "==" not in version_spec:
                # Using >= instead of == means any newer version is accepted
                version = version_spec.replace(">=", "").strip()
                alerts.append(DependencyAlert(
                    package=match.group(1),
                    version=f">={version}",
                    issue="unpinned",
                    severity="LOW",
                ))

            # Check for known vulnerable versions
            pkg_key = package.replace("_", "")
            for vuln_pkg, vulns in _KNOWN_VULNS.items():
                if pkg_key == vuln_pkg.replace("-", "").replace("_", ""):
                    for vuln_ver, cve_desc in vulns:
                        if version_spec:
                            ver = version_spec.replace(">=", "").replace("==", "").replace("~=", "").strip()
                            # Basic version comparison
                            if self._version_lte(ver, vuln_ver):
                                alerts.append(DependencyAlert(
                                    package=match.group(1),
                                    version=ver,
                                    issue=f"known_vuln: {cve_desc}",
                                    severity="HIGH",
                                ))

            # Check for typosquatting
            if package not in {p.lower().replace("-", "_") for p in _POPULAR_PACKAGES}:
                for popular in _POPULAR_PACKAGES:
                    popular_norm = popular.lower().replace("-", "_")
                    if self._is_typosquat(package, popular_norm):
                        alerts.append(DependencyAlert(
                            package=match.group(1),
                            version=version_spec or "any",
                            issue=f"typosquat_risk: similar to '{popular}'",
                            severity="HIGH",
                        ))
                        break

        self._log_event("dependency_scan", {
            "issues_found": len(alerts),
        })

        return alerts

    @staticmethod
    def _version_lte(v1: str, v2: str) -> bool:
        """Compare two version strings. Returns True if v1 <= v2."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            # Pad shorter list
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            return parts1 <= parts2
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _is_typosquat(name: str, popular: str) -> bool:
        """Check if a package name looks like a typosquat of a popular package.

        Uses simple edit distance (Levenshtein distance <= 1) and transposition detection.
        """
        if name == popular:
            return False
        if len(name) < 3 or len(popular) < 3:
            return False

        # Same length: check substitution (1 char differs) or transposition (adjacent swap)
        if len(name) == len(popular):
            diffs = sum(1 for a, b in zip(name, popular) if a != b)
            if diffs == 1:
                return True
            # Check adjacent transposition (Damerau)
            if diffs == 2:
                for i in range(len(name) - 1):
                    if (name[i] == popular[i + 1] and name[i + 1] == popular[i]
                            and name[:i] == popular[:i]
                            and name[i + 2:] == popular[i + 2:]):
                        return True
            return False

        # Check edit distance = 1 (insertion/deletion)
        if abs(len(name) - len(popular)) != 1:
            return False

        longer, shorter = (name, popular) if len(name) > len(popular) else (popular, name)
        j = 0
        skips = 0
        for i in range(len(longer)):
            if j < len(shorter) and longer[i] == shorter[j]:
                j += 1
            else:
                skips += 1
        return skips <= 1

    # ===============================================================
    # 6. MESH COMMUNICATION SECURITY
    # ===============================================================

    def audit_mesh_security(self) -> MeshSecurityReport:
        """Audit the security of mesh communication infrastructure.

        Checks: plaintext storage, node authentication, file permissions,
        unbounded log growth, message cleanup.
        """
        permission_issues: list[str] = []
        unbounded_logs: list[str] = []
        recommendations: list[str] = []

        mesh_dir = self._project_dir / "logs" / "mesh"

        # 1. Plaintext messages — mesh stores messages as plain JSON
        plaintext_messages = True
        if mesh_dir.exists():
            inbox_dir = mesh_dir / "inbox"
            if inbox_dir.exists():
                for node_dir in inbox_dir.iterdir():
                    if node_dir.is_dir():
                        for json_file in node_dir.glob("*.json"):
                            try:
                                data = json.loads(json_file.read_text())
                                if "content" in data and isinstance(data["content"], str):
                                    plaintext_messages = True
                                    break
                            except (OSError, json.JSONDecodeError):
                                pass
                        break
            recommendations.append("Encrypt mesh messages at rest (AES-256-GCM)")
        else:
            plaintext_messages = False  # no mesh dir = no messages

        # 2. Node authentication — check if there's any auth mechanism
        node_authentication = False
        nodes_file = mesh_dir / "nodes.json" if mesh_dir.exists() else None
        if nodes_file and nodes_file.exists():
            try:
                nodes_data = json.loads(nodes_file.read_text())
                # Check if any node has auth tokens/keys
                if isinstance(nodes_data, dict):
                    for _nid, ndata in nodes_data.items():
                        if isinstance(ndata, dict) and any(
                            k in ndata for k in ("auth_token", "api_key", "secret", "certificate")
                        ):
                            node_authentication = True
                            break
            except (OSError, json.JSONDecodeError):
                pass
        if not node_authentication:
            recommendations.append("Implement node authentication (shared secrets or certificates)")

        # 3. Permission issues on mesh files
        if mesh_dir.exists():
            inbox_dir = mesh_dir / "inbox"
            if inbox_dir.exists():
                try:
                    mode = inbox_dir.stat().st_mode
                    if mode & stat.S_IWOTH:
                        permission_issues.append(
                            f"inbox/ is world-writable ({oct(mode & 0o777)[2:]})"
                        )
                except OSError:
                    pass

                for node_dir in inbox_dir.iterdir():
                    if node_dir.is_dir():
                        try:
                            mode = node_dir.stat().st_mode
                            if mode & stat.S_IWOTH:
                                permission_issues.append(
                                    f"inbox/{node_dir.name}/ is world-writable ({oct(mode & 0o777)[2:]})"
                                )
                        except OSError:
                            pass

        if permission_issues:
            recommendations.append("Set inbox directories to 750 (owner + group only)")

        # 4. Unbounded log growth
        log_size_threshold = 10 * 1024 * 1024  # 10MB
        if mesh_dir.exists():
            for log_file in mesh_dir.glob("*.jsonl"):
                try:
                    size = log_file.stat().st_size
                    if size > log_size_threshold:
                        unbounded_logs.append(
                            f"{log_file.name}: {size / (1024*1024):.1f}MB"
                        )
                except OSError:
                    pass

            # Check messages.jsonl specifically
            messages_file = mesh_dir / "messages.jsonl"
            if messages_file.exists():
                try:
                    size = messages_file.stat().st_size
                    if size > 1024 * 1024:  # 1MB for messages
                        unbounded_logs.append(
                            f"messages.jsonl: {size / (1024*1024):.1f}MB (growing unbounded)"
                        )
                except OSError:
                    pass

        if unbounded_logs:
            recommendations.append("Implement log rotation for JSONL files (max 10MB, keep 5 rotations)")

        # 5. Old message cleanup
        if mesh_dir.exists():
            inbox_dir = mesh_dir / "inbox"
            if inbox_dir.exists():
                old_message_count = 0
                cutoff = time.time() - 7 * 24 * 3600  # 7 days
                for node_dir in inbox_dir.iterdir():
                    if node_dir.is_dir():
                        for json_file in node_dir.glob("*.json"):
                            try:
                                if json_file.stat().st_mtime < cutoff:
                                    old_message_count += 1
                            except OSError:
                                pass
                if old_message_count > 0:
                    recommendations.append(
                        f"Clean up {old_message_count} messages older than 7 days"
                    )

        report = MeshSecurityReport(
            plaintext_messages=plaintext_messages,
            node_authentication=node_authentication,
            permission_issues=permission_issues,
            unbounded_logs=unbounded_logs,
            recommendations=recommendations,
        )

        self._log_event("mesh_security_audit", {
            "plaintext_messages": plaintext_messages,
            "node_authentication": node_authentication,
            "permission_issues_count": len(permission_issues),
            "unbounded_logs_count": len(unbounded_logs),
        })

        return report

    # ===============================================================
    # FULL AUDIT
    # ===============================================================

    def full_audit(self) -> OpsecReport:
        """Run all security checks and produce a comprehensive report."""
        now = time.time()

        leaks = self.scan_for_leaks()
        git_leaks = self.audit_git_history()
        network = self.scan_network_exposure()
        permissions = self.audit_permissions()
        dependencies = self.scan_dependencies()
        mesh = self.audit_mesh_security()

        all_leaks = leaks + git_leaks
        critical_actions: list[str] = []

        # Collect critical actions
        critical_leaks = [a for a in all_leaks if a.severity == "CRITICAL"]
        for leak in critical_leaks[:5]:
            critical_actions.append(
                f"[LEAK] {leak.category}: {leak.pattern_matched} in {leak.file_path}"
            )

        if network.exposed_services:
            for svc in network.exposed_services:
                critical_actions.append(f"[NETWORK] Exposed: {svc}")

        for perm in permissions:
            if perm.current_permissions != perm.recommended:
                critical_actions.append(
                    f"[PERMS] {perm.file_path}: {perm.current_permissions} -> {perm.recommended}"
                )

        high_dep_alerts = [d for d in dependencies if d.severity in ("CRITICAL", "HIGH")]
        for dep in high_dep_alerts[:3]:
            critical_actions.append(f"[DEP] {dep.package}: {dep.issue}")

        if mesh.plaintext_messages:
            critical_actions.append("[MESH] Messages stored in plaintext — encrypt at rest")
        if not mesh.node_authentication:
            critical_actions.append("[MESH] No node authentication — implement auth tokens")

        # Calculate overall score (10 = fully hardened)
        score = 10.0
        # Deductions
        score -= min(3.0, len(critical_leaks) * 0.5)  # max -3 for leaks
        score -= min(2.0, {"LOW": 0, "MEDIUM": 0.5, "HIGH": 1.5, "CRITICAL": 2.0}.get(network.risk_level, 0))
        score -= min(1.5, len(permissions) * 0.3)
        score -= min(1.5, len(high_dep_alerts) * 0.3)
        mesh_issues = len(mesh.permission_issues) + len(mesh.unbounded_logs)
        mesh_issues += (1 if mesh.plaintext_messages else 0)
        mesh_issues += (1 if not mesh.node_authentication else 0)
        score -= min(2.0, mesh_issues * 0.4)
        score = max(0.0, round(score, 1))

        report = OpsecReport(
            timestamp=now,
            leaks_found=len(all_leaks),
            network_risk=network.risk_level,
            permission_issues=len(permissions),
            dependency_issues=len(dependencies),
            mesh_security_issues=mesh_issues,
            overall_score=score,
            critical_actions=critical_actions,
        )

        self._save_report(report)
        self._log_event("full_audit", asdict(report))

        return report

    # ===============================================================
    # HARDEN — Apply recommended fixes
    # ===============================================================

    def harden(self) -> list[str]:
        """Apply recommended security fixes.

        Applies: chmod on sensitive files, .gitignore updates.
        Returns list of actions taken.
        """
        actions: list[str] = []

        # Fix .env permissions
        sensitive_files = [".env", ".env.local", ".env.production",
                          "oracle_key.json", "credentials.json"]
        for filename in sensitive_files:
            file_path = self._project_dir / filename
            if file_path.exists():
                try:
                    current_mode = file_path.stat().st_mode & 0o777
                    if current_mode != 0o600:
                        os.chmod(file_path, 0o600)
                        actions.append(
                            f"chmod 600 {file_path} (was {oct(current_mode)[2:]})"
                        )
                except OSError as e:
                    actions.append(f"FAILED: chmod {file_path}: {e}")

        # Ensure .env is in .gitignore
        gitignore_path = self._project_dir / ".gitignore"
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text()
                additions = []
                for pattern in [".env", "oracle_key.json", "credentials.json",
                                "*.pem", "id_rsa", "id_ed25519"]:
                    if pattern not in content:
                        additions.append(pattern)
                if additions:
                    with open(gitignore_path, "a") as f:
                        f.write("\n# OpsecShield hardening\n")
                        for pattern in additions:
                            f.write(f"{pattern}\n")
                    actions.append(
                        f"Added to .gitignore: {', '.join(additions)}"
                    )
            except OSError as e:
                actions.append(f"FAILED: update .gitignore: {e}")

        # Fix mesh inbox permissions
        inbox_dir = self._project_dir / "logs" / "mesh" / "inbox"
        if inbox_dir.exists():
            try:
                current_mode = inbox_dir.stat().st_mode & 0o777
                if current_mode & 0o002:  # world-writable
                    os.chmod(inbox_dir, 0o750)
                    actions.append(
                        f"chmod 750 {inbox_dir} (was {oct(current_mode)[2:]})"
                    )
            except OSError as e:
                actions.append(f"FAILED: chmod {inbox_dir}: {e}")

        self._log_event("harden", {"actions": actions})
        return actions


# ===================================================================
# CONVENIENCE
# ===================================================================

def quick_scan(project_dir: str = ".") -> OpsecReport:
    """One-shot full audit."""
    return OpsecShield(project_dir=project_dir).full_audit()


# ===================================================================
# CLI
# ===================================================================

if __name__ == "__main__":
    import sys

    shield = OpsecShield(project_dir=BASE_DIR)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "leaks":
            alerts = shield.scan_for_leaks()
            print(f"=== OPSEC SHIELD — LEAK SCAN ===")
            print(f"Alerts: {len(alerts)}")
            for a in alerts[:20]:
                print(f"  [{a.severity}] {a.category}: {a.pattern_matched}")
                print(f"    File: {a.file_path}:{a.line_number}")
                print(f"    Preview: {a.preview}")
        elif cmd == "git":
            alerts = shield.audit_git_history()
            print(f"=== OPSEC SHIELD — GIT AUDIT ===")
            print(f"Alerts: {len(alerts)}")
            for a in alerts[:20]:
                print(f"  [{a.severity}] {a.pattern_matched}")
        elif cmd == "network":
            report = shield.scan_network_exposure()
            print(f"=== OPSEC SHIELD — NETWORK SCAN ===")
            print(f"Open ports: {len(report.open_ports)}")
            for p in report.open_ports:
                print(f"  {p['port']:5d} {p['service']:20s} binding={p['binding']} exposed={p['exposed']}")
            print(f"Firewall: {'ACTIVE' if report.firewall_active else 'INACTIVE'}")
            print(f"Risk: {report.risk_level}")
        elif cmd == "perms":
            alerts = shield.audit_permissions()
            print(f"=== OPSEC SHIELD — PERMISSION AUDIT ===")
            print(f"Issues: {len(alerts)}")
            for a in alerts:
                print(f"  {a.file_path}: {a.current_permissions} -> {a.recommended} ({a.reason})")
        elif cmd == "deps":
            alerts = shield.scan_dependencies()
            print(f"=== OPSEC SHIELD — DEPENDENCY SCAN ===")
            print(f"Issues: {len(alerts)}")
            for a in alerts:
                print(f"  [{a.severity}] {a.package} ({a.version}): {a.issue}")
        elif cmd == "mesh":
            report = shield.audit_mesh_security()
            print(f"=== OPSEC SHIELD — MESH SECURITY ===")
            print(f"Plaintext messages: {report.plaintext_messages}")
            print(f"Node authentication: {report.node_authentication}")
            print(f"Permission issues: {len(report.permission_issues)}")
            print(f"Unbounded logs: {len(report.unbounded_logs)}")
            print(f"Recommendations: {len(report.recommendations)}")
            for r in report.recommendations:
                print(f"  - {r}")
        elif cmd == "harden":
            actions = shield.harden()
            print(f"=== OPSEC SHIELD — HARDENING ===")
            print(f"Actions taken: {len(actions)}")
            for a in actions:
                print(f"  {a}")
        elif cmd == "full":
            report = shield.full_audit()
            print(f"=== OPSEC SHIELD — FULL AUDIT ===")
            print(f"Score: {report.overall_score}/10.0")
            print(f"Leaks: {report.leaks_found}")
            print(f"Network risk: {report.network_risk}")
            print(f"Permission issues: {report.permission_issues}")
            print(f"Dependency issues: {report.dependency_issues}")
            print(f"Mesh issues: {report.mesh_security_issues}")
            print(f"\nCritical actions:")
            for a in report.critical_actions:
                print(f"  {a}")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python3 core/opsec_shield.py [leaks|git|network|perms|deps|mesh|harden|full]")
    else:
        print("Usage: python3 core/opsec_shield.py [leaks|git|network|perms|deps|mesh|harden|full]")
        print("\nRunning quick full audit...")
        report = shield.full_audit()
        print(f"Score: {report.overall_score}/10.0 | Leaks: {report.leaks_found} | "
              f"Network: {report.network_risk} | Actions: {len(report.critical_actions)}")
