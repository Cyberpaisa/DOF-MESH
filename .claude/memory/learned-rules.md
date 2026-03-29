# Learned Rules — DOF-MESH

Reglas graduadas de correcciones y observaciones del Soberano.
Max 50 líneas. Cada regla tiene verify: machine-checkable.
Se cargan al inicio de cada sesión.

---

- agent_id debe ser int (token_id ERC-8004), nunca string.
  verify: Grep('agent_id="', path="core/") → 0 matches
  [source: corrección confirmada, 2026-03-29]

- Imports de módulos internos: `from core.X import Y` (no `from dof.X` para módulos en core/).
  verify: Grep("from dof.chain_adapter\|from dof.governance\|from dof.z3", path="core/") → 0 matches
  [source: corrección confirmada, 2026-03-29]

- Tests usan unittest, no pytest. Comando: `python3 -m unittest discover -s tests`.
  verify: Grep("import pytest", path="tests/") → 0 matches
  [source: observación confirmada, 2026-03-29]

- Hashes de attestation en documentación se truncan (0xabcd...ef), nunca el hash completo de 64 chars.
  verify: manual (pre-commit hook detecta el patrón)
  [source: incidente pre-commit hook, 2026-03-29]

- EvolveEngine budget_usd=0.0 no bloquea el run — solo aplica budget check cuando budget_usd > 0.
  verify: Grep("budget_usd > 0", path="core/evolve_engine.py") → 1+ matches
  [source: corrección de bug, 2026-03-29]

- Git commits: NUNCA Co-Authored-By. Siempre --author="Cyber <jquiceva@gmail.com>".
  verify: manual
  [source: regla canónica CLAUDE.md]

- Workers NUNCA hacen push — solo el Soberano pushea.
  verify: manual (pre-push hook activo)
  [source: incidente SCOPE-001, 2026-03-29]

<!-- Máximo 50 líneas — promover a CLAUDE.md o rules/ cuando esté lleno -->
