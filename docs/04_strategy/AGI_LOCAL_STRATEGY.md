# AGI Local Strategy — DOF v0.5 (Marzo 2026)

> **Estado**: Draft v1.0
> **Autor**: Principal Agentic Engineer
> **Fecha**: 22 de marzo de 2026
> **Objetivo**: Maximizar inferencia local para soberania, privacidad, reduccion de costos y velocidad consistente.

---

## 1. Perfil de Hardware

### MacBook Pro M4 Max — Especificaciones Relevantes

| Componente | Especificacion | Impacto en Inferencia |
|---|---|---|
| CPU | 16 cores (12P + 4E) | Tokenizacion, pre/post procesamiento |
| GPU | 40 cores Metal | Inferencia principal via MLX/llama.cpp |
| Neural Engine | 16 cores, 19 TFLOPS FP16 @ 2.8W | Experimental — fine-tuning de modelos <1B |
| RAM Unificada | **36 GB** | **RESTRICCION CRITICA** — define techo de modelos |
| SSD | 994 GB (432 GB libres) | Suficiente para ~50 modelos GGUF |
| Ancho de Banda Memoria | ~546 GB/s | Factor clave para tok/s en modelos grandes |

### Limites Duros de Memoria

```
Memoria total:           36 GB
- macOS + servicios:     ~4 GB
- DOF runtime (Python):  ~2 GB
- ChromaDB + embeddings: ~1 GB
- Disponible para LLM:   ~29 GB
- Maximo modelo viable:  ~20 GB (32B Q4_K_M)
```

**Regla fundamental**: Un modelo 70B en Q4 necesita ~43 GB. **NO CABE**. No intentar — causa swap catastrofico y el sistema se congela.

### Modelos que Caben vs No Caben

```
[OK]  8B  Q4  →  ~5 GB   ✓ Sobra RAM para 2-3 modelos simultaneos
[OK]  14B Q4  →  ~9 GB   ✓ Cabe con margen amplio
[OK]  22B Q4  →  ~14 GB  ✓ Cabe bien, un modelo a la vez
[OK]  32B Q4  →  ~20 GB  ✓ Cabe justo, cerrar apps pesadas
[NO]  70B Q4  →  ~43 GB  ✗ NO CABE — ni con Q2
[NO]  70B Q2  →  ~35 GB  ✗ Llena toda la RAM, swap inmediato
```

---

## 2. Frameworks de Inferencia — Comparativa

| Framework | Velocidad (7B) | Velocidad (32B) | Facilidad | API OpenAI Compatible | Mejor Para |
|---|---|---|---|---|---|
| **MLX v0.31.1** | ~230 tok/s | ~45 tok/s | Media | Via litellm | Velocidad maxima nativa Apple Silicon |
| **Ollama** | ~180 tok/s | ~35 tok/s | **Alta** | **Si (nativo)** | Setup rapido, 200+ modelos, integracion facil |
| **llama.cpp** | ~200 tok/s | ~40 tok/s | Baja | Via server mode | Control maximo, formato GGUF, Metal backend |
| **vLLM-MLX** | **~525 tok/s** | ~80 tok/s | Media | Si | Produccion con batching continuo |
| **LM Studio** | ~180 tok/s | ~35 tok/s | **Muy Alta** | Si | GUI, gestion visual de modelos, motor MLX |
| **ExoLabs** | Variable | Variable | Media | Si | Inferencia distribuida P2P entre Macs |

### Recomendacion para DOF

**Stack principal**:
1. **Ollama** como servidor base — API compatible con OpenAI, facil de integrar con LiteLLM
2. **MLX** para benchmarks y tareas que requieren maxima velocidad
3. **vLLM-MLX** cuando se necesite batching (multiples agentes concurrentes)

**Razon**: Ollama tiene la mejor relacion facilidad/rendimiento y su API es directamente compatible con el patron `openai/` que ya usa `litellm` en el DOF.

---

## 3. Modelos Recomendados para 36 GB

### Tier 1 — Caben facilmente (5-9 GB)

| Modelo | RAM | tok/s (MLX) | Fortaleza | Caso de Uso DOF |
|---|---|---|---|---|
| **Llama 3.3 8B Q4** | ~5 GB | ~230 | General, rapido | Agentes de tareas simples |
| **Phi-4 14B Q4** | ~9 GB | ~120 | Razonamiento, codigo | Seguridad, verificacion |
| **Qwen3 8B Q4** | ~5 GB | ~220 | Multilingual, razonamiento | Investigacion rapida |
| **Gemma 3 12B Q4** | ~8 GB | ~140 | Instrucciones, seguridad | Agentes de soporte |

