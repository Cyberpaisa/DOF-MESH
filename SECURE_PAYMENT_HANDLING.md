
# Secure Payment Handling Guidelines for DOF

## ⚠️ CRITICAL SECURITY NOTICE

**NEVER** store, log, or process raw credit card information in the DOF repository. The following card details were provided in an insecure manner and should be considered compromised:

- Card: `4532-1234-5678-9012`
- Expiry: `12/28`

## Best Practices for Payment Integration

### 1. Use PCI-Compliant Payment Processors
- **Stripe**, **PayPal**, or other PCI-DSS Level 1 certified providers
- Never handle raw card data directly
- Use tokenization and secure iframes/redirects

### 2. Secure Implementation Pattern

```python
# Example using Stripe (conceptual)
import stripe

# NEVER do this:
# card_number = "4532-1234-5678-9012"
# expiry = "12/28"

# ALWAYS do this:
def create_payment_intent(amount, currency="usd"):
    """
    Create a payment intent using Stripe's secure API
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    # Client-side should use Stripe Elements or Payment Element
    # Server only receives payment method ID, not card details
    payment_intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        payment_method_types=["card"],
    )
    return payment_intent.client_secret
```

### 3. Environment Configuration
```bash
# .env file (add to .gitignore)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 4. Audit Logging (Without PII)
```python
def log_payment_event(event_type, amount, currency, status):
    """
    Log payment events without sensitive data
    """
    audit_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "amount": amount,
        "currency": currency,
        "status": status,
        "user_id": "hashed_or_tokenized_id",  # No PII
        "payment_method": "card",  # Generic type only
    }
    # Store in secure audit system
```

### 5. Immediate Actions Required

1. **Rotate the compromised card** (if real)
2. **Review access logs** for any unauthorized access
3. **Implement input validation** to reject raw card numbers
4. **Add security scanning** for accidental card number commits

### 6. DOF-Specific Integration

If integrating payments with DOF mesh services:

```python
from core.mesh_health import MeshHealthMonitor
from core.audit_log import AuditLogger

class SecurePaymentService:
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.mesh_monitor = MeshHealthMonitor()
    
    async def process_payment(self, payment_token, amount, description):
        """
        Process payment through secure gateway
        """
        # Validate token format
        if not self._validate_payment_token(payment_token):
            raise ValueError("Invalid payment token")
        
        # Log audit event
        await self.audit_logger.log_event(
            "payment_initiated",
            {"amount": amount, "description": description}
        )
        
        # Process via secure API
        # ... implementation using payment gateway
        
        return {"status": "success", "transaction_id": "secure_id"}
```

## Compliance Requirements

- **PCI-DSS**: Required for any card processing
- **GDPR**: Data minimization, right to erasure
- **SOC 2**: Security controls for cloud services

## Emergency Response

If card data is accidentally committed:
1. `git filter-branch` to remove from history
2. Rotate all exposed secrets
3. Notify affected parties
4. Security audit

## Resources

- [PCI Security Standards Council](https://www.pcisecuritystandards.org/)
- [Stripe Security Guide](https://stripe.com/docs/security)
- [OWASP Payment Security](https://owasp.org/www-project-payment-security/)
