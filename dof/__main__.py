"""DOF — Deterministic Observability Framework
Usage: python -m dof [command]

Commands:
  verify       Run Constitution + AST + DataOracle on text
  verify-code  AST verification on code
  check-facts  DataOracle fact-checking
  prove        Run Z3 formal verification
  benchmark    Run adversarial benchmark
  privacy      Run privacy benchmark
  health       Show component status
  version      Show version

Add --json for machine-readable JSON output.
"""
from dof.cli import main

if __name__ == "__main__":
    main()