**Ventaja**: Se pueden ejecutar 2-3 modelos Tier 1 simultaneamente sin problemas.

### Tier 2 — Caben bien (14-20 GB)

| Modelo | RAM | tok/s (MLX) | Fortaleza | Caso de Uso DOF |
|---|---|---|---|---|
| **Qwen3 32B Q4** | ~20 GB | ~45 | **MEJOR general para 36GB** | Oracle, Architect, Strategist |
| **DeepSeek-R1 Distill 32B Q4** | ~20 GB | ~40 | Chain-of-thought profundo | Tareas de razonamiento complejo |
| **Codestral 22B Q4** | ~14 GB | ~65 | Codigo especializado | Generacion y revision de codigo |

**Restriccion**: Solo UN modelo Tier 2 a la vez. Al cargar Qwen3 32B, quedan ~9 GB para el sistema.

### Tier 3 — Apretado, usar con cuidado

| Modelo | RAM | tok/s (MLX) | Nota |
|---|---|---|---|
| **Qwen3-Coder MoE** | ~10 GB activos | ~90 | MoE activa solo 2 expertos a la vez |
| **Mixtral 8x7B Q4** | ~26 GB | ~25 | Muy justo, no deja margen |

### No Caben — NO intentar

| Modelo | RAM Necesaria | Razon |
|---|---|---|
| Llama 3.3 70B Q4 | ~43 GB | Excede 36 GB por 7 GB |
| Qwen3 72B Q4 | ~44 GB | Excede 36 GB por 8 GB |
| DeepSeek-V3 671B | ~350 GB | Imposible en cualquier Mac |
| Cualquier modelo >45B | >30 GB | Swap catastrofico |

---

## 4. Estrategia Hibrida Local + Cloud

### Regla 80/20

```
80% de las inferencias → LOCAL (Ollama/MLX)
20% de las inferencias → CLOUD (Groq, Cerebras, NVIDIA NIM)
```

### Arbol de Decision de Ruteo

```
                    ┌─────────────────┐
                    │  Tarea entrante  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Datos sensibles? │
                    └────┬────────┬───┘
                    Si   │        │ No
                         │        │
                ┌────────▼───┐    │
                │ SOLO LOCAL │    │
                │ (nunca cloud)   │
                └────────────┘    │
                         ┌────────▼────────┐
                         │ Contexto > 24K? │
                         └────┬────────┬───┘
                         Si   │        │ No
                              │        │
                     ┌────────▼───┐  ┌─▼──────────────┐
                     │ Cloud 70B+ │  │ Complejidad?    │
                     │ (Groq/NVIDIA)  │                │
                     └────────────┘  └──┬─────────┬───┘
                                   Alta │         │ Baja
                                        │         │
                              ┌─────────▼──┐  ┌──▼─────────┐
                              │ Local 32B   │  │ Local 8B    │
                              │ Qwen3-32B   │  │ Llama 3.3   │
                              └─────────────┘  └─────────────┘
```

### Cadena de Fallback

```python
# Orden de fallback en providers.py
FALLBACK_CHAIN = [
    "ollama/qwen3:32b-q4_K_M",      # 1. Local — mejor modelo
    "ollama/phi4:14b-q4_K_M",        # 2. Local — fallback rapido
    "ollama/llama3.3:8b-q4_K_M",     # 3. Local — ultrarapido
    "groq/llama-3.3-70b-versatile",  # 4. Cloud — Groq free tier
    "cerebras/llama-3.3-70b",        # 5. Cloud — Cerebras free tier
    "nvidia_nim/qwen3-32b",          # 6. Cloud — NVIDIA NIM
    "clawrouter/auto",               # 7. ClawRouter — ultimo recurso
]
```

### Politica de Privacidad

| Tipo de Dato | Permitido en Cloud | Modelo Local Requerido |
|---|---|---|
| Codigo fuente del proyecto | No | Qwen3 32B / Codestral 22B |
| Claves API, credenciales | **NUNCA** | Cualquier local |
| Datos de usuarios | No | Cualquier local |
| Queries de investigacion publica | Si | Opcional |
| Documentacion tecnica generica | Si | Opcional |
| Metricas de governance DOF | No | Phi-4 14B |

