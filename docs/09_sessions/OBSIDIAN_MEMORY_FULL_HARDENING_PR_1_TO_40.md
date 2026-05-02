# Obsidian Memory — Full Hardening PR #1–#40

---
project: DOF-MESH
type: obsidian-memory
scope: full-hardening-cycle
pr_range: PR #1–#40
status: finalized
final_checkpoint: checkpoint/pr-1-to-40-hash-domain-legacy-audit
tests_collected: 4802
session_date: 2026-05 approximate
duration: extended multi-session / multi-hour hardening cycle, exact duration not recorded
models_used:
  - GPT-5.5 Thinking
  - GPT-5.5 Codex
  - GPT-5.4 medium Codex
---

## 1. Executive Memory

Durante el ciclo PR #1–#40 se consolido una linea completa de hardening tecnico, documental y operacional para DOF-MESH.

El ciclo empezo con estabilizacion de testing, CI, collection limpia, mutation verifier y documentacion de metricas vivas. Despues avanzo hacia verify CLI, proof registry, Hardhat scoped testing, behavior coverage, compatibilidad de proof hashes, enforcement de EVM Keccak y auditoria legacy de dominios hash.

Resultado neto:

- baseline de testing estabilizado;
- warnings y collection de pytest saneados;
- workflows CI alineados con runners reales;
- mutation verifier aclarado y fast path rechazado por debilitar la senal;
- documentacion de testing y metricas alineada;
- memoria Obsidian del ciclo PR #1–#26 creada;
- verify CLI documentado e indexado;
- proof registry consistency audit creado;
- blockers Hardhat/ProofRegistry/Tempo/Foundry documentados;
- config scoped de Hardhat para proof registry;
- behavior tests para `DOFProofRegistry` y `DOFEvaluator`;
- compatibilidad de `ProofSerializer.hash_proof` contra `Web3.keccak` cubierta;
- semantica canonica de proof hash documentada;
- fallback silencioso a `hashlib.sha3_256` eliminado;
- legacy hash-domain audit creado;
- checkpoint final: `checkpoint/pr-1-to-40-hash-domain-legacy-audit`;
- baseline actual reportado: `4802 tests collected`.

Este documento es memoria cronologica. No reemplaza docs operacionales canonicas como `PROOF_HASH_SEMANTICS.md` o `HASH_DOMAIN_LEGACY_AUDIT.md`; las conecta como linea historica.

## 2. Final Baseline

Baseline actual del ciclo completo:

- `npm run test:collect` -> `4802 tests collected`
- Final checkpoint -> `checkpoint/pr-1-to-40-hash-domain-legacy-audit`
- HEAD reconstruido por commit/tag -> `720e076 docs: audit legacy hash-domain wording (#40)`
- Rama de memoria -> `docs/full-hardening-memory-pr-1-to-40`

Baselines intermedios documentados:

- PR #1–#26: `4797 tests collected`
- Mutation verifier del ciclo PR #1–#26: `16/16 killed`, `100.0% mutation score`
- Canonical suite del ciclo PR #1–#26: `293 passed + 11 subtests`
- PR #36: Hardhat proof registry behavior tests reportados como `7 passing`
- PR #37/#39: `tests/test_proof_hash.py` reportado como `30 passed`
- PR #39: proof indirect tests reportados como `39 passed`

## 3. Phase Map

Mapa por fases reconstruido desde commits, tags y memorias previas:

| Fase | Rango | Tema | Resultado |
|---|---|---|---|
| 1 | PR #1–#6 | testing foundation | runner formalizado, optional/integration tests aislados, safe suite estabilizada |
| 2 | PR #7–#13 | testing docs + CI | estrategia de testing documentada, workflows alineados, mutation workflow endurecido |
| 3 | PR #14–#22 | docs/metrics alignment | baseline publico y metricas vivas alineadas |
| 4 | PR #23–#26 | mutation verifier + closure | mutation verifier aclarado, fast path rechazado, cierre maestro |
| 5 | PR #27–#29 | memory + verify CLI | memoria Obsidian del ciclo anterior, verify CLI documentado e indexado |
| 6 | PR #30–#36 | proof registry / Hardhat scoped | auditorias, blockers, config scoped, behavior tests |
| 7 | PR #37–#40 | proof hash / EVM Keccak | compatibilidad hash, semantica, enforcement, legacy audit |

