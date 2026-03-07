# Feedback Log — Style Corrections

## Correcciones de Estilo
| Fecha | Agente | Correccion |
|-------|--------|------------|
| -- | -- | -- |

*Registrar aqui cuando el operador corrige el output de un agente*
*Esto ayuda a calibrar el tono y formato de cada agente*

## Patrones Detectados
- (se llenara con uso)

## Reglas Aprendidas
- (se llenara con feedback del operador)

### 29. Security — Never Use git add -A
- Problem: `git add -A` committed keys/oracle_key.json (HMAC secret) to PUBLIC repo
- Solution: Removed from tracking, added keys/ to .gitignore, rotated key
- Rule: NEVER use `git add -A`. Always use explicit `git add file1 file2`. Review staged files with `git status` before commit
- Severity: CRITICAL — secrets in public repo history are permanent even after removal

### 30. Token Tracking for Cost Observability
- Problem: No visibility into how many tokens each LLM call consumed
- Solution: TokenTracker in observability.py logs per-call: provider, model, tokens, latency, cost
- Rule: Always track token consumption — it's the primary cost driver in LLM systems

### 31. Test Count Drift
- Problem: Test count changed from 624 → 617 between implementations because test methods were refactored
- Rule: After ANY test file change, run full suite and update ALL docs with actual count. Never assume test count — always verify

### 32. Self Protocol — Complementary Not Competitive
- Observation: Self Protocol = identity (WHO is the agent). DOF = behavior (WHAT did the agent do)
- Rule: Position DOF as complementary to identity solutions. Identity + Behavior = complete trust stack