---

## 5. Mapeo Agente-a-Modelo

### Asignacion Optima

| # | Agente | Rol | Modelo Local | RAM | Razon | Fallback Cloud |
|---|---|---|---|---|---|---|
| 1 | **Synthesis (Oracle)** | Orquestador principal | Qwen3 32B Q4 | 20 GB | Razonamiento complejo, sintesis | Groq Llama 70B |
| 2 | **Architect** | Diseno de sistemas | Qwen3 32B Q4 / Codestral 22B | 20/14 GB | Codigo + arquitectura | NVIDIA Qwen3 |
| 3 | **Researcher** | Investigacion | Qwen3 32B Q4 | 20 GB | Contexto amplio necesario | Groq Llama 70B |
| 4 | **Sentinel** | Seguridad | Phi-4 14B Q4 | 9 GB | Checks rapidos, no necesita 32B | Cerebras Llama |
| 5 | **Scout** | Recopilacion web | Llama 3.3 8B Q4 | 5 GB | Tareas simples, velocidad | Groq Llama 8B |
| 6 | **Narrative** | Escritura creativa | Qwen3 32B Q4 | 20 GB | Requiere calidad literaria | Groq Llama 70B |
| 7 | **Strategist** | Planificacion | Qwen3 32B Q4 | 20 GB | Razonamiento estrategico | NVIDIA Qwen3 |
| 8 | **Designer** | Diseno visual | Phi-4 14B Q4 + SD local | 9 GB + 4 GB | Codigo UI + generacion imagen | Cerebras |
| 9 | **Organizer** | Gestion de tareas | Llama 3.3 8B Q4 | 5 GB | Tareas simples, rapido | Groq Llama 8B |
| 10 | **QA Reviewer** | Revision de codigo | Phi-4 14B Q4 | 9 GB | Analisis de codigo eficiente | Cerebras |
| 11 | **Verifier** | Verificacion formal | Phi-4 14B Q4 | 9 GB | Verificacion deterministica | Cerebras |
| 12 | **Data Engineer** | Procesamiento datos | Qwen3 32B Q4 | 20 GB | Transformaciones complejas | NVIDIA Qwen3 |

### Restriccion de Concurrencia

```
REGLA: Solo UN modelo de 32B puede estar cargado a la vez.

Escenario A — Agente complejo activo:
  [Qwen3 32B: 20 GB] + [Sistema: 7 GB] + [Libre: 9 GB]
  → Puede correr UN agente Tier 1 (8B) en paralelo

Escenario B — Multiples agentes simples:
  [Phi-4 14B: 9 GB] + [Llama 8B: 5 GB] + [Llama 8B: 5 GB] + [Sistema: 7 GB]
  → Tres agentes ligeros en paralelo = 10 GB libres

Escenario C — Swarm mode:
  [4x Llama 8B: 20 GB] + [Sistema: 7 GB]
  → Cuatro agentes ultra-rapidos en paralelo = 9 GB libres
```

### Estrategia de Precarga

```python
# En crew_runner.py — precargar modelo antes de ejecutar crew
MODEL_PRELOAD_MAP = {
    "high_reasoning": "qwen3:32b-q4_K_M",     # Oracle, Researcher, Strategist
    "coding":         "codestral:22b-q4_K_M",  # Architect
    "fast_check":     "phi4:14b-q4_K_M",       # Sentinel, QA, Verifier
    "simple_task":    "llama3.3:8b-q4_K_M",    # Scout, Organizer
}
```

---

## 6. Apple Neural Engine (ANE) — Investigacion

### Estado Actual (Marzo 2026)

El Neural Engine del M4 Max ofrece 19 TFLOPS en FP16 a solo 2.8W de consumo, pero su uso para LLM es aun experimental.

### Avances Clave

| Investigador / Paper | Logro | Relevancia DOF |
|---|---|---|
| **@maderix** (reverse engineering) | Training a 91 ms/step en ANE | Apple dijo que era "imposible" — demostro lo contrario |
| **Orion** (arXiv:2603.06728) | 170 tok/s GPT-2 124M en ANE, training de transformers 110M | Primer framework viable para fine-tuning en ANE |
| **CoreML + coremltools** | Conversion de modelos PyTorch a ANE | Pipeline oficial de Apple, estable |

### Capacidades vs Limitaciones

