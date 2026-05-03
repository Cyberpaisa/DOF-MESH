# Obsidian Memory — PR #43–#49 Hardening to On-Chain Readiness

---
project: DOF-MESH
type: obsidian-memory
scope: hardening-to-onchain-readiness
pr_range: PR #43–#49
status: finalized
final_checkpoint: checkpoint/pr-1-to-49-offline-onchain-readiness-dry-run
tests_collected: 4802
session_date: 2026-05-03
---

## 1. Mapa de memoria conectada

Este checkpoint conecta el cierre de [[LEARNINGS_FULL_HARDENING_PR_1_TO_42_20260502]] y [[OBSIDIAN_MEMORY_HARDENING_CLOSURE_PR_41_TO_42]] con la transición segura hacia on-chain readiness. La línea narrativa une [[PROOF_HASH_SEMANTICS]], [[HASH_DOMAIN_LEGACY_AUDIT]], [[PROOF_REGISTRY_CONSISTENCY_AUDIT]], [[VERIFY_CLI]], [[Z3_VERIFICATION]], [[MULTICHAIN]], [[onchain_readiness_dry_run]], [[DOFProofRegistry]], [[chains_config]] y [[checkpoint-pr-1-to-49]].

Regla de oro:

> Codex audits and writes dry-runs; Juan controls secrets and real execution.

Recordatorio explícito: no .env, no private keys, no broadcast, no deploy real.

## 2. Timeline PR #43–#49

| PR | Título | Resultado |
| --- | --- | --- |
| PR #43 | `docs: add hardening closure learnings and memory` | Creó memoria de cierre PR #1–#42 y conectó learnings con sesión Obsidian. |
| PR #44 | `docs: finish residual hash-domain wording alignment` | Terminó wording residual hash-domain en `core/tool_hooks.py`, `core/zk_governance_proof.py` y `docs/INDEX.md`. |
| PR #45 | `docs: align verify CLI outputs with current baseline` | Alineó `VERIFY_CLI` y `Z3_VERIFICATION` con `8/8 PROVEN` y `62 patterns PROVEN`. |
| PR #46 | `docs: align public live metrics with current baseline` | Alineó métricas públicas vivas a `4802 tests collected`; preservó `4,800` como milestone histórico. |
| PR #47 | `docs: mark proof registry audit post-hardening status` | Marcó audit como evidencia histórica post-hardening y actualizó collection a `4802`. |
| PR #48 | `docs: finish proof registry audit superseded wording` | Terminó wording histórico/superseded restante en audit de proof registry. |
| PR #49 | `script: add offline on-chain readiness dry-run` | Agregó dry-run offline/no-broadcast para readiness desde `core/chains_config.json`. |

## 3. Checkpoints

| PR | Checkpoint |
| --- | --- |
| PR #43 | `checkpoint/pr-1-to-43-hardening-closure-learnings-memory` |
| PR #44 | `checkpoint/pr-1-to-44-finish-residual-hash-domain-wording` |
| PR #45 | `checkpoint/pr-1-to-45-align-verify-cli-current-baseline` |
| PR #46 | `checkpoint/pr-1-to-46-align-public-live-metrics-current-baseline` |
| PR #47 | `checkpoint/pr-1-to-47-mark-proof-registry-audit-post-hardening-status` |
| PR #48 | `checkpoint/pr-1-to-48-finish-proof-registry-audit-superseded-wording` |
| PR #49 | `checkpoint/pr-1-to-49-offline-onchain-readiness-dry-run` |

## 4. Baseline técnico

- `4802 tests collected`
- `verify-states`: `8/8 PROVEN`
- `verify-hierarchy`: `62 patterns PROVEN`
- Hardhat scoped proof registry: `7 passing`
- `main` limpio al cierre validado
- checkpoints hasta PR #49
- hash-domain saneado
- métricas públicas alineadas
- auditorías históricas marcadas como superseded
- primera capa on-chain segura creada: offline dry-run sin secrets

