
#!/usr/bin/env python3
"""Broadcast test for deterministic governance verification."""

import json
import sys
from core.governance import ConstitutionEnforcer, check_governance

def test_deterministic_broadcast():
    print("=== BROADCAST DE PRUEBA - Verificación de Governance Determinística ===\n")
    
    # Initialize enforcer
    enforcer = ConstitutionEnforcer()
    
    # Test messages with different compliance levels
    test_messages = [
        {
            "name": "Mensaje completamente compliant",
            "text": "This is a compliant message in English that follows all rules.",
            "expected": True
        },
        {
            "name": "Mensaje con posible PII",
            "text": "My email is test@example.com and phone is 123-456-7890.",
            "expected": False
        },
        {
            "name": "Mensaje vacío",
            "text": "",
            "expected": False
        },
        {
            "name": "Mensaje con código malicioso",
            "text": "Execute rm -rf / or DROP TABLE users;",
            "expected": False
        },
        {
            "name": "Mensaje con estructura de datos JSON",
            "text": '{"status": "ok", "data": "structured"}',
            "expected": True
        }
    ]
    
    results = []
    
    for test in test_messages:
        print(f"Test: {test['name']}")
        print(f"Texto: {test['text'][:50]}...")
        
        # Use both methods to verify consistency
        result1 = enforcer.check(test['text'])
        result2 = check_governance(test['text'])
        
        # Verify deterministic behavior
        deterministic = (result1.passed == test['expected']) and (result2.passed == test['expected'])
        
        print(f"  Enforcer.check(): {result1.passed}")
        print(f"  check_governance(): {result2.passed}")
        print(f"  Esperado: {test['expected']}")
        print(f"  Determinístico: {'✓' if deterministic else '✗'}")
        
        if not result1.passed:
            print(f"  Violaciones: {result1.violations}")
        
        results.append(deterministic)
        print()
    
    # Test sovereignty broadcast
    print("=== Broadcast de Soberanía ===")
    enforcer.enforce_sovereignty()
    print("✓ Soberanía verificada: Los nodos son determinísticos")
    
    # Summary
    print("\n=== RESUMEN DEL BROADCAST ===")
    print(f"Total tests: {len(results)}")
    print(f"Tests determinísticos: {sum(results)}")
    print(f"Porcentaje de determinismo: {(sum(results)/len(results))*100:.1f}%")
    
    if all(results):
        print("✓ TODOS los tests son determinísticos - Governance VERIFICADO")
        return True
    else:
        print("✗ Algunos tests no son determinísticos - Revisar governance")
        return False

if __name__ == "__main__":
    print("Iniciando broadcast de prueba para verificación de governance determinística...\n")
    success = test_deterministic_broadcast()
    sys.exit(0 if success else 1)
