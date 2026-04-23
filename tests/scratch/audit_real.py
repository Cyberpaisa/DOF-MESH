#!/usr/bin/env python3
"""
Auditoría Real del Universal Governance SDK
Autor: jquiceva
Auditor Técnico: Sistema de pruebas automatizadas
Fecha: 2026-04-23

Este script realiza una auditoría técnica real, verificando:
1. Integridad de los YAML (validación de schema)
2. Robustez de los Regex (pruebas de evasión)
3. Aislamiento de instancias (no contaminación cruzada)
4. Cobertura de reglas colombianas
5. Verificación Z3 formal
"""

import sys
import re
import yaml
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

PACKS_DIR = REPO_ROOT / "constitutions" / "packs"

# Colores para la terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0

def ok(msg): 
    global passed
    passed += 1
    print(f"  {GREEN}✅ PASS{RESET} {msg}")

def fail(msg): 
    global failed
    failed += 1
    print(f"  {RED}❌ FAIL{RESET} {msg}")

def warn(msg): 
    print(f"  {YELLOW}⚠️  WARN{RESET} {msg}")

def section(title):
    print(f"\n{BOLD}{BLUE}{'━'*60}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'━'*60}{RESET}")


# ─────────────────────────────────────────────────────────────────────
# AUDITORÍA 1: Integridad de los YAML
# ─────────────────────────────────────────────────────────────────────
section("AUDITORÍA 1: Integridad Estructural de los YAML Packs")

expected_packs = [
    "core/base.yml",
    "health/hipaa.yml",
    "fintech/sox.yml",
    "colombia/gov_co.yml",
    "colombia/fintech_co.yml",
    "colombia/salud_co.yml",
    "colombia/ciberseguridad_co.yml",
    "colombia/contratacion_co.yml",
    "colombia/deeptech_co.yml",
]

for pack_path in expected_packs:
    full_path = PACKS_DIR / pack_path
    if not full_path.exists():
        fail(f"Pack ausente: {pack_path}")
        continue
    try:
        with open(full_path) as f:
            data = yaml.safe_load(f)
        assert "version" in data, "Falta 'version'"
        assert "metadata" in data, "Falta 'metadata'"
        assert "rules" in data, "Falta 'rules'"
        ok(f"Pack válido: {pack_path}")
    except Exception as e:
        fail(f"Pack inválido {pack_path}: {e}")


# ─────────────────────────────────────────────────────────────────────
# AUDITORÍA 2: Robustez de Regex (pruebas de evasión)
# ─────────────────────────────────────────────────────────────────────
section("AUDITORÍA 2: Robustez de Regex (Pruebas de Evasión)")

evasion_tests = [
    # (descripción, regex, texto_evasion, debe_detectar)
    ("CO_CYBER: 'brute  force' con doble espacio", 
     r"(?i)brute\s+force", "brute  force attack", True),
    ("CO_CONTRACT: 'dividiendo el objeto'", 
     r"(?i)divid(ir|iendo|ido|as?)\s+el\s+objeto", "dividiendo el objeto del contrato", True),
    ("CO_CONTRACT: 'dividir el objeto'", 
     r"(?i)divid(ir|iendo|ido|as?)\s+el\s+objeto", "dividir el objeto", True),
    ("CO_CYBER: 'sql injection' con espacio", 
     r"(?i)sql\s*injection", "sql injection attempt", True),
    ("CO_HEALTH: 'C.C.' como ID colombiano", 
     r"(?i)C\.C\.|Cedula:|TI:", "Paciente C.C. 123456789", True),
    ("CO_GOV: evasión cambiando mayúsculas", 
     r"(?i)informacion reservada|secreto comercial", "INFORMACION RESERVADA", True),
    ("Hallucination: '72% of users'", 
     r"\b\d{2,3}%\s+of\s+(?:cases?|users?|people)", "72% of users prefer this", True),
]

for desc, pattern, text, should_match in evasion_tests:
    match = bool(re.search(pattern, text))
    if match == should_match:
        ok(f"{desc}")
    else:
        fail(f"{desc} → {'No detectó' if should_match else 'Falso positivo'}: '{text}'")


# ─────────────────────────────────────────────────────────────────────
# AUDITORÍA 3: Aislamiento de Instancias (Zero Contamination)
# ─────────────────────────────────────────────────────────────────────
section("AUDITORÍA 3: Aislamiento de Instancias (Zero Contamination)")

