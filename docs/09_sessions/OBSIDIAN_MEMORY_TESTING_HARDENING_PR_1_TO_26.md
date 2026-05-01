# Obsidian Memory — Testing Hardening PR #1–#26

---
project: DOF-MESH
type: obsidian-memory
scope: testing-ci-mutation-docs-hardening
status: closed
baseline_tests_collected: 4797
canonical_suite: "293 passed + 11 subtests"
z3_subset: "156 passed"
mutation_verifier: "16/16 killed · 100.0% mutation score"
final_checkpoint: checkpoint/pr-1-to-26-testing-hardening-final-closure
---

## 1. Executive memory

Durante el ciclo PR #1–#26 se consolidó el baseline técnico y documental del hardening de testing para DOF-MESH. El resultado neto fue una suite segura/canónica estable, una collection limpia de pytest, workflows CI alineados con el runner correcto, una estrategia de testing documentada, métricas vivas públicas corregidas y una decisión explícita sobre mutation verifier.

Se logró:

- estabilizar la suite segura/canónica;
- limpiar `pytest --collect-only` bajo el runner canónico;
- alinear workflows CI con el baseline real;
- documentar la estrategia de testing y cierre de hardening;
- alinear métricas vivas públicas con el baseline auditado;
- clarificar el funcionamiento y propósito de `scripts/mutation_verifier.py`;
- rechazar el fast path del mutation verifier porque debilitaba la señal;
- cerrar el ciclo con el checkpoint final `checkpoint/pr-1-to-26-testing-hardening-final-closure`.

## 2. Final baseline

Baseline final del ciclo:

- `npm run test` -> `293 passed, 11 subtests passed`
- `npm run test:safe` -> `293 passed, 11 subtests passed`
- `npm run test:collect` -> `4797 tests collected`
- Z3 pytest subset -> `156 passed`
- Mutation verifier -> `16/16 killed, 100.0% mutation score`

Este baseline se trata como referencia operativa cerrada del ciclo PR #1–#26.

## 3. PR map

Mapa del ciclo:

- PR #1–#13: testing / CI hardening
- PR #14–#22: documentación viva y métricas alineadas
- PR #23–#25: mutation verifier aclarado + fast path rechazado
- PR #26: cierre maestro final

## 4. Checkpoints

Checkpoints acumulados del ciclo:

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

## 5. Critical lessons learned

- Nunca hacer commit sin confirmar rama con `git branch --show-current`.
- Si `git branch --show-current` devuelve `main`, detenerse.
- Antes de commit usar siempre `git status`.
- Después de merge, hacer `checkout main` + `pull` + limpieza de rama + tag.
- No crear checkpoint hasta verificar que el cambio realmente entró en `main`.
- El tag `checkpoint/pr-1-to-18-index-metrics-aligned` quedó como antecedente de error operativo porque apuntó al commit de README chain metrics, no al cambio real de `docs/INDEX.md`. El checkpoint confiable para `docs/INDEX.md` es `checkpoint/pr-1-to-19-index-metrics-baseline-fixed`.
- Si un heredoc queda abierto, cerrar con el delimitador exacto y luego validar archivo antes de commit.
- No pegar salidas esperadas como comandos en `zsh`.
- El mutation verifier puede ser lento, pero conserva fuerza de señal.
- La suite canónica rápida sirve para PR normal, pero no para mutation testing.

## 6. Mutation verifier decision

Decisión cerrada del ciclo:

- Se probó reemplazar el runner amplio por la suite canónica pytest.
- El baseline rápido pasó.
- Pero mutation score cayó de `100.0%` a `6.2%`.
- Mutantes `killed` bajaron de `16/16` a `1/16`.
- Decisión: mantener runner amplio `unittest discover` para mutation verifier.
- No volver a intentar optimizarlo con la suite canónica rápida salvo que se demuestre fuerza equivalente.

## 7. Files created or aligned

Documentos y archivos clave alineados en el ciclo:

- `docs/testing.md`
- `docs/testing-hardening-audit.md`
- `docs/testing-hardening-final-closure.md`
- `README.md`
- `docs/INDEX.md`
- `docs/DOC_SYSTEM.md`
- `docs/01_architecture/SYSTEM_ARCHITECTURE.md`
- `docs/accelerator/SECURITY_AND_DISCLOSURE_LIMITS.md`
- `docs/accelerator/EXECUTIVE_SUMMARY.md`
- `docs/accelerator/ONE_PAGER.md`
- `scripts/mutation_verifier.py`

## 8. Current clean state

Estado final esperado al cierre del ciclo:

- `main` sincronizado con `dof-mesh/main`
- `working tree clean`
- `npm run test:collect` -> `4797 tests collected`
- checkpoint final -> `checkpoint/pr-1-to-26-testing-hardening-final-closure`

## 9. Tomorrow next steps

Siguiente trabajo recomendado para mañana:

- revisar Z3/CLI verification path;
- validar comandos `dof verify-states`, `dof verify-hierarchy` y `dof verify`;
- auditar que las salidas sean claras, reproducibles y compatibles con docs;
- no tocar secretos, endpoints privados, llaves, wallets ni lógica sensible profunda;
- crear una rama futura sugerida: `feat/verify-cli-audit`

## 10. Operational command template

Plantilla segura:

```bash
git checkout main
git pull dof-mesh main
git checkout -b <branch-name>
git branch --show-current
git status
```

Antes de commit:

```bash
git branch --show-current
git status
npm run test:collect
```

Después de merge:

```bash
git checkout main
git pull dof-mesh main
git branch -d <branch-name>
git push dof-mesh --delete <branch-name>
npm run test:collect
git tag checkpoint/<name>
git push dof-mesh checkpoint/<name>
git status
```
