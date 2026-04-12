
import re
from pathlib import Path
import sys

# Read the governance.py file
governance_path = Path("core/governance.py")
with open(governance_path, 'r') as f:
    content = f.read()

# Check for required components
required_components = [
    "HARD_RULES",
    "SOFT_RULES", 
    "PII_PATTERNS",
    "_OVERRIDE_PATTERNS",
    "_ESCALATION_PATTERNS",
    "ConstitutionEnforcer",
    "GovernanceResult",
    "RulePriority",
    "HierarchyResult",
    "check_governance",
    "enforce_hierarchy"
]

print("=== VERIFICACIÓN DE CAMPOS DE GOVERNANCE ===\n")

# Check each component
missing_components = []
for component in required_components:
    if component in content:
        print(f"✓ {component} - PRESENTE")
    else:
        print(f"✗ {component} - AUSENTE")
        missing_components.append(component)

# Check for specific rule fields
print("\n=== VERIFICACIÓN DE ESTRUCTURA DE REGLAS ===\n")

# Extract HARD_RULES definition
hard_rules_match = re.search(r'HARD_RULES: list\[dict\] = \[(.*?)\]', content, re.DOTALL)
if hard_rules_match:
    hard_rules_text = hard_rules_match.group(1)
    print(f"HARD_RULES encontradas: {len(re.findall(r'\{', hard_rules_text))} reglas")
    
    # Check each hard rule has required fields
    hard_rule_matches = re.findall(r'\{(.*?)\}', hard_rules_text, re.DOTALL)
    for i, rule_text in enumerate(hard_rule_matches):
        required_fields = ["id", "priority", "description"]
        rule_fields = []
        for field in required_fields:
            if f'"{field}"' in rule_text or f"'{field}'" in rule_text:
                rule_fields.append(field)
        
        if len(rule_fields) == len(required_fields):
            print(f"  ✓ Regla {i+1}: tiene todos los campos requeridos")
        else:
            missing = [f for f in required_fields if f not in rule_fields]
            print(f"  ✗ Regla {i+1}: faltan campos: {missing}")
else:
    print("✗ HARD_RULES no encontradas en el formato esperado")

# Extract SOFT_RULES definition
soft_rules_match = re.search(r'SOFT_RULES: list\[dict\] = \[(.*?)\]', content, re.DOTALL)
if soft_rules_match:
    soft_rules_text = soft_rules_match.group(1)
    print(f"\nSOFT_RULES encontradas: {len(re.findall(r'\{', soft_rules_text))} reglas")
    
    # Check each soft rule has required fields
    soft_rule_matches = re.findall(r'\{(.*?)\}', soft_rules_text, re.DOTALL)
    for i, rule_text in enumerate(soft_rule_matches):
        required_fields = ["id", "priority", "description", "weight", "match_mode"]
        rule_fields = []
        for field in required_fields:
            if f'"{field}"' in rule_text or f"'{field}'" in rule_text:
                rule_fields.append(field)
        
        if len(rule_fields) == len(required_fields):
            print(f"  ✓ Regla {i+1}: tiene todos los campos requeridos")
        else:
            missing = [f for f in required_fields if f not in rule_fields]
            print(f"  ✗ Regla {i+1}: faltan campos: {missing}")
else:
    print("\n✗ SOFT_RULES no encontradas en el formato esperado")

# Extract PII_PATTERNS definition
pii_match = re.search(r'PII_PATTERNS: list\[dict\] = \[(.*?)\]', content, re.DOTALL)
if pii_match:
    pii_text = pii_match.group(1)
    print(f"\nPII_PATTERNS encontrados: {len(re.findall(r'\{', pii_text))} patrones")
    
    # Check each PII pattern has required fields
    pii_matches = re.findall(r'\{(.*?)\}', pii_text, re.DOTALL)
    for i, pattern_text in enumerate(pii_matches):
        required_fields = ["id", "pattern", "description"]
        pattern_fields = []
        for field in required_fields:
            if f'"{field}"' in pattern_text or f"'{field}'" in pattern_text:
                pattern_fields.append(field)
        
        if len(pattern_fields) == len(required_fields):
            print(f"  ✓ Patrón {i+1}: tiene todos los campos requeridos")
        else:
            missing = [f for f in required_fields if f not in pattern_fields]
            print(f"  ✗ Patrón {i+1}: faltan campos: {missing}")
else:
    print("\n✗ PII_PATTERNS no encontrados en el formato esperado")

# Check for function definitions
print("\n=== VERIFICACIÓN DE FUNCIONES ===\n")
functions_to_check = ["check_governance", "enforce_hierarchy"]
for func in functions_to_check:
    if f"def {func}" in content:
        print(f"✓ Función {func}() - DEFINIDA")
    else:
        print(f"✗ Función {func}() - NO DEFINIDA")
        missing_components.append(func)

print("\n=== RESUMEN ===")
if missing_components:
    print(f"Componentes faltantes: {missing_components}")
    print("❌ Se requieren correcciones en el módulo governance")
else:
    print("✅ Todos los campos de governance existen y están correctamente definidos")
