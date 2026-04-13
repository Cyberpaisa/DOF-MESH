"""
DOF-MCP Gateway — Tool Router

HTTP bridge que despacha llamadas a las tool functions de core/mcp_server.py.
TOOL_MAP mapea nombre_tool → función.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger("dof.gateway.router")

# Importar directamente las funciones de tool desde mcp_server
from core.mcp_server import (
    tool_verify_governance,
    tool_verify_ast,
    tool_run_z3,
    tool_memory_add,
    tool_memory_query,
    tool_memory_snapshot,
    tool_get_metrics,
    tool_create_attestation,
    tool_oags_identity,
    tool_conformance_check,
    tool_mesh_send_task,
    tool_mesh_broadcast,
    tool_mesh_route_smart,
    tool_mesh_read_inbox,
    tool_mesh_consensus,
)

TOOL_MAP: dict[str, Any] = {
    "dof_verify_governance": tool_verify_governance,
    "dof_verify_ast": tool_verify_ast,
    "dof_run_z3": tool_run_z3,
    "dof_memory_add": tool_memory_add,
    "dof_memory_query": tool_memory_query,
    "dof_memory_snapshot": tool_memory_snapshot,
    "dof_get_metrics": tool_get_metrics,
    "dof_create_attestation": tool_create_attestation,
    "dof_oags_identity": tool_oags_identity,
    "dof_conformance_check": tool_conformance_check,
    "mesh_send_task": tool_mesh_send_task,
    "mesh_broadcast": tool_mesh_broadcast,
    "mesh_route_smart": tool_mesh_route_smart,
    "mesh_read_inbox": tool_mesh_read_inbox,
    "mesh_consensus": tool_mesh_consensus,
}

TIMEOUT_SECONDS = 30


class ToolRouter:
    """Despacha llamadas HTTP a las tool functions del MCP server."""

    def __init__(self):
        self._tool_map = TOOL_MAP

    def available_tools(self) -> list[str]:
        """Retorna lista de tool names disponibles."""
        return list(self._tool_map.keys())

    async def dispatch(self, tool_name: str, params: dict) -> dict:
        """
        Despacha la llamada a la tool correspondiente.

        - Si la tool no existe → {"error": "tool_not_found", "available": [...]}
        - Si timeout → {"error": "timeout", "timeout_ms": 30000}
        - Si excepción → {"error": str(e), "tool": tool_name}
        """
        if tool_name not in self._tool_map:
            logger.warning(f"Tool no encontrada: {tool_name}")
            return {
                "error": "tool_not_found",
                "tool": tool_name,
                "available": self.available_tools(),
            }

        fn = self._tool_map[tool_name]
        logger.debug(f"Despachando tool: {tool_name} params={list(params.keys())}")

        try:
            # Las tools son síncronas — ejecutar en executor para no bloquear el event loop
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fn, params),
                timeout=TIMEOUT_SECONDS,
            )
            return result if isinstance(result, dict) else {"result": result}

        except asyncio.TimeoutError:
            logger.error(f"Timeout en tool {tool_name} ({TIMEOUT_SECONDS}s)")
            return {
                "error": "timeout",
                "tool": tool_name,
                "timeout_ms": TIMEOUT_SECONDS * 1000,
            }
        except Exception as e:
            logger.error(f"Error en tool {tool_name}: {e}", exc_info=True)
            return {
                "error": str(e),
                "tool": tool_name,
            }
