"""
DOF-MESH — Conflux Core Space Gateway
──────────────────────────────────────
Integración con Conflux Core Space (Native Chain).

Core Space usa RPC cfx_* nativo — distinto a EVM/eSpace.
Direcciones formato cfx: (base32). No requiere Web3.py.

Contraste con ConfluxGateway (eSpace):
- eSpace: EVM-compatible, chain 71, Web3.py, 0x addresses
- Core Space: cfx_* RPC, cfx: addresses, mayor throughput nativo

Docs: https://doc.confluxnetwork.org/docs/core/learn/core-space-basics
"""

from __future__ import annotations
import json
import logging
import requests
from typing import Any

log = logging.getLogger(__name__)


class ConfluxCoreGateway:
    """Gateway para Conflux Core Space via JSON-RPC cfx_* nativo."""

    RPC_MAINNET = "https://main.confluxrpc.com"
    RPC_TESTNET = "https://test.confluxrpc.com"

    # Internal contract — Storage Collateral Sponsor (Core Space)
    SPONSOR_COLLATERAL = "0x0888000000000000000000000000000000000002"

    def __init__(self, use_testnet: bool = True, dry_run: bool = True, timeout: int = 10):
        self.rpc_url  = self.RPC_TESTNET if use_testnet else self.RPC_MAINNET
        self.dry_run  = dry_run
        self.timeout  = timeout
        self.network  = "testnet" if use_testnet else "mainnet"
        self._req_id  = 0
        log.info(f"ConfluxCoreGateway initialized — {self.network} — {'DRY-RUN' if dry_run else 'LIVE'}")

    # ── JSON-RPC raw ──────────────────────────────────────────────────────────

    def _rpc(self, method: str, params: list | None = None) -> Any:
        """Hace una llamada cfx_* al RPC de Core Space."""
        if self.dry_run:
            log.debug(f"[DRY-RUN] cfx RPC: {method}({params})")
            return self._dry_run_defaults(method)

        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id":      self._req_id,
            "method":  method,
            "params":  params or [],
        }
        try:
            resp = requests.post(
                self.rpc_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"RPC error: {data['error']}")
            return data.get("result")
        except requests.RequestException as e:
            log.error(f"Core Space RPC failed: {method} — {e}")
            raise

    def _dry_run_defaults(self, method: str) -> Any:
        """Valores simulados para dry_run."""
        defaults = {
            "cfx_epochNumber":       "0x1a2b3c",
            "cfx_getBalance":        "0x3e8",
            "cfx_gasPrice":          "0x1",
            "cfx_getTransactionCount": "0x0",
            "cfx_getStatus":         {
                "chainId":           "0x1",
                "networkId":         "0x1",
                "epochNumber":       "0x1a2b3c",
                "latestConfirmed":   "0x1a2b00",
            },
        }
        return defaults.get(method, None)

    # ── Métodos de consulta ───────────────────────────────────────────────────

    def get_epoch_number(self) -> int:
        """Retorna el epoch number actual de Core Space."""
        result = self._rpc("cfx_epochNumber")
        if isinstance(result, str):
            return int(result, 16)
        return 0

    def get_balance(self, cfx_address: str) -> int:
        """Retorna el balance en Drip de una dirección cfx: (en Core Space)."""
        result = self._rpc("cfx_getBalance", [cfx_address, "latest_state"])
        if isinstance(result, str):
            return int(result, 16)
        return 0

    def get_gas_price(self) -> int:
        """Retorna el precio de gas actual en Core Space (en Drip)."""
        result = self._rpc("cfx_gasPrice")
        if isinstance(result, str):
            return int(result, 16)
        return 1

    def get_status(self) -> dict:
        """Retorna el estado actual del nodo Core Space."""
        result = self._rpc("cfx_getStatus")
        if isinstance(result, dict):
            return {
                "chain_id":        int(result.get("chainId", "0x1"), 16),
                "network_id":      int(result.get("networkId", "0x1"), 16),
                "epoch_number":    int(result.get("epochNumber", "0x0"), 16),
                "latest_confirmed": int(result.get("latestConfirmed", "0x0"), 16),
            }
        return {}

    def get_transaction_count(self, cfx_address: str) -> int:
        """Retorna el nonce de una dirección en Core Space."""
        result = self._rpc("cfx_getTransactionCount", [cfx_address, "latest_state"])
        if isinstance(result, str):
            return int(result, 16)
        return 0

    # ── Info ──────────────────────────────────────────────────────────────────

    def describe(self) -> dict:
        """Descripción del gateway para logging y docs."""
        return {
            "type":         "conflux_core_space",
            "rpc_url":      self.rpc_url,
            "network":      self.network,
            "dry_run":      self.dry_run,
            "rpc_protocol": "cfx_*",
            "address_format": "cfx: (base32)",
            "espace_complement": "0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83",
            "note": (
                "Core Space uses cfx_* native RPC — distinct from EVM/eSpace. "
                "DOFProofRegistry attestations are on eSpace (chain 71). "
                "Core Space gateway provides network-level awareness and "
                "is the foundation for future cross-space proof synchronization."
            ),
        }

    def __repr__(self) -> str:
        return f"<ConfluxCoreGateway network={self.network} dry_run={self.dry_run}>"
