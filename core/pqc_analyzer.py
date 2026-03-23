"""
Post-Quantum Cryptography Analyzer — Evaluate quantum resistance of systems.

Deterministic analysis of cryptographic algorithms against quantum threats:
  - Shor's algorithm: factoring RSA/ECC (polynomial time)
  - Grover's algorithm: brute-force AES/hashes (quadratic speedup)

Recommends migration path to NIST PQC standards:
  - ML-KEM (FIPS 203): Key encapsulation based on Module-LWE
  - ML-DSA (FIPS 204): Digital signatures based on Module-LWE
  - SLH-DSA (FIPS 205): Stateless hash-based signatures

Zero external dependencies. Analysis only — does not implement PQC primitives.
Results logged to logs/pqc_analysis.jsonl for audit.
"""

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.pqc_analyzer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "pqc_analysis.jsonl")


# --- Quantum Threat Database ---

QUANTUM_THREATS = {
    "shor": {
        "name": "Shor's Algorithm",
        "description": "Factors integers and computes discrete logs in polynomial time",
        "breaks": ["RSA", "ECC", "DSA", "ECDSA", "ECDH", "DH", "ElGamal"],
        "complexity": "O(n^3) on quantum computer",
        "qubits_needed_per_bit": 2,  # ~2n logical qubits for n-bit key
    },
    "grover": {
        "name": "Grover's Algorithm",
        "description": "Searches unstructured space in O(sqrt(N)) — halves symmetric key security",
        "weakens": ["AES", "SHA-256", "SHA-3", "HMAC", "ChaCha20"],
        "speedup": "quadratic",
        "effective_bits_factor": 0.5,  # 256-bit AES → 128-bit effective
    },
}

# --- Algorithm Database ---

@dataclass
class CryptoAlgorithm:
    """Cryptographic algorithm with quantum resistance assessment."""
    name: str
    category: str  # symmetric, asymmetric, hash, signature, kex
    classical_bits: int  # Classical security level in bits
    quantum_bits: int  # Post-quantum security level in bits
    quantum_status: str  # BROKEN, WEAKENED, SAFE
    migration_target: str  # Recommended PQC replacement
    migration_urgency: str  # CRITICAL, HIGH, MEDIUM, LOW
    notes: str = ""


ALGORITHMS: dict[str, CryptoAlgorithm] = {
    # Asymmetric — BROKEN by Shor
    "RSA-2048": CryptoAlgorithm(
        "RSA-2048", "asymmetric", 112, 0, "BROKEN",
        "ML-KEM-768 or ML-DSA-65", "CRITICAL",
        "~4099 logical qubits needed. Shor factors in polynomial time."
    ),
    "RSA-4096": CryptoAlgorithm(
        "RSA-4096", "asymmetric", 140, 0, "BROKEN",
        "ML-KEM-1024 or ML-DSA-87", "CRITICAL",
        "~8199 logical qubits needed. Still polynomial for Shor."
    ),
    "ECC-P256": CryptoAlgorithm(
        "ECC-P256", "asymmetric", 128, 0, "BROKEN",
        "ML-KEM-768 or ML-DSA-65", "CRITICAL",
        "~2330 logical qubits. Used in Bitcoin, Ethereum, most blockchains."
    ),
    "ECC-P384": CryptoAlgorithm(
        "ECC-P384", "asymmetric", 192, 0, "BROKEN",
        "ML-KEM-1024 or ML-DSA-87", "CRITICAL",
        "~3484 logical qubits. TLS 1.3 common choice."
    ),
    "Ed25519": CryptoAlgorithm(
        "Ed25519", "signature", 128, 0, "BROKEN",
        "ML-DSA-65 or SLH-DSA-SHA2-128f", "CRITICAL",
        "Used in SSH, many blockchains. Shor breaks ECDLP."
    ),
    "ECDSA-secp256k1": CryptoAlgorithm(
        "ECDSA-secp256k1", "signature", 128, 0, "BROKEN",
        "ML-DSA-65", "CRITICAL",
        "Bitcoin/Ethereum signature scheme. BROKEN by Shor."
    ),

    # Symmetric — WEAKENED by Grover (halved security bits)
    "AES-128": CryptoAlgorithm(
        "AES-128", "symmetric", 128, 64, "WEAKENED",
        "AES-256", "HIGH",
        "Grover reduces to 64-bit security. Migrate to AES-256."
    ),
    "AES-256": CryptoAlgorithm(
        "AES-256", "symmetric", 256, 128, "SAFE",
        "AES-256 (no change needed)", "LOW",
        "128-bit post-quantum security. Sufficient for foreseeable future."
    ),
    "ChaCha20": CryptoAlgorithm(
        "ChaCha20", "symmetric", 256, 128, "SAFE",
        "ChaCha20 (no change needed)", "LOW",
        "256-bit key → 128-bit post-quantum. Sufficient."
    ),

    # Hashes — WEAKENED by Grover for preimage, collision unaffected
    "SHA-256": CryptoAlgorithm(
        "SHA-256", "hash", 256, 128, "SAFE",
        "SHA-256 (no change needed)", "LOW",
        "Collision resistance: 128→85 bits post-quantum. Preimage: 256→128. Still safe."
    ),
    "SHA-3-256": CryptoAlgorithm(
        "SHA-3-256", "hash", 256, 128, "SAFE",
        "SHA-3-256 (no change needed)", "LOW",
        "Same analysis as SHA-256. Sponge construction resilient."
    ),
    "keccak256": CryptoAlgorithm(
        "keccak256", "hash", 256, 128, "SAFE",
        "keccak256 (no change needed)", "LOW",
        "Used in Ethereum/Avalanche for proof hashes. 128-bit PQ security."
    ),

    # PQC Standards — SAFE
    "ML-KEM-768": CryptoAlgorithm(
        "ML-KEM-768", "kex", 192, 192, "SAFE",
        "N/A (already PQC)", "LOW",
        "NIST FIPS 203. Module-LWE based. Replaces ECDH."
    ),
    "ML-KEM-1024": CryptoAlgorithm(
        "ML-KEM-1024", "kex", 256, 256, "SAFE",
        "N/A (already PQC)", "LOW",
        "NIST FIPS 203. Highest security level."
    ),
    "ML-DSA-65": CryptoAlgorithm(
        "ML-DSA-65", "signature", 192, 192, "SAFE",
        "N/A (already PQC)", "LOW",
        "NIST FIPS 204. Replaces ECDSA/Ed25519."
    ),
    "ML-DSA-87": CryptoAlgorithm(
        "ML-DSA-87", "signature", 256, 256, "SAFE",
        "N/A (already PQC)", "LOW",
        "NIST FIPS 204. Highest security level."
    ),
    "SLH-DSA-SHA2-128f": CryptoAlgorithm(
        "SLH-DSA-SHA2-128f", "signature", 128, 128, "SAFE",
        "N/A (already PQC)", "LOW",
        "NIST FIPS 205. Hash-based, conservative assumption."
    ),
}


