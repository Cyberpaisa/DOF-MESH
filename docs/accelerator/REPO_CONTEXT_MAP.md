# DOF-MESH — Repo Context Map

## 1. Resumen del propósito del repo

Repositorio principal de DOF-MESH, orientado a gobernanza determinística, observabilidad y verificación previa para sistemas multiagente con IA. El foco visible del repo combina:

- framework Python para orquestación, observabilidad e integraciones;
- documentación extensa de arquitectura, estrategia, research y operaciones;
- frontend web;
- contratos y artefactos blockchain;
- pruebas, scripts operativos y componentes auxiliares.

Este archivo debe servir como contexto base para futuras sesiones, evitando escaneos completos innecesarios.

## 2. Estructura principal de carpetas

Nivel alto detectado:

- `agents/`: definiciones y perfiles de agentes.
- `api/`: superficie de API en Python.
- `core/`: núcleo técnico principal.
- `dof/`: paquete/CLI principal en Python.
- `integrations/`: integraciones externas.
- `contracts/`: contratos y despliegues relacionados.
- `rust/`: módulo Rust `dof_z3_gate`.
- `frontend/`: app Next.js.
- `video-render/`: proyecto Remotion para video/demo.
- `scripts/`: utilidades operativas, benchmarks, deploy, diagnostics y experiments.
- `tests/`: suites de prueba por categoría.
- `docs/`: corpus documental amplio.
- `docs/accelerator/`: documentos compactos para preincubación.
- `data/`, `knowledge/`, `memory/`, `proof/`, `reports/`, `artifacts/`: datos, evidencia, salidas y soportes.

Subárboles relevantes dentro de `core/`:

- `core/adapters`
- `core/crews`
- `core/evolution`
- `core/gateway`
- `core/intelligence`
- `core/observability`
- `core/redteam`
- `core/router`
- `core/tools`

## 3. Archivos/documentos clave

Fuentes base ya usadas o visibles:

- `AGENTS.md`
- `PROJECT_BRIEF.md`
- `pyproject.toml`
- `requirements.txt`
- `package.json`
- `docker-compose.yml`
- `frontend/package.json`
- `video-render/package.json`
- `rust/dof_z3_gate/Cargo.toml`

Documentos útiles detectados, sin necesidad de abrir todo el repo:

- `docs/01_architecture/`
- `docs/04_strategy/`
- `docs/05_operations/`
- `docs/06_security/` mencionado desde manifiestos
- `docs/07_integrations/`
- `docs/audits/`
- `docs/accelerator/`

Nota: `README.md` existe, pero no fue inspeccionado por la restricción vigente de `AGENTS.md`.

## 4. Componentes técnicos principales detectados

- SDK/CLI Python: `dof` expone comando `dof` vía `pyproject.toml`.
- Núcleo de orquestación/observabilidad: concentrado en `core/`.
- API backend: carpeta `api/`.
- Integraciones: `integrations/datos-colombia`, `integrations/obsidian`, `integrations/virtuals`.
- Frontend institucional/producto: `frontend/` con Next.js.
- Video/demo assets: `video-render/`.
- Contratos/artefactos blockchain: `contracts/`, `artifacts/`, `out/`, `contracts_skale_deploy/`.
- Verificación/gate en Rust: `rust/dof_z3_gate`.
- Red team / seguridad / observabilidad experimental: `core/redteam`, `tests/red_team`, `docs/redteam`.

## 5. Stack o lenguajes detectados

- Python 3.10+ como stack principal.
- TypeScript/JavaScript para frontend y tooling.
- Next.js 16 + React 19 en `frontend/`.
- Tailwind CSS en frontend y video-render.
- Hardhat para contratos Solidity/infra EVM.
- Rust con `pyo3` para módulo `dof_z3_gate`.
- Docker Compose para entorno de ejecución aislado.

Dependencias visibles relevantes:

- Python: `z3-solver`, `rich`, `pyyaml`, `blake3`, `psutil`, `crewai`, `fastapi`, `uvicorn`, `sqlalchemy`, `streamlit`, `groq`.
- Node: `hardhat`, `@openzeppelin/contracts`, `next`, `react`, `framer-motion`.
- Rust: `pyo3`, `serde`, `serde_json`, `sha3`.

## 6. Scripts/comandos disponibles en archivos públicos

Top-level `package.json`:

- `npm test`: placeholder, no suite real definida ahí.

Top-level `pyproject.toml`:

- CLI instalada: `dof`

`frontend/package.json`:

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`

`video-render/package.json`:

- `npm run dev`
- `npm run render`
- `npm run upgrade`

Infra visible:

- `docker-compose.yml` define servicio `citadel-swarm` / `dof-mesh-citadel`

## 7. Módulos que parecen importantes

Por estructura y naming, conviene tratar como zonas prioritarias:

- `core/observability`
- `core/gateway`
- `core/router`
- `core/intelligence`
- `core/redteam`
- `dof/`
- `api/`
- `integrations/`
- `rust/dof_z3_gate`
- `contracts/`
- `scripts/diagnostics`, `scripts/monitoring`, `scripts/deploy`
- `tests/integration`, `tests/red_team`, `tests/z3_generated`

También hay un subárbol `deterministic-observability-framework/` que parece snapshot, fork o duplicado del proyecto principal. No asumir que sea la fuente canónica sin validación previa.

## 8. Documentos útiles para aceleradora

Ya creados:

- `docs/accelerator/ONE_PAGER.md`
- `docs/accelerator/EXECUTIVE_SUMMARY.md`
- `docs/accelerator/SECURITY_AND_DISCLOSURE_LIMITS.md`
- `docs/accelerator/HIGH_LEVEL_ARCHITECTURE.md`

Colecciones documentales útiles para futuras síntesis:

- `docs/01_architecture/` para arquitectura pública.
- `docs/04_strategy/` para narrativa, posicionamiento y roadmap.
- `docs/05_operations/` para madurez operativa.
- `docs/audits/` para señales de confianza.

## 9. Riesgos o carpetas sensibles a evitar

Evitar inspección casual de:

- `.env` y cualquier secreto montado o referenciado.
- `keys/`, `certs/`, `Sovereign_Vault/`, `supabase/.temp/`
- `logs/`, `memory/`, `conversations/`, `uploads/`
- `data/identities` y otros datasets con posible información sensible.
- `proof/`, `artifacts/`, `out/`, `release_artifacts/` si exponen detalles internos no necesarios.
- `docker-compose.yml` muestra montaje de `./.env` y `./Sovereign_Vault`; no usar como guía de ejecución sin revisión.

Riesgo adicional:

- `node_modules/`, `frontend/node_modules/`, `video-render/node_modules/` no aportan contexto y aumentan ruido.

## 10. Próximas tareas recomendadas para preparar el proyecto profesionalmente

- Crear `docs/accelerator/ROADMAP_90_DAYS.md`.
- Crear `docs/accelerator/BUSINESS_MODEL.md`.
- Crear `docs/accelerator/GLOSSARY.md`.
- Identificar desde `docs/01_architecture` y `docs/04_strategy` solo 3 a 5 documentos canónicos para narrativa externa.
- Definir una lista corta de métricas públicas verificables y repetibles.
- Preparar versión “mentor/evaluador” y versión “posible cliente B2B”.
- Aclarar si `deterministic-observability-framework/` es histórico, espejo o workspace activo.
- En futuras sesiones, usar este archivo y `docs/accelerator/*` como contexto principal antes de leer código.
