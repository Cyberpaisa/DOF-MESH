
#!/usr/bin/env python3
"""Test script to verify DOF framework basic functionality"""

import sys
import os

def test_imports():
    """Test importing core modules"""
    print("Testing DOF framework imports...")
    
    try:
        from core.providers import ProviderManager
        print("✓ ProviderManager imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ProviderManager: {e}")
        return False
    
    try:
        from core.metrics import MetricsLogger
        print("✓ MetricsLogger imported successfully")
    except Exception as e:
        print(f"✗ Failed to import MetricsLogger: {e}")
        return False
    
    try:
        from core.governance import ConstitutionEnforcer
        print("✓ ConstitutionEnforcer imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ConstitutionEnforcer: {e}")
        return False
    
    try:
        from core.observability import set_deterministic, get_session_id
        print("✓ Observability modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import observability modules: {e}")
        return False
    
    return True

def test_directory_structure():
    """Verify essential directories exist"""
    print("\nChecking directory structure...")
    
    required_dirs = [
        'core',
        'tests',
        'logs',
        'agents',
        'config'
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"✓ Directory '{dir_name}' exists")
        else:
            print(f"✗ Directory '{dir_name}' missing")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("DOF Framework Health Check")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test directory structure
    structure_ok = test_directory_structure()
    
    # Overall status
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"Structure: {'PASS' if structure_ok else 'FAIL'}")
    
    if imports_ok and structure_ok:
        print("\n✅ DOF framework appears healthy!")
        return 0
    else:
        print("\n❌ DOF framework has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
