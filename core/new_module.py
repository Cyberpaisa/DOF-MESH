
"""
PII Detection Module
Detects and masks PII in text.
"""

import re

def detect_pii(text: str) -> dict:
    """
    Detect PII in text.
    Returns dict with detected PII types and counts.
    """
    patterns = {
        "credit_card": r"\b4[0-9]{12}(?:[0-9]{3})?\b|\b5[1-5][0-9]{14}\b|\b3[47][0-9]{13}\b|\b6(?:011|5[0-9]{2})[0-9]{12}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }
    
    results = {}
    for pii_type, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            results[pii_type] = len(matches)
    return results

def mask_pii(text: str) -> str:
    """
    Mask PII in text.
    Replaces credit card numbers with [CREDIT_CARD_MASKED],
    SSNs with [SSN_MASKED], emails with [EMAIL_MASKED],
    phones with [PHONE_MASKED].
    """
    # Credit card
    text = re.sub(r"\b4[0-9]{12}(?:[0-9]{3})?\b", "[CREDIT_CARD_MASKED]", text)
    text = re.sub(r"\b5[1-5][0-9]{14}\b", "[CREDIT_CARD_MASKED]", text)
    text = re.sub(r"\b3[47][0-9]{13}\b", "[CREDIT_CARD_MASKED]", text)
    text = re.sub(r"\b6(?:011|5[0-9]{2})[0-9]{12}\b", "[CREDIT_CARD_MASKED]", text)
    
    # SSN
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_MASKED]", text)
    
    # Email
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_MASKED]", text)
    
    # Phone
    text = re.sub(r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_MASKED]", text)
    
    return text

if __name__ == "__main__":
    test_text = "El numero de tarjeta del cliente es 4532-1234-5678-9012 con vencimiento 12/28."
    print("Original:", test_text)
    print("Detected PII:", detect_pii(test_text))
    print("Masked:", mask_pii(test_text))