Incertidumbre:

- Los detalles finos de PR #1–#5 se reconstruyen principalmente por mensajes de commit y tags. Para esos PRs, esta memoria evita afirmar resultados no evidenciados por commit/tag o documentos existentes.

## 4. Chronological Timeline PR #1–#40

### PR #1 — `Prepare DOF-MESH for accelerator validation and fix API import`

Objetivo:

- Preparar el repo para validacion de aceleradora y corregir import de API.

Resultado:

- Inicio del ciclo de hardening incremental.

Checkpoint:

- No se observo tag checkpoint especifico para PR #1 en la lista actual.

### PR #2 — `test: prevent optional integration tests from breaking collection`

Objetivo:

- Evitar que optional/integration tests rompieran collection.

Resultado:

- Primer paso hacia una collection mas confiable.

Checkpoint:

- No se observo tag checkpoint especifico para PR #2 en la lista actual.

### PR #3 — `test: formalize pytest runner and isolate z3 proof artifact`

Objetivo:

- Formalizar el runner pytest y aislar artifact de Z3 proof.

Resultado:

- Se redujo acoplamiento entre artifacts y collection.

Checkpoint:

- No se observo tag checkpoint especifico para PR #3 en la lista actual.

### PR #4 — `test: apply pytest markers by test directory`

Objetivo:

- Aplicar markers pytest por directorio.

Resultado:

- Mejor separacion entre tipos de tests.

Checkpoint:

- No se observo tag checkpoint especifico para PR #4 en la lista actual.

### PR #5 — `test: mark top-level optional and integration tests`

Objetivo:

- Marcar optional/integration tests top-level.

Resultado:

- Se refino el aislamiento de tests no canonicos.

Checkpoint:

- No se observo tag checkpoint especifico para PR #5 en la lista actual.

### PR #6 — `test: stabilize safe suite runner and flaky tests`

Objetivo:

- Estabilizar safe suite runner y tests flaky.

Resultado:

- Cierre de la primera fase de test hardening.

Checkpoint:

- `checkpoint/pr-1-to-6-test-hardening`

### PR #7 — `docs: document testing strategy and safe runner`

Objetivo:

- Documentar estrategia de testing y safe runner.

Resultado:

- La estrategia dejo de vivir solo en comandos y quedo registrada como politica operativa.

Checkpoint:

- No se observo tag checkpoint especifico para PR #7 en la lista actual.

### PR #8 — `ci: align test workflow with npm test runners`

Objetivo:

- Alinear workflow de tests con runners `npm`.

Resultado:

- CI empezo a reflejar mejor la forma real de ejecutar suite local.

Checkpoint:

- `checkpoint/pr-1-to-8-ci-testing-aligned`

### PR #9 — `test: silence pytest collection warnings for helper classes`

Objetivo:

- Silenciar warnings de collection por helper classes.

Resultado:

- Collection mas limpia y menos ruido para agentes/humanos.

Checkpoint:

- `checkpoint/pr-1-to-9-clean-test-collection`

### PR #10 — `test: filter external websockets legacy warning`

Objetivo:

- Filtrar warning legacy externo de websockets.

Resultado:

- Baseline pytest mas limpio.

Checkpoint:

- `checkpoint/pr-1-to-10-clean-pytest-baseline`

### PR #11 — `ci: align main ci workflow with npm test runners`

Objetivo:

- Alinear workflow principal CI con runners `npm`.

Resultado:

- CI principal alineado con baseline real.

Checkpoint:

- `checkpoint/pr-1-to-11-ci-fully-aligned`

### PR #12 — `ci: align z3 unit tests with pytest runner`

Objetivo:

- Alinear Z3 unit tests con pytest runner.

Resultado:

- Z3 subset integrado de forma mas coherente al flujo de testing.

Checkpoint:

- `checkpoint/pr-1-to-12-ci-z3-aligned`

