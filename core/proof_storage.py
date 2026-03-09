"""
Storage for Z3 proof transcripts.

IPFS is OPTIONAL. Default is local storage in dof/storage/proofs/.
Never fail because of IPFS — local storage always works.

Modes:
- "local": Save in dof/storage/proofs/{hash_hex}.proof.json
- "ipfs": Upload to IPFS via Pinata (requires api_key)
- "both": Local + IPFS (redundancy)
"""

from __future__ import annotations

import json
import os
import logging
from typing import Optional

from core.proof_hash import ProofSerializer

logger = logging.getLogger("core.proof_storage")

_DEFAULT_PROOF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dof", "storage", "proofs",
)


class ProofStorage:
    """Store and retrieve Z3 proof transcripts."""

    def __init__(
        self,
        mode: str = "local",
        proof_dir: str = _DEFAULT_PROOF_DIR,
        ipfs_gateway: str = "",
        ipfs_key: str = "",
    ):
        """Initialize proof storage.

        Args:
            mode: "local", "ipfs", or "both".
            proof_dir: Directory for local proof files.
            ipfs_gateway: IPFS gateway URL (for "ipfs" or "both" mode).
            ipfs_key: IPFS API key (for "ipfs" or "both" mode).
        """
        self.mode = mode
        self.proof_dir = proof_dir
        self.ipfs_gateway = ipfs_gateway
        self.ipfs_key = ipfs_key

    def store_proof(self, transcript: str) -> str:
        """Store a proof transcript.

        Returns:
            Storage reference (local path or IPFS CID).
        """
        proof_hash = ProofSerializer.hash_proof(transcript)
        hash_hex = proof_hash.hex()

        ref = ""

        # Local storage
        if self.mode in ("local", "both"):
            ref = self._store_local(hash_hex, transcript)

        # IPFS storage (optional)
        if self.mode in ("ipfs", "both"):
            ipfs_ref = self._store_ipfs(hash_hex, transcript)
            if ipfs_ref:
                ref = ipfs_ref  # Prefer IPFS ref if available
            elif self.mode == "ipfs":
                # Fallback to local if IPFS-only mode fails
                logger.warning("IPFS unavailable, falling back to local")
                ref = self._store_local(hash_hex, transcript)

        return ref

    def retrieve_proof(self, ref: str) -> str:
        """Retrieve a proof transcript by reference.

        Args:
            ref: Storage reference (local path or IPFS CID).

        Returns:
            Proof transcript string.
        """
        # Try local first
        if os.path.exists(ref):
            return self._retrieve_local(ref)

        # Try as hash_hex filename
        local_path = os.path.join(self.proof_dir, f"{ref}.proof.json")
        if os.path.exists(local_path):
            return self._retrieve_local(local_path)

        # Try IPFS
        if ref.startswith("Qm") or ref.startswith("bafy"):
            return self._retrieve_ipfs(ref)

        raise FileNotFoundError(f"Proof not found: {ref}")

    def list_proofs(self) -> list[str]:
        """List all locally stored proof references.

        Returns:
            List of proof hash hex strings.
        """
        if not os.path.exists(self.proof_dir):
            return []
        proofs = []
        for f in sorted(os.listdir(self.proof_dir)):
            if f.endswith(".proof.json"):
                proofs.append(f.replace(".proof.json", ""))
        return proofs

    def _store_local(self, hash_hex: str, transcript: str) -> str:
        """Store proof transcript locally."""
        os.makedirs(self.proof_dir, exist_ok=True)
        filepath = os.path.join(self.proof_dir, f"{hash_hex}.proof.json")
        payload = {
            "hash": hash_hex,
            "transcript": transcript,
        }
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Proof stored locally: {filepath}")
        return filepath

    def _retrieve_local(self, path: str) -> str:
        """Retrieve proof from local file."""
        with open(path) as f:
            data = json.load(f)
        return data.get("transcript", "")

    def _store_ipfs(self, hash_hex: str, transcript: str) -> Optional[str]:
        """Store proof on IPFS via Pinata. Returns CID or None."""
        if not self.ipfs_gateway or not self.ipfs_key:
            logger.debug("IPFS not configured, skipping")
            return None
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.ipfs_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "pinataContent": {
                    "hash": hash_hex,
                    "transcript": transcript,
                },
                "pinataMetadata": {
                    "name": f"dof-proof-{hash_hex[:16]}",
                },
            }
            resp = requests.post(
                f"{self.ipfs_gateway}/pinning/pinJSONToIPFS",
                json=payload,
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                cid = resp.json().get("IpfsHash", "")
                logger.info(f"Proof stored on IPFS: {cid}")
                return cid
            logger.warning(f"IPFS upload failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"IPFS upload failed: {e}")
        return None

    def _retrieve_ipfs(self, cid: str) -> str:
        """Retrieve proof from IPFS."""
        try:
            import requests
            gateway = self.ipfs_gateway or "https://gateway.pinata.cloud"
            resp = requests.get(f"{gateway}/ipfs/{cid}", timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("transcript", "")
        except Exception as e:
            logger.warning(f"IPFS retrieval failed: {e}")
        raise FileNotFoundError(f"Cannot retrieve from IPFS: {cid}")