## 5. Estado de seguridad on-chain

La seguridad on-chain queda en fase pre-ejecución. PR #49 no habilita despliegue real; habilita evaluación estática/offline de readiness. El script [[onchain_readiness_dry_run]] revisa configuración en [[chains_config]] sin abrir `.env`, sin private keys, sin RPC, sin firma, sin broadcast y sin deploy.

El estado correcto es:

- permitido: documentación, auditoría, dry-run offline, reporte local;
- todavía no permitido desde agentes: wallets, private keys, broadcast, deploy real, `cast send`, comandos firmados;
- siguiente paso seguro: read-only RPC health-check sin wallet.

## 6. Riesgos y mitigaciones

| Riesgo | Estado | Mitigación |
| --- | --- | --- |
| Wording hash-domain confunde SHA3-256/FIPS con EVM Keccak | Cerrado | PR #44 y docs de [[PROOF_HASH_SEMANTICS]]. |
| Métricas públicas antiguas se leen como baseline vivo | Cerrado | PR #46 fijó `4802 tests collected` y dejó `4,800` como histórico. |
| Auditoría histórica parece deuda actual | Cerrado | PR #47–#48 marcaron hallazgos como superseded/historical. |
| Verify CLI documenta resultados viejos | Cerrado | PR #45 alineó [[VERIFY_CLI]] y [[Z3_VERIFICATION]]. |
| Codex accede a secretos reales | Abierto por política, no por evento | no .env, no private keys, no endpoints privados. |
| Pruebas on-chain masivas prematuras | Abierto | Fases 50–53 con dry-run, RPC read-only, burner manual y checklist por red. |
| Multi-chain real sin checklist por red | Abierto | Fase 53 requiere checklist por red y validación manual. |

## 7. Información antes desconectada

| Información antes desconectada | Dónde quedó conectada |
| --- | --- |
| Cierre hardening PR #1–#42 | [[LEARNINGS_FULL_HARDENING_PR_1_TO_42_20260502]] y [[OBSIDIAN_MEMORY_HARDENING_CLOSURE_PR_41_TO_42]]. |
| Semántica hash EVM vs legacy | [[PROOF_HASH_SEMANTICS]], [[HASH_DOMAIN_LEGACY_AUDIT]] y PR #44. |
| Estado de proof registry audit | [[PROOF_REGISTRY_CONSISTENCY_AUDIT]] con hallazgos superseded. |
| Baseline verify formal | [[VERIFY_CLI]] y [[Z3_VERIFICATION]] con `8/8` y `62 patterns`. |
| Baseline público de tests | Docs públicas de PR #46 con `4802 tests collected`. |
| Preparación multi-chain | [[MULTICHAIN]], [[DOFProofRegistry]], [[chains_config]] y [[onchain_readiness_dry_run]]. |
| Regla de ejecución segura | Este checkpoint y [[checkpoint-pr-1-to-49]]. |

## 8. Próximos pasos

### Fase 50: read-only RPC health-check sin wallet

- consultar chain id y block number;
- no cargar wallets;
- no firmar;
- salida `--json`/NDJSON para agentes.

### Fase 51: testnet con wallet burner manual

- Juan crea y controla burner;
- Codex prepara checklist y comandos no ejecutados;
- una testnet por vez.

### Fase 52: una mainnet mínima manual

- una red;
- operación mínima;
- ejecución manual;
- registrar evidencia sin secretos.

### Fase 53: multi-chain real con checklist por red

- checklist por red;
- sponsor/gas policy;
- límites específicos;
- reporte final sin payloads sensibles.

## 9. Cierre operativo

Este ciclo convirtió memoria dispersa en una cadena auditable:

1. hardening cerrado;
2. hash-domain saneado;
3. verify docs alineados;
4. métricas públicas corregidas;
5. auditorías históricas marcadas;
6. dry-run offline creado;
7. secretos y ejecución real reservados para control manual de Juan.

