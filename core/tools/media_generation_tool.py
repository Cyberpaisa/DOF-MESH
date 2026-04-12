"""
media_generation_tool.py — MediaGenerationTool para CrewAI.

Genera imágenes y diagramas via muapi.ai para uso en documentación DOF-MESH.
Controlado por el feature flag ``media_generation_tool`` (default: False).

Usage::
    from core.tools.media_generation_tool import create_media_generation_tool

    tool = create_media_generation_tool()
    result = tool._run("generate DOF architecture diagram")   # JSON string
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("dof.media_generation_tool")

# ── Optional imports (graceful degradation) ───────────────────────────────────

try:
    from crewai.tools import BaseTool
    _CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    logger.debug("crewai not installed — MediaGenerationTool running in stub mode")
    _CREWAI_AVAILABLE = False

    # Minimal stub so the class definition still works without crewai installed
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
    logger.debug("feature_flags not available — defaulting media_generation_tool=False")

    class _FallbackFlags:  # type: ignore[no-redef]
        def is_enabled(self, flag: str, default: bool = False) -> bool:
            return default

    _flags = _FallbackFlags()  # type: ignore[assignment]

# ── API constants ─────────────────────────────────────────────────────────────

_MUAPI_ENDPOINT = "https://api.muapi.ai/v1/generate"


# ── Tool ──────────────────────────────────────────────────────────────────────


class MediaGenerationTool(BaseTool):
    """
    CrewAI tool for generating images and diagrams via muapi.ai.

    When the ``media_generation_tool`` feature flag is **disabled** (default),
    returns a JSON payload indicating the tool is disabled — never raises.

    When the flag is **enabled**, performs an HTTP POST to the muapi.ai API
    using ``MUAPI_KEY`` from the environment.  Any network or API error is
    caught and returned as a clean error JSON — never propagated.

    Input:  natural-language prompt (e.g. ``"DOF architecture diagram"``).
    Output: JSON string with at minimum a ``status`` key.
    """

    name: str = "media_generation"
    description: str = (
        "Genera imágenes y diagramas via muapi.ai para uso en documentación DOF-MESH. "
        "Recibe un prompt descriptivo y retorna la URL de la imagen generada o un "
        "JSON de error/estado. Controlado por el feature flag media_generation_tool."
    )

    # ── CrewAI interface ──────────────────────────────────────────────────────

    def _run(self, prompt: str) -> str:
        """
        Execute synchronously — called by CrewAI agent.

        Returns a JSON string.  Never raises.
        """
        # Gate: feature flag check (deterministic, zero-LLM)
        if not _flags.is_enabled("media_generation_tool"):
            return json.dumps({
                "status": "disabled",
                "message": "media_generation_tool flag is disabled",
                "prompt": prompt,
            }, ensure_ascii=False)

        # Flag enabled — attempt real API call
        api_key = os.getenv("MUAPI_KEY", "")
        if not api_key:
            logger.warning("MUAPI_KEY not set — media generation will likely fail")

        try:
            import urllib.request

            payload = json.dumps({
                "prompt": prompt,
                "api_key": api_key,
            }).encode("utf-8")

            req = urllib.request.Request(
                _MUAPI_ENDPOINT,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
                # Parse and re-serialise to ensure valid JSON output
                data: Any = json.loads(body)
                return json.dumps({"status": "ok", "result": data}, ensure_ascii=False)

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("media_generation_tool request failed: %s", exc)
            return json.dumps({
                "status": "error",
                "message": str(exc),
                "prompt": prompt,
            }, ensure_ascii=False)

    def _arun(self, prompt: str) -> str:  # type: ignore[override]
        """Async entry-point — delegates to synchronous _run."""
        return self._run(prompt)


# ── Factory ───────────────────────────────────────────────────────────────────


def create_media_generation_tool() -> MediaGenerationTool:
    """Return a ready-to-use ``MediaGenerationTool`` instance."""
    return MediaGenerationTool()
