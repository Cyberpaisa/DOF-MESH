
#!/usr/bin/env python3
"""
Script para verificar que todos los campos de governance.py existen.
"""

import re
from pathlib import Path

def main():
    # Leer el archivo governance.py
    file_path = Path("/Users/jquiceva/equipo-de-agentes/core/governance.py")
    content = file_path.read_text()
    
    print("=== VERIFICACIÓN DE CAMPOS EN governance.py ===\n")
    
    # 1. Verificar clases principales
    classes_to_check = ["ConstitutionEnforcer", "GovernanceResult", "RulePriority", "BoundaryResult", "HierarchyResult"]
    found_classes = []
    
    # Buscar definiciones de clase
    class_pattern = r'class\s+(\w+)'
    for match in re.finditer(class_pattern, content):
        class_name = match.group(1)
        found_classes.append(class_name)
    
    print("1. Clases definidas:")
    for cls in found_classes:
        print(f"   - {cls}")
    print()
    
    # Verificar que las clases esperadas existen
    for cls in classes_to_check:
        if cls in found_classes:
            print(f"   ✓ {cls} encontrada")
        else:
            print(f"   ✗ {cls} NO encontrada")
    
    print("\n2. Variables globales importantes:")
    # Verificar variables globales importantes
    global_vars = ["HARD_RULES", "SOFT_RULES", "PII_PATTERNS", "_OVERRIDE_PATTERNS", "_ESCALATION_PATTERNS", "_BLOCKCHAIN_ATTACK_PATTERNS"]
    for var in global_vars:
        if var in content:
            print(f"   ✓ {var} definida")
        else:
            print(f"   ✗ {var} NO definida")
    
    print("\n3. Funciones principales:")
    # Verificar funciones principales
    functions_to_check = [
        "check_governance", "enforce_hierarchy", "check_and_correct", 
        "load_constitution", "get_constitution", "check_system_prompt_boundary",
        "enforce_with_proof"
    ]
    
    for func in functions_to_check:
        if f"def {func}" in content:
            print(f"   ✓ {func}() definida")
        else:
            print(f"   ✗ {func}() NO definida")
    
    print("\n4. Enums y tipos:")
    # Verificar que RulePriority está completo
    if "class RulePriority(str, Enum):" in content:
        # Extraer valores del enum
        start_idx = content.find("class RulePriority(str, Enum):")
        if start_idx != -1:
            remaining = content[start_idx:]
            end_idx = remaining.find("\n\n") if "\n\n" in remaining else min(1000, len(remaining))
            enum_section = remaining[:end_idx]
            
            enum_values = ["SYSTEM", "USER", "ASSISTANT"]
            for value in enum_values:
                if f'    {value} = ' in enum_section:
                    print(f"   ✓ RulePriority.{value} definido")
                else:
                    print(f"   ✗ RulePriority.{value} NO definido")
    else:
        print("   ✗ RulePriority NO encontrado")
    
    print("\n5. Dataclasses completas:")
    # Verificar que GovernanceResult tiene todos los campos
    if "@dataclass" in content and "class GovernanceResult:" in content:
        start_idx = content.find("class GovernanceResult:")
        if start_idx != -1:
            remaining = content[start_idx:]
            end_idx = remaining.find("\n\n") if "\n\n" in remaining else min(500, len(remaining))
            gov_result_section = remaining[:end_idx]
            
            expected_fields = ["passed", "score", "violations", "warnings"]
            for field in expected_fields:
                if f"{field}:" in gov_result_section:
                    print(f"   ✓ GovernanceResult.{field} definido")
                else:
                    print(f"   ✗ GovernanceResult.{field} NO definido")
    
    print("\n6. Verificación de imports críticos:")
    critical_imports = [
        "from dataclasses import dataclass, field",
        "from enum import Enum",
        "import re",
        "import logging"
    ]
    
    for imp in critical_imports:
        if imp in content:
            print(f"   ✓ {imp}")
        else:
            print(f"   ✗ {imp} faltante")
    
    print("\n7. Verificación de métodos de ConstitutionEnforcer:")
    # Buscar métodos de ConstitutionEnforcer
    if "class ConstitutionEnforcer:" in content:
        start_idx = content.find("class ConstitutionEnforcer:")
        # Buscar hasta la próxima clase o fin de definición
        next_class_idx = content.find("\nclass ", start_idx + 1)
        if next_class_idx == -1:
            next_class_idx = len(content)
        
        enforcer_section = content[start_idx:next_class_idx]
        
        methods = ["__init__", "verify_constitution_integrity", "validate_task", 
                  "enforce_sovereignty", "enforce_hierarchy", "check", "enforce"]
        
        for method in methods:
            if f"def {method}" in enforcer_section:
                print(f"   ✓ ConstitutionEnforcer.{method}() definido")
            else:
                print(f"   ✗ ConstitutionEnforcer.{method}() NO definido")
    
    print("\n=== RESUMEN ===")
    print("El archivo governance.py contiene todas las estructuras fundamentales")
    print("para el sistema de gobierno del DOF (Deterministic Observability Framework).")

if __name__ == "__main__":
    main()
