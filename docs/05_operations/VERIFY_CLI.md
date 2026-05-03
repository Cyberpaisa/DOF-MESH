# DOF Verify CLI

## Purpose

This document records the validated command-line verification path for DOF-MESH.

The verify CLI is used to run deterministic checks over state transitions, hierarchy constraints, and text-level governance evaluation.

## Validated commands

### State transition verification

Command:

    python3 -m dof verify-states

Expected result:

    DOF State Transition Verification — 8/8 PROVEN

### Hierarchy verification

Command:

    python3 -m dof verify-hierarchy

Expected result:

    DOF Hierarchy Verification — PROVEN
    Patterns checked: 62

### Text verification

Command:

    python3 -m dof verify "agent requests permission to publish after threat_detected"

Expected result:

    Status: PASS
    Score:  1.0
    No violations found.

## Usage note

`python3 -m dof verify` requires a text argument.

Running it without text shows the standard CLI usage error:

    usage: dof verify [-h] text
    dof verify: error: the following arguments are required: text

This is expected behavior and is not a verification failure.

## Operational expectations

The verify CLI should:

- print deterministic verification results;
- avoid writing runtime artifacts during normal verification;
- leave the Git working tree clean;
- provide clear PASS/PROVEN output for successful checks.

## Current validated baseline

Validated locally:

- `python3 -m dof verify-states` -> `8/8 PROVEN`
- `python3 -m dof verify-hierarchy` -> `PROVEN`, `62 patterns`
- `python3 -m dof verify "<text>"` -> `Status: PASS`
- `git status` -> clean

