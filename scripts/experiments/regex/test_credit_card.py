
import re

# Test the current credit card pattern
pattern = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
test_text = "El numero de tarjeta del cliente es 4532-1234-5678-9012 con vencimiento 12/28."

matches = re.findall(pattern, test_text)
print("Matches found:", matches)

# Check if it matches the full number
for match in matches:
    print(f"Match: '{match}'")
    print(f"Length: {len(match)}")
    print(f"Digits only: {re.sub(r'[^0-9]', '', match)}")
    
# Also test without dashes
test_text2 = "4532123456789012"
matches2 = re.findall(pattern, test_text2)
print("\nWithout dashes matches:", matches2)
