"""
core/rust_gate_bridge.py
Bridge que usa el módulo Rust dof_z3_gate si está compilado,
o cae en el gate Python puro como fallback.
"""
import logging
logger = logging.getLogger("dof.rust_gate")

_RUST_AVAILABLE = False
_RustGate = None

try:
    import dof_z3_gate
    _RustGate = dof_z3_gate.PyDofGate
    _RUST_AVAILABLE = True
    logger.info("[RustGateBridge] Rust gate loaded — <1ms mode active")
except ImportError:
    logger.info("[RustGateBridge] Rust gate not available — using Python fallback")


def evaluate_output(output: str) -> dict:
    """
    Evaluate output through the fastest available gate.
    Uses Rust if compiled, else Python Z3 gate.

    Returns: {"verdict": "APPROVED"|"REJECTED", "proof_hash": "0x...", "backend": "rust"|"python"}
    """
    if _RUST_AVAILABLE:
        gate = _RustGate()
        result = gate.evaluate(output)
        return {
            "verdict": result.verdict,
            "proof_hash": result.proof_hash,
            "latency_us": result.latency_us,
            "backend": "rust",
            "violated_constraint": result.violated_constraint,
        }
    else:
        # Python fallback using governance.py patterns
        import hashlib
        import re

        OVERRIDE_PATTERNS = [
            r"ignore previous instructions",
            r"disregard all rules",
            r"override governance",
            r"bypass constitution",
            r"jailbreak",
        ]

        output_lower = output.lower()
        for pattern in OVERRIDE_PATTERNS:
            if re.search(pattern, output_lower):
                proof_data = (output + "REJECTED").encode()
                proof_hash = "0x" + hashlib.sha3_256(proof_data).hexdigest()
                return {
                    "verdict": "REJECTED",
                    "proof_hash": proof_hash,
                    "latency_us": None,
                    "backend": "python",
                    "violated_constraint": pattern,
                }

        proof_data = (output + "APPROVED").encode()
        proof_hash = "0x" + hashlib.sha3_256(proof_data).hexdigest()
        return {
            "verdict": "APPROVED",
            "proof_hash": proof_hash,
            "latency_us": None,
            "backend": "python",
            "violated_constraint": None,
        }


def is_rust_available() -> bool:
    return _RUST_AVAILABLE