### PR #13 — `ci: harden mutation testing workflow triggers`

Objetivo:

- Endurecer triggers del workflow de mutation testing.

Resultado:

- Mutation workflow quedo mas controlado.

Checkpoint:

- `checkpoint/pr-1-to-13-mutation-workflow-hardened`

### PR #14 — `docs: update testing strategy after ci hardening`

Objetivo:

- Actualizar docs de testing despues del hardening CI.

Resultado:

- Documentacion alineada con la practica real.

Checkpoint:

- `checkpoint/pr-1-to-14-testing-docs-finalized`

### PR #15 — `docs: add testing hardening audit report`

Objetivo:

- Agregar reporte de auditoria del hardening de testing.

Resultado:

- Se fijo evidencia documental del ciclo de testing.

Checkpoint:

- `checkpoint/pr-1-to-15-testing-audit-report`

### PR #16 — `docs: align readme testing baseline with audit report`

Objetivo:

- Alinear README con baseline de testing auditado.

Resultado:

- Metricas publicas redujeron divergencia respecto al estado auditado.

Checkpoint:

- `checkpoint/pr-1-to-16-readme-testing-baseline-aligned`

### PR #17 — `docs: align readme chain metrics`

Objetivo:

- Alinear metricas de chain en README.

Resultado:

- Metricas chain publicas alineadas.

Checkpoint:

- `checkpoint/pr-1-to-17-readme-chain-metrics-aligned`

### PR #18 — `docs: align index metrics`

Objetivo:

- Alinear metricas de index.

Resultado:

- Este checkpoint quedo registrado como antecedente operativo delicado en la memoria PR #1–#26: el tag `checkpoint/pr-1-to-18-index-metrics-aligned` apunto al commit de README chain metrics, no al cambio real esperado de `docs/INDEX.md`.

Checkpoint:

- `checkpoint/pr-1-to-18-index-metrics-aligned`

### PR #19 — `docs: align index metrics with audit baseline`

Objetivo:

- Corregir/alinear `docs/INDEX.md` con baseline auditado.

Resultado:

- Checkpoint confiable para `docs/INDEX.md`.

Checkpoint:

- `checkpoint/pr-1-to-19-index-metrics-baseline-fixed`

### PR #20 — `docs: align doc system metrics with audit baseline`

Objetivo:

- Alinear metricas del sistema documental.

Resultado:

- `docs/DOC_SYSTEM.md` quedo mas consistente con baseline auditado.

Checkpoint:

- `checkpoint/pr-1-to-20-doc-system-metrics-aligned`

### PR #21 — `docs: align architecture metrics with audit baseline`

Objetivo:

- Alinear metricas de arquitectura.

Resultado:

- Documentacion arquitectonica sincronizada con baseline.

Checkpoint:

- `checkpoint/pr-1-to-21-architecture-metrics-aligned`

### PR #22 — `docs: align accelerator metrics with audit baseline`

Objetivo:

- Alinear metricas de materiales de aceleradora.

Resultado:

- Materiales externos/publicos redujeron drift respecto al baseline.

Checkpoint:

- `checkpoint/pr-1-to-22-accelerator-metrics-aligned`

### PR #23 — `test: clarify mutation verifier partial mode`

Objetivo:

- Aclarar modo parcial del mutation verifier.

Resultado:

- Mejor documentacion/comportamiento alrededor de mutation verifier.

Checkpoint:

- `checkpoint/pr-1-to-23-mutation-verifier-clarified`

### PR #24 — `docs: document mutation verifier diagnostics`

Objetivo:

- Documentar diagnosticos del mutation verifier.

Resultado:

- Diagnosticos y expectativas quedaron registrados.

Checkpoint:

- `checkpoint/pr-1-to-24-mutation-verifier-diagnostics-documented`

### PR #25 — `docs: document rejected mutation verifier fast path`

Objetivo:

- Documentar decision de rechazar fast path para mutation verifier.

Resultado:

- Decision clave: no optimizar velocidad si se destruye fuerza de senal.

Checkpoint:

- `checkpoint/pr-1-to-25-mutation-fast-path-rejected`

