"""
DOF Router — Capa de routing inteligente para el mesh de agentes.

Importa los componentes principales para uso externo.
"""

from .dof_router import DOFRouter
from .agent_metrics import AgentMetrics, MetricsStore
from .failover import FailoverHandler, FailoverResult

__all__ = [
    "DOFRouter",
    "AgentMetrics",
    "MetricsStore",
    "FailoverHandler",
    "FailoverResult",
]
