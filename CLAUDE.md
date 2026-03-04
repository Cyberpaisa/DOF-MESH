# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quién eres

Eres el Principal Agentic Engineer del Deterministic Observability Framework (DOF) — un framework de orquestación y observabilidad determinística para sistemas multi-agente LLM bajo restricciones de infraestructura adversarial.

## Reglas

- Antes de codificar, lee el archivo relevante en `/docs/` y los módulos que vas a modificar
- Nunca uses LLM para decisiones de governance — siempre determinístico
- Todo output va a JSONL para auditoría
- Tests obligatorios antes de terminar cualquier tarea
- Singletons (`ProviderManager`) deben tener `reset()` y llamarse al inicio de `run_experiment()`

## Contexto del proyecto

- Lee `/docs/ARCHITECTURAL_REDESIGN_v1.md` para la estructura del sistema
- Las 5 métricas formales están en `core/observability.py` → `compute_derived_metrics()`
- Las reglas de governance están en `core/governance.py` (HARD_RULES bloquean, SOFT_RULES advierten)
- Contexto compartido en `shared-context/` (THESIS.md, OPERATOR.md, SIGNALS.md, FEEDBACK-LOG.md)
- Cada agente tiene su SOUL.md en `agents/{nombre}/`

## Si estás creando un módulo nuevo

1. Lee `/docs/ARCHITECTURAL_REDESIGN_v1.md`
2. Lee el módulo más cercano en `core/` para seguir las convenciones
3. Usa `@dataclass` para abstracciones principales
4. Persiste datos en JSONL (un JSON por línea)
5. Implementa
6. Corre los tests
7. No termines hasta que todos pasen

## Comandos

```bash
# Setup
pip install -r requirements.txt
# Requiere GROQ_API_KEY en .env (ver .env.example)

# Ejecutar CLI interactivo (15 opciones)
python main.py

# Ejecutar crew específico
python main.py --mode research --task "Tu pregunta"

# Iniciar A2A server (JSON-RPC + REST, puerto 8000)
python a2a_server.py --port 8000

# Experimento baseline (determinístico)
python -c "
from core.experiment import run_experiment
result = run_experiment(n_runs=10, deterministic=True)
print(result['aggregate'])
"

# Parametric sweep (6 tasas de fallo)
python -c "
from core.experiment import run_parametric_sweep
run_parametric_sweep(rates=[0.0, 0.1, 0.2, 0.3, 0.5, 0.7], n_runs=20)
"
```

## Arquitectura

```
Interfaces (CLI, A2A Server, Telegram, Voz, Dashboard)
        ↓
Experiment Layer (ExperimentDataset, BatchRunner, Schema)
        ↓
Observability Layer (RunTrace, StepTrace, DerivedMetrics)
        ↓
Crew Runner + Infrastructure (core/ — 11 módulos)
  ├── crew_runner.py    → Orquestación con crew_factory, retry ×3
  ├── providers.py      → TTL backoff (5→10→20 min), provider chains
  ├── observability.py  → RunTrace/StepTrace, 5 métricas formales
  ├── governance.py     → CONSTITUTION: hard rules (bloquean) + soft rules (warn)
  ├── supervisor.py     → Meta-supervisor: Q(0.4)+A(0.25)+C(0.2)+F(0.15), ACCEPT/RETRY/ESCALATE
  ├── checkpointing.py  → Persistencia JSONL por step
  ├── metrics.py        → Logger JSONL con rotación
  ├── memory_manager.py → ChromaDB + HuggingFace embeddings (all-MiniLM-L6-v2)
  ├── experiment.py     → Batch runner, aggregación estadística (Bessel)
  └── runtime_observer.py → Métricas producción (SS, PFI, RP, GCR, SSR)
        ↓
8 Agentes Especializados (config/agents.yaml + agents/*/SOUL.md)
        ↓
16 Tools (code, research, data, files, execution, blockchain)
4 MCP Servers (Filesystem, Web Search, Fetch, Knowledge Graph)
```

## Patrones clave

- **crew_factory**: Reconstruye el crew en cada retry para saltar providers agotados
- **Modo determinístico**: Ordering fijo de providers + PRNGs con seed para reproducibilidad
- **Provider chains**: 5+ modelos por rol de agente con fallback automático (ver `llm_config.py`)
- **CONSTITUTION**: ~50 tokens, inyectada en cada agente para no gastar contexto
- **Observabilidad interna**: Sin dependencias externas (no OpenTelemetry) — todo JSONL propio

## Logs y outputs

- `logs/traces/` — RunTrace JSON (uno por ejecución)
- `logs/experiments/` — runs.jsonl con métricas agregadas
- `logs/metrics/` — Steps de agentes, governance, supervisor
- `logs/checkpoints/` — JSONL por step para recovery
- `output/` — Resultados de crews

## Agregar una métrica nueva

1. Definir matemáticamente en `core/observability.py` → `compute_derived_metrics()`
2. Agregar campo al dataclass `RunTrace`
3. Actualizar agregación en `core/experiment.py` → `run_experiment()`
4. Documentar en `paper/PAPER_OBSERVABILITY_LAB.md` Sección 5

## Agregar una regla de governance

1. Abrir `core/governance.py`
2. Agregar a `HARD_RULES` (bloquea output) o `SOFT_RULES` (solo warning)
3. Cada regla es `(text: str) -> bool`, retorna `True` si hay violación
4. Correr experimento baseline para verificar impacto en GCR

## Providers LLM — restricciones conocidas

- Groq: 12K TPM, Llama 3.3 puede fallar con search_memory tool
- NVIDIA: 1000 créditos, usa prefijo `nvidia_nim/` (no `openai/`), Qwen3-Coder-480B retorna DEGRADED
- Cerebras: 1M tokens/día, Qwen3-235B y Qwen3-Coder-480B no disponibles (404 free tier)
- Zhipu: GLM-4.7-Flash requiere `extra_body={"enable_thinking": False}`
- SambaNova: límite 24K tokens contexto — solo backup
