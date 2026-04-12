"""
graphify_tool.py — GraphifyTool para CrewAI.

Cuando graphify_integration flag está habilitado, usa el plugin graphify para
servir fragmentos del grafo AST de core/. Con fallback: análisis simple via
ast stdlib.

Usage::
    from core.graphify_tool import create_graphify_tool

    tool = create_graphify_tool()
    result = tool._run("governance")   # JSON con modules/classes/functions
"""

from __future__ import annotations

import ast
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("dof.graphify_tool")

# ── Paths ─────────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent          # equipo-de-agentes/
_CORE_DIR = Path(__file__).parent                  # equipo-de-agentes/core/

# ── Optional imports (graceful degradation) ───────────────────────────────────

try:
    from crewai.tools import BaseTool
    _CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    logger.debug("crewai not installed — GraphifyTool running in fallback-only mode")
    _CREWAI_AVAILABLE = False

    # Minimal stub so the class definition still works
    class BaseTool:  # type: ignore[no-redef]
        """Stub when crewai is not installed."""
        name: str = ""
        description: str = ""

        def _run(self, query: str) -> str:  # pragma: no cover
            raise NotImplementedError

        def _arun(self, query: str) -> str:  # pragma: no cover
            return self._run(query)

        def run(self, query: str) -> str:  # pragma: no cover
            return self._run(query)

# ── Feature flags ─────────────────────────────────────────────────────────────

try:
    from core.feature_flags import flags as _flags
except ImportError:  # pragma: no cover
    logger.debug("feature_flags not available — defaulting graphify_integration=False")

    class _FallbackFlags:  # type: ignore[no-redef]
        def is_enabled(self, flag: str, default: bool = False) -> bool:
            return default

    _flags = _FallbackFlags()  # type: ignore[assignment]

# ── AST fallback helpers ──────────────────────────────────────────────────────


def _scan_core(query: str) -> dict[str, Any]:
    """
    Scan ``core/*.py`` files and return classes/functions matching *query*.

    Empty query returns everything.  Matching is case-insensitive substring
    check on both the symbol name and the module name.
    """
    q = query.strip().lower()

    modules_hit: list[str] = []
    classes_hit: list[dict[str, str]] = []
    functions_hit: list[dict[str, str]] = []

    py_files = sorted(_CORE_DIR.glob("*.py"))

    for fpath in py_files:
        module_name = fpath.stem
        module_matches = (not q) or (q in module_name.lower())

        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError as exc:
            logger.debug("graphify: syntax error in %s — %s", fpath.name, exc)
            continue
        except OSError as exc:
            logger.debug("graphify: cannot read %s — %s", fpath.name, exc)
            continue

        file_classes: list[str] = []
        file_functions: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                file_classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                file_functions.append(node.name)

        if not q:
            # Empty query — include everything
            modules_hit.append(module_name)
            for c in file_classes:
                classes_hit.append({"module": module_name, "name": c})
            for f in file_functions:
                functions_hit.append({"module": module_name, "name": f})
        else:
            # Filter by query — match module name or any symbol name
            matched_classes = [c for c in file_classes if q in c.lower()]
            matched_functions = [f for f in file_functions if q in f.lower()]

            if module_matches or matched_classes or matched_functions:
                modules_hit.append(module_name)
                for c in (file_classes if module_matches else matched_classes):
                    classes_hit.append({"module": module_name, "name": c})
                for f in (file_functions if module_matches else matched_functions):
                    functions_hit.append({"module": module_name, "name": f})

    return {
        "query": query,
        "modules": modules_hit,
        "classes": classes_hit,
        "functions": functions_hit,
    }


# ── Tool ──────────────────────────────────────────────────────────────────────


class GraphifyTool(BaseTool):
    """
    CrewAI tool for code-graph analysis of the DOF-MESH codebase.

    When the ``graphify_integration`` feature flag is **disabled** (default),
    falls back to a deterministic AST scan of ``core/*.py``.

    When the flag is **enabled**, delegates to the graphify plugin for richer
    graph traversal (call graphs, dependency edges, cross-module analysis).

    Input:  a natural-language or identifier query (e.g. ``"governance"``,
            ``"Z3Verifier"``, ``"supervisor"``).
    Output: JSON string with keys ``modules``, ``classes``, ``functions``,
            ``query``.
    """

    name: str = "graphify_code_graph"
    description: str = (
        "Analyse the DOF-MESH codebase graph. "
        "Given a query (module name, class name, or keyword), returns the "
        "matching modules, classes, and functions found in core/. "
        "Use this to understand code structure before making changes."
    )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_fallback(self, query: str) -> str:
        """AST-based fallback — fully deterministic, zero-LLM."""
        try:
            result = _scan_core(query)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover — defensive catch-all
            logger.error("graphify fallback error: %s", exc)
            return json.dumps({
                "query": query,
                "modules": [],
                "classes": [],
                "functions": [],
                "error": str(exc),
            })

    def _run_graphify_plugin(self, query: str) -> str:
        """
        Placeholder for the real graphify plugin integration (v0.8.0+).

        Replace this method once the plugin is available.
        """
        logger.info("graphify_integration enabled — plugin not yet wired, using fallback")
        return self._run_fallback(query)

    # ── CrewAI interface ──────────────────────────────────────────────────────

    def _run(self, query: str) -> str:
        """Execute synchronously — called by CrewAI agent."""
        if _flags.is_enabled("graphify_integration"):
            return self._run_graphify_plugin(query)
        return self._run_fallback(query)

    def _arun(self, query: str) -> str:  # type: ignore[override]
        """Async entry-point — sync fallback (adequate for local scanning)."""
        return self._run(query)


# ── Factory ───────────────────────────────────────────────────────────────────


def create_graphify_tool() -> GraphifyTool:
    """Return a ready-to-use ``GraphifyTool`` instance."""
    return GraphifyTool()
