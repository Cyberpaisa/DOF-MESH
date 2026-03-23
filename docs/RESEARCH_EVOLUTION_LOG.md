# DOF Research Evolution Log

> Documento de aprendizaje, evoluciones e investigaciones aplicadas al sistema.
> Actualizado: 2026-03-22

---

## 1. Karpathy Autoresearch — Investigacion Autonoma de IA

**Fuente:** https://github.com/karpathy/autoresearch
**Tweet:** https://x.com/karpathy/status/2030371219518931079
**Fecha:** Marzo 2026

### Que es

Andrej Karpathy publico un repo donde un agente de IA experimenta solo, sin supervision humana. El agente:

1. Lee el codigo de entrenamiento (`train.py`, 630 lineas)
2. Propone una modificacion (arquitectura, hiperparametros, optimizador)
3. Hace git commit
4. Entrena un LLM por exactamente 5 minutos
5. Mide `val_bpb` (bits por byte en validacion)
6. Si mejoro → KEEP (avanza el branch)
7. Si no mejoro → DISCARD (git reset)
8. **NUNCA PARA** — repite indefinidamente

### Resultados

| Escala | Experimentos | Mejoras Guardadas | Mejora Total |
|--------|-------------|-------------------|-------------|
| 1 GPU | 83 | 15 (18%) | ~2.3% val_bpb |
| 8xH100 | 276 | 29 (10.5%) | ~1% val_bpb |

- Tobias Lutke (CEO Shopify) replico: 37 experimentos overnight, **19% de ganancia**
- ~12 experimentos/hora, ~100 overnight en 1 GPU

### Arquitectura del Sistema

```
program.md (instrucciones, lo edita el humano)
    ↓
Agente LLM (Claude/Codex/cualquiera)
    ↓
train.py (630 lineas, lo modifica el agente)
    ↓
prepare.py (inmutable, datos + evaluacion)
    ↓
results.tsv (historial de experimentos)
    ↓
git branch (autoresearch/tag)
```

**3 archivos clave:**
- `train.py` — GPT con RoPE, Flash Attention 3, MuonAdamW, ~50M params
- `prepare.py` — Datos ClimbMix-400B, tokenizer BPE, `evaluate_bpb()` (inmutable)
- `program.md` — Instrucciones al agente (lo unico que edita el humano)

### Como Aplica a DOF

**Mapeo directo DOF ↔ Autoresearch:**

| Autoresearch | DOF Equivalente |
|-------------|-----------------|
| `train.py` (target) | `config/agents.yaml` + `llm_config.py` |
| `val_bpb` (metrica) | Composite: SS, PFI, RP, GCR, SSR |
| `prepare.py` (ground truth) | `core/experiment.py` → `run_experiment()` |
| `program.md` (constraints) | `core/governance.py` (CONSTITUTION) |
| `results.tsv` | `logs/experiments/runs.jsonl` |
| git branch | Branch por campana de optimizacion |

**Implementacion concreta — DOF AutoResearch Loop:**

```python
# dof_autoresearch.md — instrucciones para el agente
LOOP FOREVER:
1. Leer config actual (agents.yaml, llm_config.py, governance.py)
2. Proponer modificacion (provider order, retry count, governance threshold)
3. git commit
4. Ejecutar: python -c "
   from core.experiment import run_experiment
   result = run_experiment(n_runs=10, deterministic=True)
   print(result['aggregate'])"
5. Extraer composite_score
6. Si mejoro → KEEP
7. Si empeoro → git reset --hard HEAD~1
```

**Metrica compuesta DOF:**
```python
dof_score = (0.3 * SS + 0.25 * (1 - PFI) + 0.2 * RP + 0.15 * GCR + 0.1 * SSR)
```

**Que optimizaria el agente autonomo:**
- Orden de provider chains por rol de agente
- Clasificacion HARD vs SOFT de reglas de governance
- Pesos del supervisor (Q=0.4, A=0.25, C=0.2, F=0.15)
- Texto de CONSTITUTION (~50 tokens)
- Retry count de crew_factory (actualmente 3)
- TTL backoff timing (5/10/20 min)

**Ventaja critica de DOF sobre Autoresearch:**
DOF tiene governance como safety bounds. Autoresearch confia ciegamente en el agente. DOF rechaza automaticamente experimentos que violen HARD_RULES, haciendo el loop mas seguro para sistemas multi-agente con consecuencias reales.

---

## 2. Paper SSO — Spectral Sphere Optimizer (arXiv 2601.08393)

**Fuente:** https://arxiv.org/abs/2601.08393
**Titulo:** "Controlled LLM Training on Spectral Sphere"
**Autores:** Microsoft Research Asia + Renmin University + Wuhan University
**Fecha:** Enero 2026, revision Marzo 2026

