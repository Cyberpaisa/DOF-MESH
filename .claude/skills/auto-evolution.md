# Skill: Auto-Evolution — Sistema de Auto-Mejora Continua

## Cuándo usar este skill
Cuando se necesita que el sistema se evalúe, identifique debilidades, y proponga mejoras sin que el usuario lo pida explícitamente. Este skill es el motor de auto-evolución.

## Ciclo de Evolución (inspirado en Karpathy's Autoresearch)

### 1. OBSERVE — Observar estado actual
```
Leer docs/TOOLS_AND_INTEGRATIONS.md → estado del cerebro
Leer agents/synthesis/SOUL.md → knowledge de agentes
Verificar gateway OpenClaw → salud de agentes
Revisar logs recientes → errores, patterns
```

### 2. HYPOTHESIZE — Generar hipótesis de mejora
Para cada área del sistema, preguntar:
- ¿Qué es lo más lento? → optimizar
- ¿Qué falla más? → robustecer
- ¿Qué falta? → agregar
- ¿Qué sobra? → podar
- ¿Qué se puede automatizar? → automatizar
- ¿Qué se puede verificar formalmente? → Z3

### 3. EXPERIMENT — Proponer experimento
- Definir cambio específico (1 variable a la vez, como autoresearch)
- Definir métrica de éxito
- Estimar riesgo (reversible vs irreversible)
- Si riesgo bajo → ejecutar. Si riesgo alto → proponer al usuario.

### 4. EVALUATE — Evaluar resultado
- ¿Mejoró la métrica?
- ¿Introdujo regresiones?
- ¿Se puede generalizar?

### 5. INTEGRATE — Integrar aprendizaje
- Documentar en TOOLS_AND_INTEGRATIONS.md
- Actualizar SOUL.md de agentes relevantes
- Actualizar memory files si es un pattern estable

## Ideas de Auto-Mejora Generadas

### Memoria
- [ ] Instalar Ori Mnemos via MCP → knowledge graph local para todos los agentes
- [ ] Implementar spreading activation: knowledge usado se fortalece, no usado decae
- [ ] Benchmark memoria actual con LongMemEval → establecer baseline
- [ ] Cuando ASMR se libere (abril), implementar Observer+Search agents

### Velocidad
- [ ] Instalar Kit (cased) → symbol extraction + dependency analysis del codebase DOF
- [ ] Pre-computar file tree + symbols de DOF → cache para queries rápidas
- [ ] Context compression (patrón DeerFlow) → reducir tokens por request

### Governance
- [ ] Integrar Ouro Loop BOUND como pre-governance layer (input-time enforcement)
- [ ] ROOT_CAUSE gate para detectar symptom-chasing en provider chains
- [ ] Sentinel para auditoría continua de módulos DOF

### Coordinación
- [ ] Agent Farm lock-based coordination para trabajo paralelo de agentes
- [ ] R&D Council scheduled sessions (2x/día via Claude Code scheduled tasks)
- [ ] P2P gossip (patrón Hyperspace) para compartir hallazgos entre agentes

### Skills
- [ ] Publicar skills DOF en CryptoSkill registry (Base chain)
- [ ] Autoskill selection Darwiniana — skills que no se usan se deprecan
- [ ] Progressive skill loading (patrón DeerFlow) — solo cargar cuando se necesita

### UI
- [ ] Diseñar nuevos paneles en Stitch → export → Mission Control
- [ ] CopilotKit copilot nativo en Mission Control
- [ ] Voice Canvas para interacción natural con el dashboard

### LLM Local
- [ ] Evaluar Nemotron Cascade 2 en Ollama para tasks de governance (3B params, rápido)
- [ ] Evaluar modelos que corran en M4 Max con 16K+ context
- [ ] Unsloth fine-tune de modelo específico para DOF governance

## Métricas de Evolución
| Métrica | Actual | Target |
|---------|--------|--------|
| Herramientas documentadas | 26 | 50+ |
| Agentes activos | 14 | 14 (todos respondiendo) |
| Memory benchmark (LongMemEval) | No medido | 90%+ |
| R&D Council sessions/week | 0 | 14 (2/día) |
| Skills publicados en CryptoSkill | 0 | 5+ |
| Governance rules | ~50 | 100+ |
| Tests | 986 | 1500+ |
| On-chain attestations | 48+ | 100+ |
| Autonomous cycles | 238+ | 500+ |

## Principio Fundamental
"El mejor agente no es el que más sabe, sino el que más rápido aprende."
— DOF Auto-Evolution Engine