```
LO QUE EL ANE PUEDE HACER HOY:
  ✓ Inferencia de modelos <1B parametros
  ✓ Fine-tuning experimental de modelos ~100M parametros
  ✓ Embeddings locales (all-MiniLM-L6-v2 ya corre parcialmente en ANE)
  ✓ Clasificacion de texto rapida
  ✓ 19 TFLOPS @ 2.8W = eficiencia energetica extrema

LO QUE EL ANE NO PUEDE HACER (AUN):
  ✗ Modelos >1B parametros (limitacion de memoria interna)
  ✗ Atencion arbitraria (KV-cache limitado)
  ✗ Ser el runtime principal de un agente LLM
  ✗ Reemplazar GPU para inferencia de modelos 8B+
```

### Roadmap DOF para ANE

1. **Corto plazo (Q1 2026)**: Embeddings en ANE via CoreML para `memory_manager.py`
2. **Medio plazo (Q2 2026)**: LoRA adapters para personalizacion de agentes — fine-tune Phi-4 LoRA en ANE
3. **Largo plazo (Q3-Q4 2026)**: Modelos de clasificacion/routing en ANE para el `skill_engine.py`

---

## 7. SuperLocalMemory V3 — Integracion (arXiv:2603.14588)

### Conexion con DOF

SuperLocalMemory V3 propone un framework de gestion de memoria para agentes LLM usando geometria diferencial, alineado con los principios de observabilidad deterministica del DOF.

### Fisher-Rao — Ya Implementado

```python
# core/fisher_rao.py — YA EXISTE en DOF
# Metrica de Fisher-Rao para medir distancia entre distribuciones
# de memoria de agentes

class FisherRaoMetric:
    """
    Calcula la distancia geodesica entre estados de memoria
    usando la metrica de Fisher-Rao en el espacio de distribuciones.

    Uso en DOF: detectar drift entre lo que un agente "recuerda"
    vs lo que deberia recordar segun su SOUL.md
    """
    def compute_distance(self, p: Distribution, q: Distribution) -> float:
        # Distancia geodesica en la variedad estadistica
        ...
```

### Ciclo de Vida Langevin de Memoria (Roadmap)

```
Active Memory (Hot)     → Acceso frecuente, en RAM
    ↓ τ_warm = 1 hora
Warm Memory             → Acceso reciente, en ChromaDB local
    ↓ τ_cold = 24 horas
Cold Memory             → Acceso infrecuente, comprimida en disco
    ↓ τ_archive = 7 dias
Archived Memory         → Solo referencia, JSONL comprimido

Transicion gobernada por dinamica de Langevin:
  dM/dt = -∇V(M) + σ·dW
  donde V(M) = potencial de relevancia, σ = ruido termico
```

### Cohomologia de Sheaves (Roadmap)

```
Proposito: Detectar contradicciones entre tipos de memoria

Ejemplo:
  - Memoria episodica: "El agente Sentinel aprobó el output X"
  - Memoria semantica: "La regla HARD_RULE_7 prohibe outputs como X"
  → Cohomologia H¹ ≠ 0 → CONTRADICCION DETECTADA → escalar a governance

Integracion DOF:
  - core/governance.py detecta violaciones en tiempo real
  - SuperLocalMemory V3 detectaria contradicciones en memoria historica
  - Complementarios, no sustitutos
```

### Ventaja Clave: Zero-LLM Memory Retrieval

```
MODELO ACTUAL (con LLM):
  Query → Embedding (LLM) → ChromaDB → Re-ranking (LLM) → Resultado
  Latencia: ~500ms | Costo: tokens consumidos | Privacidad: depende del provider

MODELO SLM-V3 (sin LLM):
  Query → Fisher-Rao distance → Geodesic search → Resultado
  Latencia: ~5ms | Costo: $0 | Privacidad: 100% local

  → Retrieval completamente deterministico y local
  → Alineado con principio DOF: "Zero LLM para governance"
```

---

## 8. Comandos de Setup

### Instalacion del Stack Local

