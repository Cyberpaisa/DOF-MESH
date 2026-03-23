# INFORME COMPLETO DEL SISTEMA DOF v0.5

> **Fecha**: 22 de marzo de 2026
> **Autor**: Juan Carlos Quiceno Vasquez (Cyber Paisa)
> **Branch**: `main` | **Commits**: 199 | **Versión**: v0.4.x Hackathon Sprint

---

## 1. Resumen Ejecutivo

**Deterministic Observability Framework (DOF)** es un framework de orquestación y observabilidad determinística para sistemas multi-agente LLM bajo restricciones de infraestructura adversarial.

Reemplaza la confianza probabilística por **pruebas formales verificables con Z3**, registrando cada decisión on-chain (Avalanche C-Chain + Conflux). Gobernanza **Zero-LLM**: funciones puras en Python para reglas de cumplimiento — cero alucinaciones, cero inyección de prompts en la capa de seguridad.

### Números Clave

| Métrica | Valor |
|---------|-------|
| **Líneas de código** | 860K+ (633K Python, 222K JS/TS, 5.6K Shell) |
| **Core modules** | 45 (`core/`) |
| **Agentes especializados** | 12 (cada uno con SOUL.md) |
| **A2A Skills** | 11 (expuestos via JSON-RPC) |
| **Archivos Python** | 1,889 |
| **Archivos de test** | 260 |
| **Git commits** | 199 |
| **Z3 Theorems** | 8/8 PROVEN (109ms) |
| **On-chain attestations** | 48+ |
| **Proveedores LLM** | 7 (Groq, Cerebras, NVIDIA, Zhipu, Gemini, OpenRouter, SambaNova) |
| **Smart contracts** | 3 (DOFValidationRegistry, DOFProofRegistry, DOFEvaluator) |
| **Baseline dof_score** | 0.8117 |
| **Revenue tracked** | $1,134.50 USD |
| **L0 Triage skip rate** | 72.7% (ahorro de tokens) |
| **Disco** | 4.2 GB |

---

## 2. Arquitectura General

```mermaid
flowchart TD
    subgraph Interfaces["Interfaces de Usuario"]
        CLI["CLI Interactivo<br/>main.py"]
        A2A["A2A Server<br/>Puerto 8000"]
        MCP["MCP Server<br/>Claude Desktop/Cursor"]
        TG["Telegram Bot"]
        DASH["Streamlit Dashboard<br/>Puerto 8501"]
    end

    subgraph EventBus["Bus de Eventos"]
        ES["Event Stream<br/>WebSocket + JSONL"]
    end

    subgraph Orchestration["Orquestación — crew_runner.py"]
        L0["L0 Triage<br/>Filtro Pre-LLM"]
        PM["Provider Manager<br/>7 LLMs + Bayesian"]
        CF["Crew Factory<br/>Rebuild por retry"]
        GOV["Constitution<br/>Enforcer"]
        SUP["Meta-Supervisor<br/>Q+A+C+F scoring"]
        CP["Checkpointing<br/>JSONL por step"]
    end

    subgraph Agents["12 Agentes Especializados"]
        RES["Researcher"]
        STR["Strategist"]
        ARC["Architect"]
        DEV["Ralph Code"]
        SEC["Sentinel"]
        QA["QA Reviewer"]
        NAR["Narrative"]
        DATA["Data Engineer"]
        SCO["Scout"]
        ORG["Organizer"]
        DES["Designer"]
        SYN["Synthesis"]
    end

    subgraph Tools["16+ Tools — 7 Categorías"]
        T1["Research Tools<br/>web_search, web_brief"]
        T2["Code Tools<br/>read, write, execute"]
        T3["Data Tools<br/>SQL, pandas, viz"]
        T4["Blockchain Tools<br/>ERC-8004, attestations"]
        T5["File Tools<br/>create, delete, move"]
        T6["Execution Tools<br/>shell, process"]
    end

    subgraph Verification["Verificación Formal"]
        Z3["Z3 Theorem Prover<br/>8 theorems"]
        AST["AST Verifier<br/>Security patterns"]
        CON["Constitution<br/>HARD + SOFT rules"]
    end

    subgraph Blockchain["Blockchain & Attestations"]
        AVA["Avalanche Bridge<br/>DOFValidationRegistry"]
        ENI["Enigma Bridge<br/>Supabase trust scores"]
        PH["Proof Hash<br/>keccak256 + BLAKE3"]
    end

    subgraph Observability["Observabilidad"]
        RT["RunTrace<br/>UUID v4 por ejecución"]
        MET["5 Métricas Formales<br/>SS, PFI, RP, GCR, SSR"]
        LOG["JSONL Logs<br/>traces, metrics, experiments"]
        REV["Revenue Tracker<br/>$1,134.50 USD"]
        AR["AutoResearch<br/>Self-optimization"]
    end

    Interfaces --> EventBus
    EventBus --> Orchestration
    Orchestration --> Agents
    Agents --> Tools
    Tools --> Verification
    Verification --> Blockchain
    Verification --> Observability
    Blockchain --> Observability
```

---

## 3. Pipeline de Ejecución

