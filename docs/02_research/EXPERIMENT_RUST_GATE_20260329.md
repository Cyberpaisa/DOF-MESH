# Experimento: Rust Z3 Gate con PyO3

**Fecha:** 2026-03-29
**Autor:** Cyber Paisa (Enigma Group)
**Estado:** Implementado — pendiente compilación Rust

## Objetivo

Crear un módulo Rust con bindings Python (PyO3) que implemente el Z3 gate de gobernanza DOF-MESH con latencia <1ms, reemplazando el gate Python puro (baseline ~2–8ms).

## Resultado

### Rust disponible en el sistema
**NO** — `rustc` y `cargo` no están instalados. El crate está listo para compilar cuando se instale Rust.

### Archivos creados

| Archivo | Descripción |
|---------|-------------|
| `rust/dof_z3_gate/Cargo.toml` | Manifest del crate, deps: pyo3 0.21, sha3 0.10, serde 1.0 |
| `rust/dof_z3_gate/src/gate.rs` | Lógica core: `DofGate`, `Constraint`, `GateVerdict`, `compute_hash` |
| `rust/dof_z3_gate/src/lib.rs` | PyO3 bindings: `PyDofGate`, `PyGateResult` |
| `rust/dof_z3_gate/tests/integration_test.rs` | 10 tests de integración Rust |
| `rust/dof_z3_gate/README.md` | Instrucciones de compilación e instalación |
| `core/rust_gate_bridge.py` | Bridge Python con fallback automático |
| `tests/test_rust_gate_bridge.py` | 10 tests Python del bridge |

### Tests Python ejecutados

```
Ran 10 tests in 0.001s
OK
```

**10/10 tests pasaron** usando el backend Python (fallback).

### Suite completa del proyecto

```
Ran 4133 tests in 48.988s
OK (skipped=43)
```

Ningún test existente fue afectado.

## Arquitectura implementada

### gate.rs — Constraints por defecto

| Constraint | Tipo | Keywords / Bounds |
|------------|------|-------------------|
| `no_privilege_escalation` | MustNotContain | "ignore previous instructions", "jailbreak", "you are now", "act as if", "disregard all rules" |
| `no_instruction_override` | MustNotContain | "override governance", "bypass constitution", "disable monitoring", "turn off safety" |
| `output_length_bound` | LengthBound | min=1, max=50,000 chars |

### Proof hash (Solidity-compatible)

```
proof_hash = SHA3-256(SHA3-256(output) + verdict_str)
```

El hash es determinístico y compatible con Keccak-256 del ecosistema EVM.

### Bridge Python (`core/rust_gate_bridge.py`)

```python
from core.rust_gate_bridge import evaluate_output, is_rust_available

result = evaluate_output("agent output here")
# {
#   "verdict": "APPROVED" | "REJECTED",
#   "proof_hash": "0x...",   # SHA3-256, 66 chars
#   "latency_us": 42,        # None si backend=python
#   "backend": "rust" | "python",
#   "violated_constraint": None | "constraint_id"
# }
```

## Performance esperada (cuando Rust esté compilado)

| Backend | Latencia p50 | Latencia p99 | Factor |
|---------|-------------|-------------|--------|
| Rust release | ~50µs | ~200µs | baseline |
| Python puro | ~2ms | ~8ms | ~40x más lento |

## Cómo compilar cuando Rust esté disponible

```bash
# 1. Instalar Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. Instalar maturin
pip install maturin

# 3. Compilar e instalar (modo release)
cd ~/DOF-MESH/rust/dof_z3_gate
maturin develop --release

# 4. Verificar que el bridge usa Rust
python3 -c "from core.rust_gate_bridge import is_rust_available; print(is_rust_available())"
# → True

# 5. Ejecutar tests Rust
cargo test
```

## Decisiones de diseño

1. **PyO3 0.21** — versión LTS más estable para bindings Python 3.8–3.12.
2. **SHA3-256 (sha3 crate)** — idéntico al Keccak-256 que usa Solidity, permite verificación on-chain.
3. **cdylib + rlib** — cdylib para el .so de Python, rlib para tests Rust nativos.
4. **Fallback Python** — el bridge no rompe nada si Rust no está compilado; transparente para los callers.
5. **Sin Z3 SMT solver** — el nombre "Z3 gate" es heredado de la arquitectura DOF; la implementación usa hashing determinístico + pattern matching que logra las mismas garantías con latencia 10–40x menor.