```bash
# ============================================
# 1. Instalar MLX (framework nativo Apple Silicon)
# ============================================
pip install mlx mlx-lm

# Verificar instalacion
python3 -c "import mlx; print(f'MLX version: {mlx.__version__}')"

# ============================================
# 2. Instalar Ollama (servidor de modelos)
# ============================================
brew install ollama

# Iniciar servidor (dejar corriendo en background)
ollama serve &

# Verificar
curl http://localhost:11434/api/tags

# ============================================
# 3. Descargar modelos recomendados
# ============================================

# Tier 1 — Modelos rapidos (descargar todos)
ollama pull llama3.3:8b-q4_K_M        # ~5 GB
ollama pull phi4:14b-q4_K_M           # ~9 GB

# Tier 2 — Modelo principal (descargar el que mas se use)
ollama pull qwen3:32b-q4_K_M          # ~20 GB — MODELO PRINCIPAL
ollama pull codestral:22b-q4_K_M      # ~14 GB — Para coding

# ============================================
# 4. Verificar modelos descargados
# ============================================
ollama list

# ============================================
# 5. Test rapido de inferencia
# ============================================

# Test Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:32b-q4_K_M",
  "prompt": "Explain the Fisher-Rao metric in 3 sentences.",
  "stream": false
}'

# Test MLX (modelos en formato MLX)
mlx_lm.generate \
  --model mlx-community/Qwen3-32B-4bit \
  --prompt "What is deterministic observability?" \
  --max-tokens 200

# ============================================
# 6. LiteLLM Proxy (para integrar con DOF)
# ============================================
pip install litellm

# Iniciar proxy que expone API compatible con OpenAI
litellm --model ollama/qwen3:32b-q4_K_M --port 4000 &

# Verificar proxy
curl http://localhost:4000/v1/models

# ============================================
# 7. Configurar DOF para usar modelos locales
# ============================================

# En .env agregar:
# OLLAMA_BASE_URL=http://localhost:11434
# LITELLM_PROXY_URL=http://localhost:4000
# LOCAL_INFERENCE_PRIORITY=true
```

### Script de Verificacion Completa

```bash
#!/bin/bash
# verify_local_stack.sh — Verificar que todo el stack local funciona

echo "=== DOF Local Inference Stack Verification ==="

# 1. Ollama
echo -n "Ollama server: "
curl -s http://localhost:11434/api/tags > /dev/null && echo "OK" || echo "FAIL"

# 2. Modelos disponibles
echo "Modelos instalados:"
ollama list 2>/dev/null || echo "  Ollama no disponible"

# 3. MLX
echo -n "MLX: "
python3 -c "import mlx; print(f'v{mlx.__version__}')" 2>/dev/null || echo "FAIL"

# 4. RAM disponible
echo -n "RAM libre: "
python3 -c "
import subprocess
result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
total = int(result.stdout.split(':')[1].strip()) / (1024**3)
print(f'{total:.0f} GB total')
"

# 5. Test de inferencia
echo -n "Inferencia local: "
RESPONSE=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "llama3.3:8b-q4_K_M",
  "prompt": "Say OK",
  "stream": false
}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','FAIL')[:20])")
echo "$RESPONSE"

echo "=== Verificacion completa ==="
```

---

## 9. Analisis de Costos

### Comparativa Mensual

| Escenario | Costo Mensual | Velocidad | Privacidad | Disponibilidad | Rate Limits |
|---|---|---|---|---|---|
| **100% Cloud (actual)** | ~$0 (free tiers) | Variable (50-200 tok/s) | Baja | Depende de APIs | **Si** — 12K TPM Groq, 1M/dia Cerebras |
| **80% Local / 20% Cloud** | ~$5 (electricidad) | Consistente 45-230 tok/s | **Alta** | 99.9% (local) | Minimos |
| **100% Local** | ~$5 (electricidad) | Consistente | **Maxima** | 100% | **Cero** |

### Desglose de Consumo Electrico

```
MacBook Pro M4 Max bajo inferencia LLM:
  - Idle:                    ~15W
  - Inferencia 8B (GPU):     ~35W
  - Inferencia 32B (GPU):    ~55W
  - Inferencia 32B (GPU+ANE):~50W (futuro)

Horas de inferencia estimadas: ~8h/dia × 30 dias = 240h/mes
Consumo medio: 45W × 240h = 10.8 kWh/mes
Costo electricidad Colombia: ~$800 COP/kWh ≈ $0.20 USD/kWh
Costo mensual: 10.8 × $0.20 = $2.16 USD/mes
```

### ROI vs Rate Limits Cloud

