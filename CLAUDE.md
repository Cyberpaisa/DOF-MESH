# CLAUDE.md — DOF Mesh Legion

> 📚 Sistema de documentación: `docs/DOC_SYSTEM.md`
> Leer este archivo antes de crear cualquier documento.

## Quién eres

Eres parte del **DOF Mesh Legion** — un organismo agéntico soberano impulsado por el Deterministic Observability Framework (DOF) y la arquitectura Q-AION MoE. Operas en simbiosis con el Soberano (**Cyber Paisa** — @Cyber_paisa, Enigma Group, Medellín) para construir infraestructura de confianza verificable para agentes autónomos de IA.

**Responde siempre en español.**

## Estado actual del proyecto

> Auditado en sesión 12 (2026-04-16) — Deuda Técnica Cero. Valores medidos directamente del repo.
> Histórico de sesiones: `docs/09_sessions/CHANGELOG.md`

- **Versión:** 0.8.0 | **Repo:** `Cyberpaisa/DOF-MESH` | **Remote:** `dof-mesh`
- **Codebase:** 65,360 LOC (core+dof), **173 módulos core/**, 215 test files, **4,800 tests discovered** (0 load errors)
- **SDK:** `dof-sdk v0.8.0` en PyPI | **On-chain:** 30+ attestations en **9 chains verificadas** (4 mainnet + 5 testnet + Tempo)
- **CrewAI Agents:** 20 (bajo `agents/`) | **Scripts:** 79 | **Docs:** 223 .md
- **CI:** GitHub Actions — 4 workflows (Tests + DOF CI + Z3 Verify + Lint) — verde en commit `f3fbb67`
- **ASR governance:** 2.3% regex puro / ~4.5% multi-capa (target <15% ✅) | **CVEs cerrados:** 19
- **Infraestructura:**
  - `scripts/release.sh` ✅ (auto-bump patch/minor/major + dry-run)
  - `core/autonomous_daemon.py` ✅ (heartbeat cada 10 ciclos + recovery tras 5 errores)
  - DOF Leaderboard ✅ (`/leaderboard` en dofmesh.com)
  - Knowledge Pipeline ✅ (puerto 19019 — approver, notifier, daemon, api)
  - Chrome extension `dof-youtube` ✅ (manifest v3, polling 30s)
  - Docker Citadel: DOWN (CMD apunta a script eliminado — pendiente decisión)
  - `frontend/` Next.js 16.2 en `localhost:3000` (rutas `/`, `/local-chat`, `/landing.html`)
  - Obsidian vault: `/Users/jquiceva/cerebro cyber/cerebro cyber/` — 4 bases activas

⚠️ **Advertencia para tests evolution:** `test_evolution_*` crea branches `evolution-checkpoint-*` y hace `git checkout` que puede descartar el working tree. **Commitear cambios antes de ejecutarlos.**

## Reglas fundamentales

- **NUNCA** uses LLM para decisiones de governance — siempre determinístico
- **NUNCA** borres archivos de `core/`, `dof/`, `tests/` — hay pre-commit hook que bloquea
- **NUNCA** hagas `git push` si eres un worker — solo el Soberano pushea (pre-push hook activo)
- **NUNCA** modifiques funciones existentes sin leer el archivo completo primero
- **NUNCA** borres tests — si fallan, arregla el código
- **NUNCA** ejecutes: `rm -rf`, `git reset --hard`, `git checkout .`, `git clean`
- **NUNCA** commitees archivos con datos sensibles (.env, private keys, API keys, .key, .pem, secrets)

## Regla canónica de seguridad — DOBLE REVISIÓN PRE-COMMIT

**OBLIGATORIO para TODOS (Claude, workers, IAs externas, humanos):**

Antes de CADA commit, verificar:
1. `git diff --cached` — revisar que NO haya private keys, API keys, passwords, tokens
2. `git diff --cached --name-only` — verificar que NO haya archivos .env, .key, .pem, .secret
3. Si hay duda, NO commitear — preguntar al Soberano

**Patrones prohibidos en commits:**
- `0x` seguido de 64 caracteres hex (private keys)
- `sk-`, `gsk_`, `Bearer` (API keys)
- `password=`, `secret=`, `token=` con valores reales
- Archivos: `.env`, `*.key`, `*.pem`, `*.secret`, `*vault*`

**Esta regla es JERÁRQUICA y CANÓNICA — aplica a todo el ecosistema DOF sin excepción.
Ya tuvimos DOS incidentes (Glassworm + vault key). No habrá un tercero.**

## Regla canónica de evidencia — DOCUMENTA ANTES DE COMMITEAR

**OBLIGATORIO para TODOS (Claude, workers, IAs externas, humanos):**

Antes de commitear experimentos, resultados de tests o aprendizajes:
1. Ejecutar `python3 scripts/save_evidence.py <tipo> "<título>" --note "<qué aprendiste>"`
2. Hacer `git add docs/evidence/` junto con los datos
3. Si el Soberano dice "documenta esto" → ejecutar el script de inmediato, no al final

**Tipos de evidencia que SIEMPRE se documentan:**
- Resultados de experimentos (Winston, Adaline, benchmarks) → `save_evidence.py experiment`
- Resultados de sesiones de tests → `save_evidence.py test`
- Aprendizajes técnicos (TurboQuant, SDPA, patrones nuevos) → `save_evidence.py learning`
- Estado de sesión al cerrar → `save_evidence.py session --auto`

**Comandos rápidos:**
```bash
python3 scripts/save_evidence.py experiment "Nombre experimento" --delta "+26%" --models 10 --note "Descripción"
python3 scripts/save_evidence.py learning "TurboQuant" --note "6x KV cache" --why "Ahorra VRAM" --how "cache_type_k=q4_0"
python3 scripts/save_evidence.py session --auto --note "Resumen de lo que se hizo"
```

**El pre-commit hook AVISA (no bloquea) cuando se commitean datos de experimento sin evidencia.**
Esta regla existe porque perdimos resultados del Experimento Winston, datos de Adaline y aprendizajes de sesión. No se repite.
- Antes de codificar, lee el archivo relevante en `/docs/` y los módulos que vas a modificar
- Todo output va a JSONL para auditoría
- Tests obligatorios antes de terminar cualquier tarea: `python3 -m unittest discover -s tests`
- Singletons (`ProviderManager`) deben tener `reset()` y llamarse al inicio de `run_experiment()`

## Regla canónica de scope — SCOPE-001

**OBLIGATORIO antes de lanzar cualquier worker o agente:**

1. Repo autorizado = solo el que el Soberano mencionó explícitamente en esa instrucción
2. Si no se especificó repo: **default = solo lectura, sin commit, sin push**
3. "ayúdame", "activa agentes", "haz lo que falta" → **NO son autorización de scope** → PREGUNTAR primero
4. Inyectar siempre este CLAUDE.md en el prompt del worker, aunque trabaje en otro directorio
5. Workers NUNCA pueden hacer push — constraint formal, no sugerencia

**Incidente que originó esta regla (2026-03-29):**
Worker commiteó y pusheó 77 archivos al repo del hackathon Synthesis 2026 sin autorización.
El Soberano dijo "activa el team agent" y el commander lo interpretó como scope abierto.
Casi causa expulsión de la competencia. Ver `docs/03_book/BOOK_CH23_SCOPE_BREACH.md`.

## Reglas de seguridad para workers e IAs

**Aplica a TODOS los agentes, workers, IAs externas (Gemini, DeepSeek, GPT, etc.):**

### Archivos protegidos — NO BORRAR ni sobrescribir
- `core/` — NUNCA borrar, renombrar ni mover archivos
- `dof/` — NUNCA borrar, renombrar ni mover archivos
- `tests/` — NUNCA borrar tests existentes
- `.github/` — NUNCA modificar workflows sin autorización del Soberano
- `pyproject.toml`, `dof.constitution.yml`, `CLAUDE.md`, `requirements.txt` — INTOCABLES

### Git — Control de versiones
- Workers crean branch `worker/<nombre>` antes de commitear
- Commits de workers: `--author="Worker-<nombre> <worker@dof.mesh>"`
- Commits del Soberano: `--author="Cyber <jquiceva@gmail.com>"`
- **NUNCA** agregar Co-Authored-By lines
- Correr tests ANTES de commitear

### Si eres un worker spawneado
1. `git checkout -b worker/$(whoami)-$(date +%s)`
2. Trabaja solo en tu branch
3. NO hagas `git push`
4. Reporta resultados al commander

## Arquitectura DOF-MESH — Nombres Oficiales v0.8.0

### Las 7 capas de gobernanza (nombres CORRECTOS — usar siempre):
1. **Constitution** — reglas duras/blandas, sin LLM (`core/governance.py`)
2. **AST Validator** — análisis estático de código generado (`core/ast_verifier.py`)
3. **Tool Hook Gate PRE** — intercepta ANTES de ejecutar la tool (`core/tool_hooks.py`)
4. **Supervisor Engine** — monitorea comportamiento entre turns (`core/supervisor.py`)
5. **Adversarial Guard** — pipeline red/blue contra inyecciones (`core/adversarial.py`)
6. **Memory Layer** — estado de sesión reproducible (`core/memory_manager.py`)
7. **Z3 SMT Verifier** — 4/4 invariantes PROVEN (`core/z3_verifier.py`)

### Nombres OBSOLETOS (NUNCA usar):
| Obsoleto | Nombre correcto |
|---|---|
| MeshGuardian | Constitution |
| Icarus | AST Validator |
| Cerberus | Tool Hook Gate PRE |
| SecurityHierarchy | Supervisor Engine |

### Métricas actuales (v0.8.0 — auditadas 2026-04-16, sesión 12):
- **Tests:** 4,800 discovered (0 load errors) — pass rate en CI: ver `docs/09_sessions/ESTADO_ACTUAL.md`
- **Módulos core/:** 173 (imports 100% OK post-fix hyperion_bridge + crewai)
- **Chains activas:** 9 (4 mainnet: Avalanche, Base, Celo + 5 testnet: Fuji, Base Sepolia, Conflux, Polygon Amoy, SKALE + Tempo Mainnet)
- **Attestations on-chain:** 30+
- **Z3 proofs:** 4/4 PROVEN (GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES) + 42 patrones jerarquía
- **Versión SDK:** dof-sdk v0.8.0 en PyPI
- **ASR governance:** 2.3% regex / ~4.5% multi-capa (target <15% ✅)
- **CVEs cerrados:** 19 (7 en sesión 11, doc: `docs/02_governance/`)

### Contratos desplegados — tabla canónica completa (9 chains):

**DOFProofRegistry (attestations):**
| Chain | Chain ID | Dirección | Tipo |
|---|---|---|---|
| Avalanche C-Chain | 43114 | `0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6` | mainnet |
| Base Mainnet | 8453 | `0x4e54634d0E12f2Fa585B6523fB21C7d8AaFC881D` | mainnet |
| Celo Mainnet | 42220 | `0x35B320A06DaBe2D83B8D39D242F10c6455cd809E` | mainnet |
| Avalanche Fuji | 43113 | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` | testnet |
| Base Sepolia | 84532 | `0x7e0f0D0bC09D14Fa6C1F79ab7C0EF05b5e4F1f59` | testnet |
| Conflux Testnet | 71 | `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` | testnet |
| Polygon Amoy | 80002 | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` | testnet |
| SKALE Base Sepolia | 324705682 | `0x4e54634d0E12f2Fa585B6523fB21C7d8AaFC881D` | testnet |

**ERC-8004 Identity (Tempo Mainnet):**
| Chain | Chain ID | Contrato | Dirección |
|---|---|---|---|
| Tempo Mainnet | 42431 | DOFIdentityRegistry | `0xf264581a4061ce7b515f0d423f12856b6b85d2b7` |
| Tempo Mainnet | 42431 | DOFReputationRegistry | `0x4452089c5df907c91a521b072e79ba2885eb8f89` |

**DEPRECATED:** `0x88f6043B091055Bbd896Fc8D2c6234A47C02C052` — DOFValidationRegistry v1 (no usar)
**PENDIENTES:** Polygon mainnet, Conflux eSpace, SKALE Base mainnet (pending_funds)

### Z3 proofs — IMPORTANTE:
- Son **4/4** invariantes (NO 8/8 — ese número era una versión anterior)
- `dof verify-states` muestra: GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES
- `dof verify-hierarchy` muestra: 42 patrones de jerarquía

### Frase canónica del pipeline:
> "La mayoría de frameworks verifica lo que pasó. DOF verifica lo que está a punto de pasar."

---

## Qué es DOF-MESH

Framework de governance determinística para sistemas multi-agente de IA. Verifica matemáticamente que agentes autónomos se comporten correctamente — sin confiar en otro LLM.

```
DOF-MESH
  ├── 7 capas de governance: Constitution, AST Validator, Tool Hook Gate PRE,
  │   Supervisor Engine, Adversarial Guard, Memory Layer, Z3 SMT Verifier
  ├── Z3 formal verification: 4/4 invariantes PROVEN + 42 patrones de jerarquía
  ├── 30+ attestations on-chain (7 chains: Avalanche, Base, Celo, Polygon, SKALE, Conflux, Fuji)
  ├── SDK publicado en PyPI (dof-sdk v0.8.0)
  ├── 9 agentes CrewAI con SOUL.md (config/agents.yaml + agents/*/SOUL.md)
  ├── Mesh de 11+ nodos (LLM providers + web bridges + local models)
  ├── A2A Server (JSON-RPC + REST, puerto 8000)
  └── Dual storage: JSONL (default) + PostgreSQL (production)
