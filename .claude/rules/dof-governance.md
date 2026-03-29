---
description: DOF governance invariants — active when editing core/, dof/, tests/
paths:
  - "core/**/*"
  - "dof/**/*"
  - "tests/**/*"
---

# DOF Governance Rules

## Invariantes Absolutas (nunca negociar)

**NUNCA** uses LLM en el path de governance — todo determinístico.
verify: Grep("openai\|anthropic\|llm_call", path="core/governance.py") → 0 matches en funciones críticas

**NUNCA** modifiques HARD_RULES ni Z3 theorems via EvolveEngine.
verify: FORBIDDEN_TARGETS en evolve_engine.py incluye "hard_rules", "z3_theorems"

**NUNCA** borres tests existentes — si fallan, arregla el código.
verify: git diff --name-only | grep "tests/" → solo archivos nuevos o modificados, nunca eliminados

## Antes de Modificar core/

1. Lee el archivo completo — nunca asumas la firma de un método
2. Verifica imports: `from core.X import Y` (no `from dof.X`) para módulos en core/
3. Corre tests del módulo antes y después: `python3 -m unittest tests.test_<módulo>`
4. Blast radius: qué importa este módulo → grep antes de cambiar firmas

## Patrón de módulos DOF

- Datos → JSONL (un JSON por línea)
- Logging → `logger = logging.getLogger("dof.<modulo>")`
- Errores → no swallowear, loguear con context
- Singletons → deben tener `reset()` para tests

## Tests

- Usar unittest (NO pytest — conflicto con web3)
- `python3 -m unittest discover -s tests` — todos deben pasar antes de commit
- Test names: `test_<qué>_<cuando>_<resultado_esperado>`
