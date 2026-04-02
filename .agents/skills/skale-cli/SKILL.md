---
name: skale-cli
description: Operational command playbooks for SKALE CLI usage from the skalenetwork/skale-cli codebase. Use when users need exact command syntax, target selection, parameter formatting, output interpretation, and error handling for read, whitelist, manager, ima, and skl commands.
---

# SKALE CLI

Use low-freedom, command-first runbooks.

## File Organization

- `rules/`: command validation and targeting constraints.
- `references/`: authoritative command/target/contract matrix.
- `examples/`: concrete command invocation patterns.

## Workflow

1. Read `rules/target-and-validation.md` first.
2. Load `references/command-matrix.md` for exact command and support matrix.
3. Use `examples/common-command-flows.md` for user-facing command templates.
4. If request is ecosystem-level design instead of CLI operation, route to `skale` skill.

## Rules (Must Follow)

- `rules/target-and-validation.md`
- `rules/error-handling.md`

## References (Concepts + Lookup)

- `references/command-matrix.md`

## Examples (Concrete Patterns)

- `examples/common-command-flows.md`