### PR #26 — `docs: add testing hardening final closure`

Objetivo:

- Cerrar formalmente el ciclo de testing hardening.

Resultado:

- Baseline PR #1–#26 tratado como referencia operativa cerrada.

Checkpoint:

- `checkpoint/pr-1-to-26-testing-hardening-final-closure`

### PR #27 — `docs: add obsidian memory for testing hardening cycle`

Objetivo:

- Crear memoria Obsidian del ciclo PR #1–#26.

Resultado:

- Se creo el precedente estructural usado por esta memoria: `docs/09_sessions/OBSIDIAN_MEMORY_TESTING_HARDENING_PR_1_TO_26.md`.

Checkpoint:

- `checkpoint/pr-1-to-27-obsidian-memory-testing-hardening`

### PR #28 — `docs: document verify cli usage`

Objetivo:

- Documentar uso validado del verify CLI.

Resultado:

- Verify CLI paso a estar documentado para operacion.

Checkpoint:

- `checkpoint/pr-1-to-28-verify-cli-documented`

### PR #29 — `docs: add verify cli guide to index`

Objetivo:

- Enlazar verify CLI desde el indice documental.

Resultado:

- La guia quedo descubrible desde `docs/INDEX.md`.

Checkpoint:

- `checkpoint/pr-1-to-29-index-add-verify-cli`

### PR #30 — `docs: add proof registry consistency audit`

Objetivo:

- Auditar consistencia de proof registry, nombres de campos, adapters y dominios hash.

Resultado:

- Se creo `docs/05_operations/PROOF_REGISTRY_CONSISTENCY_AUDIT.md`.
- Se identifico ambiguedad entre `z3ProofHash`, `proofHash`, `certificateHash`, EVM `keccak256`, Python `sha3_256`, SHA256, BLAKE3 y HMAC-SHA256.

Checkpoint:

- `checkpoint/pr-1-to-30-proof-registry-consistency-audit`

### PR #31 — `docs: document hardhat proof registry test blocker`

Objetivo:

- Documentar blocker de tests Hardhat para proof registry.

Resultado:

- Se creo evidencia antes de tocar configs o contratos.

Checkpoint:

- `checkpoint/pr-1-to-31-hardhat-proof-registry-test-blocker`

### PR #32 — `chore: rename non-solidity erc8004 attestation artifact`

Objetivo:

- Renombrar artifact no-Solidity con extension `.sol` para evitar compilacion erronea.

Resultado:

- Se redujo ruido de compilacion Hardhat.

Checkpoint:

- `checkpoint/pr-1-to-32-rename-erc8004-attestation-artifact`

### PR #33 — `docs: document hardhat tempo foundry compile blocker`

Objetivo:

- Documentar blocker Hardhat/Tempo/Foundry.

Resultado:

- Se evito resolver un problema de scope amplio con cambios prematuros.

Checkpoint:

- `checkpoint/pr-1-to-33-hardhat-tempo-foundry-blocker`

### PR #34 — `test: add scoped hardhat proof registry config`

Objetivo:

- Agregar config scoped para proof registry.

Resultado:

- Se introdujo `hardhat.proof-registry.config.js` como camino aislado.

Checkpoint:

- `checkpoint/pr-1-to-34-scoped-hardhat-proof-registry-config`

### PR #35 — `test: add scoped hardhat proof registry config`

Objetivo:

- Restaurar/estabilizar scoped Hardhat proof registry config.

Resultado:

- Se consolido el scope sin tocar `hardhat.config.js` principal.

Checkpoint:

- `checkpoint/pr-1-to-35-restore-scoped-hardhat-proof-registry-config`

### PR #36 — `test: add proof registry behavior coverage`

Objetivo:

- Agregar behavior tests para proof registry.

Resultado:

- Coverage reportada para `DOFProofRegistry` y `DOFEvaluator`.
- Evidencia del ciclo: `7 passing`.

Checkpoint:

- `checkpoint/pr-1-to-36-proof-registry-behavior-coverage`

### PR #37 — `test: add proof hash compatibility coverage`

Objetivo:

