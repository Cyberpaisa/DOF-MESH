"""
DOF Router — Failover Handler.

Ejecuta tareas con reintentos automáticos y rerouting inteligente
ante fallos. Persiste cada reroute en JSONL para auditoría.

Ciclo de ejecución:
    1. Seleccionar agente vía DOFRouter.
    2. Invocar task_fn(agent_id).
    3. Si falla → registrar fallo, loguear reroute, seleccionar fallback.
    4. Si éxito → registrar éxito, retornar FailoverResult.
    5. Tras max_attempts → retornar FailoverResult(success=False).
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field

from .dof_router import DOFRouter

logger = logging.getLogger("dof.router.failover")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_FAILOVER_LOG = os.path.join(BASE_DIR, "logs", "router", "failover.jsonl")


@dataclass
class FailoverResult:
    """Resultado de una ejecución con failover."""

    success: bool
    agent_used: str
    attempts: int
    total_latency_ms: float
    reroutes: list = field(default_factory=list)
    # [{from_agent, to_agent, reason, timestamp}]
    final_result: object = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "agent_used": self.agent_used,
            "attempts": self.attempts,
            "total_latency_ms": self.total_latency_ms,
            "reroutes": self.reroutes,
            "error": self.error,
            "timestamp": time.time(),
        }


class FailoverHandler:
    """Orquesta la ejecución con reintentos y rerouting automático.

    Args:
        router: Instancia de DOFRouter usada para selección y fallback.
        max_attempts: Número máximo de intentos antes de escalar el fallo.
        log_path: Ruta al JSONL donde se persisten los eventos de reroute.
    """

    def __init__(
        self,
        router: DOFRouter,
        max_attempts: int = 3,
        log_path: str = "",
    ):
        self.router = router
        self.max_attempts = max_attempts
        self._log_path = log_path or DEFAULT_FAILOVER_LOG
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

    def execute(self, task_fn, task_type: str = "default") -> FailoverResult:
        """Ejecuta task_fn con failover automático.

        Args:
            task_fn: Callable que acepta (agent_id: str) y retorna cualquier valor.
                     Debe lanzar una excepción para indicar fallo.
            task_type: Tipo de tarea para selección especializada.

        Returns:
            FailoverResult con los detalles de la ejecución.
        """
        reroutes: list = []
        total_latency_ms: float = 0.0
        current_agent = self.router.select_agent(task_type=task_type)
        last_error = ""
        failed_agents: list = []

        for attempt in range(1, self.max_attempts + 1):
            logger.debug(
                f"[failover] Intento {attempt}/{self.max_attempts} → agente={current_agent}"
            )
            start = time.time()
            try:
                result = task_fn(current_agent)
                elapsed = (time.time() - start) * 1000
                total_latency_ms += elapsed
                self.router.record_result(current_agent, success=True, latency_ms=elapsed)
                logger.info(
                    f"[failover] OK en intento {attempt} con {current_agent} "
                    f"({elapsed:.1f}ms)"
                )
                return FailoverResult(
                    success=True,
                    agent_used=current_agent,
                    attempts=attempt,
                    total_latency_ms=total_latency_ms,
                    reroutes=reroutes,
                    final_result=result,
                )
            except Exception as exc:
                elapsed = (time.time() - start) * 1000
                total_latency_ms += elapsed
                last_error = str(exc)
                self.router.record_result(current_agent, success=False, latency_ms=elapsed)

                logger.warning(
                    f"[failover] Fallo en intento {attempt} con {current_agent}: {exc}"
                )

                if attempt < self.max_attempts:
                    failed_agents.append(current_agent)
                    next_agent = self.router.get_fallback(current_agent)
                    reroute_entry = {
                        "from_agent": current_agent,
                        "to_agent": next_agent,
                        "reason": last_error[:200],
                        "timestamp": time.time(),
                    }
                    reroutes.append(reroute_entry)
                    self._log_reroute(reroute_entry)
                    current_agent = next_agent

        # Todos los intentos agotados
        logger.error(
            f"[failover] Todos los intentos fallaron ({self.max_attempts}). "
            f"Último agente: {current_agent}. Error: {last_error}"
        )
        return FailoverResult(
            success=False,
            agent_used=current_agent,
            attempts=self.max_attempts,
            total_latency_ms=total_latency_ms,
            reroutes=reroutes,
            error=last_error,
        )

    def _log_reroute(self, entry: dict) -> None:
        """Persiste un evento de reroute en JSONL."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.error(f"[failover] No se pudo loguear reroute: {exc}")
