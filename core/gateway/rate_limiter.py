"""
DOF-MCP Gateway — Persistent Rate Limiter

Persiste el conteo de requests en JSONL para sobrevivir reinicios del proceso.
Mismo patrón de persistencia que logs/daemon/cycles.jsonl.

Formato de cada línea JSONL:
  {"key": "sk-dof-xxx", "count": 45,
   "window_start": "2026-04-13T00:00:00+00:00", "timestamps": [1713000000.1, ...]}

Al iniciar: carga el archivo y descarta timestamps fuera de la ventana activa.
Al registrar: reescribe el archivo con el estado actual.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("dof.gateway.rate_limiter")

BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_LOG_PATH = BASE_DIR / "logs" / "gateway" / "rate_limits.jsonl"


class PersistentRateLimiter:
    """
    Rate limiter con persistencia JSONL.

    Diferencias vs RateLimiter en memoria:
    - Sobrevive reinicios — el conteo no se resetea al morir el proceso
    - Ventanas expiradas se descartan automáticamente al cargar
    - El directorio logs/gateway/ se crea automáticamente si no existe
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        log_path: Optional[Path] = None,
    ):
        self._max = max_requests
        self._window = window_seconds
        self._log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH
        # {api_key: [unix_timestamp, ...]}
        self._store: Dict[str, List[float]] = {}
        self._load()

    # ─────────────────────────────────────────────────────────────────
    # Persistencia
    # ─────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """
        Lee estado previo del JSONL.
        Descarta timestamps fuera de la ventana activa (ya expirados).
        """
        if not self._log_path.exists():
            return
        now = time.time()
        cutoff = now - self._window
        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        key = entry.get("key", "")
                        if not key:
                            continue
                        # Solo conservar timestamps dentro de la ventana activa
                        valid = [t for t in entry.get("timestamps", []) if t >= cutoff]
                        if valid:
                            self._store[key] = valid
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue  # línea corrupta — ignorar
        except OSError as e:
            logger.warning(f"[rate_limiter] No se pudo leer estado previo: {e}")

    def _save(self) -> None:
        """
        Escribe estado actual al JSONL.
        Sobrescribe el archivo completo con el estado en memoria.
        """
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "w") as f:
                for key, timestamps in self._store.items():
                    if not timestamps:
                        continue
                    entry = {
                        "key": key,
                        "count": len(timestamps),
                        "window_start": datetime.fromtimestamp(
                            min(timestamps), tz=timezone.utc
                        ).isoformat(),
                        "timestamps": timestamps,
                    }
                    f.write(json.dumps(entry) + "\n")
        except OSError as e:
            logger.warning(f"[rate_limiter] No se pudo guardar estado: {e}")

    # ─────────────────────────────────────────────────────────────────
    # API pública — compatible con RateLimiter existente
    # ─────────────────────────────────────────────────────────────────

    def check(self, api_key: str) -> bool:
        """
        Verifica y registra un request.

        Returns:
            True  — dentro del límite, request permitido
            False — límite superado, debe retornar 429
        """
        now = time.time()
        cutoff = now - self._window
        # Limpiar timestamps expirados para esta key
        self._store[api_key] = [
            t for t in self._store.get(api_key, []) if t >= cutoff
        ]
        if len(self._store[api_key]) >= self._max:
            return False
        self._store[api_key].append(now)
        self._save()
        return True

    def remaining(self, api_key: str) -> int:
        """Requests restantes en la ventana activa."""
        now = time.time()
        cutoff = now - self._window
        active = [t for t in self._store.get(api_key, []) if t >= cutoff]
        return max(0, self._max - len(active))

    def reset(self, api_key: Optional[str] = None) -> None:
        """
        Resetea contadores — principalmente para tests.
        Si api_key=None, resetea todos los contadores.
        """
        if api_key is not None:
            self._store.pop(api_key, None)
        else:
            self._store.clear()
        self._save()
