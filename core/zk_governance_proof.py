"""
ZK Governance Proof — Proof of compliance para decisiones de governance.

Genera hashes criptográficos verificables en un dominio legacy SHA3-256/FIPS
para cada decisión de governance. Estos hashes son determinísticos y
reproducibles, pero no deben tratarse como EVM/Solidity keccak256.

Zero dependencias externas — usa hashlib (sha3_256) de stdlib.

Usage:
    from core.zk_governance_proof import GovernanceProofGenerator

    gen = GovernanceProofGenerator()
    proof = gen.generate_proof(governance_result, rule_ids=["NO_HALLUCINATION_CLAIM"])
    assert gen.verify_proof(proof, governance_result)
    payload = proof.to_attestation_payload()
"""

from __future__ import annotations

import os
import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.governance import GovernanceResult

logger = logging.getLogger("core.zk_governance_proof")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROOFS_LOG_DIR = os.path.join(BASE_DIR, "logs", "proofs")
PROOFS_LOG_PATH = os.path.join(PROOFS_LOG_DIR, "governance_proofs.jsonl")


def _keccak256(data: bytes) -> str:
    """Legacy SHA3-256/FIPS hash -> hex string; not EVM/Solidity keccak256."""
    return hashlib.sha3_256(data).hexdigest()


