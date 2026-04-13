"""
DOF-MCP Gateway — API Key Authentication

Valida x-api-key header contra lista de keys en DOF_GATEWAY_KEYS.
Si la variable no existe, modo dev: acepta cualquier key que empiece con "sk-dof-".
"""

import os
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger("dof.gateway.auth")

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


class APIKeyAuth:
    """Valida API keys para el DOF-MCP Gateway."""

    def __init__(self):
        raw = os.environ.get("DOF_GATEWAY_KEYS", "")
        if raw.strip():
            self._keys = {k.strip() for k in raw.split(",") if k.strip()}
            self._dev_mode = False
        else:
            self._keys = set()
            self._dev_mode = True
            logger.warning(
                "DOF_GATEWAY_KEYS no configurado — modo dev activo. "
                "Acepta cualquier key con prefijo 'sk-dof-'"
            )

    def validate(self, key: str) -> bool:
        """Retorna True si la key es válida."""
        if not key:
            return False
        if self._dev_mode:
            return key.startswith("sk-dof-")
        return key in self._keys

    def check(self, key: str) -> None:
        """
        Valida la key y lanza HTTPException(401) si es inválida.
        Usar como dependencia FastAPI con Security().
        """
        if not self.validate(key):
            logger.warning("Intento de acceso con key inválida")
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_api_key", "message": "API key inválida o faltante"},
            )


# Instancia global (singleton para dependencias FastAPI)
_auth = APIKeyAuth()


def get_api_key_auth() -> APIKeyAuth:
    """Retorna la instancia singleton de APIKeyAuth."""
    return _auth


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependencia FastAPI que valida el header x-api-key.
    Levanta HTTPException(401) si la key es inválida o falta.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_api_key", "message": "Header x-api-key requerido"},
        )
    _auth.check(api_key)
    return api_key
