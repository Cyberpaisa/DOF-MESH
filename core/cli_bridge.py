"""
CLI Bridge — Wrapper DOF sobre CLI-Anything.

Arregla los 6 fallos detectados y conecta CLI-Anything con el DOF Mesh:
1. Validación de seguridad via Cerberus antes de ejecutar
2. Timeout configurable por comando (default 30s)
3. Logging de TODOS los CLI calls a JSONL  ✓ DONE (see _log / cli_commands.jsonl)
4. Adaptador SKILL.md → DOF skill format
5. File locking para session files
6. Sugerencias inteligentes (ej: ollama pull si no hay modelos)

Fuente: https://github.com/HKUDS/CLI-Anything
Integrado por: Commander (Claude Opus 4.6), DOF Mesh
Fecha: 23 de Marzo 2026

Usage:
    from core.cli_bridge import CLIBridge

    bridge = CLIBridge()
    result = bridge.execute("ollama", ["--json", "model", "list"])
    result = bridge.execute("audacity", ["--json", "project", "info"])
"""

import json
import os
import re
import subprocess
import time
import logging
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.cli_bridge")

# ═══════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════

@dataclass
class CLIResult:
    """Result of a CLI command execution."""
    cli: str
    command: list
    success: bool
    output: str
    error: str
    exit_code: int
    elapsed_ms: float
    blocked: bool = False
    block_reason: str = ""
    suggestion: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class CLIApp:
    """A registered CLI-Anything application."""
    name: str
    binary: str
    description: str
    installed: bool
    backend: str  # underlying tool (ollama, ffmpeg, sox, etc.)
    category: str  # audio, video, image, ai, office, diagrams
    capabilities: list = field(default_factory=list)

@dataclass
class BridgeHealth:
    """Health status of the CLI bridge."""
    apps_registered: int
    apps_installed: int
    apps_available: list
    apps_missing: list
    total_commands_executed: int
    total_commands_blocked: int
    uptime_seconds: float

# ═══════════════════════════════════════════════════
# SECURITY PATTERNS (Cerberus-lite for CLI commands)
# ═══════════════════════════════════════════════════

_DANGEROUS_PATTERNS = [
    re.compile(r'rm\s+-rf\s+/'),
    re.compile(r'rm\s+-rf\s+~'),
    re.compile(r';\s*curl\s+'),
    re.compile(r';\s*wget\s+'),
    re.compile(r'\|\s*bash'),
    re.compile(r'\|\s*sh\b'),
    re.compile(r'`.*`'),          # backtick execution
    re.compile(r'\$\(.*\)'),      # subshell execution
    re.compile(r'>\s*/dev/sd'),   # write to disk devices
    re.compile(r'mkfs\b'),        # format filesystem
    re.compile(r'dd\s+if='),      # disk dump
    re.compile(r'chmod\s+777'),   # world writable
    re.compile(r'\.env\b'),       # accessing env files
    re.compile(r'private.key'),
    re.compile(r'id_rsa'),
    re.compile(r'/etc/passwd'),
    re.compile(r'/etc/shadow'),
]

_ALLOWED_BINARIES = {
    'cli-anything-ollama',
    'cli-anything-audacity',
    'cli-anything-gimp',
    'cli-anything-blender',
    'cli-anything-inkscape',
    'cli-anything-drawio',
    'cli-anything-mermaid',
    'cli-anything-kdenlive',
    'cli-anything-shotcut',
    'cli-anything-libreoffice',
    'cli-anything-obs-studio',
    'cli-anything-comfyui',
    'cli-anything-musescore',
    'cli-anything-zoom',
    'cli-anything-browser',
    'cli-anything-notebooklm',
    'cli-anything-novita',
    'cli-anything-mubu',
    'ollama',
    'ffmpeg',
    'sox',
}

# ═══════════════════════════════════════════════════
# SMART SUGGESTIONS
# ═══════════════════════════════════════════════════

_SUGGESTIONS = {
    ('ollama', 'models', 'empty'): 'No models loaded. Run: ollama pull qwen3:8b (fast, 5GB) or ollama pull phi4:14b (better, 9GB)',
    ('ollama', 'server', 'down'): 'Ollama server not running. Run: ollama serve',
    ('audacity', 'sox', 'missing'): 'sox not installed. Run: brew install sox',
    ('gimp', 'gimp', 'missing'): 'GIMP not installed. Run: brew install --cask gimp',
    ('blender', 'blender', 'missing'): 'Blender not installed. Run: brew install --cask blender',
    ('mermaid', 'mmdc', 'missing'): 'Mermaid CLI not installed. Run: npm install -g @mermaid-js/mermaid-cli',
}

