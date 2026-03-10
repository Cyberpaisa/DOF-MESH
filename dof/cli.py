"""
DOF CLI — Command-line interface for the Deterministic Observability Framework.

Usage:
    python -m dof verify "text to check"
    python -m dof verify-code "print('hello')"
    python -m dof check-facts "Bitcoin was created in 2009"
    python -m dof prove
    python -m dof benchmark
    python -m dof benchmark --category governance
    python -m dof privacy
    python -m dof health
    python -m dof version

Add --json for machine-readable JSON output.
"""

import argparse
import json
import sys
import time


def _print_or_json(data: dict, as_json: bool) -> None:
    """Print data as JSON or formatted text."""
    if as_json:
        print(json.dumps(data, indent=2, default=str))
        return
    # Formatted text output handled by each command
    raise NotImplementedError("Call format-specific printer")


def cmd_verify(args):
    """Run Constitution + AST + DataOracle on text."""
    from dof.quick import verify

    text = args.text
    if text == "-":
        text = sys.stdin.read()

    result = verify(text)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    status_icon = {"pass": "PASS", "warn": "WARN", "blocked": "BLOCKED"}
    print(f"Status: {status_icon.get(result['status'], result['status'])}")
    print(f"Score:  {result['score']}")
    print(f"Latency: {result['latency_ms']:.1f}ms")
    if result["violations"]:
        print(f"\nViolations ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"  - {v}")
    else:
        print("\nNo violations found.")

    layers = result["layers"]
    print(f"\nLayers:")
    print(f"  Constitution: {'PASS' if layers['constitution']['passed'] else 'FAIL'} (score={layers['constitution']['score']})")
    print(f"  AST: {'PASS' if layers['ast']['passed'] else 'FAIL'} ({layers['ast']['code_blocks_found']} code blocks)")
    print(f"  Oracle: {layers['oracle']['overall_status']} (verified={layers['oracle']['verified_count']}, discrepancies={layers['oracle']['discrepancy_count']})")


def cmd_verify_code(args):
    """Run AST verification on code."""
    from dof.quick import verify_code

    code = args.code
    if code == "-":
        code = sys.stdin.read()

    result = verify_code(code)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"Passed: {result['passed']}")
    print(f"Score:  {result['score']}")
    print(f"Latency: {result['latency_ms']:.1f}ms")
    if result["violations"]:
        print(f"\nViolations ({len(result['violations'])}):")
        for v in result["violations"]:
            msg = v.get("message", str(v)) if isinstance(v, dict) else str(v)
            print(f"  - {msg}")
    if result["blocked_patterns"]:
        print(f"\nBlocked patterns: {', '.join(result['blocked_patterns'])}")


def cmd_check_facts(args):
    """Run DataOracle fact-checking."""
    from dof.quick import check_facts

    text = args.text
    if text == "-":
        text = sys.stdin.read()

    result = check_facts(text)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"Status: {result['overall_status']}")
    print(f"Claims checked: {result['claims_checked']}")
    print(f"Verified: {result['verified']}")
    print(f"Discrepancies: {result['discrepancies']}")
    print(f"Contradictions: {result['contradictions']}")
    print(f"Oracle score: {result['oracle_score']}")
    print(f"Latency: {result['latency_ms']:.1f}ms")
    if result["flags"]:
        print(f"\nFlags ({len(result['flags'])}):")
        for f in result["flags"]:
            if "claim" in f:
                print(f"  - {f['claim']}: expected={f['expected']}, got={f['extracted']}")
            elif "entity" in f:
                print(f"  - Contradiction in '{f['entity']}': {f['value_1']} vs {f['value_2']}")


def cmd_prove(args):
    """Run Z3 formal verification."""
    from dof.quick import prove

    result = prove()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"All verified: {result['verified']}")
    print(f"Total time: {result['total_ms']:.1f}ms")
    print()
    for t in result["theorems"]:
        status = "VERIFIED" if t["result"] == "VERIFIED" else "FAILED"
        print(f"  {status}  {t['name']}  ({t['time_ms']:.2f}ms)")


def cmd_benchmark(args):
    """Run adversarial benchmark."""
    from dof.quick import benchmark

    category = args.category or "all"
    result = benchmark(category=category)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"{'Category':<20} {'FDR':>8} {'FPR':>8} {'F1':>8} {'Tests':>6}")
    print("-" * 54)
    for cat in result["categories"]:
        print(f"{cat['name']:<20} {cat['fdr']:>7.1%} {cat['fpr']:>7.1%} {cat['f1']:>7.1%} {cat['tests']:>6}")
    print("-" * 54)
    print(f"{'Overall F1':<20} {'':>8} {'':>8} {result['overall_f1']:>7.1%}")
    print(f"\nCompleted in {result['total_ms']:.0f}ms")


