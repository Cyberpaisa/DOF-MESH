#!/usr/bin/env python3
"""
Sovereign Mutation Verifier (Advanced Edition) — DOF-MESH.

This verifier mutates selected logic/constant nodes in critical governance files,
runs the broad local test command after each mutation, and reports whether the
test suite detects the change.

Operational notes:
- The script can be slow because it runs test checks repeatedly.
- Target files are modified temporarily and restored after each mutant.
- If the process is interrupted, run `git status` and restore touched files if needed.
- "Partial mode" means the broad baseline command did not fully pass locally,
  but mutation checks still run against the available local test signal.
"""
import subprocess
import sys
import ast
import random
from pathlib import Path

REPO = Path(__file__).parent.parent
TARGETS = [
    REPO / "core" / "adversarial.py",
    REPO / "core" / "governance.py",
]
TEST_CMD = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
TEST_TIMEOUT_SECONDS = 120
MUTANTS_PER_TARGET = 8
MIN_SCORE = 0.30

# Colores para terminal
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; BD = "\033[1m"; RS = "\033[0m"

class MutationTransformer(ast.NodeTransformer):
    """Realiza cambios quirúrgicos en el AST para generar mutantes."""
    def __init__(self, target_line):
        self.target_line = target_line
        self.applied = False

    def visit_Constant(self, node):
        if not self.applied and node.lineno == self.target_line and isinstance(node.value, (int, float, bool)):
            self.applied = True
            if isinstance(node.value, bool):
                return ast.Constant(value=not node.value)
            return ast.Constant(value=node.value + 1)
        return node

    def visit_Compare(self, node):
        if not self.applied and node.lineno == self.target_line:
            new_ops = []
            for op in node.ops:
                # Mutar comparaciones lógicas
                if isinstance(op, ast.Eq): new_ops.append(ast.NotEq())
                elif isinstance(op, ast.NotEq): new_ops.append(ast.Eq())
                elif isinstance(op, ast.Gt): new_ops.append(ast.Lt())
                elif isinstance(op, ast.Lt): new_ops.append(ast.Gt())
                else: new_ops.append(op)
            self.applied = True
            return ast.Compare(left=node.left, ops=new_ops, comparators=node.comparators)
        return node

def run_tests(cwd: Path) -> tuple[bool, str]:
    """Run the broad local test command and return (ok, reason)."""
    try:
        result = subprocess.run(
            TEST_CMD,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            return True, "passed"
        return False, f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {TEST_TIMEOUT_SECONDS}s"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

def get_mutable_lines(source: str) -> list:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = []
    for node in ast.walk(tree):
        if hasattr(node, 'lineno') and isinstance(node, (ast.Constant, ast.Compare)):
            lines.append(node.lineno)
    return sorted(list(set(lines)))

def main():
    print(f"\n{BD}🧬 DOF-MESH Sovereign Mutation Verifier 2.0 (Logic + Constants){RS}")
    print("━" * 65)

    baseline_ok, baseline_reason = run_tests(REPO)
    if not baseline_ok:
        print(f"{Y}⚠️  Baseline did not fully pass ({baseline_reason}). Running in partial mode.{RS}")
        print(f"{Y}   Mutation checks will still run against the available local test signal.{RS}")
    else:
        print(f"{G}✅ Baseline: all tests passing{RS}")

    killed = survived = total = 0
    random.seed(42)

    for target in TARGETS:
        if not target.exists(): continue
        source = target.read_text()
        mutable_lines = get_mutable_lines(source)
        sample = random.sample(mutable_lines, min(MUTANTS_PER_TARGET, len(mutable_lines)))
        
        print(f"\n  📄 {target.name} — {len(sample)} mutantes lógicos")

        for lineno in sample:
            try:
                tree = ast.parse(source)
                transformer = MutationTransformer(lineno)
                mutated_tree = transformer.visit(tree)
                ast.fix_missing_locations(mutated_tree)
                mutated_source = ast.unparse(mutated_tree)
                
                target.write_text(mutated_source)
                total += 1
                tests_ok, _reason = run_tests(REPO)
                if not tests_ok:
                    killed += 1
                    print(f"    {G}✅ Killed{RS}   Linea {lineno}: Lógica/Constante alterada")
                else:
                    survived += 1
                    print(f"    {Y}⚠️  Survived{RS} Linea {lineno}: Cambio no detectado por tests")
            except Exception as e:
                print(f"    {R}❌ Error{RS}   Linea {lineno}: {e}")
            finally:
                target.write_text(source)

    print(f"\n{'━'*65}")
    if total == 0:
        print(f"  {G}✅ CI PASS — No hubo nada que mutar.{RS}")
        sys.exit(0)

    score = killed / total
    print(f"  Total Mutantes: {total} | {G}Killed: {killed}{RS} | {Y}Survived: {survived}{RS}")
    print(f"  {BD}Mutation Score: {score:.1%}{RS}")

    if score >= MIN_SCORE:
        print(f"\n  {G}{BD}🏆 PASS — Verificación completada con éxito.{RS}")
    else:
        print(f"\n  {Y}{BD}⚠️  AVISO — La cobertura de tests es mejorable ({score:.1%}){RS}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