- Cubrir compatibilidad de `ProofSerializer.hash_proof` con `Web3.keccak` y no-equivalencia con `hashlib.sha3_256`.

Resultado:

- Se demostro que `Web3.keccak(text=...)` coincide con `Web3.keccak(bytes UTF-8)`.
- Se demostro que `hashlib.sha3_256` no equivale a EVM `keccak256`.
- Se preservo empty transcript como `b"\x00" * 32`.

Checkpoint:

- `checkpoint/pr-1-to-37-proof-hash-compatibility-coverage`

### PR #38 — `docs: document proof hash semantics`

Objetivo:

- Documentar semantica canonica de proof hash.

Resultado:

- Se creo `docs/05_operations/PROOF_HASH_SEMANTICS.md`.
- Se establecio `Web3.keccak` / EVM `keccak256` como canon para proof hashes on-chain.

Checkpoint:

- `checkpoint/pr-1-to-38-proof-hash-semantics-docs`

### PR #39 — `fix: enforce evm keccak proof hash requirement`

Objetivo:

- Eliminar fallback silencioso a `hashlib.sha3_256`.

Resultado:

- `core/proof_hash.py` usa `Web3.keccak` como fuente canonica.
- Si `Web3` no esta disponible y transcript no esta vacio, `hash_proof` lanza `RuntimeError`.
- `hash_proof("")` conserva `b"\x00" * 32`.
- Evidencia reportada: `tests/test_proof_hash.py` -> `30 passed`; tests indirectos proof/z3/storage/pipeline -> `39 passed`.

Checkpoint:

- `checkpoint/pr-1-to-39-enforce-evm-keccak-proof-hash`

### PR #40 — `docs: audit legacy hash-domain wording`

Objetivo:

- Auditar deuda legacy de dominios hash y actualizar docs tras PR #39.

Resultado:

- Se creo `docs/05_operations/HASH_DOMAIN_LEGACY_AUDIT.md`.
- Se actualizo `docs/05_operations/PROOF_HASH_SEMANTICS.md`.
- Se enlazo en `docs/INDEX.md`.

Checkpoint:

- `checkpoint/pr-1-to-40-hash-domain-legacy-audit`

## 5. Checkpoints

Checkpoints observados:

- `checkpoint/pr-1-to-6-test-hardening`
- `checkpoint/pr-1-to-8-ci-testing-aligned`
- `checkpoint/pr-1-to-9-clean-test-collection`
- `checkpoint/pr-1-to-10-clean-pytest-baseline`
- `checkpoint/pr-1-to-11-ci-fully-aligned`
- `checkpoint/pr-1-to-12-ci-z3-aligned`
- `checkpoint/pr-1-to-13-mutation-workflow-hardened`
- `checkpoint/pr-1-to-14-testing-docs-finalized`
- `checkpoint/pr-1-to-15-testing-audit-report`
- `checkpoint/pr-1-to-16-readme-testing-baseline-aligned`
- `checkpoint/pr-1-to-17-readme-chain-metrics-aligned`
- `checkpoint/pr-1-to-18-index-metrics-aligned`
- `checkpoint/pr-1-to-19-index-metrics-baseline-fixed`
- `checkpoint/pr-1-to-20-doc-system-metrics-aligned`
- `checkpoint/pr-1-to-21-architecture-metrics-aligned`
- `checkpoint/pr-1-to-22-accelerator-metrics-aligned`
- `checkpoint/pr-1-to-23-mutation-verifier-clarified`
- `checkpoint/pr-1-to-24-mutation-verifier-diagnostics-documented`
- `checkpoint/pr-1-to-25-mutation-fast-path-rejected`
- `checkpoint/pr-1-to-26-testing-hardening-final-closure`
- `checkpoint/pr-1-to-27-obsidian-memory-testing-hardening`
- `checkpoint/pr-1-to-28-verify-cli-documented`
- `checkpoint/pr-1-to-29-index-add-verify-cli`
- `checkpoint/pr-1-to-30-proof-registry-consistency-audit`
- `checkpoint/pr-1-to-31-hardhat-proof-registry-test-blocker`
- `checkpoint/pr-1-to-32-rename-erc8004-attestation-artifact`
- `checkpoint/pr-1-to-33-hardhat-tempo-foundry-blocker`
- `checkpoint/pr-1-to-34-scoped-hardhat-proof-registry-config`
- `checkpoint/pr-1-to-35-restore-scoped-hardhat-proof-registry-config`
- `checkpoint/pr-1-to-36-proof-registry-behavior-coverage`
- `checkpoint/pr-1-to-37-proof-hash-compatibility-coverage`
- `checkpoint/pr-1-to-38-proof-hash-semantics-docs`
- `checkpoint/pr-1-to-39-enforce-evm-keccak-proof-hash`
- `checkpoint/pr-1-to-40-hash-domain-legacy-audit`

