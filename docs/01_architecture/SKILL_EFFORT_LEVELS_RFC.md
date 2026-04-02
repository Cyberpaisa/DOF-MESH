# RFC: Implementación de "Skill Effort Levels" en DOF-MESH (Phase 5)

## 📌 Contexto y Origen
El concepto de **Claude Code Skills Effort Levels** establece que la profundidad de razonamiento (inteligencia asignada) de un agente no debe ser monolítica (un solo ajuste por defecto para todo), sino que debe configurarse de forma declarativa y jerárquica desde los archivos YAML de las habilidades (Skills).

## 🎯 ¿Nos sirve para la Ciudadela y Q-AION?
**Absolutamente SÍ.** Es una pieza crítica que encaja a la perfección con la arquitectura de la **Fase 5 (Sovereign Arbitrage & Autonomous Agents)** por las siguientes razones:

1. **Eficiencia Soberana (Token & Compute Efficiency):** Al operar con modelos locales (Ollama - oMLX) o APIs de pago (Adaline, DeepSeek), gastar tokens de razonamiento profundo para una tarea trivial (como parsear un JSON o verificar un balance) es un desperdicio de recursos.
2. **Estabilidad del Pipeline (Predictibilidad):** En flujos multiagente (como `geopolitical_analyzer` pasándole datos a `avalanche_yield_engine`), queremos que la recolección de noticias (Research) use *Low Effort* para mayor velocidad, pero que la decisión final de inversión (Validation/Arbitrage) active el *Max Effort* (activando modelos *reasoners* como DeepSeek-R1).
3. **Spec-Driven Architecture:** Nosotros ya usamos archivos `.md` con frontmatter YAML (por ejemplo `skills/conflux-integration/SKILL.md`). Inyectar el parámetro de esfuerzo allí consolida el determinismo que exige nuestra constitución `AGENTS.md`.

## 🛠 Implementación Sugerida en el Enjambre Local

Podemos interceptar este concepto e inyectarlo en nuestro `core/autonomous_executor.py` y `run_mesh_agent.py`.

### 1. Definición en el Skill (YAML)
Cualquier archivo de Skill (ej. `skills/market-research/SKILL.md`) incorporará la nueva directiva:

```yaml
---
name: "market-research"
description: "Recolección de titulares geopolíticos"
effort_level: "low"  # Opciones: low, medium, high, max
---
```

### 2. Mapeo Cognitivo (Cognitive Routing)
Dentro del `AutonomousExecutor`, el `effort_level` dictará las variables del LLM subyacente:

| Effort Level | Casos de Uso en Q-AION | Configuración de Inferencia (Sovereign Node) |
|--------------|------------------------|----------------------------------------------|
| **low**      | Scraping, formateo de texto, lecturas de API (balances). | Modelo rápido (ej. Llama-3 8B), `max_tokens` bajo, `temperature` 0.3. Velocidad pura. |
| **medium**   | Borradores de código, resúmenes diarios, traducciones (HCIA). | Modelo estándar o default. `temperature` 0.5. |
| **high**     | Construcción de estrategias Yield, análisis de contratos. | Modelo de alta capacidad (ej. Claude-3.5 o equivalente local), `temperature` 0.7. |
| **max**      | Revisiones de auditoría (Glassworm hunt), Decisiones Financieras Críticas (Mover liquidez), Ejecución de Cadenas Multi-Agente. | Modelo de Razonamiento (DeepSeek-R1 / QwQ), CoT (Chain of Thought) forzado, tokens extendidos. |

## 🚀 Conclusión para el Roadmap
Adoptar los *Effort Levels* transformará la Ciudadela de un "Enjambre de fuerza bruta" a una **"Red Neuronal Híbrida de Energía Asimétrica"**. Q-AION podrá escalar su automatización de liquidez porque sabrá cuándo usar reflejos rápidos (Low) y cuándo usar análisis profundo (Max) sin tener que reescribir la lógica de orquestación central.