def _canonical_json(obj: dict) -> str:
    """Serialización JSON canónica (determinística) de un dict."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _hash_governance_input(violations: list[str], warnings: list[str],
                           score: float, timestamp: str,
                           rule_ids: list[str]) -> str:
    """Genera hash determinístico del input de governance."""
    canonical = _canonical_json({
        "violations": sorted(violations),
        "warnings": sorted(warnings),
        "score": score,
        "timestamp": timestamp,
        "rule_ids": sorted(rule_ids),
    })
    return _keccak256(canonical.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────
# GovernanceProof dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class GovernanceProof:
    """Proof criptográfico de una decisión de governance.

    Attributes:
        proof_hash: Hash keccak256 del resultado completo (proof de compliance).
        input_hash: Hash keccak256 de los inputs (violations + warnings + score).
        timestamp: ISO 8601 timestamp de la generación del proof.
        verdict: "PASS" si no hay violaciones, "FAIL" si hay violaciones.
        rule_ids: Lista de IDs de reglas evaluadas.
        violations_count: Número de violaciones encontradas.
        warnings_count: Número de warnings encontrados.
        score: Score de governance (0.0 a 1.0).
    """
    proof_hash: str
    input_hash: str
    timestamp: str
    verdict: str
    rule_ids: list[str]
    violations_count: int = 0
    warnings_count: int = 0
    score: float = 1.0

    def to_dict(self) -> dict:
        """Serializa el proof a dict."""
        return asdict(self)

    def to_attestation_payload(self) -> dict:
        """Genera payload compatible con on-chain attestation (web3.py).

        Retorna un dict con la estructura para llamar a un contrato
        de attestation en Avalanche C-Chain.
        """
        return {
            "method": "submitGovernanceProof",
            "params": {
                "proofHash": "0x" + self.proof_hash,
                "inputHash": "0x" + self.input_hash,
                "verdict": self.verdict == "PASS",
                "timestamp": int(datetime.fromisoformat(self.timestamp).timestamp()),
                "ruleCount": len(self.rule_ids),
                "score": int(self.score * 10000),  # 4 decimales, uint16
            },
            "abi_types": [
                "bytes32",   # proofHash
                "bytes32",   # inputHash
                "bool",      # verdict
                "uint256",   # timestamp
                "uint16",    # ruleCount
                "uint16",    # score (basis points)
            ],
            "chain_id": 43114,  # Avalanche C-Chain
        }


# ─────────────────────────────────────────────────────────────────────
# GovernanceProofGenerator
# ─────────────────────────────────────────────────────────────────────

class GovernanceProofGenerator:
    """Genera y verifica proofs criptográficos de governance.

    Args:
        log_path: Ruta al archivo JSONL para persistir proofs.
    """

    def __init__(self, log_path: str = ""):
        self._log_path = log_path or PROOFS_LOG_PATH
        self._proofs: list[GovernanceProof] = []

    @property
    def proofs(self) -> list[GovernanceProof]:
        return list(self._proofs)

    def generate_proof(
        self,
        violations: list[str],
        warnings: list[str],
        score: float,
        rule_ids: list[str] | None = None,
        timestamp: str | None = None,
    ) -> GovernanceProof:
        """Genera un GovernanceProof a partir de un resultado de governance.

        Args:
            violations: Lista de violaciones hard.
            warnings: Lista de warnings soft.
            score: Score de governance (0.0 a 1.0).
            rule_ids: IDs de reglas evaluadas. Si None, se extraen de violations/warnings.
            timestamp: ISO 8601 timestamp. Si None, se usa el momento actual.

        Returns:
            GovernanceProof con hash determinístico verificable.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        if rule_ids is None:
            rule_ids = self._extract_rule_ids(violations, warnings)

        # Input hash — solo del contenido semántico
        input_hash = _hash_governance_input(
            violations, warnings, score, timestamp, rule_ids
        )

        # Verdict
        verdict = "FAIL" if violations else "PASS"

        # Proof hash — incluye input_hash + verdict (compromiso completo)
        proof_data = _canonical_json({
            "input_hash": input_hash,
            "verdict": verdict,
            "timestamp": timestamp,
        })
        proof_hash = _keccak256(proof_data.encode("utf-8"))

        proof = GovernanceProof(
            proof_hash=proof_hash,
            input_hash=input_hash,
            timestamp=timestamp,
            verdict=verdict,
            rule_ids=sorted(rule_ids),
            violations_count=len(violations),
            warnings_count=len(warnings),
            score=score,
        )

        self._proofs.append(proof)
        self._log_proof(proof)

        logger.info(
            f"GovernanceProof generated: verdict={verdict} "
            f"hash={proof_hash[:16]}... rules={len(rule_ids)}"
        )

        return proof

    def generate_proof_from_result(
        self,
        result: "GovernanceResult",
        rule_ids: list[str] | None = None,
        timestamp: str | None = None,
    ) -> GovernanceProof:
        """Genera proof directamente desde un GovernanceResult.

        Args:
            result: GovernanceResult de core.governance.
            rule_ids: IDs de reglas evaluadas (opcional).
            timestamp: ISO timestamp (opcional).

        Returns:
            GovernanceProof.
        """
        return self.generate_proof(
            violations=result.violations,
            warnings=result.warnings,
            score=result.score,
            rule_ids=rule_ids,
            timestamp=timestamp,
        )

    def verify_proof(
        self,
        proof: GovernanceProof,
        violations: list[str],
        warnings: list[str],
        score: float,
    ) -> bool:
        """Verifica un proof re-generando el hash y comparando.

        Args:
            proof: El GovernanceProof a verificar.
            violations: Violations originales.
            warnings: Warnings originales.
            score: Score original.

        Returns:
            True si el proof es válido (hashes coinciden).
        """
        # Re-generar input_hash
        input_hash = _hash_governance_input(
            violations, warnings, score, proof.timestamp, proof.rule_ids
        )

        if input_hash != proof.input_hash:
            return False

        # Re-generar proof_hash
        proof_data = _canonical_json({
            "input_hash": input_hash,
            "verdict": proof.verdict,
            "timestamp": proof.timestamp,
        })
        expected_proof_hash = _keccak256(proof_data.encode("utf-8"))

        return expected_proof_hash == proof.proof_hash

    def verify_proof_from_result(
        self,
        proof: GovernanceProof,
        result: "GovernanceResult",
    ) -> bool:
        """Verifica un proof contra un GovernanceResult."""
        return self.verify_proof(
            proof, result.violations, result.warnings, result.score
        )

    def _extract_rule_ids(self, violations: list[str],
                          warnings: list[str]) -> list[str]:
        """Extrae rule IDs de los mensajes de violations y warnings.

        Los mensajes tienen formato: '[RULE_ID] description'
        """
        ids = []
        for msg in violations + warnings:
            if msg.startswith("[") and "]" in msg:
                rule_id = msg[1:msg.index("]")]
                ids.append(rule_id)
        return ids

    def _log_proof(self, proof: GovernanceProof):
        """Persiste proof en JSONL."""
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        entry = proof.to_dict()
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log proof: {e}")
