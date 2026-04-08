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

    def get_logs_paginated(
        self,
        from_block: int,
        to_block: int,
        address: str,
        topics: list = None
    ) -> list:
        """
        Paginated eth_getLogs for Conflux eSpace.

        BUG CONTEXT: Conflux eSpace enforces a hard limit of 1,000 blocks
        per eth_getLogs request. Queries spanning more blocks silently fail
        or return incomplete results. This affects any batch reader that
        tries to scan the full DOFProofRegistry event history.

        Related upstream issue: https://github.com/Conflux-Chain/conflux-rust/issues/2998

        This method chunks the range into 900-block windows (10% safety
        margin below the 1,000 limit) and concatenates all results.

        Args:
            from_block: Start block number (inclusive)
            to_block:   End block number (inclusive)
            address:    Contract address to filter events
            topics:     Optional list of event topic filters

        Returns:
            List of all log entries across the full block range
        """
        CHUNK_SIZE = 900  # Conservative: Conflux hard limit is 1,000
        all_logs = []
        current_from = from_block

        if self.dry_run:
            self.logger.info(
                f"[dry_run] get_logs_paginated({from_block}→{to_block}) "
                f"— {((to_block - from_block) // CHUNK_SIZE) + 1} chunks"
            )
            return []

        while current_from <= to_block:
            current_to = min(current_from + CHUNK_SIZE - 1, to_block)
            filter_params = {
                "fromBlock": hex(current_from),
                "toBlock":   hex(current_to),
                "address":   address,
            }
            if topics:
                filter_params["topics"] = topics

            try:
                chunk = self.w3.eth.get_logs(filter_params)
                all_logs.extend(chunk)
                self.logger.debug(
                    f"getLogs chunk [{current_from}–{current_to}]: {len(chunk)} events"
                )
            except Exception as exc:
                self.logger.warning(
                    f"getLogs chunk [{current_from}–{current_to}] failed: {exc}"
                )
            current_from = current_to + 1

        self.logger.info(
            f"get_logs_paginated: {len(all_logs)} total events "
            f"({from_block}→{to_block})"
        )
        return all_logs

    def get_block_context_hash(self, tx_hash: str) -> str:
        """
        Generate a block context hash using Conflux debug_blockProperties.

        Conflux eSpace v3.0.2+ exposes debug_blockProperties, which returns
        per-transaction execution context (coinbase, timestamp, difficulty).
        This is unique to Conflux: in the Tree-Graph architecture, multiple
        transactions in one block can have different execution contexts.

        DOF-MESH uses this to bind proof hashes to a specific Conflux block
        context, making proofs impossible to replay across chains or blocks.

        Falls back to block number hash on older node versions.

        Args:
            tx_hash: Transaction hash to retrieve context for

        Returns:
            Hex string of keccak256(coinbase + timestamp + difficulty)
        """
        from web3 import Web3

        if self.dry_run:
            return "0x" + "d0f" * 21 + "d"  # Deterministic dry_run sentinel

        try:
            block_props = self.w3.provider.make_request(
                "debug_blockProperties", [tx_hash]
            )
            result = block_props.get("result", {})
            if result:
                context_data = (
                    str(result.get("coinbase",   "0x0")) +
                    str(result.get("timestamp",  "0"))   +
                    str(result.get("difficulty", "0"))
                )
                return Web3.keccak(text=context_data).hex()
        except Exception:
            pass

        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            return Web3.keccak(text=str(receipt.blockNumber)).hex()
        except Exception:
            return "0x" + "0" * 64