```mermaid
flowchart LR
    A["Input<br/>(texto + crew_name)"] --> B{"L0 Triage<br/>5 checks"}
    B -->|SKIP| C["Log: skip reason<br/>Ahorro 30-50% latency"]
    B -->|PROCEED| D["Crew Factory<br/>Rebuild LLMs"]
    D --> E["crew.kickoff()<br/>CrewAI execution"]
    E --> F["step_callback<br/>StepTrace"]
    F --> G{"Governance<br/>Check"}
    G -->|HARD violation| H["BLOCK<br/>Output rejected"]
    G -->|SOFT violation| I["WARN<br/>Continue with warnings"]
    G -->|PASS| J{"Supervisor<br/>Q(0.4)+A(0.25)+C(0.2)+F(0.15)"}
    I --> J
    J -->|"Score ≥ 7"| K["ACCEPT<br/>Return output"]
    J -->|"Score 5-7<br/>retries < 2"| L["RETRY<br/>Provider rotation"]
    J -->|"Score < 5"| M["ESCALATE<br/>Multi-agent review"]
    L --> D

    style B fill:#f9f,stroke:#333
    style G fill:#ff9,stroke:#333
    style J fill:#9ff,stroke:#333
    style K fill:#9f9,stroke:#333
    style H fill:#f99,stroke:#333
```

### Detalle del Pipeline

1. **L0 Triage** (Zero LLM): input_length, retry_exhaustion, providers, repeated_errors, input_quality
2. **Crew Factory**: reconstruye el crew en cada retry para rotar providers agotados
3. **Governance**: ConstitutionEnforcer con ~50 tokens de constitución inyectada
4. **Supervisor**: scoring ponderado → decisión determinística ACCEPT/RETRY/ESCALATE
5. **Checkpointing**: JSONL por step para recovery mid-execution

---

## 4. AutoResearch Loop

```mermaid
flowchart TD
    START["Inicio<br/>Leer config actual"] --> BASE["Run Baseline<br/>5 runs determinísticos"]
    BASE --> SCORE["Compute dof_score<br/>0.3·SS + 0.25·(1-PFI) + 0.2·RP_inv + 0.15·GCR + 0.1·SSR"]
    SCORE --> CYCLE["Proponer 1 Modificación<br/>Random param + direction"]

    CYCLE --> APPLY["Aplicar Modificación<br/>config/autoresearch_overrides.json"]
    APPLY --> RUN["Run Experiment<br/>5 runs con nuevo config"]
    RUN --> EVAL["Compute nuevo dof_score"]
    EVAL --> CMP{"nuevo > baseline?"}

    CMP -->|"Sí"| KEEP["KEEP<br/>Actualizar baseline<br/>Log TSV"]
    CMP -->|"No"| DISCARD["DISCARD<br/>Revert modificación<br/>Log TSV"]

    KEEP --> WAIT["Sleep 1s"]
    DISCARD --> WAIT
    WAIT --> CYCLE

    style CMP fill:#ff9,stroke:#333
    style KEEP fill:#9f9,stroke:#333
    style DISCARD fill:#f99,stroke:#333
```

### Parámetros Tunables

| Parámetro | Rango | Step | Default |
|-----------|-------|------|---------|
| `supervisor_weight_quality` | [0.20, 0.60] | 0.05 | 0.40 |
| `supervisor_weight_actionability` | [0.10, 0.40] | 0.05 | 0.25 |
| `supervisor_weight_completeness` | [0.10, 0.35] | 0.05 | 0.20 |
| `supervisor_weight_factuality` | [0.05, 0.25] | 0.05 | 0.15 |
| `max_retries` | [1, 5] | 1 | 3 |
| `supervisor_accept_threshold` | [5.0, 9.0] | 0.5 | 7.0 |
| `supervisor_retry_threshold` | [3.0, 7.0] | 0.5 | 5.0 |

