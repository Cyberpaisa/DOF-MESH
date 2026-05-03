# Testing Hardening Audit Report

## Executive summary

This report documents the testing and CI hardening sequence completed across PRs #1 through #14.

The objective was to stabilize the canonical test baseline, remove pytest collection noise, align GitHub Actions with the documented testing strategy, preserve specialized formal-verification workflows, and improve mutation-testing governance.

At the end of this sequence, the repository has a clean pytest baseline, aligned CI workflows, documented testing policy, checkpoint tags, and a traceable audit trail.

## Scope

This audit covers:

- Canonical test runner stabilization
- Safe test runner stabilization
- Pytest marker taxonomy
- Pytest collection cleanup
- External warning filtering
- GitHub Actions test workflow alignment
- Main CI workflow alignment
- Z3 formal verification workflow alignment
- Mutation testing workflow hardening
- Documentation updates
- Checkpoint tagging

This audit does not claim to validate every optional, external, scientific, on-chain, or stress test in the full repository. Those suites remain intentionally separated from the deterministic safe path.

## Final repository state

Final branch state:

- Branch: main
- Remote: dof-mesh/main
- Working tree: clean
- Latest integrated PR: docs: update testing strategy after ci hardening (#14)

Final validated baseline:

- npm run test -> 293 passed, 11 subtests passed
- npm run test:safe -> 293 passed, 11 subtests passed
- npm run test:collect -> 4802 tests collected
- Z3 pytest subset -> 156 passed
- Mutation verifier -> 16/16 killed, 100.0% mutation score

The canonical pytest baseline is clean and does not emit visible warnings.

## PR sequence summary

### PR #1 through PR #6: test hardening foundation

These PRs established the first stable testing baseline.

Key outcomes:

- Optional and integration-style top-level tests were marked appropriately.
- The canonical safe suite was stabilized.
- Flaky tests were corrected or isolated.
- test:safe was narrowed to a defendable deterministic suite.
- A stable checkpoint was created.

Checkpoint:

- checkpoint/pr-1-to-6-test-hardening

### PR #7: testing strategy documentation

This PR introduced the first formal testing strategy document.

Key outcomes:

- Added docs/testing.md.
- Documented canonical test commands.
- Documented safe runner behavior.
- Documented marker taxonomy.
- Established policy for canonical, safe, integration, scientific, and stress test paths.

### PR #8: Tests workflow alignment

This PR aligned .github/workflows/test.yml with the npm-based canonical runners.

Key outcomes:

- Replaced manual unittest list with npm run test.
- Added npm run test:safe.
- Added Node.js setup for npm runner support.
- Preserved public API import verification.
- Preserved quickstart smoke test.

Checkpoint:

- checkpoint/pr-1-to-8-ci-testing-aligned

### PR #9: pytest collection warning cleanup

This PR silenced pytest collection warnings caused by helper classes named Test*.

Key outcomes:

- Added __test__ = False to helper/runtime classes:
  - TestGenerator
  - TestCase
  - TestResult
  - TestAnalysis
- Removed PytestCollectionWarning noise.
- Preserved runtime behavior and public imports.

Checkpoint:

- checkpoint/pr-1-to-9-clean-test-collection

### PR #10: external websockets warning filtering

This PR removed the last visible warning from the pytest baseline.

Key outcomes:

- Added a precise pytest filterwarnings rule for external websockets.legacy deprecation warnings.
- Confirmed the warning originated from dependency code paths, not direct project runtime code.
- Achieved a clean canonical pytest baseline.

Checkpoint:

- checkpoint/pr-1-to-10-clean-pytest-baseline

### PR #11: main CI workflow alignment

This PR aligned .github/workflows/ci.yml with the documented canonical testing strategy.

Key outcomes:

- Replaced manual python -m unittest list with:
  - npm run test
  - npm run test:safe
- Added Node.js setup.
- Added pytest to minimal CI dependencies.
- Preserved Z3 theorem verification.
- Preserved API import checks.
- Preserved regression checks.
- Preserved quickstart smoke test.
- Preserved prompt evaluation gate.
- Preserved security audit.
- Preserved lint job.

Checkpoint:

- checkpoint/pr-1-to-11-ci-fully-aligned

### PR #12: Z3 workflow pytest alignment

This PR aligned the Z3 unit test step with pytest while preserving the specialized formal verification workflow.

Key outcomes:

- Updated .github/workflows/z3-verify.yml.
- Added pytest to the Z3 workflow dependencies.
- Replaced Z3 unit test unittest runner with pytest.
- Preserved:
  - python -m dof verify-states
  - python -m dof verify-hierarchy
  - theorem verification through dof.verify()
  - regression baseline/check

Validated Z3 subset:

- 156 passed

Checkpoint:

- checkpoint/pr-1-to-12-ci-z3-aligned

### PR #13: mutation workflow hardening

This PR hardened mutation-testing workflow governance without changing mutation verifier behavior.

Key outcomes:

- Updated .github/workflows/mutation-testing.yml.
- Added pull_request trigger for critical mutation-tested paths.
- Added explicit read-only permissions:
  - contents: read
- Preserved:
  - workflow_dispatch
  - push trigger on main
  - Python 3.12
  - python scripts/mutation_verifier.py

Validated mutation verifier:

- Total Mutants: 16
- Killed: 16
- Survived: 0
- Mutation Score: 100.0%

Checkpoint:

- checkpoint/pr-1-to-13-mutation-workflow-hardened

### PR #14: final testing strategy documentation update

This PR updated the testing strategy documentation to reflect the final CI-hardened state.

Key outcomes:

- Updated docs/testing.md.
- Removed outdated warning-based baseline references.
- Documented clean canonical baseline.
- Documented Z3 pytest subset.
- Documented mutation verifier.
- Documented workflow responsibilities.
- Documented checkpoint history through PR #13.

Checkpoint:

- checkpoint/pr-1-to-14-testing-docs-finalized

## Current workflow map

### .github/workflows/test.yml

Purpose:

Primary tests workflow.

Expected behavior:

- Runs npm run test
- Runs npm run test:safe
- Verifies public API imports
- Runs quickstart smoke test

### .github/workflows/ci.yml

Purpose:

Main CI validation workflow.

Expected behavior:

- Runs npm run test
- Runs npm run test:safe
- Runs Z3 theorem verification
- Verifies public API imports
- Runs regression checks
- Runs quickstart smoke test
- Runs prompt evaluation gate
- Runs security audit
- Runs lint job

### .github/workflows/z3-verify.yml

Purpose:

Specialized formal verification workflow.

Expected behavior:

- Runs Z3 state transition verification
- Runs Z3 hierarchy verification
- Runs Z3 theorem verification
- Runs Z3 unit tests with pytest
- Runs regression checks

### .github/workflows/mutation-testing.yml

Purpose:

Sovereign mutation testing workflow for critical governance/adversarial files.

Expected behavior:

- Runs on push to main for critical paths
- Runs on pull_request for critical paths
- Supports manual workflow_dispatch
- Uses read-only repository permissions
- Runs python scripts/mutation_verifier.py

## Testing policy

Use this operating policy:

- Use npm run test before opening a normal PR.
- Use npm run test:safe when validating the deterministic safe path.
- Use npm run test:collect after changing pytest config, warning filters, imports, markers, package discovery, or test discovery.
- Use the Z3 pytest subset when changing Z3 models, gates, hierarchy, transitions, or formal verification tests.
- Use python scripts/mutation_verifier.py when changing:
  - core/adversarial.py
  - core/governance.py
  - core/z3_gate.py
  - .github/workflows/mutation-testing.yml
  - scripts/mutation_verifier.py
- Use npm run test:integration, npm run test:scientific, and npm run test:stress only when working on those specialized domains.

## Risk assessment

### Resolved risks

The following risks were addressed:

- Unstable safe runner scope
- Over-broad marker exclusion
- Manual duplicated test lists in CI
- Pytest collection warnings from helper classes
- External dependency deprecation warning noise
- CI/test workflow drift
- Z3 workflow unit-test runner inconsistency
- Mutation workflow lacking PR validation
- Missing explicit workflow permissions in mutation testing
- Outdated testing documentation

### Remaining known risks

The following risks remain intentionally outside this hardening sequence:

- Full marker coverage across every top-level test remains incomplete.
- Optional, integration, scientific, on-chain, external, and stress suites are not part of the canonical safe baseline.
- The mutation verifier still runs slowly by design because it executes repeated mutation checks.
- The mutation verifier can report partial mode when the broad internal baseline cannot run completely under local conditions.
- Some legacy or experimental tests may still require separate classification work.

These risks are documented and do not block the current canonical baseline.

## Auditor conclusion

The PR #1 through PR #14 sequence materially improved the test posture of DOF-MESH.

The repository now has:

- A clean canonical pytest baseline.
- A deterministic safe runner.
- Clean pytest collection.
- CI workflows aligned with local developer commands.
- A preserved formal verification workflow.
- Hardened mutation-testing workflow triggers.
- Explicit checkpoint tags.
- Updated documentation reflecting the actual validated state.

The current state is suitable as a stable engineering checkpoint for continued development, review, hackathon judging, contributor onboarding, and future security/testing audits.
