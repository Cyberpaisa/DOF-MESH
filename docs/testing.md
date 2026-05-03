# Testing Strategy

This repository uses a layered testing strategy to separate the canonical stable suite from broader integration, scientific, stress, on-chain, optional, formal-verification, and mutation-testing workflows.

The current goal is to keep the default developer and CI-safe test path deterministic, fast, clean, and green while preserving specialized workflows for Z3 verification and mutation testing.

## Canonical commands

### npm run test

Runs the canonical stable suite.

Expected baseline:

293 passed, 11 subtests passed

### npm run test:safe

Runs the same canonical safe/core suite as npm run test.

This command intentionally points to the stable canonical suite instead of relying on broad marker exclusion.

Reason: marker coverage is still incomplete across top-level tests. A marker-exclusion strategy was tested, but it still collected too many tests to be considered a true safe runner.

Expected baseline:

293 passed, 11 subtests passed

### npm run test:core

Runs the canonical core suite.

At the current stage, this is equivalent to npm run test and npm run test:safe.

### npm run test:collect

Validates that pytest can collect the full test tree.

Expected baseline:

4802 tests collected

The current collection baseline is clean and should not emit visible warnings.

## Specialized commands

### Z3 pytest subset

Runs the Z3 unit test subset used by the specialized formal verification workflow.

Command:

python3 -m pytest -q tests/test_state_model.py tests/test_transitions.py tests/test_hierarchy_z3.py tests/test_z3_gate.py tests/test_agent_output.py tests/test_boundary.py tests/test_z3_test_generator.py

Expected baseline:

156 passed

### Sovereign mutation verifier

Runs the sovereign mutation verifier against critical governance/adversarial modules.

Command:

python3 scripts/mutation_verifier.py

Expected baseline:

Total Mutants: 16
Killed: 16
Survived: 0
Mutation Score: 100.0%

Note: the mutation verifier may run slowly because it mutates target files temporarily and executes test checks repeatedly. It must leave the working tree clean after completion.

Operational diagnostics:

- `partial mode` means the broad baseline command did not fully pass locally, but mutation checks still run against the available local test signal.
- The verifier reports the baseline reason when possible, such as a non-zero exit code, timeout, or exception.
- Partial mode is not automatically a mutation failure. The relevant mutation result is still the final mutation score and whether mutants were killed or survived.
- If the verifier is interrupted, run `git status` and restore any touched target files before continuing.

Rejected fast-path note:

- A faster canonical pytest signal was tested as an internal mutation verifier runner.
- That fast path reduced mutation detection from `16/16 killed` to `1/16 killed`.
- Mutation score dropped from `100.0%` to `6.2%`.
- Because of that, the mutation verifier intentionally keeps the broader baseline command even though it is slower.
- Do not replace the mutation verifier runner with the canonical fast suite unless equivalent mutation strength is proven.

## Optional npm suites

### npm run test:integration

Runs tests marked as integration tests.

These tests may rely on broader system behavior, optional services, local files, adapters, or cross-module flows.

### npm run test:scientific

Runs tests marked as scientific or on-chain.

This suite may include research-grade experiments, formal/scientific validation flows, and on-chain related checks.

### npm run test:stress

Runs stress tests.

These tests are not expected to be part of the fast safe runner.

## CI workflows

### Tests workflow

File:

.github/workflows/test.yml

Purpose:

Runs the canonical npm-based test runners across the Python matrix.

Expected behavior:

- npm run test
- npm run test:safe
- public API import check
- quickstart smoke test

### Main CI workflow

File:

.github/workflows/ci.yml

Purpose:

Runs the main CI validation path.

Expected behavior:

- npm run test
- npm run test:safe
- Z3 theorem verification
- public API import check
- regression check
- quickstart smoke test
- prompt evaluation gate
- security audit
- lint job

### Z3 Formal Verification workflow

File:

.github/workflows/z3-verify.yml

Purpose:

Runs specialized formal verification checks.

Expected behavior:

- python -m dof verify-states
- python -m dof verify-hierarchy
- theorem verification through dof.verify()
- Z3 unit test subset with pytest
- regression baseline/check

### Mutation Testing workflow

File:

.github/workflows/mutation-testing.yml

Purpose:

Runs sovereign mutation verification for critical governance/adversarial files.

Expected behavior:

- runs on push to main for critical paths
- runs on pull_request for the same critical paths
- supports workflow_dispatch
- uses read-only repository permissions
- runs python scripts/mutation_verifier.py

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

## Current checkpoints

Stable checkpoints created during the test/CI hardening sequence:

- checkpoint/pr-1-to-6-test-hardening
- checkpoint/pr-1-to-8-ci-testing-aligned
- checkpoint/pr-1-to-9-clean-test-collection
- checkpoint/pr-1-to-10-clean-pytest-baseline
- checkpoint/pr-1-to-11-ci-fully-aligned
- checkpoint/pr-1-to-12-ci-z3-aligned
- checkpoint/pr-1-to-13-mutation-workflow-hardened

## Current baseline

After PRs #1 through #13:

npm run test         -> 293 passed, 11 subtests passed
npm run test:safe    -> 293 passed, 11 subtests passed
npm run test:collect -> 4802 tests collected
Z3 pytest subset     -> 156 passed
Mutation verifier    -> 16/16 killed, 100.0% mutation score

## Policy

Use this rule of thumb:

- Use npm run test before opening a normal PR.
- Use npm run test:safe when validating the deterministic safe path.
- Use npm run test:collect after changing markers, test discovery, pytest configuration, package-level imports, or warning filters.
- Use the Z3 pytest subset when changing Z3 state models, transitions, hierarchy, gates, or formal verification tests.
- Use python3 scripts/mutation_verifier.py when changing core/adversarial.py, core/governance.py, core/z3_gate.py, or the mutation testing workflow.
- Use specialized suites such as test:integration, test:scientific, and test:stress only when working on those domains.
- Do not expand test:safe back to a broad marker-exclusion runner until marker coverage is complete enough to avoid unrelated I/O, persistence, mesh, memory, network, on-chain, or optional dependency failures.