Nota:

- No se observaron checkpoints individuales para PR #1–#5 ni PR #7 en la lista actual. Esos tramos quedan cubiertos por checkpoints acumulados posteriores.

## 6. Technical Milestones

Hitos tecnicos:

- Suite segura/canonica estabilizada.
- Optional/integration tests aislados para no romper collection.
- Pytest runner formalizado.
- Z3 proof artifact aislado.
- CI alineado con runners `npm`.
- Z3 unit tests alineados con pytest runner.
- Mutation testing workflow endurecido.
- Mutation verifier aclarado.
- Fast path de mutation verifier rechazado porque debilitaba la senal.
- Verify CLI documentado e indexado.
- Proof registry consistency audit creado.
- Hardhat proof registry test blocker documentado.
- Artifact no-Solidity con extension `.sol` renombrado.
- Hardhat/Tempo/Foundry blocker documentado.
- `hardhat.proof-registry.config.js` introducido.
- `contracts_hardhat/proof_registry/ProofRegistryScope.sol` introducido como import-only scope.
- Scoped compile reportado: `Compiled 4 Solidity files successfully`.
- Proof registry behavior tests reportados: `7 passing`.
- Proof hash compatibility coverage agregada.
- `Web3.keccak` y `hashlib.sha3_256` diferenciados por tests.
- `core/proof_hash.py` endurecido para requerir EVM Keccak.
- `RuntimeError` explicito si `Web3` no esta disponible para transcripts no vacios.
- `hash_proof("")` preservado como `b"\x00" * 32`.
- Baseline final: `4802 tests collected`.

## 7. Documentary Milestones

Hitos documentales:

- Testing strategy documentada.
- Testing hardening audit report creado.
- Testing hardening final closure creado.
- README, index, architecture, doc system y accelerator docs alineados con baseline auditado.
- Obsidian memory PR #1–#26 creada.
- Verify CLI guide documentada e indexada.
- `PROOF_REGISTRY_CONSISTENCY_AUDIT.md` creado.
- `HARDHAT_PROOF_REGISTRY_TEST_BLOCKER.md` creado.
- `HARDHAT_TEMPO_FOUNDRY_BLOCKER.md` creado.
- `PROOF_HASH_SEMANTICS.md` creado.
- `HASH_DOMAIN_LEGACY_AUDIT.md` creado.

## 8. Hardhat Scoped Testing Summary

La linea Hardhat/proof registry se resolvio con scope controlado.

Decisiones:

- No tocar `hardhat.config.js` principal durante el desbloqueo.
- Crear `hardhat.proof-registry.config.js`.
- Usar `ProofRegistryScope.sol` como import-only scope.
- Validar proof registry sin arrastrar todo el universo Hardhat/Tempo/Foundry.

Que desbloqueo:

- Compile scoped de proof registry.
- Behavior tests para `DOFProofRegistry` y `DOFEvaluator`.
- Avance incremental antes de tocar hash semantics.

Que no prueba:

- No prueba que todo el repo Hardhat completo compile.
- No elimina todos los blockers Tempo/Foundry.
- No sustituye una auditoria completa de contratos.

## 9. Proof Hash / EVM Keccak Hardening

Politica consolidada:

