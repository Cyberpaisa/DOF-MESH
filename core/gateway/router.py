"""
DOF-MCP Gateway — Tool Router

HTTP bridge que despacha llamadas a las tool functions de core/mcp_server.py.
TOOL_MAP mapea nombre_tool → función.
"""

import asyncio
import logging
import sys
import os
from typing import Any

logger = logging.getLogger("dof.gateway.router")

# ── datos-colombia-mcp tools ─────────────────────────────────────────────────
# El directorio usa guión por lo que no es importable con notación punteada estándar.
# Se agrega al sys.path en tiempo de importación.
_DATOS_COLOMBIA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "integrations", "datos-colombia",
)
if _DATOS_COLOMBIA_PATH not in sys.path:
    sys.path.insert(0, _DATOS_COLOMBIA_PATH)

try:
    from tools.secop import fetch_contracts, detect_anomalies
    from medata import search_datasets as _search_datasets
    _DATOS_COLOMBIA_AVAILABLE = True
    logger.info("datos-colombia-mcp: SECOP + MEData tools cargadas")
except ImportError as _e:
    _DATOS_COLOMBIA_AVAILABLE = False
    logger.warning(f"datos-colombia-mcp no disponible: {_e}")


def tool_secop_search(params: dict) -> dict:
    """Busca contratos públicos en SECOP II. Params: entity, year, municipio, limit."""
    if not _DATOS_COLOMBIA_AVAILABLE:
        return {"error": "datos-colombia-mcp no disponible"}
    try:
        contracts = fetch_contracts(
            entity=params.get("entity"),
            year=params.get("year"),
            municipio=params.get("municipio"),
            limit=int(params.get("limit", 20)),
        )
        return {"contracts": contracts, "count": len(contracts)}
    except Exception as e:
        return {"error": str(e), "tool": "secop_search"}


def tool_secop_anomalies(params: dict) -> dict:
    """Detecta anomalías de fraccionamiento en SECOP. Params: entity, threshold."""
    if not _DATOS_COLOMBIA_AVAILABLE:
        return {"error": "datos-colombia-mcp no disponible"}
    try:
        entity = params.get("entity", "")
        threshold = int(params.get("threshold", 3))
        contracts = fetch_contracts(entity=entity, limit=100)
        report = detect_anomalies(contracts, entity=entity,
                                  threshold_fraccionamiento=threshold)
        return {
            "entity": entity,
            "total_contracts": len(contracts),
            "fraccionamiento": [
                {"contratista": a.contratista_id, "contracts": a.contract_ids,
                 "total_value": a.total_value, "mes": a.mes_key}
                for a in report.fraccionamiento
            ],
            "concentracion": [
                {"contratista": a.contratista_id, "porcentaje": a.porcentaje}
                for a in report.concentracion
            ],
        }
    except Exception as e:
        return {"error": str(e), "tool": "secop_anomalies"}


def tool_medata_search(params: dict) -> dict:
    """Busca datasets en MEData (portal datos abiertos Medellín). Params: query, limit."""
    if not _DATOS_COLOMBIA_AVAILABLE:
        return {"error": "datos-colombia-mcp no disponible"}
    try:
        result = _search_datasets(
            query=params.get("query", ""),
            limit=int(params.get("limit", 10)),
        )
        return result if isinstance(result, dict) else {"datasets": result}
    except Exception as e:
        return {"error": str(e), "tool": "medata_search"}


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
    # datos-colombia-mcp
    "secop_search": tool_secop_search,
    "secop_anomalies": tool_secop_anomalies,
    "medata_search": tool_medata_search,
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
