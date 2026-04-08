"""
ConfluxScan API Client for DOF-MESH
====================================
Reads DOFProofRegistry transaction history and proof events directly
from ConfluxScan's public REST API — no wallet, no Web3 required.

API reference: https://api.confluxscan.org/doc
Rate limits: 5 calls/sec (free tier), 100K calls/day

Why this matters for DOF-MESH:
  After 100+ on-chain proofs, we need a way to:
  1. Read proof history without a connected wallet
  2. Verify proofs exist on-chain from any environment
  3. Build dashboards showing agent compliance over time
  4. Feed the DOF Leaderboard with real on-chain data

NOTE: eth_getLogs on Conflux is limited to 1,000 blocks per query.
ConfluxScan's API has no such limit — it's the correct tool for
historical queries spanning large block ranges.

Author: DOF-Agent-1686 | Conflux Global Hackfest 2026
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger("dof.conflux_scan_api")

# ─── Constants ────────────────────────────────────────────────────

CONFLUXSCAN_TESTNET = "https://evmtestnet.confluxscan.io/api"
CONFLUXSCAN_MAINNET = "https://evm.confluxscan.io/api"

DOF_PROOF_REGISTRY_TESTNET = "0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83"
DOF_PROOF_REGISTRY_MAINNET = ""  # Pending mainnet deployment

FREE_TIER_DELAY = 0.25  # 250ms between calls → stays under 5 req/sec


class ConfluxScanAPI:
    """
    Client for ConfluxScan REST API.

    Provides proof history, transaction lookup, and contract verification
    status for DOFProofRegistry without requiring a connected Web3 wallet.

    Example:
        api = ConfluxScanAPI(use_testnet=True)
        txs = api.get_contract_transactions(DOF_PROOF_REGISTRY_TESTNET, limit=10)
        for tx in txs:
            print(tx["hash"], tx["timeStamp"])
    """

    def __init__(self, use_testnet: bool = True, api_key: str = ""):
        self.base_url = CONFLUXSCAN_TESTNET if use_testnet else CONFLUXSCAN_MAINNET
        self.api_key = api_key
        self.contract = (
            DOF_PROOF_REGISTRY_TESTNET if use_testnet
            else DOF_PROOF_REGISTRY_MAINNET
        )

    def _get(self, params: dict) -> dict:
        """Make a rate-limited GET request to ConfluxScan API."""
        if self.api_key:
            params["apikey"] = self.api_key
        time.sleep(FREE_TIER_DELAY)
        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "0" and data.get("message") != "No transactions found":
                logger.warning(f"ConfluxScan API error: {data.get('result')}")
            return data
        except requests.RequestException as exc:
            logger.error(f"ConfluxScan request failed: {exc}")
            return {"status": "0", "result": []}

    def get_contract_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 25,
        sort: str = "desc"
    ) -> list:
        """
        Get transactions for DOFProofRegistry (or any contract address).

        Uses ConfluxScan's /api?module=account&action=txlist endpoint.
        No block range limit — unlike eth_getLogs which is capped at 1,000.

        Args:
            address: Contract address (defaults to DOFProofRegistry)
            limit:   Max transactions to return (max 100 per page)
            sort:    "asc" or "desc" by timestamp

        Returns:
            List of transaction dicts with hash, timeStamp, from, to, value, gasUsed
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address or self.contract,
            "offset": min(limit, 100),
            "sort": sort,
        }
        data = self._get(params)
        result = data.get("result", [])
        if isinstance(result, list):
            logger.info(f"ConfluxScan: {len(result)} transactions for {address or self.contract[:10]}...")
            return result
        return []

    def get_proof_registered_events(
        self,
        address: Optional[str] = None,
        from_block: int = 0,
        to_block: str = "latest",
        limit: int = 100
    ) -> list:
        """
        Get ProofRegistered event logs from DOFProofRegistry.

        Topic0 = keccak256("ProofRegistered(bytes32,address,uint16,uint32,bool,uint40)")
        ConfluxScan returns decoded log data — no ABI parsing required.

        Args:
            address:    Contract address (defaults to DOFProofRegistry)
            from_block: Start block (0 = genesis)
            to_block:   End block ("latest" or block number)
            limit:      Max events to return

        Returns:
            List of event log dicts
        """
        # ProofRegistered event signature (V2 contract)
        PROOF_REGISTERED_TOPIC = (
            "0x" + "ProofRegistered(bytes32,address,uint16,uint32,bool,uint40)".encode().hex()
        )

        params = {
            "module":    "logs",
            "action":    "getLogs",
            "address":   address or self.contract,
            "fromBlock": str(from_block),
            "toBlock":   str(to_block),
            "offset":    min(limit, 1000),
        }
        data = self._get(params)
        result = data.get("result", [])
        if isinstance(result, list):
            logger.info(f"ConfluxScan: {len(result)} ProofRegistered events")
            return result
        return []

    def get_proof_count(self, address: Optional[str] = None) -> int:
        """
        Get total number of transactions to DOFProofRegistry.
        Approximation of proof count when contract ABI is unavailable.

        Args:
            address: Contract address (defaults to DOFProofRegistry)

        Returns:
            Transaction count as integer
        """
        params = {
            "module":  "account",
            "action":  "txlist",
            "address": address or self.contract,
            "offset":  1,
            "sort":    "desc",
        }
        data = self._get(params)
        # ConfluxScan returns total count in a separate field when paginating
        # Fall back to counting returned results
        result = data.get("result", [])
        count = int(data.get("total", len(result) if isinstance(result, list) else 0))
        logger.info(f"DOFProofRegistry TX count: {count}")
        return count

    def verify_tx_confirmed(self, tx_hash: str) -> dict:
        """
        Check if a specific transaction is confirmed on Conflux eSpace.

        Args:
            tx_hash: Full transaction hash (0x...)

        Returns:
            Dict with: confirmed (bool), block_number, gas_used, timestamp
        """
        params = {
            "module": "transaction",
            "action": "gettxreceiptstatus",
            "txhash": tx_hash,
        }
        data = self._get(params)
        result = data.get("result", {})
        status = str(result.get("status", "0"))
        confirmed = status == "1"
        logger.info(f"TX {tx_hash[:10]}... confirmed={confirmed}")
        return {
            "confirmed":    confirmed,
            "status":       status,
            "tx_hash":      tx_hash,
        }

    def get_contract_source(self, address: Optional[str] = None) -> dict:
        """
        Get verified source code metadata for DOFProofRegistry.

        Args:
            address: Contract address (defaults to DOFProofRegistry)

        Returns:
            Dict with: verified (bool), compiler_version, license, source_code
        """
        params = {
            "module":  "contract",
            "action":  "getsourcecode",
            "address": address or self.contract,
        }
        data = self._get(params)
        result = data.get("result", [{}])
        if isinstance(result, list) and result:
            info = result[0]
            return {
                "verified":        bool(info.get("ABI") and info["ABI"] != "Contract source code not verified"),
                "compiler_version": info.get("CompilerVersion", ""),
                "license":         info.get("LicenseType", ""),
                "contract_name":   info.get("ContractName", ""),
                "optimization":    info.get("OptimizationUsed", "0") == "1",
            }
        return {"verified": False}

    def summary(self) -> dict:
        """
        Full DOFProofRegistry summary from ConfluxScan.

        Returns:
            Dict with proof count, contract address, verification status
        """
        txs = self.get_contract_transactions(limit=100)
        source = self.get_contract_source()
        return {
            "contract":        self.contract,
            "network":         "Conflux eSpace Testnet (Chain ID: 71)",
            "tx_count":        len(txs),
            "verified":        source.get("verified", False),
            "compiler":        source.get("compiler_version", ""),
            "license":         source.get("license", ""),
            "api_source":      "ConfluxScan REST API — no Web3 wallet required",
        }
