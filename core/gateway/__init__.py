"""
DOF-MCP Gateway — HTTP bridge para mcp_server.py

Expone las 15 tools del DOF MCP Server como servicio FastAPI
con autenticación por API key, rate limiting y CORS.

Uso básico:
    uvicorn core.gateway.server:app --port 8080

Configuración:
    DOF_GATEWAY_KEYS=sk-dof-key1,sk-dof-key2  # keys válidas
    # Si no se configura → modo dev (acepta sk-dof-*)
"""

from .server import app
from .auth import APIKeyAuth
from .router import ToolRouter
from .rate_limiter import PersistentRateLimiter

__all__ = ["app", "APIKeyAuth", "ToolRouter", "PersistentRateLimiter"]
