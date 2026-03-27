"""
core/cross_chain_identity.py
Cross-Chain Identity Bridge — portable identity proofs across EVM chains.
Version: 0.1.0

Inspirado por OmniAgent (ERC-8004 x LayerZero V2) del hackathon Synthesis.
Implementa la logica de bridge de identidad sin conexion real a chains.

Uso:
    bridge = CrossChainIdentity()
    reg = bridge.register_identity("0xABCD...", 43114, "0xtx123")
    bridged = bridge.bridge_identity("0xABCD...", 43114, 8453)
    valid = bridge.verify_bridged_identity(bridged.proof_hash, 8453)
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs", "identity")

# Chains soportadas: nombre -> chain_id
SUPPORTED_CHAINS = {
    "avalanche": 43114,
    "base": 8453,
    "celo": 42220,
    "ethereum": 1,
    "tempo": 4217,
    "tempo_testnet": 42431,
}

CHAIN_ID_TO_NAME = {v: k for k, v in SUPPORTED_CHAINS.items()}


@dataclass
class IdentityRegistration:
    """Registro de identidad en una chain origen."""
    agent_address: str
    chain_id: int
    registration_tx: str
    timestamp: float
    proof_hash: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BridgedIdentity:
    """Identidad bridgeada de una chain a otra."""
    agent_address: str
    origin_chain: int
    target_chain: int
    proof_hash: str
    bridged_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class CrossChainIdentity:
    """
    Bridge de identidad cross-chain para agentes ERC-8004.

    Registra identidades en una chain origen, genera proofs portables
    y permite verificar autenticidad en chains destino.
    """

    def __init__(self):
        self._registrations: dict[str, IdentityRegistration] = {}
        # key: (agent_address, chain_id)
        self._bridged: list[BridgedIdentity] = []
        # proof_hash -> BridgedIdentity para verificacion rapida
        self._proof_index: dict[str, BridgedIdentity] = {}

    @staticmethod
    def _generate_proof_hash(
        agent_address: str,
        chain_id: int,
        registration_tx: str,
        timestamp: float,
    ) -> str:
        """Genera un hash determinista como proof de identidad."""
        payload = f"{agent_address.lower()}:{chain_id}:{registration_tx}:{timestamp}"
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def is_supported_chain(chain_id: int) -> bool:
        """Verifica si un chain_id esta soportado."""
        return chain_id in CHAIN_ID_TO_NAME

    def register_identity(
        self,
        agent_address: str,
        chain_id: int,
        registration_tx: str,
        timestamp: Optional[float] = None,
    ) -> IdentityRegistration:
        """
        Registra una identidad en una chain origen.

        Args:
            agent_address: Direccion del agente (hex).
            chain_id: ID de la chain origen.
            registration_tx: Hash de la transaccion de registro.
            timestamp: Epoch timestamp (default: now).

        Returns:
            IdentityRegistration con el proof_hash generado.

        Raises:
            ValueError: Si la chain no esta soportada.
        """
        if not self.is_supported_chain(chain_id):
            raise ValueError(
                f"Chain {chain_id} no soportada. "
                f"Soportadas: {list(CHAIN_ID_TO_NAME.keys())}"
            )

        ts = timestamp or time.time()
        proof_hash = self._generate_proof_hash(
            agent_address, chain_id, registration_tx, ts
        )

        reg = IdentityRegistration(
            agent_address=agent_address.lower(),
            chain_id=chain_id,
            registration_tx=registration_tx,
            timestamp=ts,
            proof_hash=proof_hash,
        )

        key = f"{agent_address.lower()}:{chain_id}"
        self._registrations[key] = reg

        logger.info(
            f"Identidad registrada: {agent_address[:10]}... en "
            f"{CHAIN_ID_TO_NAME.get(chain_id, str(chain_id))}"
        )
        return reg

    def get_registration(
        self, agent_address: str, chain_id: int
    ) -> Optional[IdentityRegistration]:
        """Obtiene el registro de identidad de un agente en una chain."""
        key = f"{agent_address.lower()}:{chain_id}"
        return self._registrations.get(key)

    def bridge_identity(
        self,
        agent_address: str,
        from_chain: int,
        to_chain: int,
    ) -> BridgedIdentity:
        """
        Crea el payload para registrar identidad en otra chain.

        Args:
            agent_address: Direccion del agente.
            from_chain: Chain ID de origen.
            to_chain: Chain ID de destino.

        Returns:
            BridgedIdentity con proof_hash portable.

        Raises:
            ValueError: Si alguna chain no esta soportada o no hay registro previo.
        """
        if not self.is_supported_chain(from_chain):
            raise ValueError(
                f"Chain origen {from_chain} no soportada. "
                f"Soportadas: {list(CHAIN_ID_TO_NAME.keys())}"
            )
        if not self.is_supported_chain(to_chain):
            raise ValueError(
                f"Chain destino {to_chain} no soportada. "
                f"Soportadas: {list(CHAIN_ID_TO_NAME.keys())}"
            )
        if from_chain == to_chain:
            raise ValueError("Chain origen y destino deben ser diferentes")

        reg = self.get_registration(agent_address, from_chain)
        if reg is None:
            raise ValueError(
                f"No hay registro de {agent_address} en chain {from_chain}. "
                f"Registra primero con register_identity()."
            )

        # El proof_hash del bridge combina el proof original + target chain
        bridge_payload = f"{reg.proof_hash}:{to_chain}"
        bridge_proof = hashlib.sha256(bridge_payload.encode()).hexdigest()

        now = datetime.now(timezone.utc).isoformat()
        bridged = BridgedIdentity(
            agent_address=agent_address.lower(),
            origin_chain=from_chain,
            target_chain=to_chain,
            proof_hash=bridge_proof,
            bridged_at=now,
        )

        self._bridged.append(bridged)
        self._proof_index[bridge_proof] = bridged

        self._log_bridge(bridged)

        logger.info(
            f"Identidad bridgeada: {agent_address[:10]}... "
            f"{CHAIN_ID_TO_NAME.get(from_chain)} -> "
            f"{CHAIN_ID_TO_NAME.get(to_chain)}"
        )
        return bridged

    def verify_bridged_identity(self, proof_hash: str, chain_id: int) -> bool:
        """
        Verifica la autenticidad de una identidad bridgeada.

        Reconstruye el proof esperado a partir de los datos originales
        y compara con el proof proporcionado.

        Args:
            proof_hash: Hash del bridge a verificar.
            chain_id: Chain ID donde se reclama la identidad.

        Returns:
            True si el proof es autentico y corresponde a la chain indicada.
        """
        bridged = self._proof_index.get(proof_hash)
        if bridged is None:
            return False

        if bridged.target_chain != chain_id:
            return False

        # Reconstruir proof desde los datos originales
        reg = self.get_registration(bridged.agent_address, bridged.origin_chain)
        if reg is None:
            return False

        expected_payload = f"{reg.proof_hash}:{chain_id}"
        expected_proof = hashlib.sha256(expected_payload.encode()).hexdigest()

        return expected_proof == proof_hash

    def get_bridges_for_agent(self, agent_address: str) -> list[BridgedIdentity]:
        """Lista todos los bridges de un agente."""
        addr = agent_address.lower()
        return [b for b in self._bridged if b.agent_address == addr]

    def list_supported_chains(self) -> dict[str, int]:
        """Retorna las chains soportadas."""
        return dict(SUPPORTED_CHAINS)

    def _log_bridge(self, bridged: BridgedIdentity):
        """Persiste el bridge en JSONL."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "bridged_identities.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **bridged.to_dict(),
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Error escribiendo log de bridge: {e}")
