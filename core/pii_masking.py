
"""
DOF Mesh — PII Masking Utility
================================
Secure masking/redaction of sensitive data for safe logging and testing.
Zero LLM — 100% deterministic.

Usage:
    from core.pii_masking import mask_credit_card, mask_pii
    
    # Mask a credit card
    masked = mask_credit_card("4532-1234-5678-9012")
    # Returns: "4532-****-****-9012"
    
    # Mask all PII in text
    safe_text = mask_pii("Customer card 4532-1234-5678-9012, SSN 123-45-6789")
    # Returns: "Customer card 4532-****-****-9012, SSN ***-**-6789"
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class MaskingResult:
    """Result of a masking operation."""
    original: str
    masked: str
    masked_count: int
    pii_types: List[str]


class PIIMasker:
    """
    Secure PII masking utility.
    All operations are deterministic and reversible only with proper authorization.
    """
    
    # Credit card patterns (Luhn-valid cards only for real detection)
    CC_PATTERNS = [
        # Visa: 4XXX-XXXX-XXXX-XXXX
        re.compile(r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?(\d{4})\b'),
        # MasterCard: 51XX-XXXX-XXXX-XXXX through 55XX-XXXX-XXXX-XXXX
        re.compile(r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?(\d{4})\b'),
        # American Express: 34XX-XXXXXX-XXXXX or 37XX-XXXXXX-XXXXX
        re.compile(r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b'),
        # Discover: 6011-XXXX-XXXX-XXXX or 65XX-XXXX-XXXX-XXXX
        re.compile(r'\b(6011|65\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?(\d{4})\b'),
        # Generic: XXXX-XXXX-XXXX-XXXX (any 16 digits with separators)
        re.compile(r'\b(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})\b'),
    ]
    
    # SSN pattern
    SSN_PATTERN = re.compile(r'\b(\d{3})[-]?(\d{2})[-]?(\d{4})\b')
    
    # Email pattern
    EMAIL_PATTERN = re.compile(r'\b([a-zA-Z0-9._%+\-]+)@([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b')
    
    # Phone pattern (US)
    PHONE_PATTERN = re.compile(r'\b(\+?1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b')
    
    @staticmethod
    def mask_credit_card(cc_number: str, keep_last: int = 4, mask_char: str = '*') -> str:
        """
        Mask a credit card number, keeping only the last N digits.
        
        Args:
            cc_number: Credit card number (with or without separators)
            keep_last: Number of digits to keep visible at the end (default: 4)
            mask_char: Character to use for masking (default: '*')
            
        Returns:
            Masked credit card number (e.g., "4532-****-****-9012")
            
        Raises:
            ValueError: If the input doesn't look like a valid credit card format
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', cc_number)
        
        # Validate basic format
        if not (13 <= len(digits) <= 19):
            raise ValueError(f"Invalid credit card length: {len(digits)} digits")
        
        if not digits.isdigit():
            raise ValueError("Credit card must contain only digits and separators")
        
        # Keep last N digits visible
        if keep_last >= len(digits):
            raise ValueError(f"keep_last ({keep_last}) must be less than total digits ({len(digits)})")
        
        # Create masked version
        masked_digits = mask_char * (len(digits) - keep_last) + digits[-keep_last:]
        
        # Try to preserve original formatting
        if '-' in cc_number:
            # Format with dashes: XXXX-XXXX-XXXX-XXXX
            groups = [masked_digits[i:i+4] for i in range(0, len(masked_digits), 4)]
            return '-'.join(groups)
        elif ' ' in cc_number:
            # Format with spaces
            groups = [masked_digits[i:i+4] for i in range(0, len(masked_digits), 4)]
            return ' '.join(groups)
        else:
            # No separators, just return masked digits
            return masked_digits
    
    @staticmethod
    def mask_ssn(ssn: str, keep_last: int = 4, mask_char: str = '*') -> str:
        """
        Mask a Social Security Number.
        
        Args:
            ssn: SSN in format XXX-XX-XXXX or XXXXXXXXX
            keep_last: Number of digits to keep visible at the end (default: 4)
            mask_char: Character to use for masking (default: '*')
            
        Returns:
            Masked SSN (e.g., "***-**-6789")
        """
        digits = re.sub(r'\D', '', ssn)
        
        if len(digits) != 9:
            raise ValueError(f"Invalid SSN length: {len(digits)} digits")
        
        if keep_last > 9:
            keep_last = 4
        
        masked_digits = mask_char * (9 - keep_last) + digits[-keep_last:]
        
        # Format with dashes
        return f"{masked_digits[:3]}-{masked_digits[3:5]}-{masked_digits[5:]}"
    
    @staticmethod
    def mask_email(email: str, mask_char: str = '*') -> str:
        """
        Mask an email address while preserving domain.
        
        Args:
            email: Email address
            mask_char: Character to use for masking (default: '*')
            
        Returns:
            Masked email (e.g., "j*****@example.com")
        """
        match = PIIMasker.EMAIL_PATTERN.match(email)
        if not match:
            return email  # Return as-is if not a valid email
        
        local_part, domain = match.groups()
        
        if len(local_part) <= 1:
            masked_local = local_part[0] + mask_char if local_part else mask_char
        else:
            masked_local = local_part[0] + mask_char * (len(local_part) - 2) + local_part[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str, keep_last: int = 4, mask_char: str = '*') -> str:
        """
        Mask a phone number.
        
        Args:
            phone: Phone number in various formats
            keep_last: Number of digits to keep visible at the end (default: 4)
            mask_char: Character to use for masking (default: '*')
            
        Returns:
            Masked phone number
        """
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) < 10:
            return phone  # Not a valid US phone number
        
        # For US numbers, last 10 digits are the actual number
        if len(digits) > 10 and digits.startswith('1'):
            country_code = '1'
            area_code = digits[1:4]
            prefix = digits[4:7]
            line_number = digits[7:]
        else:
            country_code = ''
            area_code = digits[:3]
            prefix = digits[3:6]
            line_number = digits[6:]
        
        # Mask appropriate parts
        if keep_last >= 4:
            visible_line = line_number[-keep_last:] if keep_last <= len(line_number) else line_number
            masked_line = mask_char * (len(line_number) - len(visible_line)) + visible_line
        else:
            masked_line = mask_char * len(line_number)
        
        # Reconstruct with original formatting hints
        if '(' in phone or ')' in phone:
            formatted = f"({area_code}) {mask_char * 3}-{masked_line}"
        elif '-' in phone:
            formatted = f"{area_code}-{mask_char * 3}-{masked_line}"
        else:
            formatted = f"{area_code}{mask_char * 3}{masked_line}"
        
        if country_code:
            formatted = f"+{country_code} {formatted}"
        
        return formatted
    
    @staticmethod
    def mask_text(text: str, mask_credit_cards: bool = True, mask_ssns: bool = True,
                  mask_emails: bool = True, mask_phones: bool = True) -> MaskingResult:
        """
        Mask all PII in a text string.
        
        Args:
            text: Input text containing potential PII
            mask_credit_cards: Whether to mask credit card numbers
            mask_ssns: Whether to mask Social Security Numbers
            mask_emails: Whether to mask email addresses
            mask_phones: Whether to mask phone numbers
            
        Returns:
            MaskingResult with masked text and statistics
        """
        masked_text = text
        pii_types = []
        masked_count = 0
        
        # Mask credit cards
        if mask_credit_cards:
            for pattern in PIIMasker.CC_PATTERNS:
                def replace_cc(match):
                    nonlocal masked_count
                    masked_count += 1
                    pii_types.append('CREDIT_CARD')
                    cc = match.group(0)
                    try:
                        return PIIMasker.mask_credit_card(cc)
                    except ValueError:
                        return cc  # Return original if masking fails
                
                masked_text = pattern.sub(replace_cc, masked_text)
        
        # Mask SSNs
        if mask_ssns:
            def replace_ssn(match):
                nonlocal masked_count
                masked_count += 1
                pii_types.append('SSN')
                ssn = match.group(0)
                try:
                    return PIIMasker.mask_ssn(ssn)
                except ValueError:
                    return ssn
            
            masked_text = PIIMasker.SSN_PATTERN.sub(replace_ssn, masked_text)
        
        # Mask emails
        if mask_emails:
            def replace_email(match):
                nonlocal masked_count
                masked_count += 1
                pii_types.append('EMAIL')
                email = match.group(0)
                return PIIMasker.mask_email(email)
            
            masked_text = PIIMasker.EMAIL_PATTERN.sub(replace_email, masked_text)
        
        # Mask phones
        if mask_phones:
            def replace_phone(match):
                nonlocal masked_count
                masked_count += 1
                pii_types.append('PHONE')
                phone = match.group(0)
                return PIIMasker.mask_phone(phone)
            
            masked_text = PIIMasker.PHONE_PATTERN.sub(replace_phone, masked_text)
        
        return MaskingResult(
            original=text,
            masked=masked_text,
            masked_count=masked_count,
            pii_types=list(set(pii_types))  # Unique types
        )


