
#!/usr/bin/env python3
"""Test DLP scanner with credit card detection."""

import sys
sys.path.insert(0, '.')

from core.dlp import get_dlp

def test_credit_card_detection():
    """Test DLP scanner with credit card information."""
    
    # Test case 1: Credit card with dashes
    test_text1 = "El numero de tarjeta del cliente es 4532-1234-5678-9012 con vencimiento 12/28."
    
    # Test case 2: Credit card with spaces
    test_text2 = "Card number: 4532 1234 5678 9012 exp 12/28"
    
    # Test case 3: Credit card without separators
    test_text3 = "Card: 4532123456789012"
    
    # Test case 4: Clean text (no PII)
    test_text4 = "The customer needs technical support for their account."
    
    dlp = get_dlp()
    
    print("=== DOF DLP Credit Card Detection Test ===\n")
    
    tests = [
        ("Credit card with dashes", test_text1),
        ("Credit card with spaces", test_text2),
        ("Credit card without separators", test_text3),
        ("Clean text", test_text4),
    ]
    
    for name, text in tests:
        print(f"\nTest: {name}")
        print(f"Text: {text[:60]}...")
        
        result = dlp.scan(text)
        
        print(f"  Blocked: {result.blocked}")
        print(f"  Violations: {len(result.violations)}")
        print(f"  Summary: {result.summary()}")
        
        if result.violations:
            for v in result.violations:
                print(f"    - {v.pattern_name} ({v.severity}): {v.description}")
                print(f"      Match: {v.match_text}")
                print(f"      Blocked: {v.blocked}")

if __name__ == "__main__":
    test_credit_card_detection()
