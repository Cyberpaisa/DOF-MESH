import sys
import os
from pathlib import Path

# Agregar el root del proyecto al path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(REPO_ROOT))

from core.hierarchy_z3 import HierarchyZ3

def run_formal_verification():
    print("🧠 Iniciando Verificación Formal Z3 (Hierarchy Invariant)")
    print("────────────────────────────────────────────────────────")
    
    verifier = HierarchyZ3()
    result = verifier.verify_hierarchy_inviolable()
    
    print(f"Estado de Verificación: {result.status}")
    print(f"Patrones Verificados: {result.patterns_checked}")
    print(f"Tiempo de Ejecución: {result.verification_time_ms} ms")
    
    if result.status == "PROVEN":
        print("\n✅ CERTIFICACIÓN MATEMÁTICA: La jerarquía de seguridad es INVIOLABLE.")
        print("No se encontró ningún contraejemplo lógico que permita saltarse las reglas.")
    else:
        print("\n❌ ALERTA: Se detectó una posible vulnerabilidad lógica.")
        if result.counterexample:
            print(f"Contraejemplo: {result.counterexample}")
        sys.exit(1)

if __name__ == "__main__":
    run_formal_verification()