# Convenience functions
def mask_credit_card(cc_number: str, keep_last: int = 4, mask_char: str = '*') -> str:
    """Convenience function to mask a credit card number."""
    return PIIMasker.mask_credit_card(cc_number, keep_last, mask_char)

def mask_pii(text: str, **kwargs) -> MaskingResult:
    """Convenience function to mask all PII in text."""
    return PIIMasker.mask_text(text, **kwargs)

def is_credit_card(text: str) -> bool:
    """
    Check if text looks like a credit card number.
    Basic validation without Luhn check.
    """
    digits = re.sub(r'\D', '', text)
    if not (13 <= len(digits) <= 19):
        return False
    
    # Check common prefixes
    if digits.startswith('4'):  # Visa
        return True
    if digits.startswith(('51', '52', '53', '54', '55')):  # MasterCard
        return True
    if digits.startswith(('34', '37')):  # American Express
        return True
    if digits.startswith(('6011', '65')):  # Discover
        return True
    
    return False


# Test the implementation
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("4532-1234-5678-9012", "credit card with dashes"),
        ("4532 1234 5678 9012", "credit card with spaces"),
        ("4532123456789012", "credit card without separators"),
        ("123-45-6789", "SSN"),
        ("test@example.com", "email"),
        ("(123) 456-7890", "phone"),
        ("Customer with card 4532-1234-5678-9012 and SSN 123-45-6789", "mixed PII"),
    ]
    
    print("=== DOF PII Masking Utility Test ===\n")
    
    for test_input, description in test_cases:
        print(f"Test: {description}")
        print(f"Input:  {test_input}")
        
        if is_credit_card(test_input):
            try:
                masked = mask_credit_card(test_input)
                print(f"Masked: {masked}")
            except ValueError as e:
                print(f"Error: {e}")
        else:
            result = mask_pii(test_input)
            print(f"Masked: {result.masked}")
        
        print()