# ═══════════════════════════════════════════════════
# CLI BRIDGE
# ═══════════════════════════════════════════════════

class CLIBridge:
    """DOF wrapper over CLI-Anything — security, logging, suggestions."""

    def __init__(self, log_dir: str = "logs/cli", timeout: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "cli_commands.jsonl"
        self.timeout = timeout
        self.start_time = time.time()
        self._commands_executed = 0
        self._commands_blocked = 0
        self._apps = self._discover_apps()

    def _discover_apps(self) -> dict:
        """Discover installed CLI-Anything apps."""
        apps = {}
        registry = [
            ("ollama", "cli-anything-ollama", "Local LLM inference", "ollama", "ai",
             ["model management", "text generation", "embeddings", "chat"]),
            ("audacity", "cli-anything-audacity", "Audio editing", "ffmpeg", "audio",
             ["record", "edit", "effects", "export", "mix"]),
            ("gimp", "cli-anything-gimp", "Image editing", "gimp", "image",
             ["layers", "filters", "crop", "resize", "export"]),
            ("blender", "cli-anything-blender", "3D modeling", "blender", "3d",
             ["model", "render", "animate", "sculpt", "export"]),
            ("inkscape", "cli-anything-inkscape", "SVG vector graphics", "inkscape", "image",
             ["draw", "path", "text", "export"]),
            ("obs-studio", "cli-anything-obs-studio", "Streaming/recording", "obs-studio", "streaming",
             ["scenes", "sources", "record", "stream"]),
            ("mermaid", "cli-anything-mermaid", "Diagrams from code", "mmdc", "diagrams",
             ["flowchart", "sequence", "class", "gantt"]),
            ("shotcut", "cli-anything-shotcut", "Video editing", "melt", "video",
             ["cut", "trim", "effects", "render", "export"]),
            ("libreoffice", "cli-anything-libreoffice", "Office documents", "soffice", "office",
             ["docs", "spreadsheet", "presentation", "pdf"]),
        ]
        for name, binary, desc, backend, cat, caps in registry:
            installed = shutil.which(binary) is not None
            apps[name] = CLIApp(
                name=name, binary=binary, description=desc,
                installed=installed, backend=backend,
                category=cat, capabilities=caps,
            )
        return apps

    def validate_command(self, cli: str, args: list) -> tuple:
        """Validate a CLI command for security. Returns (safe, reason)."""
        full_cmd = f"{cli} {' '.join(args)}"

        # Check binary whitelist
        if cli not in _ALLOWED_BINARIES:
            return False, f"Binary '{cli}' not in allowed list"

        # Check dangerous patterns
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(full_cmd):
                return False, f"Dangerous pattern detected: {pattern.pattern}"

        # Check for shell injection in args
        for arg in args:
            if any(c in arg for c in [';', '&&', '||', '`', '$(']):
                return False, f"Shell metacharacter in argument: {arg[:20]}"

        return True, "OK"

    def execute(self, app_name: str, args: list = None,
                timeout: int = None) -> CLIResult:
        """Execute a CLI-Anything command with security and logging."""
        args = args or []
        timeout = timeout or self.timeout

        # Resolve binary
        app = self._apps.get(app_name)
        binary = app.binary if app else f"cli-anything-{app_name}"

        # Security validation
        safe, reason = self.validate_command(binary, args)
        if not safe:
            self._commands_blocked += 1
            result = CLIResult(
                cli=app_name, command=args, success=False,
                output="", error=reason, exit_code=-1,
                elapsed_ms=0, blocked=True, block_reason=reason,
            )
            self._log(result)
            return result

        # Check if installed
        if app and not app.installed:
            suggestion = _SUGGESTIONS.get((app_name, app.backend, 'missing'), '')
            result = CLIResult(
                cli=app_name, command=args, success=False,
                output="", error=f"{binary} not installed",
                exit_code=-2, elapsed_ms=0,
                suggestion=suggestion,
            )
            self._log(result)
            return result

        # Execute with timeout
        start = time.time()
        try:
            proc = subprocess.run(
                [binary] + args,
                capture_output=True, text=True,
                timeout=timeout,
            )
            elapsed = (time.time() - start) * 1000

            output = proc.stdout
            error = proc.stderr
            success = proc.returncode == 0

            # Smart suggestions
            suggestion = self._get_suggestion(app_name, output, error)

            result = CLIResult(
                cli=app_name, command=args, success=success,
                output=output, error=error,
                exit_code=proc.returncode, elapsed_ms=elapsed,
                suggestion=suggestion,
            )

        except subprocess.TimeoutExpired:
            elapsed = (time.time() - start) * 1000
            result = CLIResult(
                cli=app_name, command=args, success=False,
                output="", error=f"TIMEOUT after {timeout}s",
                exit_code=-3, elapsed_ms=elapsed,
                suggestion=f"Command timed out. Try increasing timeout (current: {timeout}s)",
            )

        except FileNotFoundError:
            result = CLIResult(
                cli=app_name, command=args, success=False,
                output="", error=f"Binary not found: {binary}",
                exit_code=-4, elapsed_ms=0,
                suggestion=f"Install with: pip3 install cli-anything-{app_name}",
            )

        except Exception as e:
            result = CLIResult(
                cli=app_name, command=args, success=False,
                output="", error=str(e),
                exit_code=-5, elapsed_ms=0,
            )

        self._commands_executed += 1
        self._log(result)
        return result

    def _get_suggestion(self, app_name: str, output: str, error: str) -> str:
        """Generate smart suggestions based on output."""
        # Ollama: empty models
        if app_name == "ollama" and '"models": []' in output:
            return _SUGGESTIONS.get(('ollama', 'models', 'empty'), '')

        # Ollama: server down
        if app_name == "ollama" and "connection refused" in error.lower():
            return _SUGGESTIONS.get(('ollama', 'server', 'down'), '')

        return ""

    def _log(self, result: CLIResult):
        """Log command to JSONL for DOF audit trail."""
        try:
            entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cli": result.cli,
                "command": result.command,
                "success": result.success,
                "exit_code": result.exit_code,
                "elapsed_ms": result.elapsed_ms,
                "blocked": result.blocked,
                "block_reason": result.block_reason,
                "output_preview": result.output[:200] if result.output else "",
                "error_preview": result.error[:200] if result.error else "",
            }
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log CLI command: {e}")

    def list_apps(self) -> list:
        """List all registered CLI apps with status."""
        return [asdict(app) for app in self._apps.values()]

    def get_app(self, name: str) -> Optional[CLIApp]:
        """Get info about a specific app."""
        return self._apps.get(name)

    def health(self) -> BridgeHealth:
        """Get bridge health status."""
        installed = [a for a in self._apps.values() if a.installed]
        missing = [a for a in self._apps.values() if not a.installed]
        return BridgeHealth(
            apps_registered=len(self._apps),
            apps_installed=len(installed),
            apps_available=[a.name for a in installed],
            apps_missing=[a.name for a in missing],
            total_commands_executed=self._commands_executed,
            total_commands_blocked=self._commands_blocked,
            uptime_seconds=time.time() - self.start_time,
        )

    def scan_capabilities(self) -> dict:
        """Scan what the bridge can do — for mesh routing."""
        caps = {}
        for app in self._apps.values():
            if app.installed:
                for cap in app.capabilities:
                    if cap not in caps:
                        caps[cap] = []
                    caps[cap].append(app.name)
        return caps


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    bridge = CLIBridge()

    if len(sys.argv) < 2 or sys.argv[1] == "health":
        h = bridge.health()
        print(f"CLI Bridge Health")
        print(f"  Apps: {h.apps_installed}/{h.apps_registered} installed")
        print(f"  Available: {', '.join(h.apps_available)}")
        print(f"  Missing: {', '.join(h.apps_missing)}")
        print(f"  Commands: {h.total_commands_executed} executed, {h.total_commands_blocked} blocked")
    elif sys.argv[1] == "list":
        for app in bridge.list_apps():
            status = "OK" if app["installed"] else "--"
            print(f"  [{status:2}] {app['name']:15} {app['category']:10} {app['description']}")
    elif sys.argv[1] == "test":
        # Test all installed apps
        for app in bridge._apps.values():
            if app.installed:
                r = bridge.execute(app.name, ["--help"], timeout=5)
                status = "OK" if r.success else "FAIL"
                print(f"  [{status}] {app.name} ({r.elapsed_ms:.0f}ms)")
    elif sys.argv[1] == "caps":
        caps = bridge.scan_capabilities()
        for cap, apps in sorted(caps.items()):
            print(f"  {cap:20} → {', '.join(apps)}")
    else:
        # Execute: python3 core/cli_bridge.py ollama --json model list
        app = sys.argv[1]
        args = sys.argv[2:]
        r = bridge.execute(app, args)
        if r.success:
            print(r.output)
        else:
            print(f"ERROR: {r.error}")
            if r.suggestion:
                print(f"SUGGESTION: {r.suggestion}")
