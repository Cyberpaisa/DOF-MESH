"""MEData (Medellín) — CKAN API client."""
from __future__ import annotations
import httpx
from typing import Optional

BASE_URL = "https://www.medata.gov.co/api/3/action"
_TIMEOUT = 8.0  # MEData puede ser lento — falla rápido para no bloquear
_HEADERS = {"User-Agent": "DOF-MESH/0.8.0 (datos-colombia-mcp)"}
_UNAVAILABLE_MSG = "MEData API no disponible actualmente (timeout). Portal: www.medata.gov.co"


def fetch_datasets(category: Optional[str] = None, limit: int = 10) -> dict:
    """Obtiene datasets del catálogo MEData.

    Args:
        category: tag de categoría para filtrar (ej: 'movilidad', 'educacion')
        limit: número máximo de resultados

    Returns:
        dict con keys 'success', 'result' (lista de datasets)
    """
    params: dict = {"rows": limit, "start": 0}
    if category:
        params["fq"] = f"tags:{category}"

    url = f"{BASE_URL}/package_search"
    resp = httpx.get(url, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {
        "success": data.get("success", False),
        "result": data.get("result", {}).get("results", []),
        "count": data.get("result", {}).get("count", 0),
    }


def get_dataset(node_id: str) -> dict:
    """Obtiene metadatos de un dataset específico por ID o nombre.

    Args:
        node_id: ID o nombre del dataset en MEData

    Returns:
        dict con metadatos del dataset
    """
    url = f"{BASE_URL}/package_show"
    resp = httpx.get(url, params={"id": node_id}, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {
        "success": data.get("success", False),
        "result": data.get("result", {}),
    }


def search_datasets(query: str, limit: int = 10) -> dict:
    """Busca datasets por texto libre.

    Args:
        query: términos de búsqueda
        limit: número máximo de resultados

    Returns:
        dict con 'success', 'result' (lista), 'count'
    """
    url = f"{BASE_URL}/package_search"
    try:
        resp = httpx.get(url, params={"q": query, "rows": limit},
                         headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "success": data.get("success", False),
            "result": data.get("result", {}).get("results", []),
            "count": data.get("result", {}).get("count", 0),
            "query": query,
        }
    except Exception:
        return {
            "success": False,
            "result": [],
            "count": 0,
            "query": query,
            "message": _UNAVAILABLE_MSG,
        }
