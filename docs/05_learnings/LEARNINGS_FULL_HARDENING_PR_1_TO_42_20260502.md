# Learnings — Full DOF-MESH Hardening PR #1–#42

## 1. Resumen ejecutivo

Entre PR #1 y PR #42, DOF-MESH cerró un ciclo largo de hardening técnico, estabilización de testing, alineación documental y auditoría de semántica criptográfica. El resultado no fue solo una suite más confiable, sino una disciplina operativa más clara: validar antes de cambiar, documentar antes de endurecer, y cerrar cada etapa con evidencia reproducible en `main`.

El tramo final del ciclo consolidó dos temas críticos:

- el comportamiento real de `ProofSerializer.hash_proof` frente a `Web3.keccak` y `hashlib.sha3_256`;
- la necesidad de corregir comentarios y lenguaje histórico que podían inducir a error aunque la lógica ya estuviera endurecida.

## 2. Estado final validado

- HEAD #42: `9f4df34 docs: clarify legacy hash-domain comments (#42)`
- Checkpoint #42: `checkpoint/pr-1-to-42-clarify-legacy-hash-domain-comments`
- `4802 tests collected`

## 3. Qué se logró

- testing hardening
- CI/Z3 alignment
- mutation workflow hardening
- docs/index/readme/architecture alignment
- verify CLI docs
- proof registry consistency
- Hardhat scoped testing
- proof registry behavior coverage
- proof hash compatibility
- EVM Keccak semantics
- removal of silent sha3_256 fallback
- hash-domain legacy audit
- full hardening memory PR #1–#40
- legacy hash-domain comments clarified

## 4. Aprendizajes técnicos

- `SHA3-256` / FIPS no es `EVM keccak256`.
- `Web3.keccak` es la fuente canónica para proof hashes EVM / Solidity / Avalanche.
- `SHA256`, Merkle, `HMAC`, `BLAKE3` y `certificateHash` son dominios separados.
- Comentarios y docstrings pueden crear riesgo operacional aunque la lógica funcione correctamente.
- Hardhat scoped testing permite aislar subsets sin tocar la config principal.

## 5. Aprendizajes operativos

- audit first
- read-only before write
- one PR, one purpose
- docs before enforcement
- tests before implementation
- main validation before checkpoint
- no broad agentic edits

## 6. Errores detectados

- Codex puede abrir fuera del repo.
- ramas viejas pueden apuntar a commits anteriores.
- no asumir merge por push.
- no asumir merge por tag.
- no asumir checkpoint sin validar `main`.
- `docs/09_sessions/` está ignorado y requiere `git add -f`.
- evitar `Find and fix a bug in @filename` para auditorías controladas.

## 7. Protocolo maestro Git / PR / checkpoint

Nunca crear checkpoint solo porque:

- el PR fue creado;
- el PR fue mergeado;
- existe un tag;
- GitHub muestra algo como completado;
- el push fue exitoso;
- la rama parece limpia.

Antes de cualquier checkpoint:

1. `git checkout main`
2. `git pull dof-mesh main`
3. `git log --oneline --decorate -8`
4. confirmar commit esperado en `main`
5. confirmar archivos esperados en `main`
6. ejecutar validaciones técnicas
7. `npm run test:collect`
8. confirmar `git status` limpio
9. solo entonces crear y subir checkpoint

## 8. Modelos usados

- **GPT-5.5 Thinking**
  Se usó para auditorías de mayor ambigüedad, contraste de opciones y síntesis de decisiones técnicas donde importaba más la calidad del razonamiento que la velocidad.

- **GPT-5.5 Codex**
  Se usó para trabajo de ejecución técnica controlada con contexto de repo, lectura estructurada, validaciones y cambios acotados con disciplina operativa fuerte.

- **GPT-5.4 medium Codex**
  Se usó cuando convenía priorizar velocidad y costo en tareas concretas, siempre que el riesgo técnico fuera más bajo o el patrón de trabajo ya estuviera claramente definido.

El criterio general fue: subir capacidad de razonamiento cuando había ambigüedad, divergencia semántica o riesgo operacional; usar variantes más ligeras cuando el trabajo era repetible y bien delimitado.

## 9. Reglas futuras

- No mezclar auditoría, enforcement y documentación en un solo PR si no es estrictamente necesario.
- No asumir compatibilidad criptográfica por similitud de nombres entre familias de hash.
- No publicar checkpoints sin validar `main` localmente.
- No usar cambios amplios o prompts abiertos cuando la tarea exige precisión histórica.
- Documentar primero la semántica de un dominio antes de endurecer runtime si existe riesgo de romper integraciones.

## 10. Próximos PRs sugeridos

- PR de seguimiento para auditar y endurecer rutas `verify` del CLI.
- PR de documentación operacional sobre validaciones de contratos/registry si se reabre el frente Solidity/Hardhat.
- PR de limpieza controlada de deuda legacy documental restante, sin tocar runtime.
