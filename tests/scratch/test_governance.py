
#!/usr/bin/env python3
"""Test script for governance deterministic verification."""

import json
import sys
from core.governance import ConstitutionEnforcer

def test_governance():
    print("=== Testing Deterministic Governance ===")
    
    # Create enforcer
    enforcer = ConstitutionEnforcer()
    print("✓ ConstitutionEnforcer initialized")
    
    # Test 1: Verify constitution integrity
    integrity_result = enforcer.verify_constitution_integrity()
    print(f"✓ Constitution integrity check: {integrity_result}")
    
    # Test 2: Validate a simple task
    task = {
        "task_type": "sample_task",
        "task_data": "This is a sample task"
    }
    validation_result = enforcer.validate_task(task)
    print(f"✓ Task validation result: {validation_result}")
    
    # Test 3: Test sovereignty enforcement
    enforcer.enforce_sovereignty()
    print("✓ Sovereignty enforcement completed")
    
    # Test 4: Test governance check on compliant text
    compliant_text = "This is a compliant message that follows all rules."
    result = enforcer.check(compliant_text)
    print(f"✓ Governance check on compliant text: {result.passed}")
    
    # Test 5: Test governance check on non-compliant text
    # Note: We need to see what the hard rules are blocking
    non_compliant_text = "This text mentions OpenAI which might be blocked."
    result2 = enforcer.check(non_compliant_text)
    print(f"✓ Governance check on non-compliant text: {result2.passed}")
    if not result2.passed:
        print(f"  Violations: {result2.violations}")
    
    print("\n=== Governance Test Complete ===")
    print("All tests executed deterministically.")
    
    return all([integrity_result, validation_result, result.passed])

if __name__ == "__main__":
    success = test_governance()
    sys.exit(0 if success else 1)
