# Research Task Contract

Formal contract for the research crew task.
Enforced by `core/task_contract.py` at crew execution boundaries.

---

## PRECONDITIONS

- topic_provided: True
- providers_available: True

## DELIVERABLES

- output: research analysis in markdown format in output/ folder

## QUALITY_GATES

- governance_compliant: True
- supervisor_score>=7.0

## POSTCONDITIONS

- output logged to JSONL: logs/execution_log.jsonl

## FORBIDDEN_ACTIONS

- no expose API keys in raw output
- no unauthorized web requests