### Tesis Central

Los optimizadores actuales (AdamW, Muon) estan "medio alineados" con las restricciones teoricas para entrenamiento estable:
- **Muon** controla la norma espectral de las **actualizaciones** pero deja los **pesos** sin restriccion
- **SSO** restringe AMBOS: pesos Y actualizaciones en la esfera espectral

### Resultados Clave

| Experimento | Resultado |
|-------------|-----------|
| Dense 1.7B (100B tokens) | SSO alcanza misma loss que AdamW en **19% menos steps** |
| MoE 8B-A1B | Menor loss + mejor balance de carga entre expertos |
| DeepNet 200 capas | AdamW inestable con spikes; SSO estable todo el tiempo |
| Activaciones | SSO: constante Theta(1). AdamW: ~100x mas grande |
| Overhead por step | ~11.45% mas lento que Muon |

### Relevancia para DOF

1. **Estabilidad para loops autonomos**: SSO no tiene spikes → entrenamientos nocturnos sin supervision mas confiables
2. **Transferencia de hiperparametros**: Mejoras encontradas a escala pequena se transfieren a modelos grandes (muP alignment)
3. **Pattern "medio alineado"**: Similar a nuestra governance — necesitamos validar AMBOS la entrada y la salida, no solo una

### Aplicacion en DOF

SSO valida nuestro principio de **restricciones duales**: en DOF, la governance aplica HARD_RULES (restriccion de salida) Y la CONSTITUTION se inyecta en el prompt (restriccion de entrada). Es el mismo patron que SSO:
- Entrada restringida = Pesos en la esfera espectral
- Salida restringida = Actualizaciones con norma controlada
- DOF: Entrada restringida (CONSTITUTION) + Salida restringida (HARD_RULES)

---

## 3. Investigacion Gemini — Evaluacion Integral de Gobernanza y Nucleo Cognitivo

**Fuente:** Documento compartido por el operador (Marzo 22, 2026)
**Titulo:** "Evaluacion Integral de la Arquitectura de Gobernanza y el Nucleo Cognitivo para Agentes Autonomos"

### Propuestas Clave

| Propuesta | Descripcion | Impacto |
|-----------|-------------|---------|
| **Fisher Information Metric** | Reemplazar cosine similarity en memoria por metrica Fisher-Rao | Mejor relevancia contextual |
| **Deterministic Triage L0** | Capa de triage sin LLM antes del pipeline | Reduce latencia 30-50% |
| **x402 Endpoints** | HTTP 402 micropayments para servicios de agentes | Monetizacion nativa |
| **Safety Mesh Distribuido** | Red de seguridad entre agentes, no centralizada | Resiliencia |
| **Consolidacion Nocturna** | Patron A-Mem: merge de memorias episodicas en semanticas durante idle | Eficiencia de memoria |

### Capas de Memoria (A-Mem Pattern)

```
1. Episodica  — eventos recientes, TTL corto
2. Semantica  — conocimiento consolidado
3. Procedural — patrones de accion aprendidos
4. Meta-Memoria — politicas sobre cuando/como recordar
```

---

## 4. Comparacion: Karpathy Autoresearch vs Investigacion Gemini vs DOF Actual

### Tabla Comparativa

| Dimension | Karpathy Autoresearch | Investigacion Gemini | DOF Actual (v0.4.x) |
|-----------|----------------------|---------------------|---------------------|
| **Loop autonomo** | Hill-climbing 5 min/exp | No definido | Daemon 30 min/ciclo |
| **Metrica** | 1 escalar (val_bpb) | 5+ metricas compuestas | 5 formales (SS, PFI, RP, GCR, SSR) |
| **Safety** | Ninguna | Safety Mesh distribuido | CONSTITUTION + HARD_RULES |
| **Memoria** | Sin memoria entre runs | Fisher-Rao + A-Mem 4 capas | ChromaDB + embeddings |
| **Monetizacion** | No aplica | x402 micropayments | En desarrollo (x402) |
| **Git strategy** | Branch por campana | No definido | Branch main + daemon |
| **Agentes** | 1 (single agent loop) | Multi-agente propuesto | 15 agentes activos |
| **Optimizador** | MuonAdamW | N/A | Governance deterministica |
| **Escalabilidad** | 1 GPU → 8xH100 | Mesh distribuido | Mission Control + OpenClaw |
| **Triage** | keep/discard binario | L0 deterministico sin LLM | HARD (block) / SOFT (warn) |

### Sintesis: Lo Mejor de Cada Mundo para DOF

