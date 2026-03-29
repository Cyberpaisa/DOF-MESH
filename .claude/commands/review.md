---
description: Pipeline de revisión pre-commit DOF-MESH. Corre tests, verifica reglas aprendidas, revisa el diff.
---

## Pre-flight

!`git diff --name-only main...HEAD 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || echo "Sin diff"`

!`python3 -m unittest discover -s tests 2>&1 | tail -5`

!`git status --short`

## Reglas Aprendidas Activas
!`cat .claude/memory/learned-rules.md 2>/dev/null || echo "Sin reglas"`

## Diff
!`git diff HEAD~1 2>/dev/null || git diff --cached`

## Instrucciones

1. Si algún test falló → lista failures con fixes exactos. STOP.

2. Corre CADA verify: check de learned-rules.md contra el diff. Reporta violations.

3. Revisa el diff por:
   - Bugs (null access, type errors, unhandled exceptions)
   - Seguridad DOF (private keys, agent_id como string, Z3 unknown como PASS)
   - Invariantes DOF (HARD_RULES modificados, LLM en governance path)
   - Performance (JSONL completo en memoria, retry sin backoff)
   - Tests eliminados en vez de arreglados

4. Por cada problema: archivo, línea, qué está mal, cómo arreglarlo.

5. Veredicto: SHIP IT / NECESITA TRABAJO / BLOQUEADO.

6. Si SHIP IT: sugiere el mensaje de commit en formato:
   `tipo(scope): descripción`
   Ejemplo: `feat(evolve): attestation on-chain cuando pesos evolucionan`
