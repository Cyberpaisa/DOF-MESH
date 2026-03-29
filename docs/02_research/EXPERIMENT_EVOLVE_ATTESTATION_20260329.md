# EvolveEngine On-Chain Attestation — Experimento 2026-03-29

## Qué se construyó

Extensión de `EvolveController.run()` para escribir un attestation inmutable on-chain cada vez que el motor de evolución adopta nuevos pesos TRACER (cuando `result.adopted == True`).

## Componentes implementados

### `core/evolve_engine.py` — cambios

1. **Llamada en `run()`** (después de `save_adopted`):
   ```python
   if adopted:
       self._attest_evolution_onchain(result)
   ```

2. **Nuevo método `_attest_evolution_onchain(result)`**:
   - Construye un payload JSON con: `run_id`, `target`, `baseline_score`, `new_score`, `score_delta_pct`, `new_weights`, `candidates_evaluated`, `timestamp`, `event`
   - Calcula `proof_hash = sha3_256(json.dumps(payload, sort_keys=True))` — equivalente a keccak256
   - Usa `DOFChainAdapter.from_chain_name("avalanche", dry_run=dry_run)` con `dry_run=True` si `DOF_PRIVATE_KEY` no está en el entorno
   - Escribe el registro en `logs/evolve/evolution_attestations.jsonl`
   - Es no-fatal: si falla el chain call, loguea warning y retorna `{"status": "error", ...}`

### `tests/test_evolve_attestation.py` — 5 tests nuevos

| Test | Descripción |
|---|---|
| `test_attest_returns_dict` | El método siempre retorna dict |
| `test_attest_has_proof_hash_on_error` | proof_hash presente incluso si falla la chain |
| `test_attest_creates_log_file` | Se escribe en `evolution_attestations.jsonl` con `event=WEIGHTS_EVOLVED` |
| `test_attest_proof_hash_format` | El hash es `0x` + 64 caracteres hex (66 total) |
| `test_run_with_adopted_triggers_attestation` | `run()` llama exactamente 1 vez a `_attest_evolution_onchain` cuando `adopted=True` |

## Cómo funciona

```
EvolveController.run()
    ├── evaluates N candidates
    ├── if improvement_pct >= min_improvement_pct → adopted = True
    ├── _db.save_adopted(result)          ← ya existía
    └── _attest_evolution_onchain(result) ← NUEVO
            ├── build payload dict
            ├── proof_hash = "0x" + sha3_256(json(payload))
            ├── DOFChainAdapter("avalanche", dry_run=not DOF_PRIVATE_KEY)
            ├── adapter.publish_attestation(proof_hash, agent_id=0, metadata)
            └── append to logs/evolve/evolution_attestations.jsonl
```

## Proof hash de ejemplo

Para el run `test1234` con `improvement_pct=0.17`:

```
0xcc4c0ab5c0ac9044...a44105b034
```
(sha3_256 truncado para documentación — 66 chars completo en producción)

Formato: `0x` + 64 chars hex = 66 chars total. Compatible con bytes32 en Solidity.

## Resultados de tests

```
Ran 34 tests in 0.006s
OK
```

- 5 tests nuevos (test_evolve_attestation): todos PASS
- 29 tests existentes (test_evolve_engine): todos PASS — CERO regresiones

## Modo dry_run vs LIVE

| Condición | Comportamiento |
|---|---|
| `DOF_PRIVATE_KEY` no configurada | `dry_run=True` → no hay tx real, loguea igualmente |
| `DOF_PRIVATE_KEY` configurada | `dry_run=False` → tx real en Avalanche C-Chain |
| Error de chain (red, contrato) | Non-fatal → `{"status": "error", "proof_hash": "0x..."}` |

## Líneas modificadas en `core/evolve_engine.py`

- Línea ~665: `if adopted: self._attest_evolution_onchain(result)` (llamada en `run()`)
- Líneas ~672-720: Método completo `_attest_evolution_onchain` agregado a `EvolveController`