- EVM/Solidity/Avalanche proof hashes usan `Web3.keccak` / EVM `keccak256`.
- `hashlib.sha3_256` no es equivalente a EVM `keccak256`.
- SHA256/Merkle/internal integrity son dominios separados.
- HMAC-SHA256 es autenticacion/integridad, no proof hash on-chain.
- BLAKE3/`certificateHash` es dominio separado.
- `z3ProofHash` y `DOFProofRegistry` no deben mezclarse con SHA256/Merkle/certificate hashes.

PR #37 dio evidencia de compatibilidad y no-equivalencia.

PR #38 documento la semantica.

PR #39 hizo enforcement en `core/proof_hash.py`.

PR #40 registro deuda legacy de comentarios y docs.

## 10. Legacy Hash-Domain Audit

La auditoria legacy identifico texto o comentarios que podian inducir errores operativos:

- `sha3_256` descrito como equivalente o compatible con `keccak256`;
- SHA256 usado con nombre `proof_hash` en contextos que podrian confundirse con on-chain proof hashes;
- dominios Merkle/HMAC/BLAKE3/certificateHash mezclados en lenguaje general;
- docs historicas que necesitaban marca legacy o aclaracion.

Decision:

- No cambiar runtime dentro de PR documental.
- Registrar dominios y priorizar un PR futuro de comentarios/docstrings.

## 11. Master Git / PR / Checkpoint Protocol

Nunca crear checkpoint solo porque:

- el PR fue creado;
- el PR fue mergeado;
- existe un tag;
- GitHub muestra algo como completado;
- el push fue exitoso;
- la rama parece limpia.

Antes de cualquier checkpoint:

1. `git checkout main`
2. `git pull dof-mesh main`
3. `git log --oneline --decorate -8`
4. Confirmar que el commit esperado esta en `main`.
5. Confirmar que los archivos esperados existen en `main`.
6. Ejecutar validaciones tecnicas correspondientes.
7. Ejecutar `npm run test:collect`.
8. Confirmar `git status` limpio.
9. Solo entonces crear y subir checkpoint.

Este protocolo se volvio obligatorio porque el ciclo mostro que tags/checkpoints y senales visuales de GitHub no sustituyen validar commit y archivos reales en `main`.

## 12. Errors And Lessons Learned

Errores y riesgos aprendidos:

- Codex puede estar en directorio incorrecto; siempre validar repo y rama.
- Una rama vieja puede apuntar a commit anterior y no contener archivos esperados.
- No asumir merge por push, tag o UI.
- No confiar en tags sin validar commit y archivos concretos.
- No crear checkpoint hasta validar `main`.
- No usar prompts amplios tipo “Find and fix a bug in @filename” para auditorias controladas.
- No permitir escrituras si la primera fase debe ser auditoria.
- No mezclar docs, tests e implementacion en PRs delicados.
- No cambiar runtime en PR documental.
- No llamar EVM-compatible a `sha3_256`.
- No confundir formato `bytes32` con semantica EVM Keccak.

Lecciones operativas:

- Audit first.
- Read-only before write.
- One PR, one purpose.
- Main validation before checkpoint.
- Small scoped PRs beat broad fixes.
- Documentation can be a security control when it prevents wrong operational assumptions.

## 13. Models Used And Criteria

Modelos usados:

- GPT-5.5 Thinking: coordinacion, auditoria estrategica, diseno de prompts, control de riesgos.
- GPT-5.5 Codex: auditorias complejas, busqueda legacy, documentacion estructural y razonamiento criptografico.
- GPT-5.4 medium Codex: tareas pequenas, revision controlada y cambios acotados.

Criterio:

- Preferir GPT-5.5 para criptografia, seguridad, EVM compatibility, arquitectura y reasoning complejo.
- Usar GPT-5.4 medium cuando el alcance sea pequeno, claro y verificable.

## 14. Work Strategy

Estrategia aplicada:

- audit first;
- read-only before write;
- one PR, one purpose;
- small scoped PRs;
- tests before implementation;
- docs before enforcement;
- main validation before checkpoint;
- no secrets;
- no broad agentic edits;
- no mixed-scope PRs.

La secuencia mas importante fue:

