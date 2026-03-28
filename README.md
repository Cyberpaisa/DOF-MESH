# DOF-MESH

### Después de leer esto, sabrás cómo probar matemáticamente que un agente de IA hizo lo que debía — y tendrás las herramientas para hacerlo en 30 segundos.

<p align="center">
  <img src="docs/diagrams/dof_avatar.png" alt="DOF — El búho que nunca duerme" width="200"/>
  <br/>
  <strong>Matemáticas, no promesas.</strong>
</p>

[![Tests](https://img.shields.io/badge/tests-4,036+-brightgreen)](tests/)
[![Modules](https://img.shields.io/badge/modules-142-blue)](core/)
[![Z3](https://img.shields.io/badge/Z3-4%20theorems%20PROVEN-critical)](core/z3_verifier.py)
[![Chains](https://img.shields.io/badge/chains-5%20(Avalanche%2C%20Base%2C%20Celo%2C%20ETH%2C%20Tempo)-gold)](contracts/)
[![Sentinel](https://img.shields.io/badge/Sentinel-10%20checks%20%2B%20TRACER%206D-blueviolet)](core/sentinel_lite.py)
[![License](https://img.shields.io/badge/license-BSL--1.1-orange)](LICENSE)

---

## Abstract

DOF-MESH (Deterministic Observability Framework) es un sistema de governance formal para agentes autónomos de IA. A diferencia de los frameworks existentes que usan LLMs para supervisar LLMs — introduciendo el mismo vector de fallo que intentan mitigar — DOF emplea verificación formal Z3, análisis estático AST y reglas constitucionales determinísticas. Cada decisión genera una prueba criptográfica (keccak256) registrada inmutablemente en blockchain, creando un audit trail verificable por terceros sin dependencia de modelos probabilísticos.

El sistema integra un ciclo cerrado de desarrollo de IA (Iterate → Evaluate → Deploy → Monitor) con tracing estructurado, evaluación continua y un pipeline de deployment separado para prompts. Validado con 3,844 tests automatizados, deployado en 5 blockchains, y con 238 ciclos autónomos verificados sin intervención humana.

---

## El Problema

La solución obvia para controlar agentes autónomos es usar otra IA como vigilante. Suena lógico. De hecho, así lo hacen casi todos los frameworks del mercado.

Pero es como poner a un ladrón a vigilar a otro ladrón.

Un LLM vigilante puede ser manipulado con el mismo prompt injection que debería detectar. Puede alucinar que todo está bien mientras un atacante drena un treasury. Puede ser "convencido" de ignorar una violación. No puede probar nada — solo opinar.

Y aquí está el detalle que nadie ve: **monitorear no es gobernar**. Puedes tener dashboards preciosos, alertas en Slack, logs inmutables — y aún así tu agente puede actuar mal porque nadie verificó matemáticamente que la acción era válida ANTES de ejecutarla.

DOF no monitorea. DOF prueba. Antes de que la acción ocurra.

---

## Arquitectura — 12 Capas, 0 LLMs

Cada acción de tu agente atraviesa estas capas. Todas son determinísticas. Ninguna consume tokens.

### Governance y Verificación

| Capa | Qué hace | Latencia |
|------|----------|----------|
| **1. Constitution** | Reglas duras (HARD) que bloquean violaciones | <1ms |
| **2. AST Verifier** | Análisis estático del código generado por el agente | <5ms |
| **3. Supervisor** | Meta-evaluación: Q(0.4) + A(0.25) + C(0.2) + F(0.15) | <2ms |
| **4. Adversarial** | Red team automático + detección de prompt injection | <3ms |
| **5. Z3 Formal** | Prueba matemática — 4 teoremas, 42 patrones PROVEN | <20ms |
| **6. ZK Proofs** | Hash criptográfico keccak256 + Merkle batch | <1ms |

### Validación y Mesh

| Capa | Qué hace |
|------|----------|
| **7. Sentinel Engine** | 10 checks paralelos + TRACER 6 dimensiones + Survival |
| **8. Mesh** | 11 nodos LLM coordinados + threshold consensus (FROST) |
| **9. Blockchain** | 5 chains: Avalanche, Base, Celo, ETH, Tempo (Stripe) |

### Ciclo Cerrado (AI Development Lifecycle)

| Capa | Qué hace |
|------|----------|
| **10. Prompt Lifecycle** | Version control + deploy pipeline (dev→staging→prod) + rollback |
| **11. Continuous Eval** | 5 rúbricas + custom + CI gate automático en PRs |
| **12. Tracing** | Spans tipados (llm, governance, z3, sentinel, mesh, tool) |

```
Trace → Log → Dataset → Evaluate → Improve → Deploy → Monitor
  ↑                                                       ↓
  └────────────── Self-improvement (PDR) ←────────────────┘
```

---

## Quick Start

```bash
pip install dof-sdk==0.5.0
dof verify-states          # 4 teoremas Z3 → PROVEN
dof verify-hierarchy       # 42 patrones → PROVEN
dof health --json          # estado completo del sistema
```

```python
from dof import DOFVerifier

verifier = DOFVerifier()
result = verifier.verify_action(
    agent_id="apex-1687",
    action="transfer",
    params={"amount": 500, "token": "USDC"}
)

print(result.verdict)       # APPROVED | REJECTED
print(result.z3_proof)      # prueba formal completa
print(result.attestation)   # tx hash on-chain
```

---

## Métricas del Sistema

| Métrica | Valor |
|---------|-------|
| Módulos core | **142** |
| Tests automatizados | **4,036** passing |
| Teoremas Z3 | **4** probados (exhaustivos para TODOS los inputs) |
| Patrones de jerarquía | **42** PROVEN |
| Checks Sentinel | **10** (paralelos, ThreadPoolExecutor) |
| Dimensiones TRACER | **6** (Trust, Reliability, Autonomy, Capability, Economics, Reputation) |
| Chains activas | **5** (Avalanche, Base, Celo, ETH, Tempo) |
| Attestations on-chain | **21+** mainnet + contratos Tempo |
| Ciclos autónomos sin intervención | **238** |
| Modelos frontier validados | **10** (Experimento Winston v4-Web) |
| LLMs para governance | **0** |

---

## Sentinel Engine — TRACER Scoring

El validador interno evalúa cualquier agente en paralelo:

| Check | Peso | Qué mide |
|-------|------|----------|
| Health | 25% | Respuesta del endpoint <5s |
| Identity | 20% | Formato ERC-8004 válido |
| TLS | - | Certificado SSL, grade A+ a F |
| Latency | 10% | Tiempo de respuesta (<200ms=100) |
| A2A | 15% | Agent-to-Agent capability |
| MCP | 10% | Herramientas expuestas |
| x402/MPP | 5% | Capacidad de pagos |
| On-chain | - | eth_getCode via JSON-RPC |
| Proxy | - | Detección EIP-1967 |
| Ratings | 15% | Reputación comunitaria |

**TRACER**: Trust(20%) + Reliability(20%) + Autonomy(15%) + Capability(20%) + Economics(10%) + Reputation(15%)

**Classifications**: Excellent ≥80 | Good ≥65 | Acceptable ≥50 | Poor ≥35 | Unreliable <35

---

## Prompt Lifecycle — Ciclo Cerrado

DOF trata los prompts como lo que son: **lógica ejecutable de negocio**, no configuraciones desechables.

```
Register (version control)
    ↓
Stage (governance check + secrets scan)
    ↓
Validate (5 checks pre-deploy)
    ↓
Deploy (dev → staging → production)
    ↓
Monitor (continuous eval, 5 rúbricas)
    ↓
Trace (spans tipados por operación)
    ↓
TestBench (batch datasets JSONL)
    ↓
CI Gate (bloquea PR si eval falla)
    ↓
Rollback (si algo sale mal)
```

---

## Seguridad

| Protección | Estado |
|---|---|
| Supply Chain Guard | Blacklist: TeamPCP, Glassworm + IOCs (C2, hashes) |
| Doble revisión pre-commit | Regla canónica — secrets nunca en git |
| ZK Governance Proofs | keccak256 por decisión + Merkle batch |
| Cerberus + Icarus | Containment protocol + DLP |
| Prompt Eval Gate | CI bloquea prompts inseguros automáticamente |

---

## Contratos Deployados

| Chain | Contrato | Address |
|-------|----------|---------|
| Avalanche C-Chain | ERC-8004 Identity | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Avalanche C-Chain | Reputation Registry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |
| Tempo (Stripe) | DOF Identity | `0x94e8Ed614Cb051D9212c7610ECcbAEA58BE02f4e` |
| Tempo (Stripe) | DOF Reputation | `0x432E2ab9d11544A8767559675996e34756E32790` |

---

## Diferenciador

| | **DOF-MESH** | **Otros Frameworks** |
|---|---|---|
| Verificación | Z3 formal (exhaustivo) | LLM-based (probabilístico) |
| Manipulable | No (ecuaciones) | Sí (prompt injection) |
| Pruebas on-chain | 5 chains | No |
| Latencia governance | <30ms | 2-5 segundos |
| Prompt lifecycle | Version control + CI gate + deploy pipeline | String en código |
| Tracing | Spans tipados (6 tipos) | Logs planos |
| Evaluación | Continua (cada output) | Batch manual |
| Auto-mejora | PDR + self-improvement engine | No |
| Sentinel | 10 checks + TRACER 6D + Survival | Básico o ninguno |
| Seguridad supply chain | Guard + IOCs + blacklist | No |

---

## Módulos de Escalado Distribuido (v0.5.1)

Implementados a partir del Experimento Winston — 10 modelos frontier convergieron independientemente en esta arquitectura:

| Módulo | Qué hace |
|--------|----------|
| **Z3 Proof Caching** | Memoization SMT: constraints idénticos no se re-suelven (-40% latencia) |
| **Z3 Portfolio Solving** | Múltiples estrategias Z3 en paralelo, short-circuit al primer resultado |
| **Z3 Fast Path** | Políticas ya verificadas se sirven sin tocar Z3 (~70% de queries) |
| **Versioned Cache** | Cache con epoch TTL — auto-expira cuando Constitution cambia |
| **Adaptive Circuit Breaker** | Cuarentena agentes con >15% block rate (ventana 60s) |
| **Byzantine Node Guard** | Reputación 0.0-1.0 por nodo, cuarentena automática <0.3 |
| **Constitution Integrity Watcher** | SHA-256 del árbol de reglas vs baseline, drift detection <30s |
| **Constitution Update Coordinator** | Two-phase commit con quorum 67% para updates |
| **Constitution Hash Beacon** | Broadcast de hash canónico cada N bloques, HALT automático si diverge |
| **Context Epoch System** | Nodos con epoch desactualizado rechazan queries hasta sincronizar |
| **Merkle Attestation Batching** | N decisiones → 1 Merkle root on-chain (-70% gas) |
| **Node Capability Manifest** | Nodos declaran capacidades, routing por tier (Core/Standard/Edge) |
| **CRDT Memory Layer** | GCounter + LWW-Register: sincronización sin consenso |

> **Validación:** Estas 13 arquitecturas fueron propuestas independientemente por 7-10 modelos frontier sin coordinación. Cuando 10 mentes llegan al mismo diseño por separado, el diseño probablemente es correcto.

---

## Experimento Winston — Validación Multi-Modelo

10 modelos frontier evaluados con y sin framework de comunicación Winston:

```
Modelo              BLUE(Winston)  RED(baseline)  Delta
─────────────────────────────────────────────────────
DeepSeek-V3           88.7          38.7         +50.0
GLM-4.5               90.0          42.7         +47.3
Mistral-Large         78.7          41.3         +37.4
Claude Sonnet         90.0          56.0         +34.0
ChatGPT-4o            88.7          63.0         +25.7
Gemini-2.5Pro         84.7          71.3         +13.4
Perplexity-Sonar      82.0          70.0         +12.0
MiniMax-M2            76.0          66.7          +9.3
Kimi-K2               64.0          58.0          +6.0
─────────────────────────────────────────────────────
Promedio                                        +26.1
```

Scorer determinístico (0 LLMs): Claridad + Relevancia + Estructura + Sorpresa + Cierre accionable.
Datos completos: [`experiments/winston_vs_baseline/`](experiments/winston_vs_baseline/)

---

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/INDEX.md](docs/INDEX.md) | Mapa completo — 123 documentos categorizados |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Arquitectura de 12 capas |
| [docs/BOOK_CH22_EXPERIMENTO_WINSTON.md](docs/BOOK_CH22_EXPERIMENTO_WINSTON.md) | Capítulo 22 — Experimento Winston completo |
| [docs/IMPLEMENTACIONES_EXPERIMENTO_WINSTON.md](docs/IMPLEMENTACIONES_EXPERIMENTO_WINSTON.md) | 16 implementaciones extraídas del experimento |
| [docs/COMPETITION_BIBLE.md](docs/COMPETITION_BIBLE.md) | Inteligencia competitiva (685 proyectos analizados) |
| [docs/WINSTON_COMMUNICATION_FRAMEWORK.md](docs/WINSTON_COMMUNICATION_FRAMEWORK.md) | Framework de comunicación MIT |
| [docs/TEMPO_DEPLOY_GUIDE.md](docs/TEMPO_DEPLOY_GUIDE.md) | Deploy en blockchain de Stripe |
| [docs/ADALINE_ANALYSIS.md](docs/ADALINE_ANALYSIS.md) | Análisis de plataforma + 30 ideas |
| [docs/SECURITY_REPORT_2026-03-27.md](docs/SECURITY_REPORT_2026-03-27.md) | Auditoría de seguridad |

---

## Contribución

DOF-MESH usa una regla de doble revisión obligatoria. Antes de cada commit:

1. `git diff --cached` — verificar que NO haya secrets
2. Correr `python3 -m unittest discover -s tests` — todos deben pasar
3. Si toca prompts: el CI gate evalúa automáticamente

---

## Lo que te llevas

Antes de este README, la única forma de saber si tu agente se portó bien era confiar en logs que el mismo agente generó.

Ahora tienes:

- **Prueba matemática** de cada decisión — Z3, exhaustiva, para TODOS los inputs posibles
- **Hash criptográfico** por cada decisión de governance — keccak256, inmutable
- **Audit trail** en 5 blockchains — verificable por cualquier tercero
- **Ciclo cerrado** de mejora — trace → eval → improve → deploy, automático
- **Sentinel** que valida agentes externos antes de confiar en ellos — 10 checks, 6 dimensiones
- **30 segundos para empezar** — `pip install dof-sdk`

La pregunta no es si necesitas governance verificable para tus agentes.
La pregunta es cuánto te va a costar no tenerla.

```bash
pip install dof-sdk==0.5.0
```

**Si tu agente puede actuar solo, demuestra que hizo lo correcto. Con matemáticas.**

---

<p align="center">
  <strong>DOF-MESH</strong> · Deterministic Observability Framework<br/>
  <em>Matemáticas, no promesas.</em><br/><br/>
  Cyber Paisa — Enigma Group — Medellín, Colombia<br/>
  BSL-1.1 · <a href="LICENSE">License</a>
</p>
