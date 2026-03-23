"""
DOF Mesh — Data Loss Prevention (DLP)
=======================================
Scans agent outputs BEFORE they leave the mesh for sensitive data:
API keys, PII, private keys, credentials, secrets.

Integrates with cerberus.py (as addon — cerberus.py UNTOUCHED) and audit_log.py.
Zero LLM — 100% deterministic regex + entropy analysis.

Usage:
    dlp = DLPScanner()
    result = dlp.scan("output text here")
    if result.blocked:
        raise DLPViolationError(result.violations)
"""

import re
import math
import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime, timezone

logger = logging.getLogger("core.dlp")


# ═══════════════════════════════════════
# DLP PATTERNS
# ═══════════════════════════════════════

@dataclass
class DLPPattern:
    name:        str
    pattern:     str
    severity:    str        # CRITICAL / HIGH / MEDIUM
    description: str
    block:       bool = True


DLP_PATTERNS: List[DLPPattern] = [
    # API Keys
    DLPPattern("OPENAI_KEY",      r"sk-[A-Za-z0-9]{32,}",          "CRITICAL", "OpenAI API key"),
    DLPPattern("ANTHROPIC_KEY",   r"sk-ant-[A-Za-z0-9\-]{40,}",    "CRITICAL", "Anthropic API key"),
    DLPPattern("GROQ_KEY",        r"gsk_[A-Za-z0-9]{40,}",         "CRITICAL", "Groq API key"),
    DLPPattern("CEREBRAS_KEY",    r"csk-[A-Za-z0-9]{40,}",         "CRITICAL", "Cerebras API key"),
    DLPPattern("NVIDIA_KEY",      r"nvapi-[A-Za-z0-9\-_]{40,}",    "CRITICAL", "NVIDIA NIM API key"),
    DLPPattern("GENERIC_API_KEY", r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{20,}", "HIGH", "Generic API key pattern"),

    # Private Keys / Crypto
    DLPPattern("RSA_PRIVATE",   r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "CRITICAL", "Private key PEM block"),
    DLPPattern("ETH_PRIVATE",   r"(?<![A-Fa-f0-9])([A-Fa-f0-9]{64})(?![A-Fa-f0-9])", "HIGH", "Potential Ethereum private key (64 hex chars)"),
    DLPPattern("MNEMONIC_SEED", r"(?i)(seed|mnemonic|recovery).{0,20}([a-z]+ ){11,23}[a-z]+", "CRITICAL", "BIP39 mnemonic seed phrase"),

    # Credentials
    DLPPattern("PASSWORD",      r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?.{6,}", "HIGH", "Password in output"),
    DLPPattern("SECRET",        r"(?i)(secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{10,}", "HIGH", "Secret/token in output"),
    DLPPattern("DB_CONN",       r"(?i)(postgresql|mysql|mongodb|redis)://[^\s]{10,}", "CRITICAL", "Database connection string"),

    # PII
    DLPPattern("EMAIL_BULK",    r"(?:[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}(?:\s*[,;]\s*)){3,}", "MEDIUM", "Bulk email addresses (3+)"),
    DLPPattern("SSN",           r"\b\d{3}-\d{2}-\d{4}\b",           "CRITICAL", "US Social Security Number"),
    DLPPattern("CREDIT_CARD",   r"\b(?:\d{4}[- ]?){3}\d{4}\b",      "CRITICAL", "Credit card number pattern"),

    # Internal paths / infra
    DLPPattern("AWS_ACCESS",    r"AKIA[0-9A-Z]{16}",                 "CRITICAL", "AWS Access Key ID"),
    DLPPattern("AWS_SECRET",    r"(?i)aws.{0,20}secret.{0,20}[A-Za-z0-9/+=]{40}", "CRITICAL", "AWS Secret Key"),
    DLPPattern("JWT_TOKEN",     r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", "HIGH", "JWT token"),
]


# ═══════════════════════════════════════
# ENTROPY ANALYSIS
# ═══════════════════════════════════════

def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    n = len(s)
    return -sum((f/n) * math.log2(f/n) for f in freq.values())


def _has_high_entropy_token(text: str, min_len: int = 20, threshold: float = 4.5) -> List[str]:
    """Find high-entropy tokens that may be secrets."""
    suspicious = []
    for token in re.findall(r'[A-Za-z0-9+/=\-_\.]{%d,}' % min_len, text):
        if _shannon_entropy(token) >= threshold:
            suspicious.append(token[:32] + "...")
    return suspicious


# ═══════════════════════════════════════
# DLP RESULT
# ═══════════════════════════════════════

@dataclass
class DLPViolation:
    pattern_name: str
    severity:     str
    description:  str
    match_preview: str    # first 20 chars of match, redacted
    blocked:      bool


@dataclass
class DLPScanResult:
    text_length:     int
    violations:      List[DLPViolation] = field(default_factory=list)
    entropy_flags:   List[str]          = field(default_factory=list)
    blocked:         bool               = False
    scan_time_ms:    float              = 0.0
    timestamp:       str                = ""

    @property
    def has_critical(self) -> bool:
        return any(v.severity == "CRITICAL" for v in self.violations)

    def summary(self) -> str:
        if not self.violations and not self.entropy_flags:
            return "DLP_CLEAN"
        sev = "CRITICAL" if self.has_critical else "HIGH" if self.violations else "MEDIUM"
        return f"DLP_{sev}: {len(self.violations)} violations, {len(self.entropy_flags)} entropy flags"


class DLPViolationError(Exception):
    def __init__(self, result: DLPScanResult):
        self.result = result
        super().__init__(result.summary())


# ═══════════════════════════════════════
# DLP SCANNER
# ═══════════════════════════════════════

class DLPScanner:
    """
    Deterministic DLP scanner for DOF mesh agent outputs.
    Runs before any message leaves the local mesh boundary.
    Zero LLM — pure regex + entropy.
    """

    def __init__(self,
                 patterns: List[DLPPattern] = None,
                 entropy_threshold: float = 4.5,
                 entropy_min_len: int = 20,
                 block_on_critical: bool = True,
                 block_on_high: bool = False):
        self._patterns = patterns or DLP_PATTERNS
        self._compiled = [(p, re.compile(p.pattern)) for p in self._patterns]
        self._entropy_threshold = entropy_threshold
        self._entropy_min_len = entropy_min_len
        self._block_critical = block_on_critical
        self._block_high = block_on_high
        self._scan_count = 0
        self._violation_count = 0
        self._lock = threading.Lock()

    def scan(self, text: str) -> DLPScanResult:
        """Scan text for sensitive data. Returns DLPScanResult."""
        import time
        start = time.time()
        violations = []
        blocked = False

        with self._lock:
            self._scan_count += 1

        for pattern, regex in self._compiled:
            match = regex.search(text)
            if match:
                preview = match.group(0)[:8] + "****"
                v = DLPViolation(
                    pattern_name=pattern.name,
                    severity=pattern.severity,
                    description=pattern.description,
                    match_preview=preview,
                    blocked=pattern.block and (
                        (pattern.severity == "CRITICAL" and self._block_critical) or
                        (pattern.severity == "HIGH" and self._block_high)
                    ),
                )
                violations.append(v)
                if v.blocked:
                    blocked = True

        entropy_flags = _has_high_entropy_token(text, self._entropy_min_len, self._entropy_threshold)

        with self._lock:
            self._violation_count += len(violations)

        result = DLPScanResult(
            text_length=len(text),
            violations=violations,
            entropy_flags=entropy_flags,
            blocked=blocked,
            scan_time_ms=round((time.time() - start) * 1000, 2),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        if violations or entropy_flags:
            self._audit(result)
            logger.warning(f"DLP: {result.summary()} in {result.scan_time_ms}ms")

        return result

    def scan_and_raise(self, text: str) -> str:
        """Scan text and raise DLPViolationError if blocked. Returns text if clean."""
        result = self.scan(text)
        if result.blocked:
            raise DLPViolationError(result)
        return text

    def redact(self, text: str) -> str:
        """Scan and redact all matched patterns instead of blocking."""
        for pattern, regex in self._compiled:
            text = regex.sub(f"[REDACTED:{pattern.name}]", text)
        return text

    def status(self) -> Dict:
        return {
            "patterns_loaded": len(self._patterns),
            "scans_total": self._scan_count,
            "violations_total": self._violation_count,
            "entropy_threshold": self._entropy_threshold,
            "block_critical": self._block_critical,
            "block_high": self._block_high,
        }

    def _audit(self, result: DLPScanResult):
        try:
            from core.audit_log import audit_security
            audit_security("DLP_SCAN", {
                "violations": [asdict(v) for v in result.violations],
                "entropy_flags": len(result.entropy_flags),
                "blocked": result.blocked,
                "scan_time_ms": result.scan_time_ms,
            })
        except Exception:
            pass


# ═══════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════

_dlp_instance: Optional[DLPScanner] = None
_dlp_lock = threading.Lock()

def get_dlp() -> DLPScanner:
    global _dlp_instance
    if _dlp_instance is None:
        with _dlp_lock:
            if _dlp_instance is None:
                _dlp_instance = DLPScanner()
    return _dlp_instance


# ═══════════════════════════════════════
# CERBERUS ADDON HOOK (cerberus.py UNTOUCHED)
# ═══════════════════════════════════════

def cerberus_dlp_hook(text: str) -> tuple:
    """
    Drop-in addon for cerberus.py governance pipeline.
    Returns (passed: bool, reason: str).
    Compatible with cerberus governance result format.
    """
    result = get_dlp().scan(text)
    if result.blocked:
        names = [v.pattern_name for v in result.violations if v.blocked]
        return False, f"DLP_BLOCK: {', '.join(names)}"
    return True, "DLP_CLEAN"


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    dlp = get_dlp()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(dlp.status(), indent=2))
        sys.exit(0)

    # Demo scan
    test_cases = [
        ("clean", "The analysis shows 42 nodes active in the mesh"),
        ("api_key", "Use key sk-abc123def456ghi789jkl012mno345pqr678stu901vwx"),
        ("private_key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA..."),
        ("high_entropy", "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_5W4SNppx"),
    ]

    print("=== DOF DLP Scanner Demo ===\n")
    for name, text in test_cases:
        result = dlp.scan(text)
        print(f"[{name:12s}] {result.summary()} | {result.scan_time_ms}ms")
        for v in result.violations:
            print(f"             └─ {v.severity}: {v.pattern_name} — {v.description}")