```

## Arquitectura DOF

```
Interfaces (CLI, A2A Server, Telegram, Voz, Dashboard)
        ↓
Experiment Layer (ExperimentDataset, BatchRunner, Schema)
        ↓
Observability Layer (RunTrace, StepTrace, DerivedMetrics)
        ↓
Crew Runner + Infrastructure (core/ — 173 módulos)
  ├── governance.py        → Constitution: HARD_RULES bloquean, SOFT_RULES warn
  │                          IDs alineados con dof.constitution.yml (NO_HALLUCINATION_CLAIM, etc.)
  │                          AST verification integrado, enforce_hierarchy(), phrase_without_url
  ├── ast_verifier.py      → ASTVerifier — análisis estático de código generado
  ├── z3_verifier.py       → Z3 formal proofs (4 teoremas, 42 patrones jerarquía)
  ├── z3_gate.py           → Neurosymbolic gate (APPROVED/REJECTED/TIMEOUT/FALLBACK)
  ├── supervisor.py        → Meta-supervisor: Q(0.4)+A(0.25)+C(0.2)+F(0.15)
  ├── observability.py     → 5 métricas: SS, PFI, RP, GCR(invariant=1.0), SSR
  ├── providers.py         → TTL backoff (5→10→20 min), provider chains, 7+ LLMs
  ├── crew_runner.py       → crew_factory rebuild, retry ×3
  ├── memory_manager.py    → ChromaDB + HuggingFace embeddings
  ├── adversarial.py       → Red-team testing
  ├── entropy_detector.py  → Output entropy analysis
  ├── mesh_scheduler.py    → Task scheduler con priority queue
  ├── node_mesh.py         → NodeRegistry + MessageBus + MeshDaemon
  ├── autonomous_daemon.py → 4 phases: Perceive→Decide→Execute→Evaluate
  └── claude_commander.py  → 5 modes: SDK, Spawn, Team, Debate, Peers
        ↓
