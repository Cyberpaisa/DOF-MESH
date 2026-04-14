from __future__ import annotations
"""
EventBus — Sistema Pub/Sub soberano para DOF-MESH Second Brain v2.0.

Sin dependencias externas. Síncrono y thread-safe.
Diseño Unix: silencioso en éxito, ruidoso en fallos.

Eventos del sistema:
  vault_modified    → Hunter detectó cambio en el vault
  task_created      → Nueva nota task con status:pending detectada
  task_completed    → Executor terminó una tarea
  compress_needed   → Contexto superó umbral CPR
  session_start     → Sesión iniciada
  session_end       → Sesión terminada (trigger CPR auto)
"""

import threading
import logging
from typing import Callable, Any

logger = logging.getLogger("core.event_bus")


class EventBus:
    """
    Bus de eventos Pub/Sub thread-safe.

    Uso:
        bus = EventBus()
        bus.subscribe("vault_modified", handler_fn)
        bus.publish("vault_modified", {"path": "/ruta/nota.md"})
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()
        self._event_count: int = 0

    def subscribe(self, event: str, handler: Callable) -> None:
        """Registra un handler para un tipo de evento."""
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            if handler not in self._subscribers[event]:
                self._subscribers[event].append(handler)
        logger.debug("Suscrito: %s → %s", event, handler.__name__)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Elimina un handler para un tipo de evento."""
        with self._lock:
            if event in self._subscribers:
                self._subscribers[event] = [
                    h for h in self._subscribers[event] if h is not handler
                ]

    def publish(self, event: str, data: Any = None) -> int:
        """
        Publica un evento y llama a todos los handlers registrados.
        Retorna el número de handlers llamados.
        Fallos en handlers se loggean pero NO propagan.
        """
        with self._lock:
            handlers = list(self._subscribers.get(event, []))
            self._event_count += 1

        called = 0
        for handler in handlers:
            try:
                handler(data)
                called += 1
            except Exception as exc:
                logger.error(
                    "Handler %s falló en evento '%s': %s",
                    handler.__name__, event, exc
                )

        if called > 0:
            logger.debug("Evento '%s' publicado → %d handlers", event, called)
        return called

    def get_events(self) -> list[str]:
        """Retorna lista de eventos registrados."""
        with self._lock:
            return list(self._subscribers.keys())

    def get_stats(self) -> dict:
        """Estadísticas del bus para dashboard."""
        with self._lock:
            return {
                "total_events_published": self._event_count,
                "registered_events": list(self._subscribers.keys()),
                "subscriber_counts": {
                    ev: len(handlers)
                    for ev, handlers in self._subscribers.items()
                },
            }
