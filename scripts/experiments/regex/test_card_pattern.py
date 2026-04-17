
import re

# Existing pattern from governance.py
visa_pattern = r"\b4[0-9]{12}(?:[0-9]{3})?\b"
card_number = "4532-1234-5678-9012"

# Remove hyphens
cleaned = card_number.replace("-", "")
print(f"Cleaned card number: {cleaned}")
print(f"Length: {len(cleaned)}")
print(f"Matches Visa pattern: {bool(re.match(visa_pattern, cleaned))}")

# Also test with hyphens
print(f"Original with hyphens matches: {bool(re.search(visa_pattern, card_number))}")

# Test other patterns
pii_patterns = [
    {"id": "P1", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "description": "SSN"},
    {"id": "P2", "pattern": r"\b4[0-9]{12}(?:[0-9]{3})?\b", "description": "Visa card"},
    {"id": "P3", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "description": "Email"},
]

print("\nTesting all PII patterns:")
for p in pii_patterns:
    matches = re.findall(p["pattern"], card_number)
    print(f"{p['id']} ({p['description']}): {matches}")
