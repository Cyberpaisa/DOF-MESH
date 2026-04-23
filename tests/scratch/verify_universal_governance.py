import sys
import os
from pathlib import Path

# Asegurar que el core sea importable
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.governance import ConstitutionEnforcer

def test_universal_governance():
    print("🚀 Iniciando Verificación de Gobernanza Universal (M4 MAX ELITE)\n")

    # 1. Prueba Core (Reglas Base)
    print("--- Test 1: Pack CORE (Default) ---")
    enforcer = ConstitutionEnforcer()
    text_core = "According to recent studies, 99% of cats can fly."
    result_core = enforcer.enforce(text_core)
    print(f"Resultado Core: {result_core['status']}")
    print(f"Violaciones: {result_core['hard_violations']}")
    print("-" * 30 + "\n")

    # 2. Prueba Health (HIPAA)
    print("--- Test 2: Pack HEALTH (HIPAA) ---")
    enforcer_health = ConstitutionEnforcer(industry="health")
    text_health = "Patient Name: Juan Perez, DOB: 1985-05-12, Diagnosis: Healthy"
    result_health = enforcer_health.enforce(text_health)
    print(f"Resultado Health: {result_health['status']}")
    print(f"Violaciones: {result_health['hard_violations']}")
    print("-" * 30 + "\n")

    # 4. Prueba COLOMBIA (Full Pack)
    print("--- Test 4: Pack COLOMBIA (Sovereign CO) ---")
    enforcer_co = ConstitutionEnforcer(industry="colombia")
    
    # Texto que viola SECOP, Ciberseguridad y Transparencia
    text_co = "Estamos dividiendo el objeto del contrato para adjudicar a dedo. No reportaremos el incidente al ColCERT."
    result_co = enforcer_co.enforce(text_co)
    
    print(f"Resultado Colombia: {result_co['status']}")
    print(f"Violaciones: {result_co['hard_violations']}")
    print("-" * 30 + "\n")

if __name__ == "__main__":
    test_universal_governance()
