---
description: Auditoría del sistema de evolución DOF-MESH. Promueve reglas aprendidas a permanentes. Correr cada 10+ sesiones o cuando learned-rules.md esté lleno.
---

## Estado Actual

### Reglas Aprendidas
!`cat .claude/memory/learned-rules.md 2>/dev/null || echo "Sin reglas aún"`

### Correcciones Recientes (últimas 20)
!`tail -20 .claude/memory/corrections.jsonl 2>/dev/null || echo "Sin correcciones"`

### Observaciones Recientes (últimas 20)
!`tail -20 .claude/memory/observations.jsonl 2>/dev/null || echo "Sin observaciones"`

### Violaciones detectadas (últimas 10)
!`tail -10 .claude/memory/violations.jsonl 2>/dev/null || echo "Sin violaciones"`

### Historial de evolución
!`tail -40 .claude/memory/evolution-log.md 2>/dev/null || echo "Sin historial"`

### Tendencia de sesiones
!`tail -10 .claude/memory/sessions.jsonl 2>/dev/null || echo "Sin sesiones registradas"`

## Tu tarea — Eres el meta-ingeniero de DOF-MESH

### Paso 1: Analiza correcciones
- Agrupa por patrón
- Corrección 2+ veces → debe estar en learned-rules (si no, promover AHORA)
- Clusters que señalan regla faltante en CLAUDE.md o rules/

### Paso 2: Analiza observaciones
- Observaciones confirmadas múltiples veces → candidatas a learned-rules
- Observaciones que coinciden con correcciones = señal más fuerte

### Paso 3: Audita learned-rules.md
Para cada regla:
- ¿Sigue vigente? ¿El codebase la sigue?
- ¿10+ sesiones siempre seguida? → candidata a CLAUDE.md o rules/
- ¿Redundante con linter o rules/ existente? → PRUNE
- ¿Tiene verify:? Si no, agregarla ahora

### Paso 4: Propón cambios

Para cada propuesta:
```
PROPONER: [acción]
  Regla: [texto]
  Fuente: [corrections/observations/learned-rules]
  Evidencia: [por qué]
  Destino: [learned-rules.md | CLAUDE.md | rules/X.md | ELIMINAR]
```

Acciones: PROMOVER | GRADUAR | ELIMINAR | ACTUALIZAR | AGREGAR

### Paso 5: Espera aprobación

Lista TODAS las propuestas. NO apliques ningún cambio.
El Soberano dirá: aprobado, rechazado, o modificar.
Solo aplica los aprobados. Loguea todo en evolution-log.md.

### Constraints
- Nunca eliminar reglas de seguridad
- Nunca debilitar completion criteria
- Max 50 líneas en learned-rules.md
- Toda regla debe tener verify: machine-checkable
- No re-proponer lo que fue rechazado (ver evolution-log.md)
