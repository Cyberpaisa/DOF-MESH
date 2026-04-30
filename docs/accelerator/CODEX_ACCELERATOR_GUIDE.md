# DOF-MESH — Codex Accelerator Guide

## Purpose

This document defines how Codex should be used for accelerator and preincubation preparation without replacing the repository-level AGENTS.md constitution.

## Working Rules

- Do not scan the full repository unless explicitly requested.
- Do not read `.env`, private keys, wallets, tokens, secrets, private endpoints, or sensitive local paths.
- Do not execute deploys.
- Do not touch contracts on-chain.
- Do not install dependencies without explaining why.
- Do not modify code without first explaining the intended change.
- Work one task at a time.
- Prefer compact, professional, non-sensitive documentation.

## Preferred Context Files

For accelerator-related tasks, use these files first:

1. PROJECT_BRIEF.md
2. docs/accelerator/REPO_CONTEXT_MAP.md
3. docs/accelerator/CANONICAL_SCOPE.md
4. docs/accelerator/FUNCTIONAL_VALIDATION_REPORT.md
5. docs/accelerator/INTEGRATED_SMOKE_TEST_REPORT.md
6. docs/accelerator/DEMO_PAYLOAD_GUIDE.md
7. docs/accelerator/MENTORSHIP_DEMO_CHECKLIST.md

## Accelerator Scope

The accelerator-facing narrative should focus on the defendable core:

- SDK
- CLI
- governance
- Z3 verification
- tool hooks
- basic local API behavior
- auditable evidence

Experimental, historical, gaming, redteam, multichain, and peripheral components should not be presented as fully validated product scope unless explicitly revalidated.