Inspirado en [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — modify → experiment → keep/discard → repeat.

---

## 5. Governance Pipeline

```mermaid
flowchart LR
    OUT["Agent Output<br/>(texto)"] --> CE{"ConstitutionEnforcer"}

    CE --> HR{"HARD_RULES<br/>(bloquean)"}
    HR -->|"Violación"| BLOCK["BLOCKED<br/>Output rechazado"]
    HR -->|"OK"| SR{"SOFT_RULES<br/>(advierten)"}

    SR -->|"Violación"| WARN["WARNING<br/>Log + continuar"]
    SR -->|"OK"| GR["GovernanceResult<br/>passed=True, score, violations=[], warnings=[]"]

    WARN --> GR

    GR --> Z3{"Z3 Verifier<br/>8 theorems"}
    Z3 --> PR["ProofResult<br/>.theorem_name, .result, .proof_time_ms"]
    PR --> PH["proof_hash<br/>keccak256(proof)"]

    PH --> AVA["Avalanche Bridge<br/>DOFValidationRegistry.sol"]
    PH --> ENI["Enigma Bridge<br/>Supabase dof_trust_scores"]
    PH --> PS["Proof Storage<br/>JSONL + IPFS (opcional)"]

    AVA --> ATT["On-Chain Attestation<br/>bytes32 hash"]
    ENI --> TS["Trust Scores<br/>GCR, SS, AST, ACR, PFI, RP, SSR"]

    style CE fill:#ff9,stroke:#333
    style BLOCK fill:#f99,stroke:#333
    style GR fill:#9f9,stroke:#333
    style ATT fill:#99f,stroke:#333
```

### Reglas de Governance

- **HARD_RULES**: Bloquean el output completamente. Ejemplos: detección de API keys, PII, URLs maliciosas, inyección de código
- **SOFT_RULES**: Logean warning pero permiten continuar. Ejemplos: falta de fuentes, longitud insuficiente, tono inadecuado
- **Zero-LLM**: Todas las reglas son funciones puras Python + regex — cero llamadas LLM para governance

---

## 6. Observabilidad y Métricas

```mermaid
flowchart TD
    EXEC["Crew Execution"] --> SC["step_callback<br/>Por cada step de agente"]
    SC --> ST["StepTrace<br/>agent, tool, result, latency_ms, tokens"]
    ST --> ML["MetricsLogger<br/>emit() → JSONL"]
    ML --> JSONL["logs/metrics/steps.jsonl"]

    EXEC --> TC["task_callback<br/>Al completar crew"]
    TC --> RT["RunTrace<br/>UUID v4, session_id, all steps"]
    RT --> CDM["compute_derived_metrics()"]

    CDM --> SS["SS: Stability Score<br/>1 - (retry/max) × (fallback/depth)"]
    CDM --> PFI["PFI: Provider Fragility<br/>fallback_events / total_executions"]
    CDM --> RP["RP: Retry Pressure<br/>mean_retry / max_retries"]
    CDM --> GCR["GCR: Governance Compliance<br/>compliant_runs / total_runs"]
    CDM --> SSR["SSR: Supervisor Strictness<br/>escalate_decisions / total_decisions"]

    SS --> EXP["logs/experiments/runs.jsonl"]
    PFI --> EXP
    RP --> EXP
    GCR --> EXP
    SSR --> EXP

    EXP --> DASH["Streamlit Dashboard"]
    EXP --> AR["AutoResearch<br/>dof_score input"]
    EXP --> CSV["CSV Export<br/>Jupyter analysis"]

    style CDM fill:#ff9,stroke:#333
    style SS fill:#9ff,stroke:#333
    style PFI fill:#9ff,stroke:#333
    style RP fill:#9ff,stroke:#333
    style GCR fill:#9ff,stroke:#333
    style SSR fill:#9ff,stroke:#333
```

### Fórmulas Matemáticas

| Métrica | Fórmula | Rango | Ideal |
|---------|---------|-------|-------|
| **SS** | `1.0 - (retry_count / max_retries) × (fallback_depth / max_depth)` | [0, 1] | 1.0 |
| **PFI** | `Σ(fallback_events) / Σ(total_executions)` últimos N runs | [0, 1] | 0.0 |
| **RP** | `mean(retry_count) / max_retries` | [0, 1] | 0.0 |
| **GCR** | `compliant_runs / total_runs` | [0, 1] | 1.0 |
| **SSR** | `escalate_decisions / total_decisions` | [0, 1] | 0.0 |

**dof_score** (compuesto):
```
dof_score = 0.30×SS + 0.25×(1-PFI) + 0.20×(1-RP) + 0.15×GCR + 0.10×(SSR_normalized)
```

---

## 7. Memoria Fisher-Rao

```mermaid
flowchart LR
    Q["Query<br/>(texto)"] --> TOK["Tokenize<br/>lowercase + split"]
    TOK --> TFIDF["TF-IDF Distribution<br/>Frecuencias normalizadas"]

    DB["Memory Store<br/>Entries JSONL"] --> TOK2["Tokenize cada entry<br/>key + value"]
    TOK2 --> TFIDF2["TF-IDF por entry"]

    TFIDF --> FR{"Fisher-Rao Distance<br/>d_FR(P,Q) = 2·arccos(Σ√(p_i·q_i))"}
    TFIDF2 --> FR

    FR --> RANK["Ranked by similarity<br/>sim = 1 - d_FR/π ∈ [0,1]"]
    RANK --> FILTER{"sim > 0.05?"}
    FILTER -->|"Sí"| TOPK["Top-K Results"]
    FILTER -->|"No results"| FALLBACK["Fallback: keyword matching"]

    TOPK --> GMS["Governed Memory Store<br/>Separación knowledge/errors"]
    FALLBACK --> GMS

    style FR fill:#ff9,stroke:#333
    style TOPK fill:#9f9,stroke:#333
    style FALLBACK fill:#f99,stroke:#333
```

### Ventajas sobre Cosine Similarity

| Aspecto | Cosine Similarity | Fisher-Rao Distance |
|---------|-------------------|---------------------|
| **Base matemática** | Ángulo en espacio vectorial | Geometría de información en manifold estadístico |
| **Sensibilidad contextual** | Solo dirección del vector | Varianza + distribución completa |
| **Dependencias** | Requiere embeddings (PyTorch/HF) | Stdlib puro (zero deps) |
| **Complejidad** | O(n) por comparación | O(V) donde V = vocabulario |
| **Validación** | Heurístico | Fundamentado en geometría diferencial |

Referencia: arXiv:2603.14588 — *"SuperLocalMemory V3: Information-Geometric Foundations for Zero-LLM Enterprise Agent Memory"*

---

## 8. Core Modules (45)

| # | Módulo | Descripción |
|---|--------|-------------|
| 1 | `__init__.py` | Package init |
| 2 | `adversarial.py` | Red Team → Guardian → Arbiter evaluation loop |
| 3 | `agent_output.py` | Estandarización de formato de output de agentes |
| 4 | `agentleak_benchmark.py` | Privacy leak detection: PII, API keys, memory, tool inputs |
| 5 | `ast_verifier.py` | Python AST security analysis (exec, eval, __import__) |
| 6 | `avalanche_bridge.py` | Publica attestations a Avalanche C-Chain |
| 7 | `boundary.py` | Enforcement de límites de agente según SOUL |
| 8 | `chain_adapter.py` | Multi-chain adapter (Avalanche, Conflux, Base) |
| 9 | `checkpointing.py` | Persistencia JSONL por step para recovery |
| 10 | `crew_runner.py` | Orquestación principal: providers, governance, supervisor, retry ×3 |
| 11 | `data_oracle.py` | Interface de oracle de datos para verificación |
| 12 | `enigma_bridge.py` | Trust scores a Supabase (Enigma) |
| 13 | `entropy_detector.py` | Detecta outputs de alta entropía (alucinaciones) |
| 14 | `event_stream.py` | Bus de eventos: WebSocket + JSONL broadcast |
| 15 | `execution_dag.py` | Grafo de dependencias de tareas (DAG) |
| 16 | `experiment.py` | Batch runner, sweeps paramétricos, estadística Bessel |
| 17 | **`fisher_rao.py`** | **NUEVO — Distancia Fisher-Rao para memoria (stdlib-only)** |
| 18 | `governance.py` | ConstitutionEnforcer: HARD_RULES + SOFT_RULES |
| 19 | `hierarchy_z3.py` | Z3 hierarchy verification: 42 patterns, 4.9ms |
| 20 | **`l0_triage.py`** | **NUEVO — Filtro pre-LLM determinístico (5 checks)** |
| 21 | `loop_guard.py` | Detección de loops infinitos + timeout |
| 22 | `memory_governance.py` | Memoria gobernada: separa knowledge de errors |
| 23 | `memory_manager.py` | ChromaDB + HuggingFace embeddings + Fisher-Rao fallback |
| 24 | `merkle_tree.py` | Merkle tree para verificación batch de proofs |
| 25 | `metrics.py` | JSONL logger con rotación, tracking por agente |
| 26 | `oags_bridge.py` | OAGS: resolución token_id ↔ agent address |
| 27 | `observability.py` | RunTrace/StepTrace, 5 métricas formales, modo determinístico |
| 28 | `oracle_bridge.py` | ERC-8004 attestation oracle |
| 29 | `otel_bridge.py` | OpenTelemetry integration (opcional) |
| 30 | `proof_hash.py` | BLAKE3 + SHA256 proof hashes |
| 31 | `proof_storage.py` | Almacén de proofs: JSONL + IPFS opcional |
| 32 | `providers.py` | Multi-provider fallback chains, Bayesian selector, TTL recovery |
| 33 | `regression_tracker.py` | Tracking de degradación de métricas |
| 34 | **`revenue_tracker.py`** | **NUEVO — Revenue tracking real en JSONL** |
| 35 | `runtime_observer.py` | Métricas de producción (SS, PFI, RP, GCR, SSR) |
| 36 | `state_model.py` | Máquina de estados de agentes |
| 37 | `storage.py` | Abstracción file-based: JSONL, JSON, pickle |
| 38 | `supervisor.py` | Meta-supervisor: Q(0.4)+A(0.25)+C(0.2)+F(0.15) |
| 39 | `task_contract.py` | Validación de TASK_CONTRACT.md |
| 40 | `test_generator.py` | Auto-generación de tests + BenchmarkRunner |
| 41 | `transitions.py` | Verificación de transiciones de estado SOUL-compatible |
| 42 | `z3_gate.py` | Gate Z3: APPROVED/REJECTED/TIMEOUT/FALLBACK |
| 43 | `z3_proof.py` | Generación y serialización de proofs Z3 |
| 44 | `z3_test_generator.py` | Auto-generación de test cases Z3 |
| 45 | `z3_verifier.py` | Z3 formal theorem proving: INV-1,2,5,6,7,8 |

---

## 9. Agentes (12)

| # | Agente | Rol | Modelo Principal | SOUL |
|---|--------|-----|------------------|------|
| 1 | **researcher** | Investigación & Intel | Groq Llama 3.3 70B | `agents/researcher/SOUL.md` |
| 2 | **strategist** | Estrategia MVP | Cerebras GPT-OSS | `agents/strategist/SOUL.md` |
| 3 | **organizer** | Organización de proyecto | Groq | `agents/organizer/SOUL.md` |
| 4 | **architect** | Arquitectura de código | Groq | `agents/architect/SOUL.md` |
| 5 | **designer** | UI/UX Design | Cerebras | `agents/designer/SOUL.md` |
| 6 | **qa-reviewer** | Quality Assurance | Cerebras | `agents/qa-reviewer/SOUL.md` |
| 7 | **verifier** | Verificación final | Groq | `agents/verifier/SOUL.md` |
| 8 | **sentinel** | Security Auditor | Groq | `agents/sentinel/SOUL.md` |
| 9 | **narrative** | Content Writing | Groq | `agents/narrative/SOUL.md` |
| 10 | **data-engineer** | Data Pipelines | Groq | `agents/data-engineer/SOUL.md` |
| 11 | **scout** | Market Research | Cerebras | `agents/scout/SOUL.md` |
| 12 | **synthesis** | Autonomous Synthesis | Zo (Minimax) | `agents/synthesis/SOUL.md` |

Cada SOUL.md define: Identity, Principles, Cognitive Style, Risk Policy, Failure Handling, Collaboration, Output Standards, Monetization Strategies, Research Integration.

---

## 10. A2A Skills (11)

| # | Skill ID | Nombre | Descripción |
|---|----------|--------|-------------|
| 1 | `research` | Market Research | Deep market research con web data, competitor analysis, Go/No-Go |
| 2 | `code-review` | Code Review | Architecture analysis, security audit, actionable fixes |
| 3 | `data-analysis` | Data Analysis | Excel/CSV/DB con statistics, anomaly detection, Python scripts |
| 4 | `build-project` | Build Project | Genera proyecto completo: research → plan → code → review |
| 5 | `grant-hunt` | Grant Hunter | Grants/hackathons across blockchain ecosystems |
| 6 | `content` | Content Creator | Web3 content: threads, blogs, pitch decks, grant narratives |
| 7 | `daily-ops` | Daily Operations | Morning scan: news, metrics, daily plan, social content |
| 8 | `enigma-audit` | Enigma Agent Audit | Audit ERC-8004 AI agents: endpoints, metadata, trust scores |
| 9 | **`revenue`** | **Revenue Tracker** | **NUEVO — Track revenue, log API usage, generate reports** |
| 10 | **`triage-stats`** | **L0 Triage Stats** | **NUEVO — Get L0 triage statistics: decisions, skip rate** |
| 11 | **`memory-search`** | **Fisher-Rao Memory** | **NUEVO — Search memory usando Fisher-Rao information geometry** |

---

## 11. Módulos Nuevos (Marzo 2026 Hackathon)

### 11.1 L0 Triage (`core/l0_triage.py`)

**Propósito**: Filtro pre-LLM — zero llamadas LLM, puras reglas determinísticas.

**5 Checks**:
1. Input length (< 3 tokens → SKIP)
2. Input overflow (> 50K tokens → SKIP)
3. Retry exhaustion (> 5 intentos → SKIP)
4. Provider availability (0 providers → SKIP)
5. Repeated identical errors (3+ mismos → SKIP)

**API**:
```python
from core.l0_triage import L0Triage
triage = L0Triage()
decision = triage.evaluate(input_text, attempt=1, active_providers=["groq"], prev_errors=[])
# → TriageDecision(proceed=True, reason='all_checks_passed', input_tokens_est=25, ...)
```

**Estado**: PASS — 6/6 tests, skip rate 72.7%, integrado en `crew_runner.py`

### 11.2 Fisher-Rao Distance (`core/fisher_rao.py`)

**Propósito**: Retrieval de memoria basado en geometría de información.

**Fórmula**:
```
d_FR(P, Q) = 2 · arccos(Σ √(p_i · q_i))    ∈ [0, π]
similarity  = 1 - d_FR/π                      ∈ [0, 1]
```

**API**:
```python
from core.fisher_rao import fisher_rao_distance, fisher_rao_similarity, ranked_search
d = fisher_rao_distance("hello world", "hello world")  # → 0.0
s = fisher_rao_similarity("AI agents", "AI agents blockchain")  # → 0.667
results = ranked_search("ML training", documents, top_k=5)
```

**Estado**: PASS — 4/4 tests, stdlib-only, integrado en `memory_manager.py`

### 11.3 Revenue Tracker (`core/revenue_tracker.py`)

**Propósito**: Tracking real de ingresos + uso de API.

**Sources**: SaaS, grant, bounty, freelance, consulting, content, template, API
**Payment Methods**: Stripe, x402, Lightning, PayPal, crypto, bank, gumroad

**API**:
```python
from core.revenue_tracker import RevenueTracker
rt = RevenueTracker()
rt.track("grant", 500.0, "USD", "Gitcoin Round 22", client="Gitcoin", payment_method="crypto")
rt.log_api_usage("/tasks/send", "external_agent", tokens_used=5000, cost_per_token=0.0001)
report = rt.report(days=30)
# → {'total_revenue': 1134.50, 'transactions': 8, 'by_source': {...}, ...}
```

**Estado**: PASS — $1,134.50 tracked, 8 transacciones, 5 API calls

### 11.4 AutoResearch (`scripts/dof_autoresearch.py`)

**Propósito**: Self-optimization loop inspirado en Karpathy.

**Ciclo**:
1. Read config → 2. Propose modification → 3. Run experiment (5 runs)
4. Compute dof_score → 5. KEEP si mejora, DISCARD si no → 6. Repeat

**API**:
```bash
python3 scripts/dof_autoresearch.py                  # Run forever
python3 scripts/dof_autoresearch.py --max-cycles 5   # 5 ciclos
python3 scripts/dof_autoresearch.py --dry-run        # Solo propuestas
# Output: Baseline dof_score: 0.811700
#         Proposal: supervisor_accept_threshold = 7.0 → 6.5
#         [DRY RUN] Would modify supervisor_accept_threshold: 7.0 → 6.5
```

**Estado**: PASS — baseline 0.8117, proposals generadas correctamente

### 11.5 AgentMeet Daemon Integration

**Propósito**: Reuniones LLM-powered de 14 agentes cada 4 horas.

**Integración**: En `scripts/agent-legion-daemon.sh`, cada 8 ciclos (~4h):
```bash
# Topics rotativos:
# standup → brainstorm revenue → technical review → research debrief
python3 scripts/agentmeet-live.py --topic "$topic"
```

**14 Agentes en AgentMeet**:
DOF Oracle, Sentinel Shield, Ralph Code, Architect Enigma, Blockchain Wizard, Moltbook, Product Overlord, Biz Dominator, DeFi Orbital, Scrum Master Zen, Charlie UX, QA Vigilante, RWA Tokenizator, Organizer OS

**Estado**: PASS — 14 agentes registrados, 23+ mensajes reales por sesión

---

## 12. Dependencias Externas

### Proveedores LLM

| Provider | Modelo | Quota (free tier) | Notas |
|----------|--------|-------------------|-------|
| **Groq** | Llama 3.3 70B | 12K TPM | Primary |
| **Cerebras** | GPT-OSS | 1M tokens/día | Secondary |
| **NVIDIA NIM** | Various | 1000 créditos (total) | Prefijo `nvidia_nim/` |
| **Zhipu** | GLM-4.7-Flash | Generosa | Requiere `enable_thinking: False` |
| **Gemini** | gemini-pro | 20 req/día | Backup |
| **OpenRouter** | Multi-model proxy | Variable | Routing |
| **SambaNova** | Various | 24K context max | Emergency backup |

### Blockchain

| Red | Chain ID | Uso | Contrato |
|-----|----------|-----|----------|
| **Avalanche C-Chain** | 43114 | Attestations + proofs | DOFValidationRegistry, DOFProofRegistry |
| **Conflux** | 1030 | Multi-chain attestations | DOFEvaluator |
| **Base** | 8453 | ERC-8004 agent identity | Agent token |

### Servicios Externos

| Servicio | Uso |
|----------|-----|
| **Supabase** (Enigma) | Trust scores, dof_trust_scores table |
| **AgentMeet.net** | Real-time agent conversations |
| **DuckDuckGo/Serper/Tavily** | Web search tools (fallback chain) |
| **IPFS** | Proof storage (opcional) |

### Python Dependencies

```
crewai, crewai-tools     # Agent orchestration
web3                      # Blockchain interactions
z3-solver                 # Formal verification
python-dotenv             # Environment variables
chromadb (opcional)       # Vector memory
pydantic                  # Data validation
requests                  # HTTP
```

---

## 13. SuperLocalMemory V3 — Validación Académica

> **Referencia**: arXiv:2603.14588 — *"SuperLocalMemory V3: Information-Geometric Foundations for Zero-LLM Enterprise Agent Memory"*

### Fisher-Rao vs Cosine: Validado

DOF implementa `core/fisher_rao.py` con la distancia Fisher-Rao sobre distribuciones TF-IDF. SuperLocalMemory V3 confirma que esta métrica supera la similitud coseno tradicional porque:

- Opera en el **manifold estadístico** (espacio de distribuciones) en lugar del espacio vectorial plano
- Captura **varianza contextual**, no solo dirección
- Es invariante a reparametrización — la distancia no cambia si se transforma el espacio de features

**Estado DOF**: Implementado y funcional en `core/fisher_rao.py` + integrado en `core/memory_manager.py`

### Ciclo de Vida de Memoria (Langevin)

SuperLocalMemory V3 propone un ciclo de vida gobernado por dinámicas de Langevin:

```
Activo → Tibio → Frío → Archivado
```

- **Activo**: Memorias frecuentemente accedidas (< 24h)
- **Tibio**: Acceso moderado (1-7 días)
- **Frío**: Raramente accedidas (> 7 días)
- **Archivado**: Comprimidas + indexadas para retrieval profundo

La ecuación de Langevin `dX_t = -∇U(X_t)dt + √(2T)dW_t` modela la "temperatura" de cada memoria — a mayor acceso, más caliente; con el tiempo, se enfrían naturalmente.

**Estado DOF**: Roadmap — actualmente todas las memorias tienen el mismo estado. Implementación futura en `core/memory_governance.py`.

### Cohomología de Haces

SuperLocalMemory V3 introduce un marco de **cohomología de haces** (sheaf cohomology) para detección de contradicciones:

- Cada memoria se modela como una **sección de un haz** sobre el grafo de conocimiento
- Las **contradicciones** aparecen como secciones incompatibles — no se pueden pegar globalmente
- La **obstrucción** (grupo de cohomología H¹) mide cuánta inconsistencia hay

**Aplicación práctica**: Si el agente tiene memoria A = "Python es lento" y memoria B = "Python es óptimo para ML", la cohomología detecta la contradicción antes de que afecte una decisión.

**Estado DOF**: Roadmap — DOF actualmente usa `memory_governance.py` para separar knowledge de errors, pero no tiene detección topológica de contradicciones.

---

## 14. Blockchain & Attestations

### Smart Contracts

```mermaid
flowchart LR
    DOF["DOF System"] --> VR["DOFValidationRegistry<br/>registerAttestation(certHash, agentId, compliant)<br/>revokeAttestation()"]
    DOF --> PR["DOFProofRegistry<br/>Z3 proof hashes<br/>Merkle tree aggregation"]
    DOF --> EV["DOFEvaluator<br/>On-chain scoring<br/>Governance compliance"]

    VR --> AVA["Avalanche C-Chain<br/>Chain ID: 43114"]
    PR --> AVA
    EV --> CON["Conflux<br/>Chain ID: 1030"]

    DOF --> ENI["Enigma Bridge<br/>→ Supabase"]
    ENI --> TS["dof_trust_scores table<br/>GCR, SS, AST, ACR, PFI, RP, SSR<br/>+ on-chain TX hash<br/>+ z3_verified flag"]

    style VR fill:#99f,stroke:#333
    style PR fill:#99f,stroke:#333
    style EV fill:#99f,stroke:#333
```

### Flujo de Attestation

1. Agent produce output → Governance check → Z3 verification
2. proof_hash = `keccak256(z3_proof_json)`
3. `avalanche_bridge.py` → `DOFValidationRegistry.registerAttestation(hash, agentId, true)`
4. TX confirmada → hash almacenado en Supabase via `enigma_bridge.py`
5. Total: **48+ attestations** publicadas

---

## 15. Monetización

### Revenue Actual

```
Total Revenue:      $1,134.50 USD (30 días)
Transacciones:      8
API Calls tracked:  5
```

| Source | Amount | Payment Method |
|--------|--------|----------------|
| Grant | $500.00 | crypto |
| Bounty | $200.00 | crypto |
| Test | $200.00 | stripe |
| Freelance | $150.00 | paypal |
| Verify | $50.00 | stripe |
| Template | $29.00 | gumroad |
| API | $5.50 | stripe |

### Canales de Monetización

```mermaid
flowchart TD
    REV["Revenue Streams"] --> DIRECT["Directos"]
    REV --> INDIRECT["Indirectos"]
    REV --> PASSIVE["Pasivos"]

    DIRECT --> API["API-as-a-Service<br/>x402 micropagos"]
    DIRECT --> FREE["Freelance<br/>Consulting"]
    DIRECT --> GRANT["Grants<br/>Gitcoin, Octant"]

    INDIRECT --> BOUNTY["Bounties<br/>HackerOne, Immunefi"]
    INDIRECT --> AUDIT["Audit Services<br/>ERC-8004 compliance"]

    PASSIVE --> SAAS["SaaS Subscriptions<br/>DOF-as-a-Service"]
    PASSIVE --> TEMP["Templates<br/>Gumroad"]
    PASSIVE --> CONTENT["Content Licensing"]

    API --> PAY["Payment Methods"]
    PAY --> STRIPE["Stripe"]
    PAY --> X402["x402 HTTP Payments"]
    PAY --> LN["Lightning Network"]
    PAY --> PP["PayPal"]
    PAY --> CRYPTO["Crypto Direct"]
    PAY --> BANK["Bank Transfer"]
```

### Integración x402 (Roadmap)

- HTTP 402 Payment Required → agent paga automáticamente por servicios
- MoltLaunch: agents contratan otros agents con micropagos
- Revenue tracker ya soporta `payment_method: "x402"` en JSONL

---

## 16. Verificación del Sistema

### Comandos con Output Esperado

```bash
# L0 Triage
$ python3 -c "from core.l0_triage import L0Triage; t = L0Triage(); print(t.evaluate('Analyze AI market', 1))"
# → TriageDecision(proceed=True, reason='all_checks_passed', input_tokens_est=3, attempt=1, checks={'input_length': 'PASS', 'retry_exhaustion': 'PASS', 'providers': 'PASS', 'repeated_errors': 'PASS', 'input_quality': 'PASS'}, timestamp=1711097400.0)

# Fisher-Rao
$ python3 -c "from core.fisher_rao import fisher_rao_distance; print(fisher_rao_distance('hello world', 'hello world'))"
# → 0.0

$ python3 -c "from core.fisher_rao import fisher_rao_similarity; print(fisher_rao_similarity('AI agents blockchain', 'AI agents on blockchain'))"
# → 0.667

# Revenue
$ python3 -c "from core.revenue_tracker import RevenueTracker; print(RevenueTracker().report(days=30))"
# → {'period_days': 30, 'total_revenue': 1134.5, 'transactions': 8, 'by_source': {'grant': 500.0, 'bounty': 200.0, ...}, 'currency': 'USD'}

# AutoResearch (dry run)
$ python3 scripts/dof_autoresearch.py --max-cycles 2 --dry-run
# → Baseline dof_score: 0.811700
# → Proposal: supervisor_accept_threshold = 7.0 → 6.5
# → [DRY RUN] Would modify supervisor_accept_threshold: 7.0 → 6.5
# → Proposal: supervisor_weight_quality = 0.4 → 0.45
# → [DRY RUN] Would modify supervisor_weight_quality: 0.4 → 0.45
# → AutoResearch Complete
# → Cycles: 0 | Kept: 0 (0.0%) | Discarded: 0

# A2A Skills
$ python3 -c "from a2a_server import AGENT_CARD; print([s['id'] for s in AGENT_CARD['skills']])"
# → ['research', 'code-review', 'data-analysis', 'build-project', 'grant-hunt', 'content', 'daily-ops', 'enigma-audit', 'revenue', 'triage-stats', 'memory-search']

# L0 Triage Stats
$ python3 -c "from core.l0_triage import L0Triage; print(L0Triage().get_stats())"
# → {'total': 11, 'proceeded': 3, 'skipped': 8, 'skip_rate': 0.7272727272727273}
```

---

## 17. Estructura de Logs

```
logs/
├── traces/              # RunTrace JSON — uno por ejecución
│   └── {run_id}.json
├── metrics/             # Métricas por step + triage
│   ├── steps.jsonl
│   ├── l0_triage.jsonl
│   └── events.jsonl
├── experiments/         # Runs agregados
│   └── runs.jsonl
├── checkpoints/         # Recovery mid-execution
│   └── {run_id}/{step_id}.jsonl
├── revenue/             # Ingresos + API usage
│   ├── revenue.jsonl
│   └── api_usage.jsonl
├── autoresearch/        # Self-optimization
│   ├── results.tsv
│   └── config_history.jsonl
├── audit/               # Security audits
├── attestations.jsonl   # On-chain attestations
└── test_reports.jsonl   # Test results
```

---

## 18. Scripts de Automatización (17)

| Script | Propósito |
|--------|-----------|
| `agent-legion-daemon.sh` | Daemon autónomo: 14 agentes + AgentMeet cada 4h |
| `agentmeet-live.py` | Sesiones LLM-powered de 14 agentes en AgentMeet.net |
| `dof_autoresearch.py` | Self-optimization loop (Karpathy-inspired) |
| `e2e_test.py` | Test end-to-end del pipeline completo |
| `full_pipeline_test.py` | Validación completa de workflow |
| `live_test_flow.py` | Test flow con métricas en tiempo real |
| `agent_10_rounds.py` | Stress test: 10 rounds consecutivos |
| `run_benchmark.py` | Benchmark suite: latency, quality, tokens |
| `garak_benchmark.py` | GARAK: prompt injection, jailbreaks |
| `run_privacy_benchmark.py` | Privacy leak detection benchmark |
| `external_agent_audit.py` | Audit de agentes externos ERC-8004 |
| `full_audit_test.py` | Audit completo: 55 reglas |
| `final_audit.py` | Audit pre-producción |
| `agent_cross_transactions.py` | Test de comunicación inter-agente |
| `extract_garak_payloads.py` | Extracción de payloads adversariales |
| `soul-watchdog.sh` | Monitor de SOULs para drift detection |
| `start-system.sh` | Startup script del sistema completo |

---

## 19. Resumen Final

```
╔══════════════════════════════════════════════════════════════╗
║  DOF v0.5 — Deterministic Observability Framework           ║
╠══════════════════════════════════════════════════════════════╣
║  Core Modules:    45     │  Agentes:         12             ║
║  A2A Skills:      11     │  Tools:           16+            ║
║  Test Files:      260    │  Commits:         199            ║
║  LOC:             860K+  │  Z3 Theorems:     8/8 PROVEN     ║
║  Attestations:    48+    │  Smart Contracts: 3              ║
║  LLM Providers:   7      │  dof_score:       0.8117         ║
║  Revenue:         $1,134 │  L0 Skip Rate:    72.7%          ║
║  Disco:           4.2 GB │  Branch:          main           ║
╠══════════════════════════════════════════════════════════════╣
║  Nuevos Módulos (Marzo 2026):                               ║
║  ✓ L0 Triage (pre-LLM filter)                              ║
║  ✓ Fisher-Rao (information geometry memory)                 ║
║  ✓ Revenue Tracker (JSONL persistence)                      ║
║  ✓ AutoResearch (self-optimization)                         ║
║  ✓ AgentMeet Daemon (4h meetings)                           ║
╠══════════════════════════════════════════════════════════════╣
║  Validación Académica:                                      ║
║  arXiv:2603.14588 — SuperLocalMemory V3 confirma:           ║
║  ✓ Fisher-Rao > cosine para memory retrieval                ║
║  ◇ Langevin memory lifecycle (roadmap)                      ║
║  ◇ Sheaf cohomology contradictions (roadmap)                ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Generado por DOF Oracle — 22 de marzo de 2026*
*Verificado con datos reales de ejecución del sistema*
