"""
ZK Batch Prover — Batch aggregation de governance proofs con Merkle tree.

Acumula N GovernanceProofs y genera un Merkle root para publicación
on-chain en una sola transacción. Reutiliza core/merkle_tree.py.

Usage:
    from core.zk_batch_prover import GovernanceBatchProver

    prover = GovernanceBatchProver()
    prover.add_proof(proof1)
    prover.add_proof(proof2)
    root = prover.get_merkle_root()
    assert prover.verify_inclusion(proof1, root)
    batch = prover.export_batch("batch-001")
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from core.merkle_tree import MerkleTree
from core.zk_governance_proof import GovernanceProof

logger = logging.getLogger("core.zk_batch_prover")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH_LOG_DIR = os.path.join(BASE_DIR, "logs", "proofs")
BATCH_LOG_PATH = os.path.join(BATCH_LOG_DIR, "governance_batches.jsonl")


# ─────────────────────────────────────────────────────────────────────
# BatchExport dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class BatchExport:
    """Resultado de exportar un batch de proofs para on-chain."""
    batch_id: str
    merkle_root: str
    proof_count: int
    proof_hashes: list[str]
    verdicts: dict  # {"PASS": N, "FAIL": M}
    timestamp: str
    inclusion_proofs: dict  # proof_hash -> merkle proof path
    chain_payload: dict  # payload listo para web3.py

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────
# GovernanceBatchProver
# ─────────────────────────────────────────────────────────────────────

class GovernanceBatchProver:
    """Acumula governance proofs y genera Merkle root para batch attestation.

    Args:
        log_path: Ruta al JSONL para persistir batches.
    """

    def __init__(self, log_path: str = ""):
        self._proofs: list[GovernanceProof] = []
        self._tree: Optional[MerkleTree] = None
        self._dirty = True  # tree needs rebuild
        self._log_path = log_path or BATCH_LOG_PATH

    @property
    def proof_count(self) -> int:
        return len(self._proofs)

    @property
    def proofs(self) -> list[GovernanceProof]:
        return list(self._proofs)

    def add_proof(self, proof: GovernanceProof) -> None:
        """Agrega un proof al batch pendiente.

        Args:
            proof: GovernanceProof a agregar.
        """
        self._proofs.append(proof)
        self._dirty = True
        logger.debug(f"Proof added to batch: {proof.proof_hash[:16]}...")

    def _rebuild_tree(self) -> None:
        """Reconstruye el Merkle tree si hay cambios."""
        if not self._dirty:
            return
        if not self._proofs:
            self._tree = None
            self._dirty = False
            return
        leaves = [p.proof_hash for p in self._proofs]
        self._tree = MerkleTree(leaves)
        self._dirty = False

    def get_merkle_root(self) -> str:
        """Retorna el Merkle root del batch actual.

        Returns:
            Hex string del Merkle root, o cadena vacía si no hay proofs.
        """
        self._rebuild_tree()
        if self._tree is None:
            return ""
        return self._tree.root

    def get_inclusion_proof(self, proof: GovernanceProof) -> list[tuple[str, str]]:
        """Obtiene el Merkle inclusion proof para un GovernanceProof específico.

        Args:
            proof: GovernanceProof cuya inclusión se quiere probar.

        Returns:
            Lista de (sibling_hash, direction) para verificación.

        Raises:
            ValueError: Si el proof no está en el batch.
        """
        self._rebuild_tree()
        if self._tree is None:
            raise ValueError("No proofs in batch")

        # Encontrar el índice del proof
        hashes = [p.proof_hash for p in self._proofs]
        try:
            idx = hashes.index(proof.proof_hash)
        except ValueError:
            raise ValueError(
                f"Proof {proof.proof_hash[:16]}... not found in batch"
            )

        return self._tree.get_proof(idx)

    def verify_inclusion(self, proof: GovernanceProof,
                         merkle_root: str | None = None) -> bool:
        """Verifica que un proof está incluido en el Merkle tree.

        Args:
            proof: GovernanceProof a verificar.
            merkle_root: Root contra el cual verificar. Si None, usa el actual.

        Returns:
            True si el proof está incluido y el Merkle path es válido.
        """
        self._rebuild_tree()
        if self._tree is None:
            return False

        root = merkle_root or self._tree.root

        try:
            inclusion_proof = self.get_inclusion_proof(proof)
        except ValueError:
            return False

        # El leaf en el MerkleTree es el proof_hash procesado por _ensure_hex.
        # Como proof_hash ya es hex de 64 chars, se usa directamente.
        leaf = self._tree.leaves[
            [p.proof_hash for p in self._proofs].index(proof.proof_hash)
        ]
        return MerkleTree.verify_proof(leaf, inclusion_proof, root)

    def export_batch(self, batch_id: str) -> BatchExport:
        """Exporta el batch actual como payload para on-chain attestation.

        Args:
            batch_id: Identificador único del batch.

        Returns:
            BatchExport con Merkle root, proofs, y chain payload.
        """
        self._rebuild_tree()
        merkle_root = self.get_merkle_root()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Conteo de verdicts
        verdicts = {"PASS": 0, "FAIL": 0}
        for p in self._proofs:
            verdicts[p.verdict] = verdicts.get(p.verdict, 0) + 1

        # Inclusion proofs para cada proof_hash
        inclusion_proofs = {}
        for i, p in enumerate(self._proofs):
            if self._tree is not None:
                try:
                    merkle_path = self._tree.get_proof(i)
                    inclusion_proofs[p.proof_hash] = [
                        {"sibling": s, "direction": d} for s, d in merkle_path
                    ]
                except IndexError:
                    inclusion_proofs[p.proof_hash] = []

        # Chain payload para web3.py
        chain_payload = {
            "method": "submitBatchAttestation",
            "params": {
                "batchId": batch_id,
                "merkleRoot": "0x" + merkle_root if merkle_root else "0x",
                "proofCount": len(self._proofs),
                "passCount": verdicts["PASS"],
                "failCount": verdicts["FAIL"],
                "timestamp": int(
                    datetime.fromisoformat(timestamp).timestamp()
                ),
            },
            "abi_types": [
                "string",    # batchId
                "bytes32",   # merkleRoot
                "uint16",    # proofCount
                "uint16",    # passCount
                "uint16",    # failCount
                "uint256",   # timestamp
            ],
            "chain_id": 43114,
        }

        export = BatchExport(
            batch_id=batch_id,
            merkle_root=merkle_root,
            proof_count=len(self._proofs),
            proof_hashes=[p.proof_hash for p in self._proofs],
            verdicts=verdicts,
            timestamp=timestamp,
            inclusion_proofs=inclusion_proofs,
            chain_payload=chain_payload,
        )

        self._log_batch(export)

        logger.info(
            f"Batch {batch_id} exported: {len(self._proofs)} proofs, "
            f"root={merkle_root[:16]}..."
        )

        return export

    def reset(self) -> None:
        """Limpia el batch actual."""
        self._proofs.clear()
        self._tree = None
        self._dirty = True

    def _log_batch(self, export: BatchExport):
        """Persiste batch en JSONL."""
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        entry = {
            "timestamp": export.timestamp,
            "batch_id": export.batch_id,
            "merkle_root": export.merkle_root,
            "proof_count": export.proof_count,
            "proof_hashes": export.proof_hashes,
            "verdicts": export.verdicts,
        }
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log batch: {e}")
