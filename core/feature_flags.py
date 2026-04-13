"""
feature_flags.py — Runtime feature flag system for DOF-MESH.

Flags are declared in dof.constitution.yml under `feature_flags:`.
They can be overridden at runtime without code deploys.

Usage::
    from core.feature_flags import flags, FeatureFlags

    if flags.is_enabled("streaming_executor"):
        # use StreamingToolExecutor
        ...

    # Override at runtime (e.g. during tests or gradual rollout)
    flags.enable("graphify_integration")
    flags.disable("media_generation_tool")

    # Check with default if flag not declared
    if flags.is_enabled("experimental_z3_v2", default=False):
        ...

    # Snapshot for audit trail
    print(flags.snapshot())
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("dof.feature_flags")

# Stable flags shipped in v0.7.0 — all True because they are already implemented
_DEFAULTS: dict[str, bool] = {
    # ── Sesión 8 features ──────────────────────────────────────────────
    "disk_task_queue": True,           # DiskTaskQueue in mesh_scheduler.py
    "system_prompt_boundary": True,    # check_system_prompt_boundary in governance.py
    "abort_signal_cascade": True,      # abort_event in claude_commander.py
    "streaming_executor": True,        # StreamingToolExecutor in streaming_executor.py
    "git_worktree_isolation": True,    # spawn_worker.sh worktree pattern
    "daemon_governance_gate": True,    # _gate_instruction in autonomous_daemon.py
    # ── Candidates for v0.8.0 ─────────────────────────────────────────
    "graphify_integration": True,      # GraphifyTool for CrewAI agents
    "media_generation_tool": True,     # muapi.ai media generation
    "feynman_research_crew": True,     # Feynman academic research agent
    "daemon_memory": True,             # DaemonMemory historical query (Sesión 8)
    "feature_flags_governance": True,  # Check flags inside ConstitutionEnforcer (v0.7.0)
    "dof_leaderboard": False,          # Leaderboard (needs 10+ agents to make sense)
    "dof_router": True,                # DOFRouter intelligent agent routing (core/router/)
    "semantic_boundary_check": True,   # TF-IDF semantic similarity in SystemPromptBoundary (v0.8.0)
}

_CONSTITUTION_PATH = Path(__file__).parent.parent / "dof.constitution.yml"


class FeatureFlags:
    """
    Runtime feature flag registry.

    Priority order (highest wins):
      1. Runtime overrides (set via enable() / disable() / set())
      2. dof.constitution.yml [feature_flags] section
      3. _DEFAULTS (compiled defaults)

    Thread safety: simple dict reads/writes — adequate for single-process daemon.
    Not safe for concurrent multi-process writes.
    """

    def __init__(self, constitution_path: Path = _CONSTITUTION_PATH) -> None:
        self._defaults: dict[str, bool] = dict(_DEFAULTS)
        self._from_yaml: dict[str, bool] = {}
        self._overrides: dict[str, bool] = {}

        self._load_from_constitution(constitution_path)

    # ── Constitution loader ────────────────────────────────────────────────────

    def _load_from_constitution(self, path: Path) -> None:
        """Load feature_flags section from dof.constitution.yml (best-effort)."""
        if not path.exists():
            return
        try:
            import yaml  # type: ignore
            with path.open(encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
            section = doc.get("feature_flags", {})
            if isinstance(section, dict):
                for key, val in section.items():
                    if isinstance(val, bool):
                        self._from_yaml[key] = val
                    elif isinstance(val, dict):
                        # Support: key: {enabled: true, description: "..."}
                        self._from_yaml[key] = bool(val.get("enabled", False))
            if self._from_yaml:
                logger.debug(f"FeatureFlags: loaded {len(self._from_yaml)} flags from constitution")
        except ImportError:
            logger.debug("PyYAML not available — using compiled defaults only")
        except Exception as e:
            logger.warning(f"FeatureFlags: could not load constitution ({e}) — using defaults")

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_enabled(self, flag: str, default: Optional[bool] = None) -> bool:
        """
        Return True if the feature flag is enabled.

        Resolution order: runtime override → YAML → compiled default → `default` arg.
        If the flag is unknown and no `default` is given, returns False.
        """
        if flag in self._overrides:
            return self._overrides[flag]
        if flag in self._from_yaml:
            return self._from_yaml[flag]
        if flag in self._defaults:
            return self._defaults[flag]
        if default is not None:
            return default
        logger.debug(f"FeatureFlags: unknown flag '{flag}' — returning False")
        return False

    def enable(self, flag: str) -> None:
        """Override flag to True at runtime."""
        self._overrides[flag] = True

    def disable(self, flag: str) -> None:
        """Override flag to False at runtime."""
        self._overrides[flag] = False

    def set(self, flag: str, value: bool) -> None:
        """Override flag to an explicit boolean at runtime."""
        self._overrides[flag] = bool(value)

    def reset(self, flag: Optional[str] = None) -> None:
        """
        Clear runtime overrides.
        If `flag` is given, resets only that flag.
        If None, resets all runtime overrides (used in tests).
        """
        if flag is None:
            self._overrides.clear()
        else:
            self._overrides.pop(flag, None)

    def all_flags(self) -> dict[str, bool]:
        """Return the effective state of all known flags (merged view)."""
        merged: dict[str, bool] = {}
        merged.update(self._defaults)
        merged.update(self._from_yaml)
        merged.update(self._overrides)
        return merged

    def snapshot(self) -> dict[str, Any]:
        """Return a serialisable audit snapshot of all layers."""
        return {
            "defaults": dict(self._defaults),
            "from_yaml": dict(self._from_yaml),
            "overrides": dict(self._overrides),
            "effective": self.all_flags(),
        }

    def __repr__(self) -> str:
        enabled = [k for k, v in self.all_flags().items() if v]
        disabled = [k for k, v in self.all_flags().items() if not v]
        return f"<FeatureFlags enabled={enabled} disabled={disabled}>"


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import and use directly: `from core.feature_flags import flags`
flags = FeatureFlags()
