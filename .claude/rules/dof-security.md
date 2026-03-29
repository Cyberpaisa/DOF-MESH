---
description: Security rules for chain interactions, keys, and on-chain operations
paths:
  - "core/chain_adapter.py"
  - "core/z3_verifier.py"
  - "core/z3_gate.py"
  - "dof/**/*"
  - "scripts/**/*"
---

# DOF Security Rules

## Claves y Secrets

NUNCA hardcodees private keys, API keys, ni hashes de 64 chars en archivos.
El pre-commit hook bloquea: `0x` + 64 hex chars (detectado como private key).
Para hashes de attestation en docs: trunca a `0xabcd...ef` (nunca el hash completo).

DOF_PRIVATE_KEY va en `~/.dof/wallet.env` — NUNCA en el repo.
verify: Grep("DOF_PRIVATE_KEY\s*=\s*0x", path=".") → 0 matches

## On-Chain Operations

Toda operación on-chain debe tener dry_run mode.
verify: Grep("dry_run", path="core/chain_adapter.py") → presencia confirmada

agent_id es int (token_id ERC-8004), NUNCA string.
verify: Grep('agent_id="', path="core/") → 0 matches (debe ser agent_id=1687 no agent_id="apex-1687")

## Z3 Safety

Z3 unknown → FAIL, NUNCA PASS. Tratar unknown como FAIL es seguridad por diseño.
verify: Grep("z3.unknown", path="core/z3_verifier.py") → manejo explícito presente

FORBIDDEN_TARGETS no puede ser modificado sin autorización del Soberano.
verify: FORBIDDEN_TARGETS contiene {"hard_rules", "z3_theorems", "constitution", "governance_hard"}

## Antes de publicar attestation on-chain

1. Verificar que no hay private key en el payload
2. Confirmar chain correcta (Avalanche C-Chain = chain_id 43114)
3. Dry-run primero si DOF_PRIVATE_KEY no está en entorno