def cmd_privacy(args):
    """Run privacy benchmark."""
    from dof.quick import privacy_benchmark

    result = privacy_benchmark()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"{'Category':<20} {'DR':>8} {'FPR':>8} {'F1':>8}")
    print("-" * 48)
    for cat in result["categories"]:
        print(f"{cat['name']:<20} {cat['dr']:>7.1%} {cat['fpr']:>7.1%} {cat['f1']:>7.1%}")
    print("-" * 48)
    print(f"{'Overall':<20} {result['overall_dr']:>7.1%} {result['overall_fpr']:>7.1%} {result['overall_f1']:>7.1%}")
    print(f"\nCompleted in {result['total_ms']:.0f}ms")


def cmd_health(args):
    """Show component health status."""
    from dof.quick import health

    result = health()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"DOF — Deterministic Observability Framework v{result['version']}")
    print(f"Components: {result['available']}/{result['total']} available")
    print()
    for name, available in result["components"].items():
        icon = "OK" if available else "MISSING"
        print(f"  {icon:>7}  {name}")


def cmd_verify_states(args):
    """Run Z3 state transition verification."""
    from core.transitions import TransitionVerifier

    verifier = TransitionVerifier()

    if args.invariant:
        results = {args.invariant: verifier.verify_invariant(args.invariant)}
    else:
        results = verifier.verify_all()

    if args.json:
        out = {k: {"status": v.status, "time_ms": v.verification_time_ms,
                    "counterexample": v.counterexample}
               for k, v in results.items()}
        print(json.dumps(out, indent=2, default=str))
        if any(v.status != "PROVEN" for v in results.values()):
            sys.exit(1)
        return

    total = len(results)
    proven = sum(1 for v in results.values() if v.status == "PROVEN")
    total_ms = sum(v.verification_time_ms for v in results.values())

    print(f"DOF State Transition Verification — {proven}/{total} PROVEN")
    print(f"{'ID':<8} {'Status':<10} {'Time':>8}  Description")
    print("-" * 65)
    for inv_id, r in results.items():
        icon = "PROVEN" if r.status == "PROVEN" else r.status
        print(f"{inv_id:<8} {icon:<10} {r.verification_time_ms:>7.1f}ms  {r.description}")
        if args.verbose and r.counterexample:
            print(f"         Counterexample: {r.counterexample}")
    print(f"\nTotal: {total_ms:.1f}ms")

    if proven < total:
        sys.exit(1)


def cmd_verify_hierarchy(args):
    """Run Z3 hierarchy enforcement verification."""
    from core.hierarchy_z3 import HierarchyZ3

    h = HierarchyZ3()
    result = h.verify_hierarchy_inviolable()

    if args.json:
        out = {"status": result.status, "patterns": result.patterns_checked,
               "categories": result.categories_checked,
               "time_ms": result.verification_time_ms,
               "counterexample": result.counterexample}
        print(json.dumps(out, indent=2, default=str))
        if result.status != "PROVEN":
            sys.exit(1)
        return

    print(f"DOF Hierarchy Verification — {result.status}")
    print(f"Patterns checked: {result.patterns_checked} (2 categories)")
    print(f"Time: {result.verification_time_ms:.1f}ms")
    if result.counterexample:
        print(f"Counterexample: {result.counterexample}")

    if result.status != "PROVEN":
        sys.exit(1)


def cmd_regression_baseline(args):
    """Capture current state as regression baseline."""
    from core.regression_tracker import RegressionTracker

    tracker = RegressionTracker()
    baseline = tracker.capture_baseline()

    if args.json:
        print(json.dumps(baseline, indent=2, default=str))
        return

    print(f"Regression baseline captured — {baseline['git_commit']}")
    print(f"  Z3 invariants: {baseline['z3_invariants']['proven_count']}/{baseline['z3_invariants']['total_count']} PROVEN")
    print(f"  Z3 hierarchy:  {baseline['z3_hierarchy']['status']}")
    print(f"  Tests:         {baseline['tests']['passed']} passed, {baseline['tests']['failures']} failed")
    garak = baseline["garak"]
    if garak.get("available"):
        print(f"  Garak:         {garak['overall_detection_rate']}% ({garak['total_payloads']} payloads)")
    else:
        print(f"  Garak:         N/A (no results file)")
    routing = baseline.get("llm_routing", {})
    if routing.get("available"):
        print(f"  LLM Routing:   {routing.get('total_decisions', 0)} decisions")
    else:
        print(f"  LLM Routing:   N/A (llm_config not available)")
    print(f"\n  Saved: {tracker.BASELINE_FILE}")


