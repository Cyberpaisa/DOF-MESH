#!/usr/bin/env python3
"""
Phase 12 — DeFi Arbitrage Scanner for Q-AION Wallet on Avalanche C-Chain.

Reads wallet credentials from environment variables (QAION_WALLET_ADDRESS,
QAION_PRIVATE_KEY). Supports scanning DEX prices across Trader Joe and
Pangolin without executing trades.

Usage:
    python3 scripts/phase12_real_arbitrageur.py --check-balance
    python3 scripts/phase12_real_arbitrageur.py --scan
    python3 scripts/phase12_real_arbitrageur.py --scan --amount 10
    python3 scripts/phase12_real_arbitrageur.py              # full intel + scan (no trades)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv

# Configuracion de Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

load_dotenv(ENV_PATH)

# ---------------------------------------------------------------------------
# web3 import (graceful fallback)
# ---------------------------------------------------------------------------
try:
    from web3 import Web3
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware
    except ImportError:
        from web3.middleware import geth_poa_middleware as _poa_middleware
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    _poa_middleware = None

# ---------------------------------------------------------------------------
# ABIs
# ---------------------------------------------------------------------------
ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForAVAX",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# ---------------------------------------------------------------------------
# Token & Router addresses on Avalanche C-Chain
# ---------------------------------------------------------------------------
TOKENS = {
    "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
    "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
    "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
}

ROUTERS = {
    "TraderJoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
    "Pangolin": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",
}

# Pairs to scan: (token_in_symbol, token_out_symbol, amount_in_human)
DEFAULT_SCAN_PAIRS = [
    ("USDC", "WAVAX"),
    ("WAVAX", "USDC"),
    ("USDC.e", "WAVAX"),
    ("WAVAX", "USDC.e"),
]

# USDC/USDT have 6 decimals, WAVAX has 18
TOKEN_DECIMALS = {
    "WAVAX": 18,
    "USDC": 6,
    "USDC.e": 6,
    "USDT": 6,
}


class Phase12RealArbitrageur:
    """DeFi arbitrage scanner using the Q-AION sovereign wallet.

    Reads credentials exclusively from environment variables:
        QAION_WALLET_ADDRESS — public address (used for balance reads)
        QAION_PRIVATE_KEY    — private key (needed only for future tx signing)
        AVALANCHE_RPC_URL    — RPC endpoint (defaults to public endpoint)
    """

    def __init__(self, require_key: bool = False):
        if not HAS_WEB3:
            raise RuntimeError("web3 package not installed. Run: pip install web3")

        self.rpc_url = os.getenv(
            "AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # Inject POA middleware for Avalanche C-Chain
        if _poa_middleware:
            self.w3.middleware_onion.inject(_poa_middleware, layer=0)

        # --- Wallet from env vars (NEVER hardcoded) ---
        self.address = os.getenv("QAION_WALLET_ADDRESS", "")
        self._private_key = os.getenv("QAION_PRIVATE_KEY", "")

        if not self.address:
            raise RuntimeError(
                "QAION_WALLET_ADDRESS not set in environment. "
                "Add it to .env or export it."
            )

        self.address = Web3.to_checksum_address(self.address)

        # Validate private key maps to the expected address
        if self._private_key:
            acct = self.w3.eth.account.from_key(self._private_key)
            if acct.address.lower() != self.address.lower():
                raise RuntimeError(
                    f"QAION_PRIVATE_KEY derives address {acct.address} "
                    f"but QAION_WALLET_ADDRESS is {self.address}. Mismatch!"
                )
        elif require_key:
            raise RuntimeError(
                "QAION_PRIVATE_KEY not set — required for this operation."
            )

        # Pre-build token contracts
        self.token_contracts = {}
        for symbol, addr in TOKENS.items():
            self.token_contracts[symbol] = self.w3.eth.contract(
                address=Web3.to_checksum_address(addr), abi=ERC20_ABI
            )

        # Pre-build router contracts
        self.router_contracts = {}
        for name, addr in ROUTERS.items():
            self.router_contracts[name] = self.w3.eth.contract(
                address=Web3.to_checksum_address(addr), abi=ROUTER_ABI
            )

        # Connection check
        if not self.w3.is_connected():
            raise RuntimeError(f"Cannot connect to RPC: {self.rpc_url}")

    # ------------------------------------------------------------------
    # Balance checking
    # ------------------------------------------------------------------
    def check_balance(self) -> dict:
        """Return AVAX balance and all tracked token balances for the wallet."""
        result = {
            "wallet": self.address,
            "rpc": self.rpc_url,
            "chain_id": self.w3.eth.chain_id,
            "connected": self.w3.is_connected(),
            "block": self.w3.eth.block_number,
            "balances": {},
        }

        # Native AVAX
        avax_wei = self.w3.eth.get_balance(self.address)
        avax_balance = float(Web3.from_wei(avax_wei, "ether"))
        result["balances"]["AVAX"] = {
            "raw_wei": str(avax_wei),
            "human": f"{avax_balance:.6f}",
        }

        # ERC-20 tokens
        for symbol, contract in self.token_contracts.items():
            try:
                decimals = TOKEN_DECIMALS.get(symbol, 18)
                raw = contract.functions.balanceOf(self.address).call()
                human = raw / (10**decimals)
                result["balances"][symbol] = {
                    "raw": str(raw),
                    "human": f"{human:.6f}",
                    "decimals": decimals,
                }
            except Exception as e:
                result["balances"][symbol] = {"error": str(e)}

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result

    # ------------------------------------------------------------------
    # DEX price scanning
    # ------------------------------------------------------------------
    def get_price(
        self, router_name: str, token_in: str, token_out: str, amount_in_human: float
    ) -> dict:
        """Query getAmountsOut on a DEX router. No transaction, view-only.

        Args:
            router_name: "TraderJoe" or "Pangolin"
            token_in: Token symbol (e.g. "USDC")
            token_out: Token symbol (e.g. "WAVAX")
            amount_in_human: Amount in human-readable units (e.g. 5.0 USDC)

        Returns:
            Dict with amount_out, effective_price, etc.
        """
        if router_name not in self.router_contracts:
            return {"error": f"Unknown router: {router_name}"}

        router = self.router_contracts[router_name]
        decimals_in = TOKEN_DECIMALS.get(token_in, 18)
        decimals_out = TOKEN_DECIMALS.get(token_out, 18)

        amount_in_raw = int(amount_in_human * (10**decimals_in))
        path = [
            Web3.to_checksum_address(TOKENS[token_in]),
            Web3.to_checksum_address(TOKENS[token_out]),
        ]

        try:
            amounts = router.functions.getAmountsOut(amount_in_raw, path).call()
            amount_out_raw = amounts[-1]
            amount_out_human = amount_out_raw / (10**decimals_out)

            # Effective price: how much token_out per 1 token_in
            if amount_in_human > 0:
                effective_price = amount_out_human / amount_in_human
            else:
                effective_price = 0.0

            return {
                "router": router_name,
                "pair": f"{token_in} -> {token_out}",
                "amount_in": f"{amount_in_human:.6f} {token_in}",
                "amount_out": f"{amount_out_human:.6f} {token_out}",
                "effective_price": f"1 {token_in} = {effective_price:.6f} {token_out}",
                "raw_amounts": [str(a) for a in amounts],
            }
        except Exception as e:
            return {
                "router": router_name,
                "pair": f"{token_in} -> {token_out}",
                "error": str(e),
            }

    def scan_all_prices(self, amount_usdc: float = 5.0, amount_avax: float = 0.05) -> list:
        """Scan all configured pairs across all DEX routers.

        Returns a list of price quotes and any detected arbitrage spreads.
        """
        results = []
        for token_in, token_out in DEFAULT_SCAN_PAIRS:
            if token_in in ("USDC", "USDC.e", "USDT"):
                amount = amount_usdc
            else:
                amount = amount_avax

            for router_name in ROUTERS:
                quote = self.get_price(router_name, token_in, token_out, amount)
                results.append(quote)

        # Detect arbitrage spreads between routers for same pair
        spreads = self._detect_spreads(results)
        return {"quotes": results, "spreads": spreads, "timestamp": datetime.now(timezone.utc).isoformat()}

    def _detect_spreads(self, quotes: list) -> list:
        """Compare prices between routers for identical pairs."""
        from collections import defaultdict

        by_pair = defaultdict(list)
        for q in quotes:
            if "error" not in q:
                by_pair[q["pair"]].append(q)

        spreads = []
        for pair, pair_quotes in by_pair.items():
            if len(pair_quotes) < 2:
                continue
            # Extract numeric amount_out for comparison
            amounts = []
            for q in pair_quotes:
                try:
                    out_str = q["amount_out"].split()[0]
                    amounts.append((q["router"], float(out_str)))
                except (ValueError, IndexError):
                    continue

            if len(amounts) >= 2:
                amounts.sort(key=lambda x: x[1], reverse=True)
                best_router, best_amount = amounts[0]
                worst_router, worst_amount = amounts[-1]
                if worst_amount > 0:
                    spread_pct = ((best_amount - worst_amount) / worst_amount) * 100
                    spreads.append({
                        "pair": pair,
                        "best": f"{best_router} ({best_amount:.6f})",
                        "worst": f"{worst_router} ({worst_amount:.6f})",
                        "spread_pct": f"{spread_pct:.4f}%",
                        "actionable": spread_pct > 0.5,  # >0.5% might cover gas
                    })

        return spreads

    # ------------------------------------------------------------------
    # Market intelligence (Tavily — optional)
    # ------------------------------------------------------------------
    def fetch_live_market_data(self) -> str:
        """Query real-time DeFi news via Tavily API (optional)."""
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return "[SKIP] TAVILY_API_KEY not set"

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": tavily_key,
            "query": "Avalanche DeFi yields Trader Joe Pangolin AVAX USDC 2026",
            "search_depth": "advanced",
            "max_results": 5,
        }

        try:
            import requests

            response = requests.post(url, json=payload, timeout=15).json()
            results = [
                r["title"] + ": " + r["content"][:200]
                for r in response.get("results", [])
            ]
            return "\n".join(results) if results else "No results"
        except Exception as e:
            return f"Tavily error: {e}"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log_event(self, event_type: str, data: dict):
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "phase12_arbitrageur.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "wallet": self.address,
            **data,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


# ======================================================================
# CLI
# ======================================================================
def print_balance(arb: Phase12RealArbitrageur):
    """Print wallet balance report."""
    print("=" * 60)
    print("  Q-AION WALLET STATUS  —  Avalanche C-Chain")
    print("=" * 60)

    bal = arb.check_balance()

    print(f"  Wallet:   {bal['wallet']}")
    print(f"  Chain ID: {bal['chain_id']}")
    print(f"  Block:    {bal['block']}")
    print(f"  RPC:      {bal['rpc']}")
    print("-" * 60)

    for token, info in bal["balances"].items():
        if "error" in info:
            print(f"  {token:10s}  ERROR: {info['error']}")
        else:
            print(f"  {token:10s}  {info['human']}")

    print("-" * 60)
    print(f"  Timestamp: {bal['timestamp']}")
    print("=" * 60)

    arb._log_event("check_balance", bal)
    return bal


def print_scan(arb: Phase12RealArbitrageur, amount_usdc: float, amount_avax: float):
    """Print DEX price scan report."""
    print("=" * 60)
    print("  DEX PRICE SCAN  —  Trader Joe & Pangolin")
    print(f"  Scanning with {amount_usdc} USDC / {amount_avax} AVAX")
    print("=" * 60)

    scan = arb.scan_all_prices(amount_usdc=amount_usdc, amount_avax=amount_avax)

    for q in scan["quotes"]:
        if "error" in q:
            print(f"  [{q['router']:10s}] {q['pair']:20s}  ERROR: {q['error']}")
        else:
            print(f"  [{q['router']:10s}] {q['pair']:20s}  => {q['amount_out']:>20s}  ({q['effective_price']})")

    if scan["spreads"]:
        print("-" * 60)
        print("  ARBITRAGE SPREADS DETECTED:")
        for s in scan["spreads"]:
            flag = " ** ACTIONABLE **" if s["actionable"] else ""
            print(f"    {s['pair']:20s}  spread={s['spread_pct']:>10s}  best={s['best']}  worst={s['worst']}{flag}")
    else:
        print("-" * 60)
        print("  No cross-DEX spreads found (all pairs single-router or same price)")

    print("-" * 60)
    print(f"  Timestamp: {scan['timestamp']}")
    print("  NOTE: Read-only scan. No trades executed.")
    print("=" * 60)

    arb._log_event("scan", scan)
    return scan


def main():
    parser = argparse.ArgumentParser(
        description="Phase 12 — Q-AION DeFi Arbitrage Scanner (Avalanche C-Chain)"
    )
    parser.add_argument(
        "--check-balance",
        action="store_true",
        help="Report wallet AVAX and token balances, then exit.",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan DEX prices on Trader Joe and Pangolin without trading.",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=5.0,
        help="USDC amount to use for price quotes (default: 5.0)",
    )
    parser.add_argument(
        "--amount-avax",
        type=float,
        default=0.05,
        help="AVAX amount to use for price quotes (default: 0.05)",
    )
    parser.add_argument(
        "--intel",
        action="store_true",
        help="Fetch live market intelligence via Tavily.",
    )

    args = parser.parse_args()

    # Default: if no flags, run check-balance + scan
    run_all = not (args.check_balance or args.scan or args.intel)

    # Only require private key if we would ever trade (never in current CLI)
    arb = Phase12RealArbitrageur(require_key=False)

    if args.check_balance or run_all:
        print_balance(arb)
        print()

    if args.scan or run_all:
        print_scan(arb, amount_usdc=args.amount, amount_avax=args.amount_avax)
        print()

    if args.intel or run_all:
        print("=" * 60)
        print("  MARKET INTELLIGENCE (Tavily)")
        print("=" * 60)
        intel = arb.fetch_live_market_data()
        print(intel[:1000])
        print("=" * 60)
        arb._log_event("intel", {"data": intel[:500]})


if __name__ == "__main__":
    main()
