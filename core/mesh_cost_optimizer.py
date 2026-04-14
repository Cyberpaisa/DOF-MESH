from __future__ import annotations
"""
DOF Mesh - Autonomous Scaling: Cost Optimizer
Implementación de Phase 9 para calcular y aprovisionar dinámicamente el nodo
mas eficiente según el requerimiento de tokens, costo y especialidad de la tarea.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Dict, Optional, Any

# Ruta al registry local de nodos en el file system protocol P2P
NODES_JSON_PATH = Path("logs/mesh/nodes.json")


@dataclass
class CostOptimizer:
    """
    Singleton que audita y toma decisiones financieras sobre el enrutamiento
    de tareas en el DOF Mesh (Phase 9).
    """
    _instance: ClassVar[Optional["CostOptimizer"]] = None
    
    # Precios fijos en USD por cada 1,000 tokens (Input + Output mix)
    # Definidos por el Commander P2P
    PRICING_TABLE: ClassVar[Dict[str, float]] = {
        "deepseek": 0.001,
        "cerebras": 0.0,
        "sambanova": 0.0,
        "nvidia": 0.0,
        "zhipu": 0.0,   # GLM-5 provider
        "ollama": 0.0   # Local-qwen
    }
    
    # Prioridad de desempate para nodos de costo $0.0
    # Preferimos inferencia local sobre nube gratis si la especialidad lo permite
    ZERO_COST_PRIORITY: ClassVar[list[str]] = [
        "ollama",      # 1. Local (mayor privacidad, 0 dependencia)
        "cerebras",    # 2. Ultra-rápido Llama 3
        "sambanova",   # 3. Deep Research Llama 3
        "zhipu",       # 4. GLM-5 Fast response
        "nvidia"       # 5. General workload
    ]

    # Caché temporal para no leer el FS si no es necesario en bench tests
    _nodes_cache: Dict[str, Any] = field(default_factory=dict, init=False)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def _load_nodes(self) -> Dict[str, Any]:
        """Carga el registro de nodos desde el filesystem."""
        if not NODES_JSON_PATH.exists():
            return self._nodes_cache
            
        try:
            with NODES_JSON_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._nodes_cache = data
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return self._nodes_cache

    def get_cheapest_node(self, context_length: int, task_type: str) -> str:
        """
        Determina el node_id más barato y capaz de solventar la tarea.
        Resuelve empates de precio ($0.0) haciendo match con especialidad
        y finalmente por la política de prioridades de Zero Cost.
        """
        nodes = self._load_nodes()
        if not nodes:
            # Fallback a local-agi-m4max asumiendo que es soberano y siempre existirá
            return "local-agi-m4max"
            
        viable_nodes = []
        for node_id, data in nodes.items():
            # Filtro 1: Debe soportar el largo de contexto requerido
            if data.get("context_window", 0) >= context_length:
                # El estado no importa estrictamente porque Phase 9 usa
                # el AutoProvisioner para prenderlo, pero asumimos que filtraremos
                viable_nodes.append((node_id, data))
                
        if not viable_nodes:
            # Si ninguna ventana de contexto estricta coincide, usar el que tenga más
            sorted_by_max_ctx = sorted(nodes.items(), key=lambda x: x[1].get("context_window", 0), reverse=True)
            return sorted_by_max_ctx[0][0] if sorted_by_max_ctx else "local-agi-m4max"
            
        # Puntuación combinada (Costo, Especialidad y Prioridad)
        # Buscamos MINIMIZAR el score.
        scored_nodes = []
        for node_id, data in viable_nodes:
            provider = data.get("provider", "ollama").lower()
            specialty = data.get("specialty", "").lower()
            
            # Costo base
            cost_per_1k = self.PRICING_TABLE.get(provider, 0.0)
            
            # Penalidad para desempatar los gratuitos
            priority_penalty = 0.0000001 * self.ZERO_COST_PRIORITY.index(provider) if provider in self.ZERO_COST_PRIORITY else 0.0000009
            
            # Bono por emparejamiento de especialidad estricto (pesa más que la prioridad base)
            specialty_bonus = 0.0
            if task_type.lower() in specialty or specialty in task_type.lower():
                specialty_bonus = -0.0000005  # Resta contundente para ganar la prioridad

                
            final_score = cost_per_1k + priority_penalty + specialty_bonus
            scored_nodes.append((final_score, node_id))
            
        scored_nodes.sort()
        return scored_nodes[0][1]