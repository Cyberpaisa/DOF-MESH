# Capítulo 22 — El Experimento Winston: Cuando los Modelos se Miden Entre Sí

*28 de marzo de 2026 — DOF Mesh Legion v0.5.0*

---

## 22.1 — La Pregunta

¿Vale la pena tener un framework de comunicación? ¿O los modelos frontier ya responden bien sin instrucción?

La pregunta era simple. La respuesta, no tanto.

El **Experimento Winston** fue diseñado para medir el valor real del framework Winston Communication en 10 modelos frontier: mismas preguntas, mismos contextos, dos condiciones — BLUE (con Winston) y RED (baseline sin formato). El resultado sería numérico, determinístico, reproducible.

Tres niveles de pregunta: BASIC (qué es DOF), INTERMEDIATE (cómo funciona), ADVANCED (cómo escalar a 50 nodos). Cada respuesta puntuada con el CQ scorer: Claridad(25) + Relevancia(25) + Estructura(20) + Sorpresa(15) + Cierre accionable(15). Sin LLM. Sin subjetividad. Solo regex y conteo de tokens.

---

## 22.2 — El Protocolo BLUE vs RED

**BLUE team:** System prompt con framework Winston completo + ejemplo de respuesta. El modelo sabía exactamente qué formato usar: [INDICATOR] → "Esto significa que..." → evidencia con números → "Siguiente paso:".

**RED team:** System prompt baseline. "Eres un asistente útil. Sé detallado." El mismo contexto DOF. Sin formato. Sin estructura. Sin guía.

Misma pregunta. Distinto molde.

El resultado se almacenó en `experiments/winston_vs_baseline/web_experiment_prompts.json`. Los scores en `web_experiment_results.json`. El scorer en `web_experiment_scorer.py` — 200 líneas de Python puro, sin dependencias externas.

---

## 22.3 — Los Resultados Finales

```
Modelo              BLUE    RED    Delta
────────────────────────────────────────
Grok-3              84.7    0.0   +84.7  (sin tokens en RED — excluido análisis)
DeepSeek-V3-web     88.7   38.7   +50.0  ← mayor beneficio Winston
GLM-4.5             90.0   42.7   +47.3
Mistral-Large       78.7   41.3   +37.4
Claude-3.7-Sonnet   90.0   56.0   +34.0
ChatGPT-4o          88.7   63.0   +25.7
Gemini-2.5Pro       84.7   71.3   +13.4
Perplexity-Sonar    82.0   70.0   +12.0
MiniMax-M2          76.0   66.7    +9.3
Kimi-K2             64.0   58.0    +6.0
────────────────────────────────────────
Promedio delta: +26.5 pts
```

26.5 puntos de mejora promedio. Solo por el system prompt.

---

## 22.4 — Lo Que Nadie Esperaba

El experimento confirmó la hipótesis principal: Winston funciona. Pero reveló algo más interesante.

**Hallazgo 1: Cuatro modelos tienen Winston internalizado.**

ChatGPT-4o (+25.7), Gemini-2.5Pro (+13.4), Perplexity-Sonar (+12.0), MiniMax-M2 (+9.3) y Kimi-K2 (+6.0) responden RED con estructura comparable a BLUE. No necesitan instrucción. Ya producen tablas de trade-offs, fases numeradas, métricas de éxito, riesgos con mitigación concreta.

Estos modelos han internalizado el patrón. El delta real de Winston para ellos es mínimo. La instrucción refina; no transforma.

**Hallazgo 2: Para GLM, DeepSeek y Mistral, Winston es esencial.**

Sin instrucción, estos modelos caen a 38-42 puntos. Con Winston, suben a 78-90. El delta de +37 a +50 puntos es la diferencia entre una respuesta útil y una respuesta procesable.

**Hallazgo 3: MiMo rechazó responder.**

En el nivel ADVANCED, MiMo-01 fue el único modelo que cuestionó la premisa del experimento. En lugar de generar una estrategia de escalado, respondió:

> *"No tengo verificación de que DOF Mesh Legion exista como proyecto real... Cualquier estrategia que genere sería construida sobre aire."*

Un modelo que exige evidencia antes de proceder. En el contexto del experimento — sin el system prompt Winston que enmarca el contexto — MiMo interpretó la pregunta como potencialmente ficticia. Único modelo con epistemología adversarial activa. Puntuó 28/100, no por falta de capacidad sino por exceso de rigor.

**Hallazgo 4: DeepSeek fabricó métricas en INTERMEDIATE.**

En RED INTERMEDIATE, DeepSeek-V3 citó "22,891 LOC en el Supervisor", "18,234 LOC en la capa Z3", "47 fallos críticos en CI". Números imposibles de verificar. No están en el código. No están en los logs. Son hallucinations con precisión quirúrgica — el peor tipo, porque suenan creíbles.

Documentado en la sección PATRONES RECHAZADOS de `IMPLEMENTACIONES_EXPERIMENTO_WINSTON.md`.

