"""
DOF-MCP Gateway — FastAPI Server

HTTP bridge que expone core/mcp_server.py como servicio REST con:
- Autenticación por API key (x-api-key header)
- Rate limiting en memoria (100 req/min por key)
- CORS habilitado para todos los origins
- Logging de cada request con latencia
"""

import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_api_key
from .rate_limiter import PersistentRateLimiter
from .router import ToolRouter

logger = logging.getLogger("dof.gateway.server")

# ─────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────

GATEWAY_VERSION = "0.8.0"
TOTAL_TOOLS = 15
RATE_LIMIT_MAX = 100   # requests por ventana
RATE_LIMIT_WINDOW = 60  # segundos

# ─────────────────────────────────────────────────────────────────────
# Rate limiter en memoria
# ─────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Rate limiter simple en memoria. {api_key: [timestamps]}"""

    def __init__(self, max_requests: int = RATE_LIMIT_MAX, window_seconds: int = RATE_LIMIT_WINDOW):
        self._max = max_requests
        self._window = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)

    def check(self, api_key: str) -> bool:
        """
        Retorna True si la key está dentro del límite.
        Retorna False si superó el límite (debe responder 429).
        """
        now = time.time()
        cutoff = now - self._window
        timestamps = self._store[api_key]
        # Limpiar timestamps fuera de la ventana
        self._store[api_key] = [t for t in timestamps if t >= cutoff]
        if len(self._store[api_key]) >= self._max:
            return False
        self._store[api_key].append(now)
        return True

    def remaining(self, api_key: str) -> int:
        """Retorna cuántas requests quedan en la ventana actual."""
        now = time.time()
        cutoff = now - self._window
        active = [t for t in self._store[api_key] if t >= cutoff]
        return max(0, self._max - len(active))


_rate_limiter = PersistentRateLimiter()
_router = ToolRouter()
_start_time = time.time()

# ─────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DOF-MCP Gateway",
    version=GATEWAY_VERSION,
    description=(
        "HTTP bridge para DOF-MCP Server. "
        "Expone las 15 tools de governance, memoria, métricas e identidad "
        "como endpoints REST con autenticación por API key."
    ),
)

# CORS — habilitado para todos los origins (servicio público)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────
# Middleware de logging
# ─────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Loguea cada request: método, path, latencia, status."""
    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} latency={latency_ms}ms"
    )
    return response


# ─────────────────────────────────────────────────────────────────────
# Dependencia: rate limit
# ─────────────────────────────────────────────────────────────────────

async def check_rate_limit(api_key: str = Depends(require_api_key)) -> str:
    """Dependencia que verifica rate limit después de autenticación."""
    if not _rate_limiter.check(api_key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Máximo {RATE_LIMIT_MAX} requests por {RATE_LIMIT_WINDOW}s",
                "retry_after": RATE_LIMIT_WINDOW,
            },
        )
    return api_key


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    """
    Health check — no requiere autenticación.
    Retorna estado del gateway, versión y tools disponibles.
    """
    uptime_ms = round((time.time() - _start_time) * 1000)
    return {
        "status": "ok",
        "version": GATEWAY_VERSION,
        "tools": TOTAL_TOOLS,
        "uptime_ms": uptime_ms,
    }


@app.post("/mcp/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    request: Request,
    api_key: str = Depends(check_rate_limit),
) -> dict[str, Any]:
    """
    Invoca una tool del DOF-MCP Server.

    - Requiere header x-api-key válido
    - Body: JSON dict con los parámetros de la tool
    - Retorna el resultado de la tool como JSON
    """
    # Parsear body — vacío si no se envía JSON
    try:
        params: dict = await request.json()
    except Exception:
        params = {}

    if not isinstance(params, dict):
        params = {}

    start = time.time()
    result = await _router.dispatch(tool_name, params)
    latency_ms = round((time.time() - start) * 1000, 1)

    logger.info(
        f"tool={tool_name} key={api_key[:12]}... "
        f"latency={latency_ms}ms "
        f"error={'error' in result}"
    )

    return result
