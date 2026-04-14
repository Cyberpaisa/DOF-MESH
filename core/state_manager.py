"""
StateManager — Gestor de estado global persistente para DOF-MESH Second Brain v2.0.

Persiste en memory/global_state.json.
Thread-safe. Sin dependencias externas.

Estado global:
  current_task    → tarea activa actual
  history         → lista de resultados de tareas (últimas N)
  memory          → contexto CPR comprimido
  session_id      → ID único de sesión actual
  token_count     → estimado de tokens consumidos en sesión
"""

import os
import json
import uuid
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("core.state_manager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "memory", "global_state.json")

MAX_HISTORY = 50        # máximo de ítems en historial
TOKEN_COMPRESS_THRESHOLD = 1500  # chars antes de recomendar CPR


class StateManager:
    """
    Gestor de estado global con persistencia en JSON.

    Uso:
        state = StateManager()
        state.update("current_task", "Analizar SAM")
        state.append("history", resultado)
        task = state.get("current_task")
    """

    def __init__(self, state_file: str = STATE_FILE) -> None:
        self._file = state_file
        self._lock = threading.Lock()
        self._state = self._load()

    # ── Persistencia ──────────────────────────────────────────────────

    def _load(self) -> dict:
        """Carga estado desde disco o retorna estado inicial."""
        os.makedirs(os.path.dirname(self._file), exist_ok=True)
        if os.path.exists(self._file):
            try:
                with open(self._file, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Estado cargado desde %s", self._file)
                return data
            except Exception as exc:
                logger.warning("No se pudo cargar estado: %s — iniciando limpio", exc)
        return self._initial_state()

    def _initial_state(self) -> dict:
        return {
            "session_id": str(uuid.uuid4())[:8],
            "session_start": datetime.now(timezone.utc).isoformat(),
            "current_task": None,
            "history": [],
            "memory": [],
            "pending_tasks": [],
            "token_count": 0,
        }

    def _save(self) -> None:
        """Persiste estado actual en disco."""
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as exc:
            logger.error("Error al persistir estado: %s", exc)

    # ── API Pública ────────────────────────────────────────────────────

    def update(self, key: str, value: Any) -> None:
        """Actualiza un campo del estado y persiste."""
        with self._lock:
            self._state[key] = value
            self._save()

    def append(self, key: str, value: Any, max_items: int = MAX_HISTORY) -> None:
        """Añade un ítem a una lista del estado (con límite)."""
        with self._lock:
            if key not in self._state:
                self._state[key] = []
            self._state[key].append(value)
            # Mantener solo los últimos N ítems
            if len(self._state[key]) > max_items:
                self._state[key] = self._state[key][-max_items:]
            self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un campo del estado."""
        with self._lock:
            return self._state.get(key, default)

    def get_all(self) -> dict:
        """Retorna copia completa del estado."""
        with self._lock:
            return dict(self._state)

    def reset_session(self) -> str:
        """Inicia nueva sesión preservando historial."""
        with self._lock:
            new_id = str(uuid.uuid4())[:8]
            self._state["session_id"] = new_id
            self._state["session_start"] = datetime.now(timezone.utc).isoformat()
            self._state["current_task"] = None
            self._state["token_count"] = 0
            self._save()
        return new_id

    def add_tokens(self, chars: int) -> int:
        """Registra tokens consumidos. Retorna total acumulado."""
        with self._lock:
            self._state["token_count"] = self._state.get("token_count", 0) + chars
            total = self._state["token_count"]
            self._save()
        return total

    def needs_compression(self) -> bool:
        """True si el contexto acumulado supera el umbral CPR."""
        with self._lock:
            return self._state.get("token_count", 0) > TOKEN_COMPRESS_THRESHOLD

    def get_stats(self) -> dict:
        """Estadísticas del estado para dashboard."""
        with self._lock:
            return {
                "session_id": self._state.get("session_id"),
                "session_start": self._state.get("session_start"),
                "current_task": self._state.get("current_task"),
                "history_count": len(self._state.get("history", [])),
                "memory_count": len(self._state.get("memory", [])),
                "pending_tasks": len(self._state.get("pending_tasks", [])),
                "token_count": self._state.get("token_count", 0),
                "needs_compression": self.needs_compression(),
            }
