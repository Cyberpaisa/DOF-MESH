# Testing Hardening Final Closure

## Scope

This document closes the testing, CI, mutation-verifier, and documentation-alignment sequence completed across PRs #1 through #25.

The sequence stabilized the canonical test baseline, aligned CI workflows, cleaned pytest collection, documented testing policy, aligned public metrics, clarified mutation-verifier behavior, and recorded why the rejected fast mutation-testing path should not be used.

## Final baseline

- npm run test: 293 passed, 11 subtests passed
- npm run test:safe: 293 passed, 11 subtests passed
- npm run test:collect: 4802 tests collected
- Z3 pytest subset: 156 passed
- Mutation verifier: 16/16 killed, 100.0% mutation score

## Closure map

### PR #1–#13: testing and CI hardening

Outcome:

- Safe/core test runner stabilized
- Pytest markers formalized
- Pytest collection warnings removed
- External dependency warning filtered
- Main CI aligned with npm test runners
- Z3 workflow aligned with pytest
- Mutation testing workflow hardened with PR triggers and read-only permissions

### PR #14–#22: documentation and public metrics alignment

Outcome:

- Testing strategy updated
- Testing hardening audit report added
- README testing baseline aligned
- README chain metrics aligned
- Documentation index corrected
- Documentation system metrics aligned
- Architecture metrics aligned
- Accelerator-facing metrics aligned

### PR #23–#25: mutation verifier operational closure

Outcome:

- Mutation verifier partial mode clarified
- Mutation verifier diagnostics documented
- Rejected fast-path experiment documented
- The canonical fast pytest suite was explicitly rejected as mutation-verifier runner because it reduced detection from 16/16 killed to 1/16 killed and dropped mutation score from 100.0% to 6.2%

## Final engineering decision

The mutation verifier intentionally keeps the broader baseline command even though it is slower.

Reason:

- The broad runner preserves mutation strength.
- The canonical fast pytest suite is suitable for normal PR validation.
- The canonical fast pytest suite is not strong enough as a mutation-testing signal for the current adversarial/governance mutation targets.

## Operational policy

Use:

- npm run test for normal PR validation
- npm run test:safe for deterministic safe-path validation
- npm run test:collect after pytest config, import, marker, package, or discovery changes
- Z3 pytest subset for formal verification changes
- python3 scripts/mutation_verifier.py for governance/adversarial mutation validation

Do not replace the mutation verifier runner with the canonical fast suite unless equivalent mutation strength is proven.

## Final status

The repository is now in a stable testing baseline state suitable for:

- contributor onboarding
- hackathon judging
- technical audit
- CI review
- future security hardening
- product development on top of a clean baseline

