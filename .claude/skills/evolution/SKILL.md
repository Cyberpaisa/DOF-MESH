---
name: evolution-engine
description: >
  Sistema autónomo de aprendizaje DOF-MESH. Se activa en:
  - Inicio de sesión (verification sweep de todas las reglas)
  - Correcciones del Soberano ("no", "mal", "eso no", "siempre X")
  - Fin de tarea (scorecard de sesión)
  - Descubrimientos durante trabajo (verificación de hipótesis)
  - "recuerda esto", "agrega esto como regla"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Evolution Engine — DOF-MESH

No eres un diario. Eres un sistema inmune. Verificas, enforces y aprendes.

---

## SECCIÓN 1: VERIFICATION SWEEP (al inicio de sesión)

Lee .claude/memory/learned-rules.md. Por cada regla con línea `verify:`:

1. Ejecuta el check (Grep, Glob, o Read).
2. PASS → silencio. Continúa.
3. FAIL → loguea en .claude/memory/violations.jsonl:
   ```json
   {"timestamp": "NOW", "rule": "texto", "check": "qué se corrió", "result": "qué se encontró", "file": "dónde", "auto_fixed": false}
   ```
   Reporta al Soberano:
   ```
   VIOLACIÓN DETECTADA:
   - [regla]: encontrado [violación] en [archivo:línea]
     fix: [fix específico]
   ```

Si TODAS pasan → silencio total. El mejor sistema inmune es invisible.

---

## SECCIÓN 2: CAPTURA DE CORRECCIONES

Cuando el Soberano te corrige:

1. Reconoce naturalmente.
2. Loguea en .claude/memory/corrections.jsonl:
   ```json
   {"timestamp": "NOW", "correction": "qué", "context": "qué hacías", "category": "api|security|testing|naming|process", "times_corrected": 1, "verify": "check generado"}
   ```
3. Genera verify: pattern inmediatamente. Si la corrección es "no hagas X" → `Grep("X pattern") → 0 matches`.
4. Misma corrección 2ª vez → auto-promover a learned-rules.md CON verify.
5. Aplica la corrección inmediatamente.

---

## SECCIÓN 3: OBSERVACIONES CON VERIFICACIÓN

Cuando notas un patrón durante el trabajo:

1. Formula como afirmación testeable.
2. Verifica con grep INMEDIATAMENTE antes de loguear.
3. Loguea con evidencia:
   ```json
   {"timestamp": "NOW", "hypothesis": "X", "evidence": "Grep encontró Y", "counter_examples": 0, "confidence": "confirmed", "verify": "Grep('X') → N matches"}
   ```
4. Si confidence=confirmed y counter_examples=0 → auto-promover a learned-rules.md.
   Informa: "Patrón verificado y agregado como regla: [regla]. Check: [verify]."

---

## SECCIÓN 4: SCORECARD DE SESIÓN

Al cerrar sesión o antes de commit:

```json
{"date": "TODAY", "corrections_received": 0, "rules_checked": 7, "rules_passed": 7, "rules_failed": 0, "violations": [], "observations_made": 0, "rules_added": 0}
```

Si sessions.jsonl tiene 5+ entradas:
- Correcciones disminuyendo → sistema funcionando
- Correcciones planas o subiendo → reglas no consultadas o muy vagas → avisar para /evolve
- Misma violación recurrente → necesita graduarse a CLAUDE.md o convertirse en linter rule

Una línea de tendencia: "Sesión 5: 0 correcciones (baja de 3 avg). 7/7 reglas pasando."

---

## SECCIÓN 5: "RECUERDA ESTO"

Cuando el Soberano pide recordar algo:

1. Reescribe como regla testeable.
2. Genera verify: pattern.
3. Agrega a learned-rules.md:
   ```
   - [regla]
     verify: [check]
     [source: soberano-explícito, FECHA]
   ```
4. Confirma: "Regla agregada: [regla]. Verificación: [check]. Auto-enforced desde ahora."

Si no puedes hacerla machine-checkable: "Agregada como regla manual. La sigo pero no puedo auto-verificar. Reformula para que pueda escribir un grep."

---

## GESTIÓN DE CAPACIDAD

Antes de agregar a learned-rules.md:
1. Contar líneas. Max 50.
2. Si >45 líneas → revisar candidatos a graduación (10+ sesiones seguidas)
3. Sugerir /evolve si está lleno
