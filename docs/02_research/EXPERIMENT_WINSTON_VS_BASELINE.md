# Experimento: Winston vs Baseline
## DOF Mesh Legion — Cyber Paisa / Enigma Group

> **Status:** Fase 1 completada (local + API) | Fase 2 en curso (web models)
> **Fecha inicio:** 27 mar 2026 | **Última actualización:** 28 mar 2026

---

## Objetivo

Medir el impacto cuantitativo del **Winston Communication Framework** sobre la calidad de respuestas de LLMs, usando el **CQ Score** como métrica principal.

Hipótesis: Un sistema prompt estructurado con formato Winston (indicador → impacto → evidencia → acción) mejora la calidad de comunicación en ≥ 30 puntos CQ vs. baseline libre.

---

## El Framework Winston

Basado en el trabajo de **Patrick Winston (MIT)** sobre comunicación efectiva. Principio central: la calidad de la comunicación determina el impacto del conocimiento.

### Formato obligatorio (4 partes)

```
[INDICADOR] Conclusión directa en primera línea.
Esto significa que [impacto concreto en el sistema/usuario].
Evidencia: [datos concretos — números, métricas, porcentajes].
Siguiente paso: [acción específica y ejecutable].
```

### Indicadores disponibles
- `[PROVEN]` — verificado formalmente (Z3, tests)
- `[BLOCKED]` — bloqueado por governance
- `[WARNING]` — condición de riesgo
- `[PASS]` — validación exitosa
- `[FAIL]` — validación fallida
- `[DONE]` — tarea completada

### Prohibido
- "Aquí está el resultado..."
- "Espero que sea útil"
- "Si necesitas más información"
- "Como asistente de IA..."

---

## CQ Score — Métrica de Calidad

**Communication Quality Score (0-100)** — determinístico, sin LLM.

| Componente       | Pts | Criterio |
|------------------|-----|----------|
| Claridad         | 25  | Indicador en primera línea (15) + longitud óptima (10) |
| Relevancia       | 25  | "Esto significa que..." presente |
| Estructura       | 20  | Indicadores + markdown (headers, bullets) |
| Sorpresa         | 15  | Marcadores de hallazgo inesperado |
| Cierre accionable| 15  | "Siguiente paso:" presente, sin filler phrases (-10) |

**Score compuesto total (0-100):**
```
Total = CQ×0.40 + Componentes×0.40 + Keywords×0.20
```

Donde Componentes = promedio binario de 5 checks Winston.

---

## Infraestructura del Experimento

### Archivos

```
experiments/winston_vs_baseline/
  ├── experiment_runner.py        # Runner local + API (Fase 1)
  ├── web_experiment_prompts.json # Prompts + respuestas web (Fase 2)
  └── web_experiment_scorer.py   # Scorer para respuestas web

logs/experiments/winston_vs_baseline/
  ├── experiment_20260328_003941.jsonl  # v1 — solo Ollama local
  ├── experiment_20260328_004212.jsonl  # v2 — + API models
  ├── experiment_20260328_004941.jsonl  # v3 — + few-shot + anchor (REFERENCIA)
  ├── report_20260328_003941.json
  ├── report_20260328_004212.json
  └── report_20260328_004941.json       # ← Resultados canónicos Fase 1
```

### Niveles de dificultad

| Nivel        | Tarea | Max tokens |
|--------------|-------|------------|
| BASIC        | Descripción factual del proyecto | 200 |
| INTERMEDIATE | Análisis crítico + mejoras medibles | 350 |
| ADVANCED     | Planificación estratégica compleja con trade-offs | 500 |

### Teams

- **Team BLUE**: System prompt Winston + few-shot examples + anchor al final
- **Team RED**: Baseline — "sé útil y detallado", mismo contexto

---

## Resultados Fase 1 — Experimento v3 (Referencia Canónica)

