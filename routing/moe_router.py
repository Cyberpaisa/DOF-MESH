"""
MoE Router — Mixture of Experts Router con contexto real.

Decide qué modelo/crew usar basándose en:
  - Intento (palabras clave en la tarea)
  - Contexto recuperado del vault (Obsidian)
  - Estado del StateManager (historial, tokens)

Reglas de prioridad:
  1. SAM / trading / finance → reasoner (DeepSeek/qwen3)
  2. code / script / python / bug → coder (Ollama dof-coder)
  3. report / summary / weekly → flash (Gemini/GLM-4)
  4. search / find / busca → hunter
  5. memoria llena (tokens > umbral) → compressor
  6. default → general (llama3.3/minimax)

Sin dependencias externas.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.state_manager import StateManager

logger = logging.getLogger("routing.moe_router")

# ── Reglas de Routing ──────────────────────────────────────────────────

_RULES: list[tuple[str, list[str]]] = [
    # (modelo, [palabras_clave])
    ("reasoner", [
        "sam", "trading", "arbitrage", "finance", "financiero",
        "defi", "token", "precio", "mercado", "portfolio",
        "z3", "verificación formal", "proof", "invariant",
    ]),
    ("coder", [
        "code", "código", "python", "script", "bug", "error",
        "función", "function", "clase", "class", "test",
        "implementar", "implement", "refactor", "fix",
        "dockerfile", "docker", "api", "endpoint",
    ]),
    ("flash", [
        "report", "reporte", "resumen", "summary", "weekly",
        "semanal", "diario", "daily", "newsletter", "blog",
        "thread", "tweet", "contenido", "content", "pitch",
        "narrativa", "narrative",
    ]),
    ("hunter", [
        "busca", "encuentra", "search", "find", "qué dice",
        "tengo notas", "revisa el vault", "contexto de",
        "qué sé sobre", "what do i know", "lookup",
    ]),
    ("compressor", [
        "compress", "comprimir", "cpr", "resume", "resumir",
        "guardar sesión", "save session", "memoria llena",
    ]),
]


def route(
    task: str,
    context: str = "",
    state: "StateManager | None" = None,
) -> str:
    """
    Selecciona el modelo óptimo para una tarea.

    Args:
        task: Instrucción del usuario.
        context: Texto recuperado del vault (Obsidian / CPR resume).
        state: StateManager para verificar si se necesita compresión.

    Returns:
        Nombre del modelo/modo: 'reasoner' | 'coder' | 'flash' | 'hunter' |
                                 'compressor' | 'general'
    """
    # Compresión forzada si el contexto está lleno
    if state is not None and state.needs_compression():
        logger.info("Router: contexto lleno → compressor")
        return "compressor"

    # Texto combinado para análisis
    combined = (task + " " + context).lower()

    # Evaluar reglas por prioridad
    for model, keywords in _RULES:
        if any(kw in combined for kw in keywords):
            logger.info("Router: '%s' → %s (keyword match)", task[:50], model)
            return model

    # Default
    logger.info("Router: '%s' → general (no match)", task[:50])
    return "general"


def get_model_config(model_name: str) -> dict:
    """
    Retorna configuración del modelo para el ejecutor.
    Mapea nombres lógicos a modelos concretos disponibles.
    """
    configs = {
        "reasoner": {
            "model_name": "reasoner",
            "ollama_model": "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M",
            "temperature": 0.4,
            "description": "🧠 Qwen3 30B abliterated — razonamiento complejo sin censura",
            "crew_hint": "enigma_audit",
        },
        "coder": {
            "model_name": "coder",
            "ollama_model": "dof-coder:latest",
            "temperature": 0.2,
            "description": "💻 dof-coder 14B — especializado en código",
            "crew_hint": "code_review",
        },
        "analyst": {
            "model_name": "analyst",
            "ollama_model": "dof-analyst:latest",
            "temperature": 0.5,
            "description": "📊 dof-analyst 14B — análisis y datos",
            "crew_hint": "data_analysis",
        },
        "guardian": {
            "model_name": "guardian",
            "ollama_model": "dof-guardian:latest",
            "temperature": 0.2,
            "description": "🛡️ dof-guardian 14B — seguridad y gobernanza",
            "crew_hint": "enigma_audit",
        },
        "flash": {
            "model_name": "flash",
            "ollama_model": "gemma2:9b",
            "temperature": 0.7,
            "description": "⚡ Gemma2 9B — respuesta rápida",
            "crew_hint": "content",
        },
        "general": {
            "model_name": "general",
            "ollama_model": "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M",
            "temperature": 0.6,
            "description": "🌐 Qwen3 30B — general purpose élite",
            "crew_hint": "research",
        },
        "hunter": {
            "model_name": "hunter",
            "ollama_model": "phi4:latest",
            "temperature": 0.1,
            "description": "🔍 phi4 14B — búsqueda determinística",
            "crew_hint": None,
        },
        "compressor": {
            "model_name": "compressor",
            "ollama_model": "phi4:latest",
            "temperature": 0.1,
            "description": "🗜️ phi4 14B — compresión CPR",
            "crew_hint": None,
        },
    }
    return configs.get(model_name, configs["general"])


# ── Test standalone ─────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        "Analiza el SAM test y el arbitrage de APEX",
        "Escribe un script Python para limpiar los logs",
        "Genera el reporte semanal del proyecto DOF-MESH",
        "Busca qué notas tengo sobre el router MoE",
        "compress la sesión actual",
        "Hola, cómo estás?",
    ]

    print("=== MoE Router Tests ===\n")
    for task in tests:
        model = route(task)
        config = get_model_config(model)
        print(f"Task:  {task[:60]}")
        print(f"Model: {model} ({config['description']})")
        print()
