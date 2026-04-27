# DOF-MESH — CHANGELOG Histórico

Evolución de métricas por sesión. Valores medidos directamente del repo en cada hito.

## v0.8.0 — sesión 12 (2026-04-16) — Deuda Técnica Cero

**Auditoría completa end-to-end con team agents. Todo en verde.**

| Métrica | Valor |
|---|---|
| LOC (core+dof) | 65,360 |
| Core modules | 173 (0 imports rotos) |
| Test files | 215 |
| Tests discovered | 4,800 (0 load errors) |
| Chains verificadas | 9 (3 mainnet + 5 testnet + Tempo) |
| On-chain attestations | 30+ |
| CrewAI agents | 20 |
| Scripts | 79 |
| Docs .md | 223 |
| CI workflows | 4 |
| ASR governance | 2.3% regex / ~4.5% multi-capa |
| CVEs cerrados | 19 |

Cambios clave:
- `core/hyperion_bridge.py` recuperado desde `_internal/core_legacy/` (usado en mesh_orchestrator:39, 161, 486)
- `crewai 1.14.1` + `crewai-tools` + `filelock` + `cryptography` + `setuptools` instalados en python3.11
- 9 archivos .py huérfanos movidos de raíz → `scripts/diagnostics/` + `scripts/experiments/regex/`
- 7 PNGs movidos a `proof/evidence/2026-04/`
- `.gitignore` actualizado: `.playwright-mcp/`, `global-hackfest-2026/` (256M fork), `video-render/` (819M renders)

## v0.8.0 — sesión 11 (2026-04-16) — CVEs + daemon + release.sh

- `scripts/release.sh` creado (auto-bump patch/minor/major + dry-run)
- `autonomous_daemon.py` con heartbeat cada 10 ciclos + recovery tras 5 errores
- 7 CVEs cerrados en governance (CVE-DI-003, SI-003/004/005/007/008, GB-003)
- Tests: 63/63 governance+constitution+z3 OK
- Commit: `f3fbb67`

## v0.8.0 — sesión 10-B (2026-04-13) — Red Team + Capa 8

- 36 commits · 4,800 tests · 178 módulos (conteo incluye __init__.py)
- Red Team + Capa 8 Semántica + Evolution Engine + Segundo Cerebro Vivo
- `datos-colombia-mcp` integrado (SECOP + MEData)
- ASR bajó de 13.6% → 2.3% (5 CVEs parchados, 1 accepted risk)
- Commit: `38f43ec` / `b4ae273`

## v0.6.0 — sesión 5 (2026-04-05)

- CI verde: 583/583 tests
- Mintlify: 23 páginas live en dofmesh.com
- QA: 11/11 checks
- Tráfico: 459 visitas
- Commit: `672fba5`

## v0.5.1 (2026-04-03 — on-chain verification)

- Tests: 4,157 pasando, 0 fallos
- Módulos: 142
- 9 chains activas (3 mainnet + 5 testnet)
- Attestations on-chain: 30+
- Ciclos autónomos: 238
- Z3 proofs: 4/4 PROVEN
- SDK: v0.5.1 en PyPI

## v0.5.0 (histórico — febrero/marzo 2026)

- Core modules: 132
- Test files: 143
- Tests: 3,698
- LOC: 119,409 (luego limpiado → 65,360 en v0.8.0)
- Docs: 105 .md
- Scripts: 13
- CI: 3 workflows
- SDK: dof-sdk 0.6.0
- On-chain: 21+ attestations (solo Avalanche)
- CrewAI: 17 agents
