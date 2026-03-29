---
description: Boot de sesión DOF-MESH. Carga memoria, verifica reglas, reporta estado del sistema.
---

## Memoria

### Reglas Aprendidas
!`cat .claude/memory/learned-rules.md 2>/dev/null || echo "Sin reglas aún"`

### Última sesión
!`tail -1 .claude/memory/sessions.jsonl 2>/dev/null || echo "Sin historial de sesiones"`

### Violaciones no resueltas
!`tail -5 .claude/memory/violations.jsonl 2>/dev/null || echo "Sin violaciones"`

## Estado del Repo
!`git log --oneline -5`

!`python3 -m unittest discover -s tests 2>&1 | tail -3`

## Instrucciones

1. Lee cada regla en learned-rules.md.
   Para cada regla con línea `verify:` → ejecuta el check AHORA.

2. Reporta:
   - Todas pasan → "Sistema verificado. Listo para trabajar."
   - Alguna falla → lista violations con archivo:línea y fix específico.

3. Revisa tendencia de sesiones: correcciones aumentando o disminuyendo.

4. Una frase de estado: "Sesión X: Y correcciones previas. Z/Z reglas verificadas. [Estado]."

5. Listo. Procede con la tarea del Soberano.
