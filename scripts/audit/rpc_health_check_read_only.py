#!/usr/bin/env python3
"""
DOF-MESH read-only RPC health check.

Safety guarantees:
- Does not load .env
- Does not read private keys
- Does not create wallets
- Does not sign transactions
- Does not broadcast transactions
- Does not deploy contracts
- Does not modify chains_config.json
- Performs only read-only JSON-RPC calls:
  - eth_chainId
  - eth_blockNumber
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("core/chains_config.json")
READ_ONLY_METHODS = {"eth_chainId", "eth_blockNumber"}


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "chains" not in data or not isinstance(data["chains"], dict):
        raise ValueError("Invalid chains_config.json: missing object field 'chains'")

    return data


def rpc_call(url: str, method: str, timeout: float) -> dict[str, Any]:
    if method not in READ_ONLY_METHODS:
        raise ValueError(f"Blocked non-read-only RPC method: {method}")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": [],
    }

    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            elapsed_ms = round((time.monotonic() - started) * 1000, 2)
            parsed = json.loads(raw)
            return {
                "ok": "error" not in parsed,
                "elapsed_ms": elapsed_ms,
                "response": parsed,
                "error": parsed.get("error"),
            }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return {
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "response": None,
            "error": str(exc),
        }


def parse_hex_int(value: Any) -> int | None:
    if not isinstance(value, str):
        return None

    try:
        return int(value, 16)
    except ValueError:
        return None


def check_endpoint(url: str, expected_chain_id: int | None, timeout: float) -> dict[str, Any]:
    chain_result = rpc_call(url, "eth_chainId", timeout)
    block_result = rpc_call(url, "eth_blockNumber", timeout) if chain_result["ok"] else None

    observed_chain_id = None
    chain_match = False
    latest_block = None
    warnings: list[str] = []

    if chain_result["ok"]:
        observed_chain_id = parse_hex_int(chain_result["response"].get("result"))
        chain_match = observed_chain_id == expected_chain_id
        if not chain_match:
            warnings.append(
                f"chain_id_mismatch:expected={expected_chain_id}:observed={observed_chain_id}"
            )
    else:
        warnings.append("eth_chainId_failed")

    if block_result and block_result["ok"]:
        latest_block = parse_hex_int(block_result["response"].get("result"))
    elif block_result:
        warnings.append("eth_blockNumber_failed")

    return {
        "reachable": bool(chain_result["ok"]),
        "expected_chain_id": expected_chain_id,
        "observed_chain_id": observed_chain_id,
        "chain_id_match": chain_match,
        "latest_block": latest_block,
        "eth_chainId_ms": chain_result["elapsed_ms"],
        "eth_blockNumber_ms": block_result["elapsed_ms"] if block_result else None,
        "warnings": warnings,
        "error": chain_result["error"] if not chain_result["ok"] else None,
    }


def build_report(config: dict[str, Any], timeout: float, include_fallback: bool) -> dict[str, Any]:
    chains = config["chains"]
    checked_chains: list[dict[str, Any]] = []

    for key, chain in sorted(chains.items()):
        expected_chain_id = chain.get("chain_id")
        primary_rpc = chain.get("rpc_url")
        fallback_rpc = chain.get("rpc_fallback")

        endpoints: list[dict[str, Any]] = []

        if primary_rpc:
            endpoints.append(
                {
                    "kind": "primary",
                    "url": primary_rpc,
                    **check_endpoint(primary_rpc, expected_chain_id, timeout),
                }
            )
        else:
            endpoints.append(
                {
                    "kind": "primary",
                    "url": None,
                    "reachable": False,
                    "expected_chain_id": expected_chain_id,
                    "observed_chain_id": None,
                    "chain_id_match": False,
                    "latest_block": None,
                    "eth_chainId_ms": None,
                    "eth_blockNumber_ms": None,
                    "warnings": ["missing_rpc_url"],
                    "error": "missing_rpc_url",
                }
            )

        if include_fallback and fallback_rpc:
            endpoints.append(
                {
                    "kind": "fallback",
                    "url": fallback_rpc,
                    **check_endpoint(fallback_rpc, expected_chain_id, timeout),
                }
            )

        any_reachable = any(endpoint["reachable"] for endpoint in endpoints)
        any_match = any(endpoint["chain_id_match"] for endpoint in endpoints)

        checked_chains.append(
            {
                "key": key,
                "name": chain.get("name"),
                "status": chain.get("status"),
                "expected_chain_id": expected_chain_id,
                "native_token": chain.get("native_token"),
                "has_contract_address": bool(chain.get("contract_address")),
                "endpoint_count": len(endpoints),
                "any_reachable": any_reachable,
                "any_chain_id_match": any_match,
                "readiness": "rpc_readable" if any_reachable and any_match else "needs_review",
                "endpoints": endpoints,
            }
        )

    totals = {
        "chain_count": len(checked_chains),
        "rpc_readable": sum(1 for chain in checked_chains if chain["readiness"] == "rpc_readable"),
        "needs_review": sum(1 for chain in checked_chains if chain["readiness"] == "needs_review"),
        "with_any_reachable_endpoint": sum(1 for chain in checked_chains if chain["any_reachable"]),
        "with_chain_id_match": sum(1 for chain in checked_chains if chain["any_chain_id_match"]),
    }

    return {
        "mode": "read_only_rpc_health_check",
        "safety": {
            "loads_env": False,
            "reads_private_keys": False,
            "creates_wallets": False,
            "signs_transactions": False,
            "broadcasts_transactions": False,
            "deploys_contracts": False,
            "writes_files": False,
            "rpc_methods": sorted(READ_ONLY_METHODS),
        },
        "config": {
            "version": config.get("version"),
            "verified_date": config.get("verified_date"),
            "active_chains": config.get("active_chains"),
        },
        "options": {
            "timeout_seconds": timeout,
            "include_fallback": include_fallback,
        },
        "totals": totals,
        "chains": checked_chains,
    }


def print_text_report(report: dict[str, Any]) -> None:
    print("DOF-MESH Read-Only RPC Health Check")
    print("Mode: read_only_rpc_health_check")
    print()
    print("Safety:")
    for key, value in report["safety"].items():
        print(f"  {key}: {value}")

    print()
    print("Options:")
    for key, value in report["options"].items():
        print(f"  {key}: {value}")

    print()
    print("Totals:")
    for key, value in report["totals"].items():
        print(f"  {key}: {value}")

    print()
    print("Chains:")
    for chain in report["chains"]:
        print(
            f"  - {chain['key']} | expected_chain_id={chain['expected_chain_id']} | "
            f"readiness={chain['readiness']} | reachable={chain['any_reachable']} | "
            f"chain_id_match={chain['any_chain_id_match']}"
        )
        for endpoint in chain["endpoints"]:
            warnings = ", ".join(endpoint["warnings"]) if endpoint["warnings"] else "none"
            print(
                f"      {endpoint['kind']}: reachable={endpoint['reachable']} | "
                f"observed_chain_id={endpoint['observed_chain_id']} | "
                f"latest_block={endpoint['latest_block']} | warnings={warnings}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only RPC health check")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to chains_config.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Per-RPC-call timeout in seconds",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Also check rpc_fallback endpoints when configured",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    report = build_report(config, timeout=args.timeout, include_fallback=args.include_fallback)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
