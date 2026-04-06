"""
Gateway de Conflux eSpace.
Maneja la conexión RPC y utilidades para interactuar con la red Conflux eSpace,
incluyendo los contratos internos para Gas Sponsorship.
"""

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as _poa_mw
except ImportError:
    from web3.middleware import geth_poa_middleware as _poa_mw
import logging

class ConfluxGateway:
    """Gateway soberano para conexión con Conflux eSpace (Capa de Músculo SDD)."""

    MAINNET_RPC = "https://evm.confluxrpc.com"
    TESTNET_RPC = "https://evmtestnet.confluxrpc.com"

    PROOF_REGISTRY_TESTNET = "0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83"
    PROOF_REGISTRY_CHAIN_ID = 71

    # Internal Contract in Core Space bridged to eSpace address format
    SPONSOR_CONTRACT_ADDRESS = "0x0888000000000000000000000000000000000001"

    def __init__(self, use_testnet: bool = False, dry_run: bool = False):
        self.logger = logging.getLogger("ConfluxGateway")
        self.dry_run = dry_run
        self.rpc_url = self.TESTNET_RPC if use_testnet else self.MAINNET_RPC

        if dry_run:
            from unittest.mock import MagicMock
            self.w3 = MagicMock()
            self.w3.eth.chain_id = self.PROOF_REGISTRY_CHAIN_ID
            self.w3.is_connected.return_value = True
            self.logger.info("ConfluxGateway en modo dry_run")
            return

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        try:
            self.w3.middleware_onion.inject(_poa_mw, layer=0)
        except Exception:
            pass  # Conflux eSpace no siempre requiere PoA middleware

        if self.w3.is_connected():
            self.logger.info(f"Conectado a Conflux eSpace. ChainID: {self.w3.eth.chain_id}")
        else:
            self.logger.error("Error crítico: No se pudo conectar a Conflux eSpace")
            raise ConnectionError("Fallo de conexión RPC a Conflux")
            
    def get_sponsor_contract(self):
        """Devuelve la instancia del contrato SponsorWhitelistControl."""
        # Minimal ABI for SponsorWhitelistControl interactions
        abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "contractAddr", "type": "address"}, 
                    {"internalType": "address[]", "name": "addresses", "type": "address[]"}
                ],
                "name": "addPrivilegeByAdmin",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "contractAddr", "type": "address"}, 
                    {"internalType": "uint256", "name": "upperBound", "type": "uint256"}
                ],
                "name": "setSponsorForGas",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "contractAddr", "type": "address"}
                ],
                "name": "setSponsorForCollateral",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
        return self.w3.eth.contract(address=self.SPONSOR_CONTRACT_ADDRESS, abi=abi)