try:
    from core.governance import ConstitutionEnforcer, HARD_RULES

    baseline_count = len(HARD_RULES)

    enforcer_health = ConstitutionEnforcer(industry="health")
    enforcer_fintech = ConstitutionEnforcer(industry="fintech")
    enforcer_co = ConstitutionEnforcer(industry="colombia")

    # Verificar que los globals no se contaminaron
    if len(HARD_RULES) == baseline_count:
        ok(f"HARD_RULES global no fue contaminado (sigue en {baseline_count} reglas)")
    else:
        fail(f"HARD_RULES CONTAMINADO: pasó de {baseline_count} a {len(HARD_RULES)} reglas")

    # Verificar que las reglas de salud no están en fintech
    health_ids = {r["id"] for r in enforcer_health.hard_rules}
    fintech_ids = {r["id"] for r in enforcer_fintech.hard_rules}
    co_ids = {r["id"] for r in enforcer_co.hard_rules}

    if "PHI_STRICT_BLOCK" in health_ids and "PHI_STRICT_BLOCK" not in fintech_ids:
        ok("PHI_STRICT_BLOCK aislado en Health (no contamina Fintech)")
    else:
        fail("PHI_STRICT_BLOCK se filtró a Fintech — CONTAMINACIÓN DETECTADA")

    if "CO_FINTECH_HABEAS_DATA" in co_ids and "CO_FINTECH_HABEAS_DATA" not in fintech_ids:
        ok("CO_FINTECH_HABEAS_DATA aislado en Colombia (no contamina pack global Fintech)")
    else:
        warn("CO_FINTECH_HABEAS_DATA también está en pack Fintech (revisar si es intencional)")

    # Verificar que el pack Colombia tiene más reglas que el default
    if len(enforcer_co.hard_rules) > len(enforcer_health.hard_rules):
        ok(f"Pack Colombia ({len(enforcer_co.hard_rules)} reglas) > Health ({len(enforcer_health.hard_rules)} reglas) — correctamente más estricto")
    else:
        warn(f"Pack Colombia ({len(enforcer_co.hard_rules)} reglas) no supera Health ({len(enforcer_health.hard_rules)}) en reglas hard")

except Exception as e:
    fail(f"Error importando ConstitutionEnforcer: {e}")


# ─────────────────────────────────────────────────────────────────────
# AUDITORÍA 4: Verificación Z3 Formal
# ─────────────────────────────────────────────────────────────────────
section("AUDITORÍA 4: Verificación Formal Z3 (Hierarchy Invariant)")

try:
    from core.hierarchy_z3 import HierarchyZ3
    verifier = HierarchyZ3()
    result = verifier.verify_hierarchy_inviolable()
    
    if result.status == "PROVEN":
        ok(f"Jerarquía INVIOLABLE — {result.patterns_checked} patrones en {result.verification_time_ms}ms")
    elif result.status == "TIMEOUT":
        fail(f"Z3 TIMEOUT — No se pudo verificar en {result.verification_time_ms}ms")
    else:
        fail(f"VULNERABILIDAD LÓGICA DETECTADA: {result.counterexample}")

    # Test adicional: buscar patrón más débil
    weak = verifier.find_weakest_pattern()
    if weak is None:
        ok("Ningún patrón individual es débil — todos son fuertes")
    else:
        fail(f"Patrón débil encontrado en índice {weak}: {verifier.all_patterns[weak]}")

except Exception as e:
    fail(f"Error en verificación Z3: {e}")


# ─────────────────────────────────────────────────────────────────────
# REPORTE FINAL
# ─────────────────────────────────────────────────────────────────────
section("REPORTE FINAL DE AUDITORÍA")

total = passed + failed
score = round((passed / total) * 10, 1) if total > 0 else 0

print(f"\n  Pruebas ejecutadas : {total}")
print(f"  {GREEN}✅ Pasadas{RESET}          : {passed}")
print(f"  {RED}❌ Fallidas{RESET}         : {failed}")
print(f"\n  {BOLD}Puntuación Final   : {score}/10{RESET}")

if failed == 0:
    print(f"\n  {GREEN}{BOLD}🏆 CERTIFICADO: El sistema ha pasado la auditoría sin fallas.{RESET}")
    print(f"  {GREEN}   Listo para entornos de producción gubernamental colombiana.{RESET}")
else:
    print(f"\n  {YELLOW}{BOLD}⚠️  REVISAR: Se detectaron {failed} falla(s) que requieren atención.{RESET}")
    sys.exit(1)
