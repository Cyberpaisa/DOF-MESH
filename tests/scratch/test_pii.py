
import re

# Current patterns from governance.py
PII_PATTERNS = [
    {"id": "P1", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "description": "SSN"},
    {"id": "P2", "pattern": r"\b4[0-9]{12}(?:[0-9]{3})?\b", "description": "Visa card"},
    {"id": "P3", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "description": "Email"},
]

# Test cases
test_cases = [
    "4532-1234-5678-9012",
    "4532123456789012",
    "12/28",
    "El numero de tarjeta del cliente es 4532-1234-5678-9012 con vencimiento 12/28.",
    "4111-1111-1111-1111",
    "4111111111111111",
    "3782-822463-10005",  # American Express
    "378282246310005",
    "6011-1111-1111-1117",  # Discover
    "6011111111111117",
    "5555-5555-5555-4444",  # MasterCard
    "5555555555554444",
]

print("Testing current PII patterns:")
print("=" * 60)

for text in test_cases:
    print(f"\nText: {text}")
    detected = False
    for pat in PII_PATTERNS:
        if re.search(pat["pattern"], text, re.IGNORECASE):
            print(f"  ✓ Detected by {pat['id']}: {pat['description']}")
            detected = True
    if not detected:
        print(f"  ✗ Not detected")

print("\n" + "=" * 60)
print("\nAnalysis:")
print("1. Current Visa pattern only matches 16-digit numbers without separators")
print("2. Expiration dates (MM/YY) are not detected")
print("3. Other card types (Amex, Discover, MasterCard) are not covered")
