---
description: Performance rules for DOF governance pipeline
paths:
  - "core/**/*"
  - "dof/**/*"
---

# DOF Performance Rules

## Los 3 cuellos de botella críticos en DOF

### 1. Z3 Latencia
Z3 debe resolver en <10ms para governance en tiempo real.
Si un constraint es demasiado complejo, simplificar antes de agregar.
verify: ProofResult.proof_time_ms < 10 en test runs normales

### 2. Carga de JSONL
No cargar archivos JSONL completos en memoria si tienen >10K líneas.
Usar streaming line-by-line para evolve_data.py y logs grandes.
verify: Grep("readlines()\|read()", path="core/evolve_data.py") → 0 matches

### 3. Providers LLM
Provider chains tienen backoff TTL (5→10→20 min).
Nunca hacer retry inmediato en loop — crash silencioso de performance.
verify: Grep("time.sleep(0)", path="core/providers.py") → 0 matches

## Web3 / Chain

Limitar reintentos de transaction receipt a timeout=60s.
verify: Grep("wait_for_transaction_receipt", path="core/chain_adapter.py") → tiene timeout parameter

Caché de chain_id validation — no verificar en cada llamada.
verify: _initialized flag en DOFChainAdapter

## Tests de performance

Tests que midan latencia Z3 deben correr en entornos limpios.
Benchmark baseline: Z3 4 teoremas < 50ms total.
