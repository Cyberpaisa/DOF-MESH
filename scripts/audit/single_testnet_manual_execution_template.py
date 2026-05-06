#!/usr/bin/env python3
"""
DOF-MESH single-testnet manual execution template.

Safety guarantees:
- Does not load .env
- Does not read private keys
- Does not create wallets
- Does not sign transactions
- Does not broadcast transactions
- Does not deploy contracts
- Does not modify chains_config.json
- Does not execute cast/hardhat commands
- Produces only a manual execution checklist/template

This script is intentionally non-executing. It prepares a human-reviewed
manual execution plan for Avalanche Fuji only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("core/chains_config.json")
DEFAULT_CHAIN_KEY = "avalanche_testnet"
EXPECTED_CHAIN_ID = 43113
EXPECTED_STATUS = "testnet"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if "chains" not in data or not isinstance(data["chains"], dict):
        raise ValueError("Invalid chains_config.json: missing object field 'chains'")

    return data


def get_chain(config: dict[str, Any], chain_key: str) -> dict[str, Any]:
    chains = config["chains"]
    if chain_key not in chains:
        raise KeyError(f"Chain key not found in config: {chain_key}")
    return chains[chain_key]


def validate_chain(chain_key: str, chain: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    chain_id = chain.get("chain_id")
    status = chain.get("status")
    contract_address = chain.get("contract_address")
    rpc_url = chain.get("rpc_url")

    if chain_key != DEFAULT_CHAIN_KEY:
        errors.append(f"unsupported_chain_key:{chain_key}")

    if chain_id != EXPECTED_CHAIN_ID:
        errors.append(f"unexpected_chain_id:expected={EXPECTED_CHAIN_ID}:actual={chain_id}")

    if status != EXPECTED_STATUS:
        errors.append(f"unexpected_status:expected={EXPECTED_STATUS}:actual={status}")

    if not contract_address:
        errors.append("missing_contract_address")

    if not rpc_url:
        errors.append("missing_rpc_url")

    return errors


def build_template(config: dict[str, Any], chain_key: str) -> dict[str, Any]:
    chain = get_chain(config, chain_key)
    errors = validate_chain(chain_key, chain)

    contract_address = chain.get("contract_address")
    explorer = chain.get("explorer")

    return {
        "mode": "manual_single_testnet_execution_template",
        "execution_enabled": False,
        "safety": {
            "loads_env": False,
            "reads_private_keys": False,
            "creates_wallets": False,
            "signs_transactions": False,
            "broadcasts_transactions": False,
            "deploys_contracts": False,
            "writes_files": False,
            "executes_shell_commands": False,
        },
        "chain": {
            "key": chain_key,
            "name": chain.get("name"),
            "chain_id": chain.get("chain_id"),
            "status": chain.get("status"),
            "native_token": chain.get("native_token"),
            "rpc_url": chain.get("rpc_url"),
            "explorer": explorer,
            "contract_address": contract_address,
        },
        "validation": {
            "ready_for_manual_review": not errors,
            "errors": errors,
        },
        "manual_boundaries": [
            "Juan creates and controls the burner wallet manually.",
            "Juan never pastes private keys into Codex, ChatGPT, GitHub, docs, commits, or logs.",
            "Codex may only prepare the plan and dry-run templates.",
            "The final transaction command must be reviewed and executed manually by Juan.",
            "No deploy, no admin method, no mainnet, no batch, no multi-chain broadcast.",
        ],
        "pre_execution_checks": [
            "git checkout main",
            "git pull dof-mesh main",
            "git status",
            "npm run test:collect",
            "python3 scripts/audit/onchain_readiness_dry_run.py",
            "python3 scripts/audit/rpc_health_check_read_only.py --timeout 2 --json | python3 -m json.tool",
            "Confirm avalanche_testnet chain_id is 43113",
            f"Confirm contract address is {contract_address}",
            "Confirm burner wallet has only minimal Fuji AVAX",
            "Confirm gas estimate before any write operation",
        ],
        "manual_command_template": {
            "description": "Template only. Do not execute automatically.",
            "example_shape": "cast send <CONTRACT_ADDRESS> <METHOD_SIGNATURE> <ARGS> --rpc-url <FUJI_RPC_URL> --private-key <LOCAL_BURNER_PRIVATE_KEY>",
            "required_replacements": [
                "<CONTRACT_ADDRESS>",
                "<METHOD_SIGNATURE>",
                "<ARGS>",
                "<FUJI_RPC_URL>",
                "<LOCAL_BURNER_PRIVATE_KEY>",
            ],
            "forbidden_in_ai_context": [
                "<LOCAL_BURNER_PRIVATE_KEY>",
                "seed phrase",
                ".env",
                "raw signed transaction",
            ],
        },
        "evidence_template": {
            "chain_key": chain_key,
            "chain_id": chain.get("chain_id"),
            "contract_address": contract_address,
            "transaction_hash": "<fill_after_manual_execution>",
            "block_number": "<fill_after_manual_execution>",
            "explorer_url": f"{explorer}/tx/<transaction_hash>" if explorer else "<explorer>/tx/<transaction_hash>",
            "gas_used": "<fill_after_manual_execution>",
            "status": "<success_or_failed>",
            "notes": "No private keys, no .env, no seed phrase, no secrets.",
        },
        "abort_conditions": [
            "git status is dirty",
            "chain ID mismatch",
            "contract address mismatch",
            "wallet is not burner",
            "balance is too high for burner policy",
            "gas estimate unexpectedly high",
            "command includes deploy",
            "command includes mainnet",
            "command includes admin method",
            "private key appears in visible logs",
            "AI tool requests .env or private key",
        ],
    }


def print_text(template: dict[str, Any]) -> None:
    print("DOF-MESH Single-Testnet Manual Execution Template")
    print("Mode: manual_single_testnet_execution_template")
    print("Execution enabled: False")
    print()

    print("Safety:")
    for key, value in template["safety"].items():
        print(f"  {key}: {value}")

    print()
    print("Chain:")
    for key, value in template["chain"].items():
        print(f"  {key}: {value}")

    print()
    print("Validation:")
    print(f"  ready_for_manual_review: {template['validation']['ready_for_manual_review']}")
    print(f"  errors: {template['validation']['errors']}")

    print()
    print("Manual boundaries:")
    for item in template["manual_boundaries"]:
        print(f"  - {item}")

    print()
    print("Pre-execution checks:")
    for item in template["pre_execution_checks"]:
        print(f"  - {item}")

    print()
    print("Manual command template:")
    print(f"  {template['manual_command_template']['example_shape']}")

    print()
    print("Abort conditions:")
    for item in template["abort_conditions"]:
        print(f"  - {item}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a non-executing manual template for one testnet transaction"
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to chains_config.json",
    )
    parser.add_argument(
        "--chain",
        default=DEFAULT_CHAIN_KEY,
        help="Only avalanche_testnet is supported in this template",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Blocked by design. This script never executes transactions.",
    )
    args = parser.parse_args()

    if args.execute:
        raise SystemExit(
            "Execution blocked by design. This template never signs or broadcasts transactions."
        )

    config = load_config(Path(args.config))
    template = build_template(config, args.chain)

    if args.json:
        print(json.dumps(template, indent=2, sort_keys=True))
    else:
        print_text(template)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