# --- Analysis Results ---

@dataclass
class PQCAssessment:
    """Post-quantum cryptography assessment result."""
    algorithm: str
    status: str  # BROKEN, WEAKENED, SAFE
    classical_bits: int
    quantum_bits: int
    threat: str  # shor, grover, none
    migration_target: str
    urgency: str
    notes: str
    qubits_estimated: int = 0  # Estimated logical qubits to break
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemAssessment:
    """Full system post-quantum assessment."""
    algorithms_found: list[str]
    critical_count: int
    high_count: int
    safe_count: int
    overall_status: str  # VULNERABLE, AT_RISK, QUANTUM_READY
    assessments: list[PQCAssessment]
    migration_plan: list[str]
    timestamp: float = field(default_factory=time.time)


# --- Analyzer ---

class PQCAnalyzer:
    """Post-Quantum Cryptography resistance analyzer.

    Evaluates cryptographic algorithms against quantum threats
    and recommends migration paths to NIST PQC standards.

    Zero LLM. Deterministic. Auditable.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def assess_algorithm(self, algo_name: str) -> PQCAssessment:
        """Assess a single algorithm's quantum resistance."""
        algo = ALGORITHMS.get(algo_name)
        if not algo:
            # Try fuzzy match
            for key, val in ALGORITHMS.items():
                if algo_name.lower() in key.lower() or key.lower() in algo_name.lower():
                    algo = val
                    break

        if not algo:
            return PQCAssessment(
                algorithm=algo_name,
                status="UNKNOWN",
                classical_bits=0,
                quantum_bits=0,
                threat="unknown",
                migration_target="Evaluate manually",
                urgency="MEDIUM",
                notes=f"Algorithm '{algo_name}' not in database. Manual assessment required.",
            )

        # Determine threat
        threat = "none"
        qubits = 0
        if algo.quantum_status == "BROKEN":
            threat = "shor"
            # Estimate qubits: ~2n for n-bit key
            qubits = algo.classical_bits * QUANTUM_THREATS["shor"]["qubits_needed_per_bit"]
        elif algo.quantum_status == "WEAKENED":
            threat = "grover"

        assessment = PQCAssessment(
            algorithm=algo.name,
            status=algo.quantum_status,
            classical_bits=algo.classical_bits,
            quantum_bits=algo.quantum_bits,
            threat=threat,
            migration_target=algo.migration_target,
            urgency=algo.migration_urgency,
            notes=algo.notes,
            qubits_estimated=qubits,
        )

        self._log(assessment)
        return assessment

    def assess_system(self, algorithms: list[str]) -> SystemAssessment:
        """Assess a full system's quantum resistance."""
        assessments = [self.assess_algorithm(a) for a in algorithms]

        critical = sum(1 for a in assessments if a.urgency == "CRITICAL")
        high = sum(1 for a in assessments if a.urgency == "HIGH")
        safe = sum(1 for a in assessments if a.status == "SAFE")

        if critical > 0:
            overall = "VULNERABLE"
        elif high > 0:
            overall = "AT_RISK"
        else:
            overall = "QUANTUM_READY"

        # Generate migration plan
        migration = []
        for a in sorted(assessments, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.urgency, 4)):
            if a.urgency in ("CRITICAL", "HIGH"):
                migration.append(f"[{a.urgency}] {a.algorithm} → {a.migration_target}")

        return SystemAssessment(
            algorithms_found=algorithms,
            critical_count=critical,
            high_count=high,
            safe_count=safe,
            overall_status=overall,
            assessments=assessments,
            migration_plan=migration,
        )

    def assess_dof(self) -> SystemAssessment:
        """Assess DOF's own cryptographic stack."""
        dof_algorithms = [
            "ECDSA-secp256k1",  # Avalanche/Base signing
            "keccak256",         # Proof hashes
            "SHA-256",           # Model verification, GGUF hashes
            "Ed25519",           # Potential SSH/agent keys
            "AES-256",           # Encryption at rest (if used)
            "ECC-P256",          # TLS connections to providers
        ]
        return self.assess_system(dof_algorithms)

    def q_day_estimate(self) -> dict:
        """Estimate Q-Day timeline based on current research."""
        return {
            "optimistic": "2030-2033",
            "moderate": "2033-2040",
            "conservative": "2040+",
            "current_largest_factored": "RSA-250 (829 bits, classical, 2020)",
            "current_qubits_available": "~1200 (IBM Condor, noisy)",
            "qubits_needed_rsa2048": "~4099 logical (error-corrected)",
            "qubits_needed_ecc256": "~2330 logical (error-corrected)",
            "physical_to_logical_ratio": "~1000:1 with current error rates",
            "recommendation": "Begin hybrid migration (classical + PQC) NOW. Full PQC by 2028.",
            "harvest_now_decrypt_later": "ACTIVE THREAT — adversaries storing encrypted data today for future quantum decryption",
        }

    def report(self, assessment: SystemAssessment) -> str:
        """Generate human-readable assessment report."""
        lines = [
            "=== Post-Quantum Cryptography Assessment ===",
            f"Status: {assessment.overall_status}",
            f"Algorithms analyzed: {len(assessment.algorithms_found)}",
            f"CRITICAL: {assessment.critical_count} | HIGH: {assessment.high_count} | SAFE: {assessment.safe_count}",
            "",
        ]

        for a in assessment.assessments:
            icon = {"BROKEN": "!!!", "WEAKENED": " ! ", "SAFE": " OK", "UNKNOWN": " ? "}
            lines.append(
                f"  [{icon.get(a.status, '???')}] {a.algorithm:25s} "
                f"Classical: {a.classical_bits:3d}b → PQ: {a.quantum_bits:3d}b "
                f"[{a.urgency}]"
            )
            if a.urgency in ("CRITICAL", "HIGH"):
                lines.append(f"        → Migrate to: {a.migration_target}")

        if assessment.migration_plan:
            lines.append("")
            lines.append("Migration Plan:")
            for step in assessment.migration_plan:
                lines.append(f"  {step}")

        return "\n".join(lines)

    def _log(self, assessment: PQCAssessment):
        """Log assessment to JSONL."""
        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(asdict(assessment), default=str) + "\n")
        except Exception as e:
            logger.error(f"PQC log error: {e}")


# --- Convenience ---

def assess_dof() -> SystemAssessment:
    """Quick assessment of DOF's cryptographic stack."""
    return PQCAnalyzer().assess_dof()


def assess_algorithm(name: str) -> PQCAssessment:
    """Quick assessment of a single algorithm."""
    return PQCAnalyzer().assess_algorithm(name)


# --- Quick test ---

if __name__ == "__main__":
    analyzer = PQCAnalyzer()

    print("=== DOF System Assessment ===\n")
    result = analyzer.assess_dof()
    print(analyzer.report(result))

    print("\n=== Q-Day Timeline ===\n")
    timeline = analyzer.q_day_estimate()
    for k, v in timeline.items():
        print(f"  {k}: {v}")
