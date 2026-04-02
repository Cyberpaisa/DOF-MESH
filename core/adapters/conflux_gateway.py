"""
Gateway de Conflux eSpace.
Maneja la conexión RPC y utilidades para interactuar con la red Conflux eSpace,
incluyendo los contratos internos para Gas Sponsorship.
"""

from web3 import Web3
from web3.middleware import geth_poa_middleware
import logging

class ConfluxGateway:
    """Gateway soberano para conexión con Conflux eSpace (Capa de Músculo SDD)."""
    
    MAINNET_RPC = "https://evm.confluxrpc.com"
    TESTNET_RPC = "https://evmtestnet.confluxrpc.com"
    
    # Internal Contract in Core Space bridged to eSpace address format
    # Address: 0x0888000000000000000000000000000000000001
    SPONSOR_CONTRACT_ADDRESS = "0x0888000000000000000000000000000000000001"
    
    def __init__(self, use_testnet: bool = False):
        self.logger = logging.getLogger("ConfluxGateway")
        self.rpc_url = self.TESTNET_RPC if use_testnet else self.MAINNET_RPC
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Inject PoA middleware required for Conflux eSpace (EVM compatibility)
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
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