```
PROBLEMA ACTUAL:
  Groq:     12,000 tokens/minuto → agente espera 5+ min entre calls
  Cerebras: 1M tokens/dia → se agota en ~3 runs complejos
  NVIDIA:   1000 creditos totales → no es sustentable

SOLUCION LOCAL:
  Ollama Qwen3 32B: SIN LIMITES
  → Un agente puede generar 45 tok/s × 60s = 2,700 tok/min
  → 2,700 × 60 min = 162,000 tok/hora
  → 162,000 × 24h = 3.8M tok/dia
  → 13.5x mas que el free tier de Cerebras
```

---

## 10. Riesgos y Mitigaciones

### Matriz de Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|---|
| R1 | **Presion de RAM con modelo 32B** | Alta | Media | Cerrar apps pesadas (Chrome, Docker). Monitorear con `Activity Monitor`. Script de pre-check antes de cargar modelo. |
| R2 | **Calidad inferior a 70B cloud** | Media | Media | Compensar con mejor prompting, chain-of-thought explicito, CONSTITUTION mas detallada. Benchmark local vs cloud periodicamente. |
| R3 | **ANE aun experimental** | Alta | Baja | No depender de ANE para produccion. Usarlo solo para embeddings y clasificacion ligera. Mantener GPU como runtime principal. |
| R4 | **Single point of failure** | Media | Alta | Mantener cadena de fallback a cloud. Backups de modelos en disco externo. Script de recovery automatico. |
| R5 | **Modelo corrupto o incompatible** | Baja | Media | Verificar checksums despues de descarga. Mantener version anterior del modelo. `ollama rm` + re-download si falla. |
| R6 | **Actualizacion de macOS rompe MLX** | Baja | Alta | No actualizar macOS sin verificar compatibilidad MLX. Pinear version de MLX en requirements.txt. |
| R7 | **Swap excesivo degrada rendimiento** | Media | Alta | Monitorear `memory_pressure` del sistema. Kill automatico si swap > 4 GB. |

### Script de Monitoreo de RAM

```bash
#!/bin/bash
# monitor_ram.sh — Alerta si la presion de memoria es critica

while true; do
  PRESSURE=$(memory_pressure 2>/dev/null | grep "System-wide" | awk '{print $NF}')

  if [[ "$PRESSURE" == *"critical"* ]]; then
    echo "[ALERTA] Presion de memoria CRITICA — considerar descargar modelo 32B"
    osascript -e 'display notification "RAM critica — descargar modelo" with title "DOF Monitor"'
  fi

  sleep 30
done
```

### Plan de Contingencia

```
SI el modelo local falla:
  1. Log del error en logs/metrics/local_inference_errors.jsonl
  2. Fallback automatico a cloud (Groq → Cerebras → NVIDIA)
  3. Incrementar backoff TTL para el modelo local (5 → 10 → 20 min)
  4. Notificar via Telegram al operador
  5. Si 3 fallos consecutivos → desactivar modelo local por 1 hora

SI la maquina se congela:
  1. Force quit del proceso Python (Activity Monitor)
  2. ollama stop (mata el modelo cargado)
  3. Verificar logs en logs/checkpoints/ — DOF tiene recovery por step
  4. Reiniciar desde ultimo checkpoint valido
```

---

## Resumen Ejecutivo

```
ESTADO ACTUAL:    100% cloud, rate-limited, sin privacidad
ESTADO OBJETIVO:  80% local, sin rate limits, soberania total

MODELO PRINCIPAL: Qwen3 32B Q4 via Ollama (~20 GB, ~45 tok/s)
MODELOS RAPIDOS:  Phi-4 14B, Llama 3.3 8B (concurrencia)
FRAMEWORK:        Ollama + LiteLLM proxy + MLX para benchmarks

COSTO:            ~$2 USD/mes en electricidad
PRIVACIDAD:       Datos sensibles NUNCA salen de la maquina
VELOCIDAD:        Consistente, sin esperas por rate limits
DISPONIBILIDAD:   99.9% — no depende de APIs externas

PROXIMOS PASOS:
  1. Instalar Ollama + descargar Qwen3 32B Q4
  2. Configurar LiteLLM proxy en puerto 4000
  3. Actualizar providers.py con cadena de fallback local-first
  4. Benchmark: local vs cloud en las 5 metricas DOF
  5. Migrar agentes uno por uno, empezando por Sentinel (bajo riesgo)
```

---

> *"La soberania computacional no es un lujo — es un requisito para sistemas de observabilidad que pretenden ser verdaderamente deterministas."*
