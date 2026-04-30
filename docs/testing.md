# Testing Strategy

This repository uses a layered testing strategy to separate the canonical stable suite from broader integration, scientific, stress, on-chain, optional, and experimental tests.

The goal is to keep the default developer and CI-safe test path deterministic, fast, and green while the broader pytest marker taxonomy continues to mature.

## Commands

### npm run test

Runs the canonical stable suite.

Expected baseline:

293 passed, 1 warning, 11 subtests passed

### npm run test:safe

Runs the same canonical safe/core suite as npm run test.

This command intentionally points to the stable canonical suite instead of relying on broad marker exclusion.

Reason: marker coverage is still incomplete across top-level tests. A marker-exclusion strategy was tested, but it still collected too many tests to be considered a true safe runner.

Expected baseline:

293 passed, 1 warning, 11 subtests passed

### npm run test:core

Runs the canonical core suite.

At the current stage, this is equivalent to npm run test and npm run test:safe.

### npm run test:collect

Validates that pytest can collect the full test tree.

Expected baseline:

4797 tests collected

Known non-blocking warnings:

- websockets.legacy deprecation warning
- PytestCollectionWarning for internal classes named Test* that define __init__

### npm run test:integration

Runs tests marked as integration tests.

These tests may rely on broader system behavior, optional services, local files, adapters, or cross-module flows.

### npm run test:scientific

Runs tests marked as scientific or on-chain.

This suite may include research-grade experiments, formal/scientific validation flows, and on-chain related checks.

### npm run test:stress

Runs stress tests.

These tests are not expected to be part of the fast safe runner.

## Marker taxonomy

Known marker categories include:

- integration
- optional
- slow
- scientific
- onchain
- external
- stress
- scratch
- red_team

Marker coverage is still incomplete across top-level tests. Because of that, test:safe does not yet rely on a broad marker exclusion expression.

## Current baseline

The stable checkpoint after PRs #1 through #6 is tagged as:

checkpoint/pr-1-to-6-test-hardening

At that checkpoint:

npm run test         -> 293 passed, 1 warning, 11 subtests passed
npm run test:safe    -> 293 passed, 1 warning, 11 subtests passed
npm run test:collect -> 4797 tests collected

## Policy

Use this rule of thumb:

- Use npm run test before opening a normal PR.
- Use npm run test:safe when validating the deterministic safe path.
- Use npm run test:collect after changing markers, test discovery, pytest configuration, or package-level imports.
- Use specialized suites such as test:integration, test:scientific, and test:stress only when working on those domains.
- Do not expand test:safe back to a broad marker-exclusion runner until marker coverage is complete enough to avoid unrelated I/O, persistence, mesh, memory, network, on-chain, or optional dependency failures.
