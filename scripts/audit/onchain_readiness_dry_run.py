#!/usr/bin/env python3
"""
DOF-MESH on-chain readiness dry-run.

Safety guarantees:
- Does not load .env
- Does not read private keys
- Does not sign transactions
- Does not broadcast transactions
- Does not call RPC endpoints
- Does not modify chains_config.json
- Produces only an offline readiness report from core/chains_config.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("core/chains_config.json")

MAINNET_STATUSES = {"mainnet", "pending_funds", "pending_deploy", "planned"}
TESTNET_STATUSES = {"testnet"}


def classify_risk(chain: dict[str, Any]) -> list[str]:
    risks: list[str] = []

    status = str(chain.get("status", "")).lower()
    contract_address = chain.get("contract_address")
    gas_multiplier = chain.get("gas_multiplier", 1)
    rpc_url = chain.get("rpc_url")

    if status in MAINNET_STATUSES:
        risks.append("mainnet_or_mainnet_candidate")

    if not contract_address:
        risks.append("missing_contract_address")

    if status in {"planned", "pending_funds", "pending_deploy"}:
        risks.append(f"not_ready_status:{status}")

    try:
        gas_value = float(gas_multiplier)
        if gas_value > 1:
            risks.append(f"gas_multiplier:{gas_value}")
    except (TypeError, ValueError):
        risks.append("invalid_gas_multiplier")

    if not rpc_url:
        risks.append("missing_rpc_url")

    return risks


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "chains" not in data or not isinstance(data["chains"], dict):
        raise ValueError("Invalid chains_config.json: missing object field 'chains'")

    return data


def build_report(config: dict[str, Any]) -> dict[str, Any]:
    chains = config["chains"]
    report_chains: list[dict[str, Any]] = []

    for key, chain in sorted(chains.items()):
        status = chain.get("status")
        contract_address = chain.get("contract_address")
        risks = classify_risk(chain)

        report_chains.append(
            {
                "key": key,
                "name": chain.get("name"),
                "chain_id": chain.get("chain_id"),
                "status": status,
                "native_token": chain.get("native_token"),
                "has_contract_address": bool(contract_address),
                "contract_address": contract_address,
                "gas_multiplier": chain.get("gas_multiplier"),
                "rpc_configured": bool(chain.get("rpc_url")),
                "explorer_configured": bool(chain.get("explorer")),
                "readiness": "ready_for_read_only_check" if not risks else "needs_review",
                "risks": risks,
            }
        )

    totals = {
        "chain_count": len(report_chains),
        "with_contract_address": sum(1 for c in report_chains if c["has_contract_address"]),
        "without_contract_address": sum(1 for c in report_chains if not c["has_contract_address"]),
        "mainnet_or_candidates": sum(
            1 for c in report_chains if "mainnet_or_mainnet_candidate" in c["risks"]
        ),
        "testnets": sum(1 for c in report_chains if c["status"] == "testnet"),
        "needs_review": sum(1 for c in report_chains if c["readiness"] == "needs_review"),
    }

    return {
        "mode": "offline_no_broadcast_dry_run",
        "safety": {
            "loads_env": False,
            "reads_private_keys": False,
            "uses_rpc": False,
            "signs_transactions": False,
            "broadcasts_transactions": False,
            "writes_files": False,
        },
        "config": {
            "version": config.get("version"),
            "verified_date": config.get("verified_date"),
            "active_chains": config.get("active_chains"),
        },
        "totals": totals,
        "chains": report_chains,
    }


def print_text_report(report: dict[str, Any]) -> None:
    print("DOF-MESH On-Chain Readiness Dry-Run")
    print("Mode: offline_no_broadcast_dry_run")
    print()
    print("Safety:")
    for key, value in report["safety"].items():
        print(f"  {key}: {value}")

    print()
    print("Config:")
    for key, value in report["config"].items():
        print(f"  {key}: {value}")

    print()
    print("Totals:")
    for key, value in report["totals"].items():
        print(f"  {key}: {value}")

    print()
    print("Chains:")
    for chain in report["chains"]:
        risks = ", ".join(chain["risks"]) if chain["risks"] else "none"
        print(
            f"  - {chain['key']} | chain_id={chain['chain_id']} | "
            f"status={chain['status']} | contract={chain['has_contract_address']} | "
            f"readiness={chain['readiness']} | risks={risks}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline no-broadcast on-chain readiness dry-run")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to chains_config.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    report = build_report(config)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
