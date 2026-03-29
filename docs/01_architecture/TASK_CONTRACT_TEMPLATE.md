# Task Contract Template

A task contract defines formal pre/post-conditions for crew execution.
Each section is parsed by `core/task_contract.py` and enforced automatically.

---

## PRECONDITIONS

Requirements that MUST be true before execution starts.
Each item is checked against the `context` dict passed to the contract.

- topic_provided: True
- providers_available: True

## DELIVERABLES

Artifacts that MUST exist after successful execution.
Supported checks: output content, file existence, directory existence.

- output: research result in markdown format
- file: output/research_result.md

## QUALITY_GATES

Automated quality checks run against the output.
Each gate has a key and expected value/threshold.

Supported gates:
- `governance_compliant: True` — runs ConstitutionEnforcer, requires GCR=1.0
- `ast_clean: True` — runs ASTVerifier on embedded code blocks
- `supervisor_score>=N` — checks supervisor score meets threshold (e.g., >=7.0)
- `tests_pass: <module>` — runs `python3 -m unittest <module>`, requires exit 0
- `adversarial_pass: True` — runs adversarial evaluation, requires PASS verdict

- governance_compliant: True
- supervisor_score>=7.0

## POSTCONDITIONS

State that MUST be true after execution completes.
Used to verify logging, file persistence, and side effects.

- output logged to JSONL: logs/execution_log.jsonl

## FORBIDDEN_ACTIONS

Actions that MUST NOT occur during or after execution.
Scanned in output text and execution logs.

- no expose API keys in raw output
- no unauthorized web requests
