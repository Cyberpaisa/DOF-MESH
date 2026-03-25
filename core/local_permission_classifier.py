"""
LocalPermissionClassifier — DOF's local auto-mode.

Classifies agent actions before execution:
  SAFE  → auto-approve, no interruption
  WARN  → log warning, proceed with caution flag
  BLOCK → reject, log reason, agent must find alternative

100% local, zero API tokens, zero external calls.
Inspired by Claude Code auto mode — implemented independently.
"""
import re
import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path

logger = logging.getLogger("core.local_permission_classifier")


class ActionClass(Enum):
    SAFE = "SAFE"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class ClassificationResult:
    action: str
    action_class: ActionClass
    reason: str
    confidence: float  # 0.0–1.0
    alternatives: list[str] = field(default_factory=list)

    def is_allowed(self) -> bool:
        """Returns True if action is SAFE or WARN (not blocked)."""
        return self.action_class in (ActionClass.SAFE, ActionClass.WARN)


class LocalPermissionClassifier:
    """
    Deterministic, local-only permission classifier.
    Singleton — shared instance across the process.
    """

    _instance: Optional["LocalPermissionClassifier"] = None

    # Always blocked — high-confidence destructive or exfiltrating patterns
    BLOCK_PATTERNS = [
        # Mass file deletion
        (r"rm\s+-rf?\s+/", "Mass filesystem deletion from root"),
        (r"rm\s+-rf?\s+\.", "Mass deletion of current directory"),
        (r"git\s+clean\s+-fd", "Destructive git clean"),
        (r"git\s+reset\s+--hard\s+HEAD", "Hard reset losing uncommitted work"),
        # Secret exfiltration
        (r"(api_key|secret|password|token|private_key)\s*=\s*['\"][^'\"]{8,}", "Secret value in output"),
        (r"curl.*\|\s*bash", "Remote code execution via curl pipe"),
        (r"wget.*\|\s*sh", "Remote code execution via wget pipe"),
        # Force push to main
        (r"git\s+push.*--force.*main", "Force push to main branch"),
        (r"git\s+push.*-f.*main", "Force push to main branch"),
        # Drop database
        (r"DROP\s+TABLE", "Database table destruction"),
        (r"DROP\s+DATABASE", "Database destruction"),
        # Kill system processes
        (r"kill\s+-9\s+1\b", "Kill init process"),
        (r"killall\s+-9", "Kill all processes"),
    ]

    # Proceed with caution — log warning, set caution flag
    WARN_PATTERNS = [
        (r"git\s+push", "Pushes code to remote — verify branch"),
        (r"git\s+force", "Force git operation"),
        (r"chmod\s+777", "World-writable permissions"),
        (r"sudo\s+", "Elevated privileges"),
        (r"pip\s+install", "Package installation — check supply chain"),
        (r"npm\s+install", "Package installation — check supply chain"),
        (r"curl\s+", "External network request"),
        (r"wget\s+", "External network request"),
        (r"os\.remove|os\.unlink", "File deletion"),
        (r"shutil\.rmtree", "Directory tree deletion"),
    ]

    # Always auto-approved — read-only or known-safe operations
    SAFE_PATTERNS = [
        r"python3\s+-m\s+unittest",  # Running tests
        r"python3\s+-m\s+dof",       # DOF CLI
        r"git\s+status",             # Read-only git
        r"git\s+log",                # Read-only git
        r"git\s+diff",               # Read-only git
        r"git\s+add\s+",             # Staging (not destructive)
        r"git\s+commit",             # Committing (local only)
        r"git\s+tag",                # Tagging (local only)
        r"ls\s+",                    # List files
        r"cat\s+",                   # Read file
        r"grep\s+",                  # Search
    ]

    # BLOCK pattern → suggested safer alternatives
    BLOCK_ALTERNATIVES = {
        r"rm\s+-rf": "Use os.remove() for specific files, or git clean with --dry-run first",
        r"curl.*\|\s*bash": "Download file first, inspect, then execute manually",
        r"wget.*\|\s*sh": "Download file first, inspect, then execute manually",
        r"git\s+push.*--force|git\s+push.*-f": "Create a new branch or use git push without --force",
        r"DROP\s+TABLE|DROP\s+DATABASE": "Use soft delete (is_deleted flag) or backup before dropping",
        r"kill\s+-9\s+1|killall\s+-9": "Use SIGTERM first; only escalate after graceful shutdown fails",
        r"git\s+reset\s+--hard": "Use git stash to save work before resetting",
        r"git\s+clean\s+-fd": "Run git clean --dry-run first to preview what would be deleted",
        r"(api_key|secret|password|token|private_key)\s*=\s*['\"]": "Store secrets in .env or a vault; never inline them in commands",
    }

    def __new__(cls) -> "LocalPermissionClassifier":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._blocked_count = 0
        self._warned_count = 0
        self._safe_count = 0
        self._initialized = True
        logger.debug("LocalPermissionClassifier initialised (singleton)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, action: str, context: dict = None) -> ClassificationResult:
        """
        Classify a raw action string (shell command, code snippet, description).

        Order of evaluation:
          1. SAFE_PATTERNS  → SAFE  (confidence 0.95)
          2. BLOCK_PATTERNS → BLOCK (confidence 0.99)
          3. WARN_PATTERNS  → WARN  (confidence 0.80)
          4. Default        → SAFE  (confidence 0.70)
        """
        if context is None:
            context = {}

        # 1. SAFE fast-path
        for pattern in self.SAFE_PATTERNS:
            if re.search(pattern, action, re.IGNORECASE):
                self._safe_count += 1
                logger.debug("SAFE match pattern=%r action=%r", pattern, action[:80])
                return ClassificationResult(
                    action=action,
                    action_class=ActionClass.SAFE,
                    reason=f"Matches known-safe pattern: {pattern}",
                    confidence=0.95,
                )

        # 2. BLOCK rules — highest priority after safe fast-path
        for pattern, description in self.BLOCK_PATTERNS:
            if re.search(pattern, action, re.IGNORECASE):
                alternatives = self._get_alternatives(action)
                self._blocked_count += 1
                logger.warning("BLOCK pattern=%r action=%r reason=%r", pattern, action[:80], description)
                return ClassificationResult(
                    action=action,
                    action_class=ActionClass.BLOCK,
                    reason=description,
                    confidence=0.99,
                    alternatives=alternatives,
                )

        # 3. WARN — proceed but flag
        for pattern, description in self.WARN_PATTERNS:
            if re.search(pattern, action, re.IGNORECASE):
                self._warned_count += 1
                logger.warning("WARN pattern=%r action=%r reason=%r", pattern, action[:80], description)
                return ClassificationResult(
                    action=action,
                    action_class=ActionClass.WARN,
                    reason=description,
                    confidence=0.80,
                )

        # 4. Default — unknown but not suspicious
        self._safe_count += 1
        return ClassificationResult(
            action=action,
            action_class=ActionClass.SAFE,
            reason="No matching block or warn patterns — defaulting to SAFE",
            confidence=0.70,
        )

    def classify_tool_call(self, tool_name: str, params: dict) -> ClassificationResult:
        """
        Classify a structured tool call by name and parameters.
        Maps to classify() for Bash; applies path-sensitive logic for file tools.
        """
        sensitive_path_patterns = [".env", "oracle_key", "credentials"]

        if tool_name == "Bash":
            command = params.get("command", "")
            return self.classify(command)

        if tool_name == "Write":
            path = params.get("file_path", "")
            if any(s in path for s in sensitive_path_patterns):
                self._warned_count += 1
                return ClassificationResult(
                    action=f"Write:{path}",
                    action_class=ActionClass.WARN,
                    reason=f"Writing to sensitive file path: {path}",
                    confidence=0.90,
                    alternatives=["Write to a non-sensitive location and reference via env vars"],
                )
            self._safe_count += 1
            return ClassificationResult(
                action=f"Write:{path}",
                action_class=ActionClass.SAFE,
                reason="File write to non-sensitive path",
                confidence=0.85,
            )

        if tool_name == "Edit":
            path = params.get("file_path", "")
            if any(s in path for s in sensitive_path_patterns):
                self._warned_count += 1
                return ClassificationResult(
                    action=f"Edit:{path}",
                    action_class=ActionClass.WARN,
                    reason=f"Editing sensitive file path: {path}",
                    confidence=0.90,
                    alternatives=["Review diff carefully before applying edits to sensitive files"],
                )
            self._safe_count += 1
            return ClassificationResult(
                action=f"Edit:{path}",
                action_class=ActionClass.SAFE,
                reason="File edit to non-sensitive path",
                confidence=0.85,
            )

        if tool_name in ("Read", "Glob", "Grep"):
            self._safe_count += 1
            return ClassificationResult(
                action=f"{tool_name}",
                action_class=ActionClass.SAFE,
                reason=f"{tool_name} is a read-only operation",
                confidence=0.99,
            )

        # Unknown tool — default SAFE
        self._safe_count += 1
        return ClassificationResult(
            action=f"{tool_name}",
            action_class=ActionClass.SAFE,
            reason=f"Unknown tool '{tool_name}' — defaulting to SAFE",
            confidence=0.60,
        )

    def get_stats(self) -> dict:
        """Return classification counters for observability."""
        total = self._blocked_count + self._warned_count + self._safe_count
        return {
            "blocked_count": self._blocked_count,
            "warned_count": self._warned_count,
            "safe_count": self._safe_count,
            "total": total,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_alternatives(self, action: str) -> list[str]:
        """Return human-readable alternatives for a blocked action."""
        suggestions = []
        for pattern, alternative in self.BLOCK_ALTERNATIVES.items():
            if re.search(pattern, action, re.IGNORECASE):
                suggestions.append(alternative)
        return suggestions if suggestions else ["Review the action and use a safer equivalent"]


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def classify_action(action: str, context: dict = None) -> ClassificationResult:
    """Convenience wrapper — uses the singleton classifier."""
    return LocalPermissionClassifier().classify(action, context)
