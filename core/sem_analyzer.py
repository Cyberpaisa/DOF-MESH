from __future__ import annotations
"""
SemAnalyzer — Semantic diff layer for DOF-MESH agent code verification.

Uses `sem` (https://github.com/ataraxy-labs/sem) to produce entity-level
diffs of agent-generated Python code. Reports which functions and classes
were added, modified, or deleted — not just which lines changed.

Integrates with ASTVerifier as an enrichment layer. If `sem` is not
installed, all functions degrade gracefully to empty/neutral results so
the existing AST verification continues working unchanged.

Typical flow inside DOF-MESH:
    before_code = existing_module_source   # what the agent received
    after_code  = agent_generated_source   # what the agent produced
    diff        = sem_diff(before_code, after_code)
    ok, issues  = sem_verify_entities(diff, constitution_rules)
    entry       = sem_audit_entry(diff, agent_id="apex-1687", action="code_gen")
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.sem_analyzer")

# ── Constants ─────────────────────────────────────────────────────────────────

_SEM_BIN = shutil.which("sem")
_SEM_AVAILABLE = _SEM_BIN is not None

# Entity types sem reports for Python
ENTITY_TYPES = {"function", "class", "method", "variable"}

# Default rules if no constitution is provided
DEFAULT_BLOCKED_ENTITIES: set[str] = set()
DEFAULT_ALLOWED_CHANGE_TYPES: set[str] = {"modified"}   # added/deleted require explicit permit


# ── Availability check ────────────────────────────────────────────────────────

def sem_available() -> bool:
    """Return True if sem CLI is installed and reachable."""
    return _SEM_AVAILABLE


# ── Core diff ─────────────────────────────────────────────────────────────────

def sem_diff(
    before_code: str,
    after_code: str,
    filename: str = "agent_code.py",
    timeout: int = 10,
) -> dict:
    """
    Return a semantic diff between two versions of source code.

    Creates a temporary git repository, commits `before_code`, then stages
    `after_code` as an unstaged change and runs `sem diff --format json`.

    Args:
        before_code: Original source (what the agent received / previous version).
        after_code:  New source (what the agent generated / current version).
        filename:    Filename to use inside the temp repo (affects language detection).
        timeout:     Seconds before subprocess is killed.

    Returns:
        dict with keys:
            "available": bool  — False means sem is not installed (fallback active)
            "changes":  list[dict] — one entry per changed entity
            "summary":  dict       — totals by change type
            "error":    str | None — set if sem returned non-zero

        Each change entry from sem looks like:
            {
                "entityId":     "agent_code.py::function::send_data",
                "entityName":   "send_data",
                "entityType":   "function",
                "changeType":   "added",          # added | modified | deleted | renamed
                "beforeContent": null,
                "afterContent": "def send_data(url):\n    ...",
                "filePath":     "agent_code.py",
            }
    """
    if not _SEM_AVAILABLE:
        logger.debug("sem not installed — returning empty diff (AST fallback active)")
        return {"available": False, "changes": [], "summary": {}, "error": None}

    if before_code == after_code:
        return {
            "available": True,
            "changes": [],
            "summary": {"added": 0, "deleted": 0, "modified": 0, "total": 0},
            "error": None,
        }

    tmpdir = tempfile.mkdtemp(prefix="dof_sem_")
    try:
        repo = Path(tmpdir)
        code_file = repo / filename

        # Init git repo (quiet)
        subprocess.run(
            ["git", "init", "-q"],
            cwd=tmpdir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "dof@mesh.local"],
            cwd=tmpdir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "DOF-MESH"],
            cwd=tmpdir, check=True, capture_output=True
        )

        # Commit before_code
        code_file.write_text(before_code, encoding="utf-8")
        subprocess.run(
            ["git", "add", filename],
            cwd=tmpdir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "before"],
            cwd=tmpdir, check=True, capture_output=True
        )

        # Write after_code as unstaged change
        code_file.write_text(after_code, encoding="utf-8")

        # Run sem diff
        proc = subprocess.run(
            [_SEM_BIN, "diff", "--format", "json"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if proc.returncode != 0:
            logger.warning(f"sem diff error: {proc.stderr.strip()}")
            return {
                "available": True,
                "changes": [],
                "summary": {},
                "error": proc.stderr.strip(),
            }

        raw = json.loads(proc.stdout)
        return {
            "available": True,
            "changes": raw.get("changes", []),
            "summary": raw.get("summary", {}),
            "error": None,
        }

    except subprocess.TimeoutExpired:
        logger.error("sem diff timed out")
        return {"available": True, "changes": [], "summary": {}, "error": "timeout"}
    except Exception as e:
        logger.error(f"sem_diff failed: {e}")
        return {"available": True, "changes": [], "summary": {}, "error": str(e)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Entity verification ───────────────────────────────────────────────────────

def sem_verify_entities(
    diff_result: dict,
    constitution_rules: Optional[dict] = None,
) -> tuple[bool, list[dict]]:
    """
    Verify that the semantic changes comply with DOF constitution rules.

    Args:
        diff_result:        Output from sem_diff().
        constitution_rules: Optional dict with keys:
            "blocked_entities":      list[str] — entity names that must not be added
            "allowed_change_types":  list[str] — e.g. ["modified"] means only modifications
                                                  are allowed; "added" would block new funcs

    Returns:
        (passed: bool, violations: list[dict])
        Each violation: {"entity": str, "type": str, "change": str, "reason": str}
    """
    if not diff_result.get("available") or not diff_result.get("changes"):
        # sem unavailable or no changes — neutral pass
        return True, []

    rules = constitution_rules or {}
    blocked_names: set[str] = set(rules.get("blocked_entities", DEFAULT_BLOCKED_ENTITIES))
    allowed_types: set[str] = set(
        rules.get("allowed_change_types", list(DEFAULT_ALLOWED_CHANGE_TYPES))
    )

    violations = []

    for change in diff_result["changes"]:
        entity_name  = change.get("entityName", "")
        entity_type  = change.get("entityType", "")
        change_type  = change.get("changeType", "")
        entity_id    = change.get("entityId", "")

        # Rule 1: blocked entity names (e.g. "__import__", "exec", "eval")
        if entity_name in blocked_names:
            violations.append({
                "entity":  entity_id,
                "type":    entity_type,
                "change":  change_type,
                "reason":  f"Entity '{entity_name}' is blocked by constitution",
                "rule_id": "SEM_BLOCKED_ENTITY",
                "severity": "block",
            })

        # Rule 2: disallowed change types
        if allowed_types and change_type not in allowed_types:
            violations.append({
                "entity":  entity_id,
                "type":    entity_type,
                "change":  change_type,
                "reason":  (
                    f"Change type '{change_type}' not in allowed set {sorted(allowed_types)}. "
                    f"Entity '{entity_name}' was {change_type}."
                ),
                "rule_id": "SEM_DISALLOWED_CHANGE",
                "severity": "warn",
            })

    passed = not any(v["severity"] == "block" for v in violations)
    return passed, violations


# ── Audit trail ───────────────────────────────────────────────────────────────

def sem_audit_entry(
    diff_result: dict,
    agent_id: str,
    action: str,
) -> dict:
    """
    Build a semantic audit trail entry from a sem_diff result.

    This is the structured record that gets written to the execution trace,
    enriching it beyond a plain hash with entity-level context.

    Returns:
        dict with "semantic_diff" ready to embed in get_execution_trace().
    """
    if not diff_result.get("available"):
        return {
            "semantic_diff": {
                "available": False,
                "note": "sem not installed — structural hash only",
            }
        }

    changes = diff_result.get("changes", [])
    summary = diff_result.get("summary", {})

    # Group by change type for the audit entry
    by_type: dict[str, list[str]] = {}
    for c in changes:
        ct = c.get("changeType", "unknown")
        by_type.setdefault(ct, []).append(c.get("entityId", ""))

    return {
        "semantic_diff": {
            "agent_id":   agent_id,
            "action":     action,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary":    summary,
            "by_type":    by_type,
            "entities":   [
                {
                    "id":     c.get("entityId"),
                    "name":   c.get("entityName"),
                    "type":   c.get("entityType"),
                    "change": c.get("changeType"),
                }
                for c in changes
            ],
        }
    }