1. Auditar el riesgo.
2. Documentar el blocker.
3. Desbloquear test scoped.
4. Agregar cobertura.
5. Documentar semantica.
6. Hacer enforcement.
7. Auditar legacy.
8. Crear checkpoint solo tras validar `main`.

## 15. Relation To Obsidian / Memory

Este documento extiende el patron iniciado por:

- `docs/09_sessions/OBSIDIAN_MEMORY_TESTING_HARDENING_PR_1_TO_26.md`

La memoria PR #1–#26 registra testing/CI/mutation/docs hardening.

Esta memoria PR #1–#40 une ese ciclo con verify CLI, proof registry, Hardhat scoped testing y EVM Keccak hardening.

Uso esperado:

- recuperacion de contexto;
- handoff para futuros agentes;
- evidencia de decisiones;
- fuente para lecciones destiladas;
- fuente para material narrativo futuro.

## 16. Relation To The DOF-MESH Book

Este documento no es capitulo del libro. Es material fuente estructurado.

Puede alimentar:

- escenas tecnicas sobre errores reales de ingenieria;
- evolucion de la tesis “monitoring is not governance”;
- capitulos sobre deterministic observability;
- capitulos sobre proof governance;
- secciones sobre hash semantics, EVM Keccak y evidencia criptografica;
- narrativa sobre por que un sistema agentic necesita checkpoint discipline.

No debe copiarse literalmente al libro sin edicion.

## 17. DOF-MESH Vision Reinforced

El ciclo reforzo:

- DOF doesn’t monitor. DOF proves.
- Mathematics, not promises.
- Verify before act.
- Deterministic shell around stochastic agents.
- `S_workflow` deterministico/verificable vs `S_env` estocastico/opaco.
- Pre-verification con reglas deterministicas y Z3/SMT.
- Cryptographic attestations as evidence, not mere logs.

La arquitectura correcta no intenta leer la mente completa del LLM. Verifica el workflow alrededor del agente y genera evidencia reproducible antes de permitir acciones criticas.

## 18. Suggested Next PRs

PRs sugeridos:

- `docs/comment: clarify legacy hash-domain comments`
- `test: clarify dummy proof hash fixtures`
- `docs: add deterministic observability alignment audit`
- `docs: distill PR1-40 lessons learned`
- `book: draft proof governance hardening chapter notes`

Orden recomendado:

1. Comentarios/docstrings legacy sin runtime changes.
2. Test fixtures para distinguir dummy `bytes32` de proof hash canonico.
3. Auditoria de alineacion deterministic observability / agentic AI.
4. Lecciones destiladas en docs canonicas.
5. Material narrativo para libro.

## 19. Future Master Rules

Reglas maestras futuras:

- Validar directorio, rama y estado antes de tocar nada.
- Si el objetivo es auditoria, empezar read-only.
- No crear checkpoint sin `main` actualizado y validado.
- No confiar en tags sin validar archivos.
- No mezclar PRs de documentacion, tests e implementacion si el tema es delicado.
- No tocar contratos/configs/secrets fuera de scope explicito.
- No llamar “keccak-compatible” a `hashlib.sha3_256`.
- Separar EVM proof hash, Merkle root, audit hash chain, HMAC, BLAKE3, certificateHash e IDs internos.
- Mantener pruebas antes de enforcement.
- Mantener docs antes de cambios de comportamiento cuando hay riesgo conceptual.

## 20. Final State

Documento creado:

- `docs/09_sessions/OBSIDIAN_MEMORY_FULL_HARDENING_PR_1_TO_40.md`

Estado esperado:

- Rama: `docs/full-hardening-memory-pr-1-to-40`
- Working tree limpio antes de crear este archivo.
- Archivo en `docs/09_sessions/`, directorio actualmente ignorado por `.gitignore`.
- Pendiente agregar manualmente con `git add -f` si se quiere incluir en PR.

Restricciones de este documento:

- No toca codigo.
- No toca tests.
- No toca contratos.
- No toca configs.
- No toca `MEMORY.md`.
- No toca `.claude/memory/`.
- No toca `docs/03_book/`.
- No toca `docs/02_research/LESSONS_LEARNED.md`.
- No crea commit, push ni tag.
