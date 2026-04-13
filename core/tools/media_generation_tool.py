"""
media_generation_tool.py — MediaGenerationTool para CrewAI.

Genera imágenes y diagramas via muapi.ai para uso en documentación DOF-MESH.
Controlado por el feature flag ``media_generation_tool`` (default: False).

API muapi.ai (async):
  POST  https://api.muapi.ai/api/v1/{model}       → {"request_id": "...", "status": "processing"}
  GET   https://api.muapi.ai/api/v1/predictions/{request_id}/result
                                                   → {"status": "completed", "images": [...]}
  Auth: x-api-key header (NOT Authorization: Bearer)

Default model: flux-schnell-image (fast, works in sandbox)

Usage::
    from core.tools.media_generation_tool import create_media_generation_tool

    tool = create_media_generation_tool()
    result = tool._run("generate DOF architecture diagram")   # JSON string
"""

from __future__ import annotations

import json
import logging
import os
import time
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

_MUAPI_BASE = "https://api.muapi.ai/api/v1"
_DEFAULT_IMAGE_MODEL = "flux-schnell-image"
_POLL_MAX_ATTEMPTS = 20   # 20 × 2s = 40s max
_POLL_INTERVAL = 2.0      # seconds between polls


# ── Tool ──────────────────────────────────────────────────────────────────────


class MediaGenerationTool(BaseTool):
    """
    CrewAI tool for generating images and diagrams via muapi.ai.

    When the ``media_generation_tool`` feature flag is **disabled** (default),
    returns a JSON payload indicating the tool is disabled — never raises.

    When the flag is **enabled**, performs an async HTTP flow to muapi.ai:
      1. POST  /api/v1/{model}                  → request_id
      2. GET   /api/v1/predictions/{id}/result  → poll until completed / failed

    Auth: ``x-api-key`` header using ``MUAPI_KEY`` env var.
    Any network or API error is caught and returned as clean error JSON.

    Input:  natural-language prompt (e.g. ``"DOF architecture diagram"``).
            Optionally prefix with ``model:<name> `` to select a different model.
    Output: JSON string with at minimum a ``status`` key.
    """

    name: str = "media_generation"
    description: str = (
        "Genera imágenes y diagramas via muapi.ai para uso en documentación DOF-MESH. "
        "Recibe un prompt descriptivo y retorna la URL de la imagen generada o un "
        "JSON de error/estado. Controlado por el feature flag media_generation_tool. "
        "Prefija con 'model:<nombre> ' para seleccionar un modelo específico "
        "(ej: 'model:flux-dev-image DOF architecture')."
    )

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_model_and_prompt(prompt: str | None) -> tuple[str, str]:
        """Extract optional ``model:<name>`` prefix from prompt."""
        if not prompt:
            return _DEFAULT_IMAGE_MODEL, ""
        p = prompt if isinstance(prompt, str) else str(prompt)
        if p.startswith("model:"):
            parts = p[len("model:"):].split(" ", 1)
            model = parts[0].strip() or _DEFAULT_IMAGE_MODEL
            text = parts[1].strip() if len(parts) > 1 else ""
            return model, text
        return _DEFAULT_IMAGE_MODEL, p

    @staticmethod
    def _http_post(url: str, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        import urllib.request
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _http_get(url: str, headers: dict[str, str]) -> dict[str, Any]:
        import urllib.request
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    def _poll_result(self, request_id: str, headers: dict[str, str]) -> dict[str, Any]:
        """Poll predictions endpoint until status is terminal or max attempts reached."""
        url = f"{_MUAPI_BASE}/predictions/{request_id}/result"
        for attempt in range(_POLL_MAX_ATTEMPTS):
            try:
                data = self._http_get(url, headers)
                status = data.get("status", "")
                if status == "completed":
                    return data
                if status in ("failed", "error", "cancelled"):
                    return data
                # Still processing — wait and retry
                if attempt < _POLL_MAX_ATTEMPTS - 1:
                    time.sleep(_POLL_INTERVAL)
            except Exception as exc:
                logger.debug("muapi poll attempt %d failed: %s", attempt + 1, exc)
                if attempt < _POLL_MAX_ATTEMPTS - 1:
                    time.sleep(_POLL_INTERVAL)
        return {"status": "timeout", "request_id": request_id}

    # ── CrewAI interface ──────────────────────────────────────────────────────

    def _run(self, prompt: str) -> str:
        """
        Execute synchronously — called by CrewAI agent.

        Returns a JSON string.  Never raises.
        """
        try:
            return self._run_inner(prompt)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("media_generation_tool unexpected error: %s", exc)
            return json.dumps({
                "status": "error",
                "message": str(exc),
                "prompt": prompt,
            }, ensure_ascii=False)

    def _run_inner(self, prompt: str) -> str:
        # Gate: feature flag check
        if not _flags.is_enabled("media_generation_tool"):
            return json.dumps({
                "status": "disabled",
                "message": "media_generation_tool flag is disabled",
                "prompt": prompt,
            }, ensure_ascii=False)

        # Flag enabled — check API key before any network call
        api_key = os.getenv("MUAPI_KEY", "")
        if not api_key:
            logger.warning("MUAPI_KEY not set — media_generation_tool requires MUAPI_KEY env var")
            return json.dumps({
                "status": "no_api_key",
                "message": "MUAPI_KEY environment variable not set. Set it to enable media generation.",
                "prompt": prompt,
            }, ensure_ascii=False)

        model, clean_prompt = self._parse_model_and_prompt(prompt)

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        payload = json.dumps({"prompt": clean_prompt}).encode("utf-8")

        # Step 1: submit generation request
        submit_url = f"{_MUAPI_BASE}/{model}"
        try:
            submit_resp = self._http_post(submit_url, payload, headers)
        except Exception as exc:
            logger.error("muapi submit failed: %s", exc)
            return json.dumps({
                "status": "error",
                "message": f"Submit failed: {exc}",
                "prompt": prompt,
            }, ensure_ascii=False)

        request_id = submit_resp.get("request_id") or submit_resp.get("id")
        if not request_id:
            # Some sandbox responses return the result immediately
            if submit_resp.get("status") == "completed" or submit_resp.get("images"):
                return json.dumps({
                    "status": "ok",
                    "model": model,
                    "prompt": clean_prompt,
                    "result": submit_resp,
                }, ensure_ascii=False)
            return json.dumps({
                "status": "error",
                "message": "No request_id in response",
                "response": submit_resp,
                "prompt": prompt,
            }, ensure_ascii=False)

        logger.info("muapi job submitted: request_id=%s model=%s", request_id, model)

        # Step 2: poll until done
        result = self._poll_result(request_id, headers)

        final_status = result.get("status", "unknown")
        images = result.get("images") or result.get("outputs") or []

        if final_status == "completed":
            return json.dumps({
                "status": "ok",
                "model": model,
                "request_id": request_id,
                "prompt": clean_prompt,
                "images": images,
                "result": result,
            }, ensure_ascii=False)

        return json.dumps({
            "status": final_status,
            "model": model,
            "request_id": request_id,
            "prompt": clean_prompt,
            "result": result,
        }, ensure_ascii=False)

    def _arun(self, prompt: str) -> str:  # type: ignore[override]
        """Async entry-point — delegates to synchronous _run."""
        return self._run(prompt)


# ── Factory ───────────────────────────────────────────────────────────────────


def create_media_generation_tool() -> MediaGenerationTool:
    """Return a ready-to-use ``MediaGenerationTool`` instance."""
    return MediaGenerationTool()