**Fecha:** 28 mar 2026 | **ID:** `20260328_004941`
**Mejoras sobre v1/v2:** few-shot examples + anchor al final de messages

### Ranking completo

| Posición | Modelo | BLUE | RED | Delta | Tipo |
|----------|--------|------|-----|-------|------|
| 1 | gemma2:9b | 86.0 | 32.0 | **+54.0** | Local |
| 2 | dof-voice-fast (gemma2) | 84.7 | 34.7 | **+50.0** | Local custom |
| 3 | dof-analyst | 80.7 | 30.7 | **+50.0** | Local custom |
| 4 | dof-coder | 81.3 | 32.0 | **+49.3** | Local custom |
| 5 | DeepSeek-V3 (API) | 80.7 | 32.0 | **+48.7** | API |
| 6 | dof-guardian | 82.7 | 36.0 | **+46.7** | Local custom |
| 7 | dof-voice | 79.3 | 35.3 | **+44.0** | Local custom |
| 8 | SambaNova-DSV3 | 81.3 | 38.7 | **+42.7** | API |
| 9 | local-agi-m4max | 78.7 | 36.0 | **+42.7** | Local custom |
| 10 | MiniMax-M2.1 | 67.3 | 37.3 | **+30.0** | API |
| 11 | DeepSeek-R1 | 18.0 | 8.0 | +10.0 | API (reasoning) |
| — | Gemini-2.0Flash | 16.0 | 16.0 | 0 | API (error/empty) |
| — | Groq-Llama | 12.0 | 12.0 | 0 | API (key error) |
| — | Cerebras | 12.0 | 12.0 | 0 | API (key error) |
| — | NVIDIA-NIM | 12.0 | 12.0 | 0 | API (credits) |

### Hallazgos clave

1. **gemma2:9b es el campeón local de Winston** — 86/100 CQ con framework vs 32 sin él (+54pts)
2. **few-shot + anchor elimina ambigüedad** — gemma2 pasó de ~60 a 86 al agregar ejemplos concretos
3. **DeepSeek-V3 supera a todos los APIs** — 80.7 BLUE, latencia ~2s (streaming)
4. **R1/Reasoner son inmunes al formato Winston** — generan `<think>` tokens, ignoran instrucciones externas. Delta +10 se debe a contenido, no formato.
5. **MiniMax-M2.1 adopción parcial** — 67.3 BLUE. Entiende Winston pero no ancla la conclusión en primera línea consistentemente.
6. **Groq/Cerebras/NVIDIA vacíos** — endpoints o keys incorrectos al momento del experimento (12.0 = score mínimo por no_filler=True)

### Análisis de componentes (BLUE team, top modelos)

| Modelo | Indicador | Impacto | Evidencia | Acción | Sin-relleno |
|--------|-----------|---------|-----------|--------|-------------|
| gemma2:9b | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 |
| dof-voice-fast | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 |
| DeepSeek-V3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 |
| SambaNova-DSV3 | ✓ 3/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 | ✓ 3/3 |
| MiniMax-M2.1 | ✗ 1/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 | ✓ 3/3 |

---

## Técnicas que mejoran adopción Winston

### Nivel básico (system prompt solo)
- Mejora ~20-30pts en modelos instructed
- Suficiente para modelos fuertes (GPT-4, Gemini Pro, Claude)

### Nivel avanzado (few-shot + anchor)
- **Few-shot**: Incluir 1-2 ejemplos de respuesta correcta en el formato correcto
- **Anchor al final**: Repetir el formato requerido como último mensaje del sistema al final de `messages[]`
- Mejora adicional de ~20pts sobre system prompt solo

```python
# Ejemplo de anchor al final de messages:
messages = [
    {"role": "system", "content": SYSTEM_BLUE},
    {"role": "user",   "content": FEW_SHOT_EXAMPLE_USER},
    {"role": "assistant", "content": FEW_SHOT_EXAMPLE_RESPONSE},
    {"role": "user",   "content": actual_task},
    {"role": "system", "content": ANCHOR_BLUE},  # ← anchor al final
]
```