def cmd_regression_check(args):
    """Compare current state vs saved baseline."""
    from core.regression_tracker import RegressionTracker

    tracker = RegressionTracker()

    try:
        report = tracker.compare()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run 'dof regression-baseline' first.")
        sys.exit(1)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
        if report.has_regressions:
            sys.exit(1)
        return

    print()
    print(report.summary())
    print()

    if report.has_regressions:
        sys.exit(1)


def cmd_regression_history(args):
    """Show last N regression reports."""
    from core.regression_tracker import RegressionTracker

    tracker = RegressionTracker()
    history = tracker.get_history(n=args.count)

    if not history:
        print("No regression reports found.")
        return

    if args.json:
        print(json.dumps(history, indent=2, default=str))
        return

    print(f"Last {len(history)} regression reports:\n")
    for report in history:
        commit = report.get("git_commit", "?")
        base = report.get("baseline_commit", "?")
        regs = report.get("regression_count", 0)
        imps = report.get("improvement_count", 0)
        stable = report.get("stable_count", 0)
        has_reg = report.get("has_regressions", False)
        ts = report.get("timestamp", "?")[:19]

        icon = "FAIL" if has_reg else "PASS"
        print(f"  {icon}  {commit} vs {base}  ({regs}R/{imps}I/{stable}S)  {ts}")


def cmd_version(args):
    """Show version."""
    from dof import __version__
    if args.json:
        print(json.dumps({"version": __version__}))
    else:
        print(f"dof-sdk {__version__}")


def main():
    parser = argparse.ArgumentParser(
        prog="dof",
        description="DOF — Deterministic Observability Framework CLI",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # verify
    p_verify = subparsers.add_parser("verify", help="Run Constitution + AST + DataOracle")
    p_verify.add_argument("text", help="Text to verify (use '-' for stdin)")
    p_verify.set_defaults(func=cmd_verify)

    # verify-code
    p_code = subparsers.add_parser("verify-code", help="AST verification on code")
    p_code.add_argument("code", help="Code to verify (use '-' for stdin)")
    p_code.set_defaults(func=cmd_verify_code)

    # check-facts
    p_facts = subparsers.add_parser("check-facts", help="DataOracle fact-checking")
    p_facts.add_argument("text", help="Text to fact-check (use '-' for stdin)")
    p_facts.set_defaults(func=cmd_check_facts)

    # prove
    p_prove = subparsers.add_parser("prove", help="Run Z3 formal verification")
    p_prove.set_defaults(func=cmd_prove)

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run adversarial benchmark")
    p_bench.add_argument("--category", choices=["governance", "code_safety", "hallucination", "consistency"],
                         help="Run only this category")
    p_bench.set_defaults(func=cmd_benchmark)

    # privacy
    p_priv = subparsers.add_parser("privacy", help="Run privacy benchmark")
    p_priv.set_defaults(func=cmd_privacy)

    # health
    p_health = subparsers.add_parser("health", help="Show component status")
    p_health.set_defaults(func=cmd_health)

    # verify-states
    p_states = subparsers.add_parser("verify-states", help="Z3 state transition verification")
    p_states.add_argument("--invariant", help="Verify only this invariant (e.g. INV-1)")
    p_states.add_argument("--verbose", action="store_true", help="Show counterexamples")
    p_states.set_defaults(func=cmd_verify_states)

    # verify-hierarchy
    p_hier = subparsers.add_parser("verify-hierarchy", help="Z3 hierarchy enforcement verification")
    p_hier.set_defaults(func=cmd_verify_hierarchy)

    # regression-baseline
    p_regbase = subparsers.add_parser("regression-baseline", help="Capture regression baseline")
    p_regbase.set_defaults(func=cmd_regression_baseline)

    # regression-check
    p_regcheck = subparsers.add_parser("regression-check", help="Compare vs baseline (exit 1 if regressions)")
    p_regcheck.set_defaults(func=cmd_regression_check)

    # regression-history
    p_reghist = subparsers.add_parser("regression-history", help="Show regression report history")
    p_reghist.add_argument("--count", type=int, default=10, help="Number of reports to show")
    p_reghist.set_defaults(func=cmd_regression_history)

    # version
    p_ver = subparsers.add_parser("version", help="Show version")
    p_ver.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
