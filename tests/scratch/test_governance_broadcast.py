
#!/usr/bin/env python3
"""
Broadcast de prueba para verificar governance deterministica.
Test broadcast to verify deterministic governance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.governance import ConstitutionEnforcer, check_governance, GovernanceResult

def test_broadcast():
    """Test broadcast to verify deterministic governance."""
    print("=== Broadcast de prueba para verificar governance deterministica ===")
    print("=== Test broadcast to verify deterministic governance ===\n")
    
    # Initialize the ConstitutionEnforcer
    enforcer = ConstitutionEnforcer()
    print("✓ ConstitutionEnforcer initialized")
    
    # Test 1: Verify constitution integrity
    integrity_check = enforcer.verify_constitution_integrity()
    print(f"✓ Constitution integrity check: {integrity_check}")
    
    # Test 2: Test sovereignty enforcement
    enforcer.enforce_sovereignty()
    print("✓ Sovereignty enforcement passed")
    
    # Test 3: Test task validation
    valid_task = {"task_type": "test_broadcast", "description": "Governance test broadcast"}
    task_valid = enforcer.validate_task(valid_task)
    print(f"✓ Task validation: {task_valid}")
    
    # Test 4: Test governance check on compliant text
    compliant_text = """
    The Deterministic Observability Framework (DOF) ensures that all agent interactions
    are traceable, verifiable, and deterministic. The mesh architecture uses file-based
    communication with atomic operations to guarantee consistency across nodes.
    """
    
    result = enforcer.enforce(compliant_text)
    print(f"✓ Governance enforcement on compliant text: {result['status']}")
    
    # Test 5: Direct check_governance function
    direct_result = check_governance(compliant_text)
    print(f"✓ Direct check_governance result: {'PASSED' if direct_result.passed else 'FAILED'}")
    
    # Test 6: Test the check() method alias
    check_result = enforcer.check(compliant_text)
    print(f"✓ enforcer.check() result: {'PASSED' if check_result.passed else 'FAILED'}")
    
    print("\n=== Resumen del broadcast / Broadcast summary ===")
    print(f"• Constitution integrity: {'✓' if integrity_check else '✗'}")
    print(f"• Sovereignty enforcement: ✓")
    print(f"• Task validation: {'✓' if task_valid else '✗'}")
    print(f"• Governance enforcement: {result['status']}")
    print(f"• Direct check_governance: {'✓ PASSED' if direct_result.passed else '✗ FAILED'}")
    print(f"• enforcer.check() method: {'✓ PASSED' if check_result.passed else '✗ FAILED'}")
    
    # Final verification
    all_passed = (integrity_check and task_valid and 
                  result['status'] == 'COMPLIANT' and 
                  direct_result.passed and check_result.passed)
    
    print(f"\n=== Resultado final / Final result ===")
    if all_passed:
        print("✅ TODAS LAS PRUEBAS PASARON / ALL TESTS PASSED")
        print("✅ Governance deterministica verificada / Deterministic governance verified")
        return 0
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON / SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = test_broadcast()
    sys.exit(exit_code)
