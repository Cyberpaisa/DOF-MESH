# DOF-MESH — Sistema de Documentación Maestro
> Última actualización: 2026-04-12 | v0.8.0

## Regla de oro

Un lugar para cada tipo de información.
Nunca duplicar intencionalmente.
Si existe, actualizar. Si no existe, crear en el lugar correcto.

---

## Mapa canónico

| Tipo | Repo | Archivo | Formato |
|------|------|---------|---------|
| Lección técnica backend | equipo-de-agentes | `docs/02_research/LESSONS_LEARNED.md` | `**L-NN — título.**` |
| Lección frontend/UX/CSS/iOS | dof-landing | `docs/sessions/LESSONS_LEARNED.md` | `## LECCIÓN NN` |
| Regla operacional activa | equipo-de-agentes | `.claude/memory/learned-rules.md` | max 50 líneas |
| Sesión de trabajo | dof-landing | `docs/sessions/YYYY-MM-DD-session-NN.md` | template |
| Arquitectura | equipo-de-agentes | `docs/01_architecture/` | libre |
| Estado del proyecto | equipo-de-agentes | `MEMORY.md` | actualizar con cada fase |
| Decisión estratégica | equipo-de-agentes | `docs/04_strategy/` | libre |
| Historial versiones | equipo-de-agentes | `CHANGELOG.md` | semver |
| Constitución de documentación | equipo-de-agentes | `docs/DOC_SYSTEM.md` | este archivo |

---

## Protocolo cuando Juan dice "documenta"

Claude pregunta automáticamente:

1. ¿Es lección técnica, sesión, regla o arquitectura?
2. ¿Afecta frontend (dof-landing) o backend (equipo-de-agentes)?
3. ¿Ya existe entrada similar? → buscar antes de crear

---

## Protocolo de recuperación (contexto perdido)

Leer en este orden:

1. `CLAUDE.md` → reglas fundamentales
2. `.claude/memory/learned-rules.md` → reglas operacionales activas
3. `docs/02_research/LESSONS_LEARNED.md` → histórico L-1 → L-72
4. `dof-landing/docs/sessions/README.md` → sesiones recientes
5. `MEMORY.md` → estado actual del sistema

---

## Repos y propósito

| Repo | Propósito | CI | GitHub |
|------|-----------|----|--------|
| equipo-de-agentes | SDK, governance, multi-agent, tests | ✅ 4,800 tests | github.com/Cyberpaisa/DOF-MESH |
| dof-landing | dofmesh.com, chat widget | ✅ Vercel auto-deploy | github.com/Cyberpaisa/dof-landing |
| deterministic-observability-framework | Origen público v0.4.1 | — | github.com/Cyberpaisa/deterministic-observability-framework |

---

## Línea de tiempo de evolución

| Versión | Repo | Fecha | Hito |
|---------|------|-------|------|
| v0.3.3 | `dof-hackathon` branch | 2026-03-24 | Prototipo hackathon, 53 test files |
| v0.4.1 | `deterministic-observability-framework` main | 2026-03-22 | Open source público, 69 test files |
| v0.6.0 | `equipo-de-agentes` (DOF-MESH) | 2026-04-04 | PyPI live, 4,800 tests — harness: mock_provider + session_resume + cost_tracker |
| v0.8.0 | `equipo-de-agentes` (DOF-MESH) | 2026-04-12 | 4,800 tests · 148 módulos |
| — | `dof-landing` | 2026-04-04 | dofmesh.com producción, chat widget |

---

## Estado actual (actualizar con cada fase)

- **SDK version:** v0.8.0
- **Módulos Python:** 231 archivos
- **Tests:** 4,800 passing (583 en CI GitHub Actions)
- **Lecciones:** L-1 → L-72
- **Chains:** 8 (3 mainnet: Avalanche, Base, Celo + 5 testnet)
- **Agentes especializados:** 15
- **Nodos mesh:** 29 registrados
- **Attestations on-chain:** 30+
- **Docker:** dof-mesh-citadel activo (OrbStack)

---

## Duplicados conocidos y resolución

| Archivo | Ubicaciones | Canónico |
|---------|-------------|----------|
| `LESSONS_LEARNED.md` (backend) | `equipo-de-agentes/docs/02_research/` + copias | `equipo-de-agentes/docs/02_research/` |
| `LESSONS_LEARNED.md` (frontend) | `dof-landing/docs/sessions/` | `dof-landing/docs/sessions/` |
| `MEMORY.md` | `equipo-de-agentes/` + `~/.claude/` | `equipo-de-agentes/` para proyecto, `~/.claude/` para Claude |
