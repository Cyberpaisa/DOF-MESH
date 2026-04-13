"""
DOF Router — Intelligent Agent Routing Layer.

Selecciona qué agente del mesh ejecuta cada tarea usando métricas de
latencia y tasa de éxito. Integración OPCIONAL y backward-compatible
con AutonomousDaemon — no modifica autonomous_daemon.py.

INTEGRATION POINT: En autonomous_daemon.py, función execute(),
reemplazar:
    agent_id = self._select_provider()
con:
    agent_id = self.router.select_agent(task_type=action.mode) if self.router else self._select_provider()

El daemon instanciaría el router en __init__ como dependencia opcional:
    self.router: Optional[DOFRouter] = None
"""

import logging
import os

from .agent_metrics import MetricsStore

logger = logging.getLogger("dof.router")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_METRICS_PATH = os.path.join(BASE_DIR, "logs", "router", "agent_metrics.jsonl")

# Agentes conocidos por defecto — mapeados a los proveedores LLM actuales del mesh
DEFAULT_AGENTS = [
    "minimax-m2.1",
    "groq-llama-70b",
    "nvidia-nim-qwen",
    "cerebras-gpt-120b",
    "sambanova-deepseek",
]

# Umbral de fallos consecutivos antes de excluir un agente
CONSECUTIVE_FAILURE_THRESHOLD = 3

# Diferencia mínima de latencia para preferir un agente sobre otro (ms)
LATENCY_TIE_THRESHOLD_MS = 50.0


class DOFRouter:
    """Router inteligente para el mesh de agentes DOF.

    Selecciona agentes según latencia promedio y tasa de éxito.
    Admite exclusión temporal de agentes con fallos consecutivos.
    Configurable — sin hardcoding de lógica de negocio.

    Args:
        agents: Lista de agent_ids disponibles. Por defecto DEFAULT_AGENTS.
        metrics_path: Ruta al JSONL de métricas persistidas.
        failure_threshold: Número de fallos consecutivos para excluir un agente.
        latency_tie_threshold_ms: Diferencia de latencia para considerar empate.
    """

    def __init__(
        self,
        agents: list = None,
        metrics_path: str = "",
        failure_threshold: int = CONSECUTIVE_FAILURE_THRESHOLD,
        latency_tie_threshold_ms: float = LATENCY_TIE_THRESHOLD_MS,
    ):
        self.agents = list(agents) if agents else list(DEFAULT_AGENTS)
        self.failure_threshold = failure_threshold
        self.latency_tie_threshold_ms = latency_tie_threshold_ms
        self._metrics_path = metrics_path or DEFAULT_METRICS_PATH
        self.metrics = MetricsStore(metrics_path=self._metrics_path)
        if os.path.exists(self._metrics_path):
            self.metrics.load(self._metrics_path)

    # ──────────────────────────────────────────────────────────
    # Selección principal
    # ──────────────────────────────────────────────────────────

    def select_agent(self, task_type: str = "default", exclude: list = None) -> str:
        """Selecciona el mejor agente disponible para la tarea.

        Lógica de decisión:
        1. Excluir agentes con consecutive_failures >= failure_threshold.
        2. De los restantes, elegir el de menor avg_latency_ms.
        3. Si empate (diff < latency_tie_threshold_ms) → elegir el menos usado
           recientemente (menor last_used).
        4. Si TODOS excluidos → usar el de menor consecutive_failures
           (mejor malo que nada).

        Args:
            task_type: Tipo de tarea — se usará en futuras extensiones para
                       routing especializado por dominio.
            exclude: Lista adicional de agent_ids a excluir en esta selección.

        Returns:
            agent_id seleccionado.
        """
        exclude_set = set(exclude or [])

        # Candidatos vivos (sin fallos excesivos ni en exclusión explícita)
        candidates = [
            a for a in self.agents
            if a not in exclude_set
            and self.metrics.get(a).consecutive_failures < self.failure_threshold
        ]

        if not candidates:
            # Fallback degradado: todos fallan → elegir el "menos malo"
            logger.warning(
                "[router] Todos los agentes superaron el umbral de fallos — "
                "seleccionando el menos malo"
            )
            candidates = [a for a in self.agents if a not in exclude_set]
            if not candidates:
                # Si exclude_set cubre todo, ignorar exclusiones externas
                candidates = list(self.agents)
            return min(
                candidates,
                key=lambda a: self.metrics.get(a).consecutive_failures,
            )

        # Ordenar por avg_latency_ms ascendente (0.0 = sin datos → va primero como exploración)
        candidates_sorted = sorted(
            candidates,
            key=lambda a: self.metrics.get(a).avg_latency_ms,
        )

        best = candidates_sorted[0]
        best_latency = self.metrics.get(best).avg_latency_ms

        # Detectar empate por latencia
        tied = [
            a for a in candidates_sorted
            if abs(self.metrics.get(a).avg_latency_ms - best_latency)
            < self.latency_tie_threshold_ms
        ]

        if len(tied) > 1:
            # Desempate: elegir el menos usado recientemente
            selected = min(tied, key=lambda a: self.metrics.get(a).last_used)
            logger.debug(
                f"[router] Empate de latencia entre {tied} → seleccionado {selected} "
                f"(menor last_used)"
            )
            return selected

        logger.debug(
            f"[router] Seleccionado {best} "
            f"(latency={best_latency:.1f}ms, task_type={task_type})"
        )
        return best

    def get_fallback(self, failed_agent: str) -> str:
        """Retorna el siguiente mejor agente excluyendo al que falló.

        Args:
            failed_agent: agent_id del agente que acaba de fallar.

        Returns:
            agent_id del agente de fallback.
        """
        return self.select_agent(exclude=[failed_agent])

    # ──────────────────────────────────────────────────────────
    # Registro de resultados
    # ──────────────────────────────────────────────────────────

    def record_result(self, agent_id: str, success: bool, latency_ms: float) -> None:
        """Actualiza métricas del agente y persiste en JSONL.

        Args:
            agent_id: Identificador del agente.
            success: True si la ejecución fue exitosa.
            latency_ms: Tiempo de respuesta en milisegundos.
        """
        self.metrics.update(agent_id, success, latency_ms)
        self.metrics.save(self._metrics_path)

    # ──────────────────────────────────────────────────────────
    # Estadísticas
    # ──────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Resumen de métricas por agente.

        Returns:
            dict: {agent_id: {success_rate, avg_latency_ms, consecutive_failures}}
        """
        return {
            a: {
                "success_rate": round(self.metrics.get(a).success_rate, 3),
                "avg_latency_ms": round(self.metrics.get(a).avg_latency_ms, 2),
                "consecutive_failures": self.metrics.get(a).consecutive_failures,
            }
            for a in self.agents
        }
