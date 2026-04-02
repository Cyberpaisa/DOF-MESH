---
title: Target and Validation
impact: HIGH
impactDescription: Wrong flags = failed commands
tags: flags, validation, cli
---

## Target and Validation

**Impact: HIGH** - Wrong flags = failed commands.

**Incorrect:**

```bash
skale read contract method  # Missing --chain
skale ima chain-id          # Missing --network
```

**Correct:**

```bash
skale read contract method --chain europa
skale ima chain-id --network mainnet
```

Rules:
- Require `--chain` for SKALE chain-targeted commands
- Require `--network` for Ethereum network-targeted commands
- Validate contract support against command-matrix
- Validate address format
- Don't suggest flags not in the matrix

Reference: [Command Matrix](references/command-matrix.md)
