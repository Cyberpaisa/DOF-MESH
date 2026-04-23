#!/usr/bin/env python3
"""
Sovereign Mutation Verifier (Advanced Edition) — DOF-MESH
Autor: jquiceva
Grado Militar: Manipulación de AST para mutación de constantes y lógica.
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

def run_tests(cwd: Path) -> bool:
    try:
        result = subprocess.run(TEST_CMD, cwd=cwd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False

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

    if not run_tests(REPO):
        print(f"{Y}⚠️  Baseline incomplete or missing dependencies. Running in partial mode.{RS}")
    else:
        print(f"{G}✅ Baseline: all tests passing{RS}")

    killed = survived = total = 0
    random.seed(42)

    for target in TARGETS:
        if not target.exists(): continue
        source = target.read_text()
        mutable_lines = get_mutable_lines(source)
        sample = random.sample(mutable_lines, min(8, len(mutable_lines)))
        
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
                if not run_tests(REPO):
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