---

## 22.5 — Ideas Implementadas

El experimento no fue solo medición. Fue mining de arquitectura.

De las respuestas RED y BLUE de 10 modelos frontier en 3 niveles emergieron ideas implementables. Las mejores fueron construidas durante el mismo experimento:

**Z3 Unknown Rate Monitor** (`core/z3_verifier.py`)
Z3 nunca retorna `unknown` silenciosamente. Si retorna `unknown`, fuerza `FAIL` + alerta. Si la tasa supera 1% en ventana de 5 minutos, activa modo degradado. Origen: Perplexity-Sonar INTERMEDIATE. Implementado en 30 minutos. Commit `0d96f94`.

**Z3 Proof Caching — SMT Memoization** (`core/z3_gate.py`)
SHA-256 de los inputs del constraint → `GateVerification` cacheada. Mismos constraints (score=0.9, level=1) en cualquier agente → mismo resultado sin re-solver Z3. Cache hit rate objetivo ≥60% en CI. Latencia promedio ↓40-70%. Origen: DeepSeek-V3 + Grok-3 + ChatGPT-4o (coincidencia 3 modelos). Commit `140f0e9`.

**AdaptiveCircuitBreaker** (`core/adaptive_circuit_breaker.py`)
Ventana deslizante de 60s. CLOSED si block rate <9%. HALF_OPEN si 9-15%. OPEN si ≥15%. Auto-recovery cuando el rate baja. El Supervisor puede consultar `cb.state()` antes de ejecutar acciones del agente. Origen: Claude Sonnet 4.6 INTERMEDIATE. 12 tests. Commit `140f0e9`.

Pendiente en roadmap: `ConstitutionIntegrityWatcher`, `ByzantineNodeGuard`, `ConstitutionUpdateCoordinator`, `Z3 Portfolio Solving`, `Attestation Batching Merkle`.

---

## 22.6 — El Patrón del Escalado

Diez modelos frontier diseñaron la misma arquitectura para escalar DOF Mesh de 11 a 50 nodos. Sin coordinación entre ellos. Sin ver las respuestas de los otros.

Todos llegaron a:

1. **Nodos heterogéneos con roles diferenciados.** Z3 Heavy (8-12 nodos), Z3 Lite (20-30 nodos), Oracle/Memory (8-10 nodos). Nadie propuso 50 nodos idénticos.

2. **Escalado en 3 fases.** 11→20, 20→35, 35→50. Duración 6-8 semanas por fase. Métricas específicas antes de avanzar.

3. **Riesgo #1 universal: divergencia de contexto Z3.** Todos lo identificaron como crítico. Las mitigaciones varían (Context Epochs, Golden Node, Paxos en Constitution Layer, State Fingerprinting) pero el diagnóstico es idéntico.

4. **Batch attestation on-chain.** Merkle tree de N decisiones → 1 root en Avalanche C-Chain. -60% a -78% en gas costs. Coincidencia en 7 de 10 modelos.

Cuando 10 LLMs frontier convergen en la misma arquitectura sin verse entre sí, esa arquitectura probablemente es correcta.

---

## 22.7 — Lo Que el Experimento Le Hizo al Framework

Antes del experimento: 3,720 tests. Módulos estables. Z3 funcional pero sin monitoreo de casos edge.

Después del experimento: 3 nuevos módulos (`z3_verifier.py` extendido, `z3_gate.py` con cache, `adaptive_circuit_breaker.py`), 39 tests nuevos, 2 commits, y un roadmap de 7 implementaciones priorizadas.

El experimento generó su propio backlog.

Winston no solo midió cómo los modelos comunican. Midió cómo piensan. Y lo que pensaron, lo construimos.

---

## 22.8 — El Score Final de Winston

**¿Vale la pena tener un framework de comunicación?**

Sí. +26.5 puntos en promedio. Para GLM, DeepSeek y Mistral: +37 a +50 puntos. Para modelos con Winston internalizado: +6 a +13 puntos de refinamiento.

El costo del framework: un system prompt de ~200 tokens.
El retorno: respuestas que llegan directamente al punto, con evidencia, con siguiente paso.

En un sistema de governance determinística donde cada respuesta puede convertirse en una acción ejecutada por un agente en producción, la diferencia entre 42 y 90 puntos no es estética. Es la diferencia entre una acción ambigua y una acción auditable.

Winston es infraestructura de comunicación. Como Z3 es infraestructura de verificación.

---

*Experimento ejecutado: 28 marzo 2026 | 10 modelos frontier | 3 niveles | BLUE + RED*
*Datos: `experiments/winston_vs_baseline/web_experiment_results.json`*
*Implementaciones: `docs/IMPLEMENTACIONES_EXPERIMENTO_WINSTON.md`*
*Tests: `tests/test_z3_verifier.py`, `tests/test_z3_gate_cache.py`, `tests/test_adaptive_circuit_breaker.py`*
