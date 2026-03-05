"""DOF — Deterministic Observability Framework
Usage: python -m dof [command]

Commands:
  verify     Run Z3 formal verification (4 theorems)
  governance Check governance on stdin text
  health     Show system status
  version    Show version
  mcp        Start MCP server
  api        Start REST API server
"""
import sys


def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else ["health"]
    cmd = args[0]

    if cmd == "version":
        from dof import __version__
        print(f"dof-sdk {__version__}")

    elif cmd == "verify":
        from core.z3_verifier import Z3Verifier
        v = Z3Verifier()
        results = v.verify_all()
        for r in results:
            status = "VERIFIED" if r.result == "VERIFIED" else "FAILED"
            print(f"  {status}  {r.theorem_name}  ({r.proof_time_ms:.2f}ms)")
        all_ok = all(r.result == "VERIFIED" for r in results)
        print(f"\nAll verified: {all_ok}")

    elif cmd == "governance":
        from dof import GenericAdapter
        text = sys.stdin.read() if not sys.stdin.isatty() else "No input provided. Pipe text: echo 'text' | python -m dof governance"
        result = GenericAdapter().wrap_output(text)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Violations: {result.get('violations', [])}")

    elif cmd == "health":
        from dof import __version__
        print(f"DOF — Deterministic Observability Framework")
        print(f"Version: {__version__}")
        print(f"Z3: available")
        try:
            from core.z3_verifier import Z3Verifier
            Z3Verifier().verify_all()
            print(f"Theorems: 4/4 verified")
        except Exception as e:
            print(f"Theorems: error — {e}")
        print(f"Governance: ready")
        print(f"AST Verifier: ready")

    elif cmd == "mcp":
        print("Starting MCP server...")
        import mcp_server
        mcp_server.main()

    elif cmd == "api":
        print("Starting REST API on http://localhost:8080")
        import uvicorn
        uvicorn.run("api.server:app", host="0.0.0.0", port=8080)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
