# Sistema de Memoria — DOF-MESH Legion

Este directorio es la infraestructura de aprendizaje de Claude entre sesiones.
Captura correcciones, observaciones y reglas graduadas del Soberano.

## Cómo funciona

```
Inicio de sesión
    ↓
VERIFICATION SWEEP — ejecuta verify: check de cada regla en learned-rules.md
    ↓
Trabajo normal
    ↓
corrections.jsonl    ← correcciones del Soberano (auto-capturadas)
observations.jsonl   ← patrones descubiertos y verificados con grep
violations.jsonl     ← violaciones detectadas por el sweep
sessions.jsonl       ← scorecard por sesión + tendencias
    ↓
/evolve (command manual)
    ↓
learned-rules.md     ← patrones graduados CON verify: checks
    ↓
CLAUDE.md / rules/   ← promovidos a config permanente
```

## Archivos

### corrections.jsonl
Correcciones del Soberano. Append-only. Claude escribe aquí cuando es corregido.
```json
{"timestamp": "2026-03-29T15:00:00Z", "correction": "agent_id debe ser int no string", "context": "usé agent_id='apex-1687'", "category": "api", "times_corrected": 1}
```

### observations.jsonl
Patrones verificados con grep. Solo se loguea si hay evidencia real.
```json
{"timestamp": "2026-03-29T15:00:00Z", "hypothesis": "Todos los módulos core usan logging.getLogger('dof.X')", "evidence": "Grep encontró 23 matches, 0 excepciones", "confidence": "confirmed", "verify": "Grep('getLogger', path='core/') → 1+ matches"}
```

### violations.jsonl
Violaciones de reglas detectadas en verification sweep.

### sessions.jsonl
Scorecard por sesión. Usado para detectar tendencias.

### learned-rules.md
Reglas graduadas de corrections y observations. Max 50 líneas.
Cada regla DEBE tener una línea `verify:` — reglas sin verificación son deseos, no guardrails.

### evolution-log.md
Historial de decisiones de `/evolve`. Qué se aprobó, qué se rechazó.

## Escalera de Promoción

| Señal | Destino |
|---|---|
| Corregido 1 vez | corrections.jsonl |
| Corregido 2 veces, mismo patrón | learned-rules.md (auto-promovido) |
| Observado 3+ veces confirmado | learned-rules.md (via /evolve) |
| En learned-rules 10+ sesiones siempre seguido | Candidato a CLAUDE.md o rules/ |
| Rechazado en /evolve | evolution-log.md (nunca re-propuesto) |

## Reglas del sistema

1. Correcciones → loguear siempre, sin excepción
2. Observaciones → verificar con grep ANTES de loguear
3. Learned rules → max 50 líneas, cada una con verify:
4. Nunca borrar corrections.jsonl — es la historia
5. Una regla sin verify: es deuda técnica — agregarla antes del próximo /evolve
