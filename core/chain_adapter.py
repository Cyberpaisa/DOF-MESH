"""
core/chain_adapter.py
DOF Multichain Adapter — plug-and-play para cualquier EVM.
Version: 0.4.0

Uso:
    adapter = DOFChainAdapter.from_chain_name("conflux_testnet")
    result = adapter.publish_attestation(proof_hash, agent_id, metadata)
    valid = adapter.verify_proof(proof_hash)
"""

import json
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

# ABI de DOFProofRegistry — Solo las rutinas que usa este SDK
DOF_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "trustScore", "type": "uint256"},
            {"name": "z3ProofHash", "type": "bytes32"},
            {"name": "storageRef", "type": "string"},
            {"name": "invariantsCount", "type": "uint8"}
        ],
        "name": "registerProof",
        "outputs": [{"name": "proofId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getProofCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "proofId", "type": "uint256"}],
        "name": "getProof",
        "outputs": [
            {
                "components": [
                    {"name": "agentId", "type": "uint256"},
                    {"name": "trustScore", "type": "uint256"},
                    {"name": "z3ProofHash", "type": "bytes32"},
                    {"name": "storageRef", "type": "string"},
                    {"name": "invariantsCount", "type": "uint8"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "verified", "type": "bool"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class ChainConfig:
    """Configuración de una chain cargada desde chains_config.json."""

    def __init__(self, chain_key: str, data: dict):
        self.chain_key = chain_key
        self.chain_id = data["chain_id"]
        self.name = data["name"]
        self.rpc_url = data["rpc_url"]
        self.rpc_fallback = data.get("rpc_fallback")
        self.explorer = data.get("explorer", "")
        self.contract_address = data.get("contract_address")
        self.status = data["status"]
        self.gas_multiplier = data.get("gas_multiplier", 1.0)
        self.native_token = data.get("native_token", "ETH")
        self.notes = data.get("notes", "")


class DOFChainAdapter:
    """
    Adapter multichain para DOFProofRegistry.
    Compatible con cualquier EVM — solo cambia chain_id + rpc_url + contract_address.
    
    El Python SDK (Z3, GenericAdapter, TrustGateway) es 100% off-chain
    y nunca cambia. Solo este adapter es chain-specific.
    """

    CHAINS_CONFIG_PATH = Path(__file__).parent / "chains_config.json"

    def __init__(self, config: ChainConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self._web3 = None
        self._contract = None
        self._initialized = False

    @classmethod
    def load_chains_config(cls) -> dict:
        """Carga el registro de chains desde chains_config.json."""
        with open(cls.CHAINS_CONFIG_PATH) as f:
            return json.load(f)

    @classmethod
    def from_chain_name(cls, chain_name: str, dry_run: bool = False) -> "DOFChainAdapter":
        """
        Crea un adapter por nombre de chain.
        
        Ejemplo:
            adapter = DOFChainAdapter.from_chain_name("conflux_testnet")
            adapter = DOFChainAdapter.from_chain_name("base")
        """
        config_data = cls.load_chains_config()
        chains = config_data.get("chains", {})
        if chain_name not in chains:
            available = list(chains.keys())
            raise ValueError(
                f"Chain '{chain_name}' no encontrada. "
                f"Disponibles: {available}"
            )
        chain_config = ChainConfig(chain_name, chains[chain_name])
        return cls(chain_config, dry_run=dry_run)

    @classmethod
    def from_chain_id(cls, chain_id: int, dry_run: bool = False) -> "DOFChainAdapter":
        """Crea un adapter por chain_id numérico."""
        config_data = cls.load_chains_config()
        chains = config_data.get("chains", {})
        for key, data in chains.items():
            if data["chain_id"] == chain_id:
                return cls(ChainConfig(key, data), dry_run=dry_run)
        raise ValueError(f"chain_id {chain_id} no encontrado en chains_config.json")

    def _init_web3(self):
        """Inicializa conexión web3. Lazy — solo cuando se necesita."""
        if self._initialized:
            return

        if self.dry_run:
            self._web3 = MagicMock()
            self._web3.is_connected.return_value = True
            self._web3.eth.chain_id = self.config.chain_id
            self._contract = MagicMock()
            self._initialized = True
            logger.info(f"[DRY RUN] DOFChainAdapter inicializado para {self.config.name}")
            return

        try:
            from web3 import Web3
            self._web3 = Web3(Web3.HTTPProvider(self.config.rpc_url))

            if not self._web3.is_connected():
                if self.config.rpc_fallback:
                    logger.warning(
                        f"RPC principal falló, intentando fallback: {self.config.rpc_fallback}"
                    )
                    self._web3 = Web3(Web3.HTTPProvider(self.config.rpc_fallback))
                    if not self._web3.is_connected():
                        raise ConnectionError(
                            f"No se pudo conectar a {self.config.name} "
                            f"(ni RPC principal ni fallback)"
                        )
                else:
                    raise ConnectionError(
                        f"No se pudo conectar a {self.config.name}: {self.config.rpc_url}"
                    )

            actual_chain_id = self._web3.eth.chain_id
            if actual_chain_id != self.config.chain_id:
                raise ValueError(
                    f"chain_id incorrecto: esperado {self.config.chain_id}, "
                    f"recibido {actual_chain_id}"
                )

            if self.config.contract_address:
                self._contract = self._web3.eth.contract(
                    address=self._web3.to_checksum_address(self.config.contract_address),
                    abi=DOF_REGISTRY_ABI
                )

            self._initialized = True
            logger.info(
                f"DOFChainAdapter conectado a {self.config.name} "
                f"(chain_id={self.config.chain_id})"
            )

        except ImportError:
            raise ImportError(
                "web3 no está instalado. Ejecuta: pip install web3 --break-system-packages"
            )

    def is_ready(self) -> bool:
        """True si hay contrato deployado y conexión activa."""
        return (
            self.config.contract_address is not None
            and self.config.status in ("mainnet", "testnet")
        )

    def publish_attestation(
        self,
        proof_hash: str,
        agent_id: int,
        metadata: str = "",
        private_key: Optional[str] = None
    ) -> dict:
        """
        Publica una attestation on-chain en la chain configurada.
        
        Args:
            proof_hash: keccak256 hash del proof (hex string, 0x...)
            agent_id: token_id del agente (ERC-8004 compatible)
            metadata: string adicional referenciado (IPFS, url, base64)
            private_key: clave privada para firmar (o usa env DOF_PRIVATE_KEY)
        
        Returns:
            dict con tx_hash, chain_id, chain_name, explorer_url, status
        """
        self._init_web3()

        if not self.is_ready():
            return {
                "status": "skipped",
                "reason": f"No hay contrato deployado en {self.config.name}",
                "chain_id": self.config.chain_id,
                "chain_name": self.config.name,
                "deploy_status": self.config.status
            }

        if self.dry_run:
            fake_hash = "0x" + hashlib.sha256(
                f"{proof_hash}{agent_id}{metadata}".encode()
            ).hexdigest()
            return {
                "status": "dry_run",
                "tx_hash": fake_hash,
                "chain_id": self.config.chain_id,
                "chain_name": self.config.name,
                "proof_hash": proof_hash,
                "agent_id": agent_id
            }

        key = private_key or os.environ.get("DOF_PRIVATE_KEY")
        if not key:
            raise ValueError(
                "Se requiere private_key o variable de entorno DOF_PRIVATE_KEY"
            )

        proof_bytes = bytes.fromhex(proof_hash.replace("0x", "").ljust(64, "0"))
        # Default defaults para campos requeridos por el ABI real de DOFProofRegistry
        trust_score = 1000000000000000000 # 1.0 en WAD
        invariants = 8

        account = self._web3.eth.account.from_key(key)
        gas_price = int(self._web3.eth.gas_price * self.config.gas_multiplier)

        tx = self._contract.functions.registerProof(
            agent_id,
            trust_score,
            proof_bytes,
            metadata,
            invariants
        ).build_transaction({
            "from": account.address,
            "nonce": self._web3.eth.get_transaction_count(account.address),
            "gasPrice": gas_price
        })

        signed = self._web3.eth.account.sign_transaction(tx, key)
        tx_hash = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        explorer_url = (
            f"{self.config.explorer}/tx/{tx_hash.hex()}"
            if self.config.explorer else ""
        )

        return {
            "status": "confirmed" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "chain_id": self.config.chain_id,
            "chain_name": self.config.name,
            "explorer_url": explorer_url,
            "proof_hash": proof_hash,
            "agent_id": agent_id,
            "gas_used": receipt.gasUsed
        }

    def verify_proof(self, proof_hash: str) -> bool:
        """
        Verifica si un proof hash existe en el registry on-chain.
        
        Returns:
            True si existe, False si no. False también si no hay contrato.
        """
        self._init_web3()

        if not self.is_ready():
            logger.warning(
                f"verify_proof: no hay contrato en {self.config.name}, retorna False"
            )
            return False

        if self.dry_run:
            return True

        proof_bytes = bytes.fromhex(proof_hash.replace("0x", "").ljust(64, "0"))
        
        # Real ABI needs iterating getProofCount and matching the hash off-chain
        try:
            count = self._contract.functions.getProofCount().call()
            # Iterating backwards to find the newest matches faster
            for i in range(count - 1, -1, -1):
                record = self._contract.functions.getProof(i).call()
                # record format: [agentId, trustScore, z3ProofHash, storageRef, invariantsCount, timestamp, verified]
                if record[2] == proof_bytes:
                    return True
        except Exception as e:
            logger.error(f"Error checking proof existence: {e}")
            
        return False

    def get_chain_info(self) -> dict:
        """Retorna metadata de la chain configurada."""
        return {
            "chain_key": self.config.chain_key,
            "chain_id": self.config.chain_id,
            "name": self.config.name,
            "status": self.config.status,
            "contract_address": self.config.contract_address,
            "native_token": self.config.native_token,
            "gas_multiplier": self.config.gas_multiplier,
            "explorer": self.config.explorer,
            "notes": self.config.notes
        }

    @classmethod
    def list_supported_chains(cls) -> list:
        """Lista todas las chains en chains_config.json con su status."""
        config_data = cls.load_chains_config()
        result = []
        for key, data in config_data.get("chains", {}).items():
            result.append({
                "chain_key": key,
                "chain_id": data["chain_id"],
                "name": data["name"],
                "status": data["status"],
                "has_contract": data.get("contract_address") is not None
            })
        return result