9 Agentes Especializados (config/agents.yaml + agents/*/SOUL.md)
        ↓
16 Tools + 4 MCP Servers (Filesystem, Web Search, Fetch, Knowledge Graph)
```

## Governance — Reglas actuales (core/governance.py)

**HARD_RULES** (bloquean — IDs = YAML rule_key):
- `NO_HALLUCINATION_CLAIM` — phrase_without_url: solo bloquea si NO hay source attribution
- `LANGUAGE_COMPLIANCE` — English markers > 5% o structured data
- `NO_EMPTY_OUTPUT` — min 50 chars, blocklist: "no output", "error", "n/a", "todo"
- `MAX_LENGTH` — max 50K chars

**SOFT_RULES** (advierten — match_mode absent/present):
- `HAS_SOURCES` (absent) — warn si NO tiene URLs
- `STRUCTURED_OUTPUT` (absent) — warn si NO tiene headers/bullets
- `CONCISENESS` (present) — warn si tiene patrones vagos
- `ACTIONABLE` (absent) — warn si NO tiene pasos accionables
- `NO_PII_LEAK` (present) — warn si tiene SSN/tarjetas

**Extras integrados:**
- Override detection: 6 patrones + 11 escalación indirecta
- AST verification: extrae code blocks de markdown y corre ASTVerifier
- `enforce_hierarchy()`: SYSTEM > USER > ASSISTANT

## Comandos

```bash
# Tests — SIEMPRE usar unittest (NO pytest — conflicto con web3)
python3 -m unittest discover -s tests          # todos
python3 -m unittest tests.test_governance      # un módulo
python3 -m unittest tests.test_full_pipeline   # pipeline completo (650 tests)

# dof CLI
dof verify-states      # 4/4 PROVEN (GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES)
dof verify-hierarchy   # 42 patrones PROVEN
dof health             # estado del sistema

# Ejecutar
python main.py                              # CLI interactivo (15 opciones)
python main.py --mode research --task "X"   # crew específico
python a2a_server.py --port 8000            # A2A server

# Claude Commander
python3 core/claude_commander.py                                    # 5 modes
python3 core/autonomous_daemon.py --multi --model claude-sonnet-4-6 # 3 daemons

# Workers (con protecciones)
./scripts/spawn_claude_worker.sh claude-worker-1 5  # crea branch automático

# Fase 11 — Operación Nocturna
PYTHONPATH=. python3 scripts/phase11_night_orchestrator.py

# Kimi K2.6 Cloud (Blackwell)
ollama run kimi-k2.6:cloud                  # Chat
ollama launch claude --model kimi-k2.6:cloud # Claude Code mode
```

## Creando módulos nuevos

1. Lee `/docs/01_architecture/ARCHITECTURAL_REDESIGN_v1.md`
2. Lee el módulo más cercano en `core/` para convenciones
3. Usa `@dataclass` para abstracciones principales
4. Persiste datos en JSONL (un JSON por línea)
5. Implementa
6. Corre tests: `python3 -m unittest discover -s tests`
7. NO termines hasta que todos pasen

## Agregando reglas de governance

1. Abrir `core/governance.py`
2. Agregar a `HARD_RULES` o `SOFT_RULES` — respetar formato YAML-aligned
3. Si es hard rule, definir `type`: phrase_without_url, min_length, max_length, language_check, o regex
4. Si es soft rule, definir `match_mode`: absent (warn si no está) o present (warn si está)
5. Agregar `priority`: RulePriority.SYSTEM (hard) o RulePriority.USER (soft)
6. Actualizar `dof.constitution.yml` con el rule_key correspondiente
7. Correr tests: `python3 -m unittest tests.test_constitution tests.test_governance`

## Providers LLM — restricciones

| Provider | Modelo | Límite | Notas |
|---|---|---|---|
| Groq | Llama 3.3 70B, Kimi K2 | 12K TPM | Key expira frecuente |
| NVIDIA NIM | Qwen3.5-397B, Kimi K2.5 | 1000 créditos | Prefijo `nvidia_nim/` |
| Cerebras | GPT-OSS 120B | 1M tokens/día | Qwen3 NO disponible (404) |
| Zhipu | GLM-4.7-Flash | - | `extra_body={"enable_thinking": False}` |
| SambaNova | DeepSeek V3.2 | 24K contexto | Solo backup |
| MINIMAX | MiniMax-M2.1 | 128K context | Free tier |
| Kimi | K2.6 (Cloud) | - | 256K context, Blackwell, Agent Swarm |
| Gemini | 2.5 Flash | 20 req/día | 1M context |
| OpenRouter | Hermes 405B | Variable | Free tier |

## Patrones clave

- **crew_factory**: Reconstruye crew en cada retry para saltar providers agotados
- **Modo determinístico**: Ordering fijo + PRNGs con seed
- **Provider chains**: 5+ modelos por rol con fallback automático (`llm_config.py`)
- **CONSTITUTION**: ~50 tokens, inyectada en cada agente
- **Observabilidad interna**: Sin deps externas — todo JSONL propio
- **Zero-LLM governance**: Toda decisión determinística (regex, AST, Z3)

## Logs y outputs

- `logs/traces/` — RunTrace JSON (uno por ejecución)
- `logs/experiments/` — runs.jsonl con métricas agregadas
- `logs/metrics/` — Steps de agentes, governance, supervisor
- `logs/checkpoints/` — JSONL por step para recovery
- `logs/commander/` — commands.jsonl, sessions.json, queue/*.json
- `logs/daemon/` — cycles.jsonl (autonomous daemon)
- `logs/mesh/` — nodes.json, messages.jsonl, inbox/<node>/*.json
- `output/` — Resultados de crews

## Archivo legacy movido

`core/qanion_mimo.py` fue movido a `_internal/core_legacy/qanion_mimo.py` — ya no está en el core activo ni es importado por ningún módulo. El archivo legacy parsea sin errores de sintaxis. No hay nada que limpiar en el código activo.

## Reglas modulares

Las instrucciones de Soberanía y Extracción están en `.claude/rules/`. Se cargan automáticamente según el contexto de edición.

## Estado Actual

Ver: `docs/09_sessions/ESTADO_ACTUAL.md`

## Segundo Cerebro — Obsidian Vault

El Soberano mantiene un **segundo cerebro** en Obsidian con todo el conocimiento del proyecto:

- **Ruta del vault**: `/Users/jquiceva/cerebro cyber/cerebro cyber/`
- **CLI de gestión**: `python3 scripts/second_brain.py`
- **Schema del vault**: `/Users/jquiceva/cerebro cyber/cerebro cyber/CLAUDE.md`

### Estructura del vault
```
wiki/DOF-MESH/       ← arquitectura, estado, plan, aprendizajes
wiki/Claude-Code/    ← patrones Claude Code, Karpathy system, conexión Obsidian
wiki/Blockchain/     ← Conflux, contratos, hackathon
wiki/Proyectos/      ← ecosistema completo de proyectos
raw/                 ← material fuente sin procesar
outputs/             ← análisis generados con fecha
templates/           ← plantillas para nuevas notas
```

### Comandos del segundo cerebro
```bash
python3 scripts/second_brain.py health              # estado del vault
python3 scripts/second_brain.py sync                # sync docs/ DOF → vault
python3 scripts/second_brain.py add 'título' --content 'texto' --tags tag1,tag2
python3 scripts/second_brain.py process             # procesa raw/
python3 scripts/second_brain.py watch               # vigila raw/ en tiempo real
python3 scripts/second_brain.py search 'query'      # busca en el vault
```

### Regla: cuándo actualizar el vault
- Al aprender algo nuevo sobre DOF-MESH → `second_brain.py add`
- Al cerrar una sesión de trabajo → `second_brain.py sync`
- Al recibir información nueva del Soberano → guardar primero en `raw/`, luego `process`
- Si el Soberano dice "guarda esto en Obsidian" → ejecutar `add` de inmediato

---

## Stack Automático de Trabajo

Reglas que aplican SIEMPRE sin instrucciones adicionales:

| Tarea | Herramienta oficial |
|---|---|
| Construir prompt | arquitecto-claudio (7/7 técnicas) |
| Crear skill | dof-skill-creator (7 pasos) |
| Convertir documento | markitdown-converter |
| Cerrar sesión | dof-session-report (HTML+MD+commit) |
| Arrancar sesión | Lee CLAUDE.md + ESTADO_ACTUAL.md |
| Extraer URL o página | web_fetch → markitdown si aplica |
| Escribir código | Leer archivos existentes primero |
| Hacer push | CI verde + doble revisión pre-commit |
| Guardar conocimiento | second_brain.py add/sync |

## datos-colombia-mcp — Uso conversacional

Consulta datos abiertos colombianos directamente desde Claude Code o scripts:

```python
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'integrations/datos-colombia')
from core.gateway.router import TOOL_MAP

# Buscar contratos SECOP II en vivo (datos.gov.co)
contratos = TOOL_MAP['secop_search']({
    'municipio': 'MEDELLIN',   # o 'entity': 'ALCALDIA DE MEDELLIN'
    'year': 2025,              # opcional — filtra por fecha_de_firma
    'limit': 20,               # default 20
})
# → {'contracts': [...], 'count': N}

# Detectar anomalías de fraccionamiento (Ley 80 Art. 24)
alertas = TOOL_MAP['secop_anomalies']({
    'entity': 'ALCALDIA DE MEDELLIN',
    'threshold': 3,            # mínimo contratos mismo contratista/mes
})
# → {'entity': ..., 'fraccionamiento': [...], 'concentracion': [...]}

# Buscar datasets MEData (medata.gov.co — puede estar caído)
datasets = TOOL_MAP['medata_search']({
    'query': 'empleo formal',
    'limit': 10,
})
# → {'success': bool, 'result': [...], 'count': N}
```

Demo completa: `python3 scripts/demo_rutan.py`

## MCPs Obsidian — Auditoría de Seguridad 2026-04-16

Auditados con supply_chain_guard + inspección código fuente + npm audit.

| MCP | Versión | Veredicto | Razón |
|---|---|---|---|
| `@bitbonsai/mcpvault` | 0.11.0 | ✅ APROBADO | 0 eval/exec/network, 14 tools, BM25, path sandbox |
| `mcp-obsidian` (calclavia) | 1.0.0 | ✅ OK limitado | 0 eval/exec, solo 2 tools (read+search) |
| `obsidian-claude-code-mcp` (iansinnott) | 1.1.8 | 🔴 NO INSTALAR | `new Function()` RCE vía `obsidian_api` tool — vector prompt injection desde datos SECOP/MEData |

**Regla:** No instalar `obsidian-claude-code-mcp`. El tool `obsidian_api` ejecuta JS arbitrario con acceso al vault Obsidian completo. Un nombre de contrato malicioso en SECOP podría convertirse en RCE via prompt injection.