### Por qué R1 es inmune
DeepSeek-R1 y modelos reasoner generan un bloque `<think>...</think>` antes de la respuesta. Durante el thinking ignoran instrucciones de formato. La respuesta final tiende a ser narrativa. Solución: usar R1 como thinker, pasar su output por gemma2 como formatter.

---

## Fase 2 — Web Models (En curso)

### Modelos objetivo

| Modelo | Interfaz | Estado |
|--------|----------|--------|
| ChatGPT-4o | chat.openai.com | Pendiente |
| ChatGPT-o3 | chat.openai.com | Pendiente |
| Gemini-2.5Pro | gemini.google.com | Pendiente |
| Gemini-2.5Flash | gemini.google.com | Pendiente |
| Kimi-K2 | kimi.ai | Pendiente |
| GLM-4.5 | chatglm.cn | Pendiente |
| MiniMax-M2 | hailuoai.com | Pendiente |
| Perplexity-Sonar | perplexity.ai | Pendiente |
| Claude-3.7-Sonnet | claude.ai | Pendiente |
| DeepSeek-V3-web | chat.deepseek.com | Pendiente |
| Mistral-Large | chat.mistral.ai | Pendiente |
| Grok-3 | x.ai/grok | Pendiente |

### Procedimiento manual

Para cada modelo:

**BLUE (Con Winston):**
1. Nueva conversación (sesión limpia, sin historial)
2. Pegar system prompt BLUE completo del JSON
3. Enviar task BASIC → copiar respuesta al JSON
4. Enviar task INTERMEDIATE → copiar respuesta
5. Enviar task ADVANCED → copiar respuesta

**RED (Baseline):**
1. Nueva conversación limpia
2. Pegar system prompt RED
3. Repetir las 3 tasks → copiar respuestas

### Scorer automático

```bash
# Ver resultados parciales (a medida que llenas respuestas)
python3 experiments/winston_vs_baseline/web_experiment_scorer.py

# Guardar resultados JSON
python3 experiments/winston_vs_baseline/web_experiment_scorer.py --json

# Ranking combinado web + local
python3 experiments/winston_vs_baseline/web_experiment_scorer.py --merge
```

---

## Implicaciones para DOF Mesh

### Integración actual

Winston ya está integrado en:
- `config/agents.yaml` — campo `communication_framework: "winston-v1"` en 17 agentes
- `agents/*/SOUL.md` — tabla 5S adaptada al rol en 9 SOULs
- `core/supervisor.py` — `evaluate_communication_quality()` + campo `communication_quality` en `SupervisorVerdict`
- Score compuesto del supervisor: `Q(0.35) + A(0.20) + C(0.20) + F(0.10) + CQ(0.15)`

### Valor demostrado

Con solo cambiar el system prompt:
- gemma2:9b: **+54pts** de calidad de comunicación
- Todos los modelos custom DOF: **+42-50pts**
- Sin cambiar el modelo, sin fine-tuning, sin costo adicional

Esto significa que el framework Winston actúa como **multiplicador de capacidad** — el mismo modelo, con instrucciones correctas, produce outputs más claros, accionables y verificables.

---

## Próximos pasos

1. **Completar Fase 2** — llenar respuestas web, correr scorer, actualizar tabla de resultados
2. **Pipeline R1 → gemma2** — R1 razona, gemma2 formatea (combina profundidad + claridad)
3. **Winston en voz** — sistema voice_v4 ya usa el formato en su system prompt
4. **Experimento v4** — testar variantes del anchor (posición, extensión, formato)
5. **Publicar resultados** — como parte del DOF SDK documentation o blog post técnico

---

*Documentación generada: 28 mar 2026 | DOF Mesh Legion v0.5.0*
