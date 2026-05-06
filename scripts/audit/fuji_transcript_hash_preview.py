#!/usr/bin/env python3
"""Fuji transcript hash and calldata preview helper.

This helper is intentionally non-executing. It computes deterministic local
preview data for the Fuji transcript verification runbook and refuses any
execution path.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


MODE = "fuji_transcript_hash_preview"
EXECUTION_BLOCKED = (
    "Execution blocked by design. This helper never signs or broadcasts transactions."
)

CHAIN_ID = 43113
CONTRACT = "0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c"
RPC_PLACEHOLDER = "$FUJI_RPC"
CONTRACT_PLACEHOLDER = "$DOF_FUJI_CONTRACT"
BURNER_PLACEHOLDER = "<BURNER_PUBLIC_ADDRESS>"

TRANSCRIPT = (
    "DOF-MESH Fuji transcript verification test 001 | "
    "agentId=1686 | invariants=8 | chainId=43113"
)
AGENT_ID = 1686
TRUST_SCORE = 900000000000000000
STORAGE_REF = "ipfs://dofmesh/fuji/transcript-verification-test/001"
INVARIANTS_COUNT = 8
DEFAULT_PROOF_COUNT_BEFORE = 4
DEFAULT_PROOF_ID = 4

REGISTER_SIGNATURE = "registerProof(uint256,uint256,bytes32,string,uint8)"
VERIFY_SIGNATURE = "verifyProof(uint256,bytes)"


def evm_keccak(data: bytes) -> bytes:
    """Return EVM-compatible Keccak-256 or fail closed with operator guidance."""
    try:
        from Crypto.Hash import keccak
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "EVM Keccak-256 provider unavailable. Install pycryptodome locally "
            f'or use: cast keccak "{TRANSCRIPT}"'
        ) from exc

    hasher = keccak.new(digest_bits=256)
    hasher.update(data)
    return bytes.fromhex(hasher.hexdigest())


def hex0(data: bytes) -> str:
    return "0x" + data.hex()


def uint_word(value: int) -> str:
    if value < 0:
        raise ValueError("uint value cannot be negative")
    return value.to_bytes(32, "big").hex()


def bytes32_word(value: str) -> str:
    raw = bytes.fromhex(value.removeprefix("0x"))
    if len(raw) != 32:
        raise ValueError("bytes32 value must be exactly 32 bytes")
    return raw.hex()


def padded_dynamic_bytes(data: bytes) -> str:
    padding_len = (32 - (len(data) % 32)) % 32
    return uint_word(len(data)) + data.hex() + ("00" * padding_len)


def selector(signature: str) -> str:
    return evm_keccak(signature.encode("utf-8"))[:4].hex()


def encode_register_calldata(computed_keccak: str) -> str:
    storage_bytes = STORAGE_REF.encode("utf-8")
    head_words = [
        uint_word(AGENT_ID),
        uint_word(TRUST_SCORE),
        bytes32_word(computed_keccak),
        uint_word(32 * 5),
        uint_word(INVARIANTS_COUNT),
    ]
    return "0x" + selector(REGISTER_SIGNATURE) + "".join(head_words) + padded_dynamic_bytes(storage_bytes)


def encode_verify_calldata(proof_id: int, transcript_bytes: bytes) -> str:
    head_words = [
        uint_word(proof_id),
        uint_word(32 * 2),
    ]
    return "0x" + selector(VERIFY_SIGNATURE) + "".join(head_words) + padded_dynamic_bytes(transcript_bytes)


def build_preview(proof_id: int, proof_count_before: int) -> dict[str, Any]:
    transcript_bytes = TRANSCRIPT.encode("utf-8")
    computed = hex0(evm_keccak(transcript_bytes))
    transcript_hex = hex0(transcript_bytes)

    return {
        "mode": MODE,
        "execution_enabled": False,
        "chain_id": CHAIN_ID,
        "contract": CONTRACT,
        "transcript": TRANSCRIPT,
        "transcript_bytes_hex": transcript_hex,
        "computed_keccak": computed,
        "registerProof": {
            "signature": REGISTER_SIGNATURE,
            "arguments": {
                "agentId": AGENT_ID,
                "trustScore": TRUST_SCORE,
                "z3ProofHash": computed,
                "storageRef": STORAGE_REF,
                "invariantsCount": INVARIANTS_COUNT,
            },
            "calldata_preview": encode_register_calldata(computed),
        },
        "expected": {
            "proof_count_before": proof_count_before,
            "new_proofId": proof_id,
        },
        "verifyProof": {
            "signature": VERIFY_SIGNATURE,
            "arguments": {
                "proofId": proof_id,
                "proofTranscript": transcript_hex,
            },
            "calldata_preview": encode_verify_calldata(proof_id, transcript_bytes),
        },
        "manual_estimate_templates": [
            (
                f'cast estimate "{CONTRACT_PLACEHOLDER}" "{REGISTER_SIGNATURE}" '
                f'{AGENT_ID} {TRUST_SCORE} {computed} "{STORAGE_REF}" {INVARIANTS_COUNT} '
                f"--from {BURNER_PLACEHOLDER} --rpc-url {RPC_PLACEHOLDER}"
            ),
            (
                f'cast estimate "{CONTRACT_PLACEHOLDER}" "{VERIFY_SIGNATURE}" '
                f'{proof_id} "{transcript_hex}" --from {BURNER_PLACEHOLDER} '
                f"--rpc-url {RPC_PLACEHOLDER}"
            ),
        ],
        "manual_execution_templates": [
            (
                "Manual Foundry send template for registerProof: "
                f'"{CONTRACT_PLACEHOLDER}" "{REGISTER_SIGNATURE}" '
                f'{AGENT_ID} {TRUST_SCORE} {computed} "{STORAGE_REF}" {INVARIANTS_COUNT} '
                f"--rpc-url {RPC_PLACEHOLDER} --signing-key <LOCAL_BURNER_SIGNING_KEY>"
            ),
            (
                "Manual Foundry send template for verifyProof: "
                f'"{CONTRACT_PLACEHOLDER}" "{VERIFY_SIGNATURE}" {proof_id} '
                f'"{transcript_hex}" --rpc-url {RPC_PLACEHOLDER} '
                "--signing-key <LOCAL_BURNER_SIGNING_KEY>"
            ),
        ],
        "safety_warnings": [
            "Preview only; execution_enabled is false.",
            "No .env is read by this helper.",
            "No signing key is read by this helper.",
            "No wallet is created by this helper.",
            "No transaction is signed or broadcast by this helper.",
            "Juan controls secrets and real execution.",
        ],
    }


def print_text(preview: dict[str, Any]) -> None:
    register_args = preview["registerProof"]["arguments"]
    verify_args = preview["verifyProof"]["arguments"]
    expected = preview["expected"]

    print(f"mode: {preview['mode']}")
    print(f"execution_enabled: {str(preview['execution_enabled']).lower()}")
    print(f"chain_id: {preview['chain_id']}")
    print(f"contract: {preview['contract']}")
    print(f"transcript: {preview['transcript']}")
    print(f"transcript_bytes_hex: {preview['transcript_bytes_hex']}")
    print(f"computed_keccak: {preview['computed_keccak']}")
    print("registerProof arguments:")
    print(f"  agentId: {register_args['agentId']}")
    print(f"  trustScore: {register_args['trustScore']}")
    print(f"  z3ProofHash: {register_args['z3ProofHash']}")
    print(f"  storageRef: {register_args['storageRef']}")
    print(f"  invariantsCount: {register_args['invariantsCount']}")
    print(f"registerProof calldata_preview: {preview['registerProof']['calldata_preview']}")
    print(f"expected proof count before: {expected['proof_count_before']}")
    print(f"expected new proofId: {expected['new_proofId']}")
    print("verifyProof arguments:")
    print(f"  proofId: {verify_args['proofId']}")
    print(f"  proofTranscript: {verify_args['proofTranscript']}")
    print(f"verifyProof calldata_preview: {preview['verifyProof']['calldata_preview']}")
    print("manual estimate templates:")
    for item in preview["manual_estimate_templates"]:
        print(f"  {item}")
    print("manual execution templates:")
    for item in preview["manual_execution_templates"]:
        print(f"  {item}")
    print("safety warnings:")
    for warning in preview["safety_warnings"]:
        print(f"  - {warning}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview Fuji transcript hash and calldata without execution."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Always blocked. This helper never signs or broadcasts transactions.",
    )
    parser.add_argument("--proof-id", type=int, default=DEFAULT_PROOF_ID)
    parser.add_argument(
        "--proof-count-before",
        type=int,
        default=DEFAULT_PROOF_COUNT_BEFORE,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.execute:
        print(EXECUTION_BLOCKED, file=sys.stderr)
        return 1

    try:
        preview = build_preview(args.proof_id, args.proof_count_before)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Hint: install pycryptodome locally or use the runbook cast keccak command.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(preview, indent=2, sort_keys=True))
    else:
        print_text(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