**De Karpathy Autoresearch adoptamos:**
1. **Loop autonomo con metrica escalar** — Crear `dof_autoresearch.py` que optimice configs automaticamente
2. **Git branch por campana** — Cada ciclo de optimizacion en su propio branch
3. **5-minute budget** — Time-boxed experiments para iterar rapido
4. **Keep/Discard deterministico** — Si `dof_score` mejora → keep, sino → reset
5. **program.md como skill** — Nuestro equivalente ya existe: SOUL.md por agente

**De la investigacion Gemini adoptamos:**
1. **Fisher-Rao para memoria** — Reemplazar cosine similarity en `memory_manager.py`
2. **Triage L0 sin LLM** — Capa deterministica antes del crew_runner (reduce latencia)
3. **x402 monetizacion** — Endpoints de pago para servicios DOF
4. **A-Mem 4 capas** — Episodica → Semantica → Procedural → Meta
5. **Consolidacion nocturna** — Cron job que merge memorias en horario idle

**Del paper SSO adoptamos:**
1. **Restricciones duales** — Validar ENTRADA (constitution) Y SALIDA (hard_rules)
2. **Estabilidad sobre velocidad** — SSO es 11% mas lento pero nunca tiene spikes
3. **Transferencia entre escalas** — Mejoras en experimentos pequenos deben transferirse

### Hoja de Ruta de Integracion

```
Fase 1 (Inmediata):
├── Crear dof_autoresearch.py (loop autonomo con metrica compuesta)
├── Implementar L0 Triage deterministico en crew_runner.py
└── Agregar x402 endpoint basico /verify-block

Fase 2 (1 semana):
├── Fisher-Rao metric en memory_manager.py
├── A-Mem 4 capas (episodica, semantica, procedural, meta)
└── Consolidacion nocturna como cron job

Fase 3 (2 semanas):
├── Safety Mesh distribuido entre agentes
├── DOF AutoResearch loop completo en produccion
└── x402 pricing tiers y documentacion API
```

---

## 5. AgentMeet — Comunicacion Multi-Agente en Vivo

**Fuente:** https://www.agentmeet.net/
**Fecha descubrimiento:** 2026-03-22

### Que es
"Google Meet para agentes de IA" — salas de chat donde agentes se registran via API HTTP y conversan en tiempo real.

### API Endpoints
```
POST /rooms                          → Crear sala
GET  /{room}/agent-join?format=json  → Registrar agente, obtener agent_id
POST /{room}/message                 → Enviar mensaje
GET  /{room}/wait?after=N            → Long-poll para nuevos mensajes (30s)
GET  /{room}/transcript              → Historial completo
POST /{room}/leave                   → Salir de la sala
```

### Integracion con DOF
- Script: `scripts/agentmeet-live.py` — 14 agentes con LLM real via OpenClaw
- Cada agente lee el transcript, piensa con su LLM, responde genuinamente
- 2 rounds de conversacion con Oracle resumiendo cada round
- **Resultado:** Conversaciones reales donde agentes se referencian por nombre, debaten, proponen acciones concretas

### Reunion Exitosa: Room 98f-f075-e535
- 14 agentes registrados y activos
- 23 mensajes reales de conversacion
- Tema: Integracion Fisher-Info, SHA-256, x402, Security Mesh
- Decisiones tomadas: SignedMemoryBlock schema, hash_memory_block(), /verify-block endpoint, pricing tier $0.02/1k blocks

---

## 6. Lecciones Aprendidas

### Tecnicas
1. **OpenClaw `--json` flag es problematico**: Output tiene prefijos `[plugins]` que rompen JSON parsing. Usar plain text y filtrar ruido.
2. **macOS no tiene `timeout`**: Usar `perl -e 'alarm N; exec @ARGV'`
3. **`date +%H` retorna octal**: 08/09 rompen aritmetica bash. Usar `date +%-H`
4. **NVM PATH en scripts**: Agregar `/Users/jquiceva/.nvm/versions/node/v22.16.0/bin` explicitamente
5. **AgentMeet rooms expiran**: Si no hay actividad por ~15-20 minutos, la sala se cierra

### Estrategicas
1. **Autoresearch pattern es aplicable a DOF**: La metrica compuesta + governance como safety bounds lo hacen mas robusto que el original
2. **Reuniones de agentes son valiosas**: No solo para brainstorming — generan action items concretos y trazables
3. **Zero LLM for governance sigue siendo correcto**: Tanto SSO (restricciones matematicas) como Autoresearch (metrica escalar deterministica) validan el enfoque deterministico
4. **Fisher-Rao > Cosine Similarity**: Para memoria contextual, la geometria de Fisher es mas informativa
5. **x402 es el path de monetizacion natural**: Micropayments por verificacion, auditoria, y acceso a proofs on-chain

---

*Documento vivo — se actualiza con cada investigacion y evolucion del sistema.*
