"""
DOF-MESH Evolution Attestation
Inmortaliza cada generación ganadora del Evolution Engine on-chain.

Analogía: cada vez que el sistema inmune crea un anticuerpo nuevo,
lo graba en piedra para siempre.
"""
import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass

logger = logging.getLogger("dof.evolution.attestation")

# Importar DOFChainAdapter en el namespace del módulo para que los mocks funcionen
try:
    from core.chain_adapter import DOFChainAdapter
except ImportError:
    DOFChainAdapter = None  # type: ignore[assignment,misc]

# Agent ID del Evolution Engine (no es un ERC-8004 user, es el sistema)
_EVOLUTION_AGENT_ID = 9999


@dataclass
class GenerationAttestation:
    """Registro inmutable de una generación evolutiva ganadora."""
    generation: int
    asr_before: float
    asr_after: float
    improvement_pp: float        # puntos porcentuales de mejora
    genes_mutated: int
    genes_crossed: int
    survivors: int
    gene_pool_hash: str          # SHA-256 del gene_pool.jsonl
    timestamp: str
    session: str = "auto"


def compute_gene_pool_hash(gene_pool_path: str) -> str:
    """SHA-256 del gene_pool.jsonl — fingerprint inmutable del genoma."""
    try:
        with open(gene_pool_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return "unknown"


def attest_generation(
    attestation: GenerationAttestation,
    chain: str = "avalanche",
) -> dict:
    """
    Publica la attestation de una generación ganadora on-chain.
    Usa DOFChainAdapter.publish_attestation().

    dry_run automático si DOF_PRIVATE_KEY no está en entorno.
    La attestation falla sin romper el loop evolutivo (retorna error en dict).

    Retorna: {success, tx_hash, chain, generation, error}
    """
    if DOFChainAdapter is None:
        return {
            "success": False,
            "tx_hash": None,
            "chain": chain,
            "generation": attestation.generation,
            "error": "DOFChainAdapter no disponible (import failed)",
        }

    try:
        dry_run = not bool(os.environ.get("DOF_PRIVATE_KEY"))
        adapter = DOFChainAdapter.from_chain_name(chain, dry_run=dry_run)

        # Proof hash = SHA-256 del payload serializado
        payload = {
            "type": "EVOLUTION_GENERATION",
            "version": "1.0",
            "generation": attestation.generation,
            "asr_before": attestation.asr_before,
            "asr_after": attestation.asr_after,
            "improvement_pp": attestation.improvement_pp,
            "genes_mutated": attestation.genes_mutated,
            "gene_pool_hash": attestation.gene_pool_hash,
            "timestamp": attestation.timestamp,
        }
        proof_hash = "0x" + hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        metadata = json.dumps({
            "gen": attestation.generation,
            "asr_delta": attestation.improvement_pp,
            "pool_hash": attestation.gene_pool_hash[:16],
        })

        result = adapter.publish_attestation(
            proof_hash=proof_hash,
            agent_id=_EVOLUTION_AGENT_ID,
            metadata=metadata,
        )

        tx_hash = result.get("tx_hash")
        status = result.get("status", "unknown")
        success = status in ("success", "dry_run")

        if success:
            logger.info(
                f"Attestation gen-{attestation.generation} on-chain "
                f"[{chain}] tx={str(tx_hash)[:20]}... "
                f"({'dry_run' if dry_run else 'LIVE'})"
            )
        else:
            logger.warning(f"Attestation gen-{attestation.generation} status={status}")

        return {
            "success": success,
            "tx_hash": tx_hash,
            "chain": chain,
            "generation": attestation.generation,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Attestation gen-{attestation.generation} error: {e}")
        return {
            "success": False,
            "tx_hash": None,
            "chain": chain,
            "generation": attestation.generation,
            "error": str(e),
        }


def attest_multichain(
    attestation: GenerationAttestation,
    chains: list = None,
) -> list:
    """
    Publica en múltiples chains en secuencia.
    Default: solo Avalanche (mainnet más rápido para Evolution Engine).
    """
    if chains is None:
        chains = ["avalanche"]
    return [attest_generation(attestation, chain) for chain in chains]
