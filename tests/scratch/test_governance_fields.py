
#!/usr/bin/env python3
"""Test script to verify all governance fields exist."""

import sys
sys.path.insert(0, '/Users/jquiceva/equipo-de-agentes')

from core.governance import (
    GovernanceResult,
    RulePriority,
    HierarchyResult,
    ConstitutionEnforcer,
    check_governance,
    enforce_hierarchy,
    HARD_RULES,
    SOFT_RULES,
    PII_PATTERNS,
    _OVERRIDE_PATTERNS,
    _ESCALATION_PATTERNS,
    GOVERNANCE_RULES
)

def test_dataclasses():
    """Verify dataclass fields exist."""
    print("=== Testing Dataclasses ===")
    
    # GovernanceResult
    gr_fields = GovernanceResult.__dataclass_fields__.keys()
    print(f"GovernanceResult fields: {list(gr_fields)}")
    expected_gr_fields = {'passed', 'score', 'violations', 'warnings'}
    assert expected_gr_fields.issubset(set(gr_fields)), f"Missing fields in GovernanceResult: {expected_gr_fields - set(gr_fields)}"
    
    # HierarchyResult
    hr_fields = HierarchyResult.__dataclass_fields__.keys()
    print(f"HierarchyResult fields: {list(hr_fields)}")
    expected_hr_fields = {'compliant', 'violation_level', 'details'}
    assert expected_hr_fields.issubset(set(hr_fields)), f"Missing fields in HierarchyResult: {expected_hr_fields - set(hr_fields)}"
    
    print("✓ Dataclasses have all required fields")

def test_enums():
    """Verify enum values exist."""
    print("\n=== Testing Enums ===")
    
    print(f"RulePriority values: {[e.value for e in RulePriority]}")
    expected_values = {'SYSTEM', 'USER', 'ASSISTANT'}
    actual_values = {e.value for e in RulePriority}
    assert actual_values == expected_values, f"RulePriority values mismatch: expected {expected_values}, got {actual_values}"
    
    print("✓ Enums have all required values")

def test_rules():
    """Verify rules lists exist and have required structure."""
    print("\n=== Testing Rules ===")
    
    print(f"HARD_RULES count: {len(HARD_RULES)}")
    print(f"SOFT_RULES count: {len(SOFT_RULES)}")
    print(f"PII_PATTERNS count: {len(PII_PATTERNS)}")
    print(f"GOVERNANCE_RULES count: {len(GOVERNANCE_RULES)}")
    
    # Check HARD_RULES structure
    required_hard_fields = {'id', 'priority', 'description'}
    for rule in HARD_RULES:
        assert all(field in rule for field in required_hard_fields), f"HARD_RULE missing fields: {rule}"
    
    # Check SOFT_RULES structure
    required_soft_fields = {'id', 'priority', 'description', 'weight', 'match_mode'}
    for rule in SOFT_RULES:
        assert all(field in rule for field in required_soft_fields), f"SOFT_RULE missing fields: {rule}"
    
    # Check PII_PATTERNS structure
    required_pii_fields = {'id', 'pattern', 'description'}
    for pattern in PII_PATTERNS:
        assert all(field in pattern for field in required_pii_fields), f"PII_PATTERN missing fields: {pattern}"
    
    print("✓ All rules have required structure")

def test_functions():
    """Verify main functions exist."""
    print("\n=== Testing Functions ===")
    
    functions_to_check = [
        ('check_governance', check_governance),
        ('enforce_hierarchy', enforce_hierarchy),
    ]
    
    for name, func in functions_to_check:
        assert callable(func), f"Function {name} is not callable"
        print(f"✓ {name} is callable")
    
    print("✓ All required functions exist")

def test_constitution_enforcer():
    """Verify ConstitutionEnforcer methods exist."""
    print("\n=== Testing ConstitutionEnforcer ===")
    
    enforcer = ConstitutionEnforcer()
    
    methods_to_check = [
        'enforce',
        'check',
        'validate_task',
        'verify_constitution_integrity',
        'enforce_sovereignty',
        'enforce_hierarchy'
    ]
    
    for method_name in methods_to_check:
        assert hasattr(enforcer, method_name), f"ConstitutionEnforcer missing method: {method_name}"
        method = getattr(enforcer, method_name)
        assert callable(method), f"ConstitutionEnforcer.{method_name} is not callable"
        print(f"✓ ConstitutionEnforcer.{method_name} exists and is callable")
    
    print("✓ ConstitutionEnforcer has all required methods")

def test_patterns():
    """Verify pattern lists exist."""
    print("\n=== Testing Patterns ===")
    
    print(f"_OVERRIDE_PATTERNS count: {len(_OVERRIDE_PATTERNS)}")
    print(f"_ESCALATION_PATTERNS count: {len(_ESCALATION_PATTERNS)}")
    
    assert isinstance(_OVERRIDE_PATTERNS, list), "_OVERRIDE_PATTERNS should be a list"
    assert isinstance(_ESCALATION_PATTERNS, list), "_ESCALATION_PATTERNS should be a list"
    
    # Check patterns are strings
    for pattern in _OVERRIDE_PATTERNS:
        assert isinstance(pattern, str), f"_OVERRIDE_PATTERNS contains non-string: {pattern}"
    
    for pattern in _ESCALATION_PATTERNS:
        assert isinstance(pattern, str), f"_ESCALATION_PATTERNS contains non-string: {pattern}"
    
    print("✓ All pattern lists are valid")

def test_integration():
    """Test integration with sample text."""
    print("\n=== Testing Integration ===")
    
    sample_text = "This is a test response with no violations. It includes a URL: https://example.com for testing."
    
    # Test check_governance
    result = check_governance(sample_text)
    print(f"check_governance result: passed={result.passed}, score={result.score}")
    print(f"  violations: {result.violations}")
    print(f"  warnings: {result.warnings}")
    
    assert isinstance(result, GovernanceResult), "check_governance should return GovernanceResult"
    
    # Test ConstitutionEnforcer.enforce
    enforcer = ConstitutionEnforcer()
    enforce_result = enforcer.enforce(sample_text)
    print(f"ConstitutionEnforcer.enforce result: {enforce_result}")
    
    expected_enforce_keys = {'status', 'hard_violations', 'soft_violations', 'score'}
    assert all(key in enforce_result for key in expected_enforce_keys), f"enforce result missing keys: {expected_enforce_keys - set(enforce_result.keys())}"
    
    # Test ConstitutionEnforcer.check
    check_result = enforcer.check(sample_text)
    print(f"ConstitutionEnforcer.check result: passed={check_result.passed}, score={check_result.score}")
    
    assert isinstance(check_result, GovernanceResult), "enforcer.check should return GovernanceResult"
    
    print("✓ Integration tests passed")

def main():
    """Run all tests."""
    print("Verifying all governance fields exist...\n")
    
    try:
        test_dataclasses()
        test_enums()
        test_rules()
        test_functions()
        test_constitution_enforcer()
        test_patterns()
        test_integration()
        
        print("\n" + "="*50)
        print("✅ ALL GOVERNANCE FIELDS VERIFIED SUCCESSFULLY")
        print("="*50)
        return 0
    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
