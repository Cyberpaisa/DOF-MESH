"""
Avalanche Bridge — Real on-chain attestation publishing via web3.py.

Connects DOF governance attestations to the DOFValidationRegistry smart contract
deployed on Avalanche C-Chain. Converts BLAKE3/SHA256 hashes to bytes32 and
sends signed transactions.

IMPORTANT: Requires AVALANCHE_RPC_URL, AVALANCHE_PRIVATE_KEY, and
           VALIDATION_REGISTRY_ADDRESS in environment.
           Graceful offline fallback if any are missing.

Usage:
    from core.avalanche_bridge import AvalancheBridge

    bridge = AvalancheBridge()
    if bridge.is_online:
        result = bridge.send_attestation(cert_hash, agent_id, compliant=True)
        print(result)  # {"tx_hash": "0x...", "block_number": 123, ...}
"""

import os
import json
import logging
from datetime import datetime, timezone

# Load .env if available (same pattern as other core modules)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("core.avalanche_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# web3 is optional — graceful fallback
try:
    from web3 import Web3
    # POA middleware name differs across web3 versions
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware
    except ImportError:
        from web3.middleware import geth_poa_middleware as _poa_middleware
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    _poa_middleware = None

# Minimal ABI — only the functions we use from DOFValidationRegistry
REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "certificateHash", "type": "bytes32"},
            {"name": "agentId", "type": "bytes32"},
            {"name": "compliant", "type": "bool"},
        ],
        "name": "registerAttestation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "certHashes", "type": "bytes32[]"},
            {"name": "agentIds", "type": "bytes32[]"},
            {"name": "compliants", "type": "bool[]"},
        ],
        "name": "registerBatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "certificateHash", "type": "bytes32"}],
        "name": "revokeAttestation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "certificateHash", "type": "bytes32"}],
        "name": "isCompliant",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "certificateHash", "type": "bytes32"}],
        "name": "getAttestation",
        "outputs": [
            {"name": "agentId", "type": "bytes32"},
            {"name": "compliant", "type": "bool"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalAttestations",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _hex_to_bytes32(hex_str: str) -> bytes:
    """Convert a hex string (BLAKE3/SHA256 hash) to bytes32.

    Pads with zeros on the right if shorter than 32 bytes.
    Truncates to 32 bytes if longer.
    """
    clean = hex_str.replace("0x", "")
    raw = bytes.fromhex(clean)
    if len(raw) >= 32:
        return raw[:32]
    return raw + b"\x00" * (32 - len(raw))


class AvalancheBridge:
    """Real on-chain bridge to DOFValidationRegistry on Avalanche C-Chain.

    Reads configuration from environment:
        AVALANCHE_RPC_URL: Avalanche C-Chain RPC endpoint
        AVALANCHE_PRIVATE_KEY: Wallet private key for signing
        VALIDATION_REGISTRY_ADDRESS: Deployed contract address

    If any are missing, operates in offline mode (no transactions sent).
    """

    def __init__(self):
        self._rpc_url = os.environ.get("AVALANCHE_RPC_URL", "")
        self._private_key = os.environ.get("AVALANCHE_PRIVATE_KEY", "")
        self._contract_address = os.environ.get("VALIDATION_REGISTRY_ADDRESS", "")
        self._w3 = None
        self._contract = None
        self._account = None
        self._offline = True

        if not HAS_WEB3:
            logger.info("AvalancheBridge offline — web3 not installed")
            return

        if not self._rpc_url:
            logger.info("AvalancheBridge offline — AVALANCHE_RPC_URL not set")
            return
        if not self._private_key:
            logger.info("AvalancheBridge offline — AVALANCHE_PRIVATE_KEY not set")
            return
        if not self._contract_address:
            logger.info("AvalancheBridge offline — VALIDATION_REGISTRY_ADDRESS not set")
            return

        try:
            self._w3 = Web3(Web3.HTTPProvider(self._rpc_url))
            # Avalanche C-Chain is a POA chain — inject middleware
            self._w3.middleware_onion.inject(_poa_middleware, layer=0)

            if not self._w3.is_connected():
                logger.warning("AvalancheBridge offline — cannot connect to RPC")
                return

            self._account = self._w3.eth.account.from_key(self._private_key)
            self._contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self._contract_address),
                abi=REGISTRY_ABI,
            )
            self._offline = False
            logger.info(
                f"AvalancheBridge connected — "
                f"wallet={self._account.address}, "
                f"contract={self._contract_address}"
            )
        except Exception as e:
            logger.warning(f"AvalancheBridge offline — init error: {e}")

    @property
    def is_online(self) -> bool:
        return not self._offline

    def send_attestation(self, certificate_hash: str, agent_id: str,
                         compliant: bool) -> dict:
        """Send a single attestation to the on-chain registry.

        Args:
            certificate_hash: BLAKE3/SHA256 hash of the attestation certificate.
            agent_id: BLAKE3 hash of the agent identity (from OAGS).
            compliant: Whether GCR == 1.0.

        Returns:
            Dict with tx_hash, block_number, gas_used, status.
        """
        if self._offline:
            logger.warning("Cannot send attestation in offline mode")
            return {"status": "offline", "error": "Bridge not connected"}

        cert_bytes32 = _hex_to_bytes32(certificate_hash)
        agent_bytes32 = _hex_to_bytes32(agent_id)

        try:
            # Build transaction
            tx = self._contract.functions.registerAttestation(
                cert_bytes32, agent_bytes32, compliant
            ).build_transaction({
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "gas": 0,  # Will be estimated
                "gasPrice": int(self._w3.eth.gas_price * 1.25),  # 25% above current
                "chainId": 43114,
            })

            # Estimate gas
            gas_estimate = self._w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.2)  # 20% buffer

            # Sign
            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)

            # Send
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            logger.info(f"Attestation tx sent: {tx_hash.hex()}")

            # Wait for confirmation (timeout 60s)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            result = {
                "status": "confirmed" if receipt["status"] == 1 else "failed",
                "tx_hash": tx_hash.hex(),
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "certificate_hash": certificate_hash[:16] + "...",
                "agent_id": agent_id[:16] + "...",
                "compliant": compliant,
            }

            self._log_tx(result)
            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "certificate_hash": certificate_hash[:16] + "...",
            }
            self._log_tx(error_result)
            logger.error(f"Attestation tx failed: {e}")
            return error_result

    def send_batch(self, attestations: list[dict]) -> dict:
        """Send a batch of attestations in a single transaction.

        Args:
            attestations: List of dicts with keys: certificate_hash, agent_id, compliant.

        Returns:
            Dict with tx_hash, block_number, gas_used, count, status.
        """
        if self._offline:
            return {"status": "offline", "error": "Bridge not connected"}

        if not attestations:
            return {"status": "error", "error": "No attestations to send"}

        cert_hashes = [_hex_to_bytes32(a["certificate_hash"]) for a in attestations]
        agent_ids = [_hex_to_bytes32(a["agent_id"]) for a in attestations]
        compliants = [bool(a.get("compliant", False)) for a in attestations]

        try:
            tx = self._contract.functions.registerBatch(
                cert_hashes, agent_ids, compliants
            ).build_transaction({
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "gas": 0,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": 43114,
            })

            gas_estimate = self._w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.2)

            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            logger.info(f"Batch tx sent ({len(attestations)} attestations): {tx_hash.hex()}")

            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            result = {
                "status": "confirmed" if receipt["status"] == 1 else "failed",
                "tx_hash": tx_hash.hex(),
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "count": len(attestations),
            }

            self._log_tx(result)
            return result

        except Exception as e:
            error_result = {"status": "error", "error": str(e), "count": len(attestations)}
            self._log_tx(error_result)
            logger.error(f"Batch tx failed: {e}")
            return error_result

    def verify_on_chain(self, certificate_hash: str) -> dict:
        """Read attestation from on-chain registry (view call, no gas).

        Args:
            certificate_hash: BLAKE3/SHA256 hash of the attestation certificate.

        Returns:
            Dict with agent_id, compliant, timestamp, submitter — or error.
        """
        if self._offline:
            return {"status": "offline", "error": "Bridge not connected"}

        cert_bytes32 = _hex_to_bytes32(certificate_hash)

        try:
            agent_id, compliant, timestamp, submitter = (
                self._contract.functions.getAttestation(cert_bytes32).call()
            )

            if timestamp == 0:
                return {"status": "not_found", "certificate_hash": certificate_hash[:16] + "..."}

            return {
                "status": "found",
                "agent_id": "0x" + agent_id.hex(),
                "compliant": compliant,
                "timestamp": timestamp,
                "submitter": submitter,
            }
        except Exception as e:
            logger.error(f"On-chain verify failed: {e}")
            return {"status": "error", "error": str(e)}

    def is_compliant_on_chain(self, certificate_hash: str) -> bool | None:
        """Check if attestation is compliant on-chain (view call).

        Returns True/False, or None if offline or not found.
        """
        if self._offline:
            return None

        cert_bytes32 = _hex_to_bytes32(certificate_hash)
        try:
            return self._contract.functions.isCompliant(cert_bytes32).call()
        except Exception as e:
            logger.error(f"isCompliant call failed: {e}")
            return None

    def total_attestations(self) -> int | None:
        """Get total number of on-chain attestations (view call).

        Returns count or None if offline.
        """
        if self._offline:
            return None

        try:
            return self._contract.functions.totalAttestations().call()
        except Exception as e:
            logger.error(f"totalAttestations call failed: {e}")
            return None

    def get_balance(self) -> float | None:
        """Get wallet AVAX balance. Returns None if offline."""
        if self._offline or self._account is None:
            return None

        try:
            balance_wei = self._w3.eth.get_balance(self._account.address)
            return float(Web3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"get_balance failed: {e}")
            return None

    def _log_tx(self, data: dict):
        """Log transaction event to logs/avalanche_bridge.jsonl."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "avalanche_bridge.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log tx: {e}")
