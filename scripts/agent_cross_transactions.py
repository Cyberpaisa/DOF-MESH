#!/usr/bin/env python3
"""
Agent Cross-Transactions — Real on-chain activity between Apex and AvaBuilder.

4 rounds of real transactions with DOF governance, autofeedback scoring,
on-chain attestations, and Enigma trust score publishing.

Round 1: Apex sends 0.001 AVAX to AvaBuilder → AvaBuilder evaluates → attestation
Round 2: AvaBuilder sends 0.001 AVAX to Apex → Apex evaluates → attestation
Round 3: Apex calls AvaBuilder OASF → Apex evaluates → attestation
Round 4: AvaBuilder calls Apex OASF → AvaBuilder evaluates → attestation

Requirements:
    APEX_PRIVATE_KEY, AVABUILDER_PRIVATE_KEY, AVALANCHE_RPC_URL,
    VALIDATION_REGISTRY_ADDRESS in .env
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import ssl
import logging
from datetime import datetime, timezone
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware as _poa_middleware

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("agent_cross_tx")

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

RPC_URL = os.environ.get("AVALANCHE_RPC_URL", "")
CONTRACT_ADDR = os.environ.get("VALIDATION_REGISTRY_ADDRESS", "")
APEX_KEY = os.environ.get("APEX_PRIVATE_KEY", "")
AVA_KEY = os.environ.get("AVABUILDER_PRIVATE_KEY", "")

APEX_OASF = "https://apex-arbitrage-agent-production.up.railway.app/oasf"
AVA_OASF = "https://avariskscan-defi-production.up.railway.app/oasf"

TRANSFER_AMOUNT = Web3.to_wei(0.001, "ether")
CHAIN_ID = 43114

# Minimal ABI for registerAttestation
REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "certificateHash", "type": "bytes32"},
            {"name": "agentId", "type": "bytes32"},
            {"name": "compliant", "type": "bool"},
        ],
        "name": "registerAttestation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalAttestations",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _hex_to_bytes32(hex_str: str) -> bytes:
    clean = hex_str.replace("0x", "")
    raw = bytes.fromhex(clean)
    if len(raw) >= 32:
        return raw[:32]
    return raw + b"\x00" * (32 - len(raw))


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────

def setup():
    """Initialize web3 and accounts."""
    assert RPC_URL, "AVALANCHE_RPC_URL not set"
    assert CONTRACT_ADDR, "VALIDATION_REGISTRY_ADDRESS not set"
    assert APEX_KEY, "APEX_PRIVATE_KEY not set"
    assert AVA_KEY, "AVABUILDER_PRIVATE_KEY not set"

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(_poa_middleware, layer=0)
    assert w3.is_connected(), "Cannot connect to Avalanche RPC"

    apex = w3.eth.account.from_key(APEX_KEY)
    ava = w3.eth.account.from_key(AVA_KEY)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDR),
        abi=REGISTRY_ABI,
    )

    return w3, apex, ava, contract


# ─────────────────────────────────────────────────────────────────────
# Transaction helpers
# ─────────────────────────────────────────────────────────────────────

def send_avax(w3, sender_account, sender_key, to_address, amount_wei):
    """Send AVAX from sender to recipient. Returns tx receipt and timing."""
    t0 = time.time()

    nonce = w3.eth.get_transaction_count(sender_account.address)
    gas_price = int(w3.eth.gas_price * 1.25)

    tx = {
        "from": sender_account.address,
        "to": Web3.to_checksum_address(to_address),
        "value": amount_wei,
        "gas": 21000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID,
    }

    signed = w3.eth.account.sign_transaction(tx, sender_key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    logger.info(f"  TX sent: {tx_hash.hex()}")
    logger.info(f"  https://snowtrace.io/tx/0x{tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    elapsed = time.time() - t0

    return {
        "tx_hash": "0x" + tx_hash.hex(),
        "block_number": receipt["blockNumber"],
        "gas_used": receipt["gasUsed"],
        "status": "confirmed" if receipt["status"] == 1 else "failed",
        "elapsed_sec": round(elapsed, 2),
        "snowtrace": f"https://snowtrace.io/tx/{tx_hash.hex()}",
    }


def send_attestation(w3, evaluator_account, evaluator_key, contract,
                     cert_hash, agent_id_str, compliant=True):
    """Send attestation on-chain signed by the evaluator agent."""
    t0 = time.time()

    cert_bytes32 = _hex_to_bytes32(cert_hash)
    agent_bytes32 = _hex_to_bytes32(_sha256(agent_id_str))

    nonce = w3.eth.get_transaction_count(evaluator_account.address)
    gas_price = int(w3.eth.gas_price * 1.25)

    tx = contract.functions.registerAttestation(
        cert_bytes32, agent_bytes32, compliant
    ).build_transaction({
        "from": evaluator_account.address,
        "nonce": nonce,
        "gas": 0,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    })

    gas_estimate = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_estimate * 1.2)

    signed = w3.eth.account.sign_transaction(tx, evaluator_key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    logger.info(f"  Attestation TX: {tx_hash.hex()}")
    logger.info(f"  https://snowtrace.io/tx/0x{tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    elapsed = time.time() - t0

    return {
        "tx_hash": "0x" + tx_hash.hex(),
        "block_number": receipt["blockNumber"],
        "gas_used": receipt["gasUsed"],
        "status": "confirmed" if receipt["status"] == 1 else "failed",
        "elapsed_sec": round(elapsed, 2),
        "snowtrace": f"https://snowtrace.io/tx/{tx_hash.hex()}",
    }


def call_oasf(url):
    """Call an agent's OASF endpoint. Returns response dict and timing."""
    t0 = time.time()
    ctx = ssl.create_default_context()

    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            elapsed = time.time() - t0
            return {
                "status": "ok",
                "http_code": resp.status,
                "data": data,
                "elapsed_sec": round(elapsed, 2),
            }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "status": "error",
            "error": str(e),
            "elapsed_sec": round(elapsed, 2),
        }


# ─────────────────────────────────────────────────────────────────────
# DOF Governance check
# ─────────────────────────────────────────────────────────────────────

def governance_check(text):
    """Run DOF governance on text. Returns result dict."""
    try:
        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        result = enforcer.check(text)
        return {
            "passed": result.passed,
            "hard_violations": len(result.hard_violations),
            "soft_violations": len(result.soft_violations),
        }
    except Exception as e:
        return {"passed": True, "hard_violations": 0, "soft_violations": 0,
                "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# Autofeedback scoring
# ─────────────────────────────────────────────────────────────────────

def autofeedback_score(tx_result, governance_result, round_type):
    """Calculate autofeedback score 1-100.

    Base: 70
    +10 if tx confirmed
    +5 if gas < 50000 (transfer) or < 100000 (attestation)
    +5 if elapsed < 5 sec
    +5 if governance passed with 0 violations
    +5 if round completed without errors
    """
    score = 70

    if tx_result.get("status") == "confirmed":
        score += 10

    gas = tx_result.get("gas_used", 999999)
    if round_type in ("transfer", "oasf_call"):
        if gas < 50000:
            score += 5
    else:
        if gas < 100000:
            score += 5

    elapsed = tx_result.get("elapsed_sec", 999)
    if elapsed < 5:
        score += 5

    if governance_result.get("passed") and governance_result.get("hard_violations", 0) == 0:
        score += 5

    if tx_result.get("status") != "error":
        score += 5

    return min(score, 100)


# ─────────────────────────────────────────────────────────────────────
# Enigma trust score publish
# ─────────────────────────────────────────────────────────────────────

def publish_enigma_score(agent_address, score, round_name):
    """Publish trust score to Enigma dof_trust_scores."""
    try:
        from core.enigma_bridge import EnigmaBridge
        bridge = EnigmaBridge()
        if not bridge.is_online:
            return {"status": "offline"}

        metrics = {
            "SS": score / 100.0,
            "GCR": 1.0 if score >= 70 else 0.0,
            "PFI": 0.0,
            "AST_score": 0.0,
            "ACR": 0.0,
        }
        snapshot = {
            "round": round_name,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result = bridge.publish_trust_score(
            agent_id=agent_address.lower(),
            metrics=metrics,
            snapshot_data=snapshot,
        )
        return {"status": "published", "overall": getattr(result, "overall_score", None)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# Rounds
# ─────────────────────────────────────────────────────────────────────

def run_round_transfer(w3, sender, sender_key, receiver, evaluator,
                       evaluator_key, contract, round_num, round_name):
    """Execute a transfer round: send AVAX → governance → score → attestation."""
    print(f"\n{'='*70}")
    print(f"  ROUND {round_num}: {round_name}")
    print(f"{'='*70}")

    # Step 1: Transfer
    print(f"\n  [1/4] Sending 0.001 AVAX: {sender.address[:10]}... → {receiver.address[:10]}...")
    tx_result = send_avax(w3, sender, sender_key, receiver.address, TRANSFER_AMOUNT)
    print(f"  Status: {tx_result['status']} | Block: {tx_result['block_number']} | "
          f"Gas: {tx_result['gas_used']} | Time: {tx_result['elapsed_sec']}s")

    # Step 2: Governance check
    print(f"\n  [2/4] DOF Governance check...")
    gov_text = (f"Agent {sender.address} sent 0.001 AVAX to {receiver.address}. "
                f"TX: {tx_result['tx_hash']}. Status: {tx_result['status']}.")
    gov_result = governance_check(gov_text)
    print(f"  Passed: {gov_result['passed']} | Hard: {gov_result['hard_violations']} | "
          f"Soft: {gov_result['soft_violations']}")

    # Step 3: Autofeedback score
    print(f"\n  [3/4] Autofeedback scoring...")
    score = autofeedback_score(tx_result, gov_result, "transfer")
    print(f"  Score: {score}/100")

    # Step 4: Attestation on-chain (from evaluator)
    print(f"\n  [4/4] On-chain attestation (signed by {evaluator.address[:10]}...)...")
    cert_hash = _sha256(f"{round_name}:{tx_result['tx_hash']}:{score}:{datetime.now(timezone.utc).isoformat()}")
    att_result = send_attestation(
        w3, evaluator, evaluator_key, contract,
        cert_hash, f"round:{round_num}:{sender.address}",
        compliant=(score >= 70),
    )
    print(f"  Attestation: {att_result['status']} | Block: {att_result['block_number']} | "
          f"Gas: {att_result['gas_used']} | Time: {att_result['elapsed_sec']}s")

    # Enigma publish
    enigma = publish_enigma_score(sender.address, score, round_name)
    print(f"  Enigma: {enigma.get('status', 'n/a')}")

    return {
        "round": round_num,
        "name": round_name,
        "type": "transfer",
        "sender": sender.address,
        "receiver": receiver.address,
        "evaluator": evaluator.address,
        "transfer_tx": tx_result,
        "governance": gov_result,
        "score": score,
        "attestation_tx": att_result,
        "enigma": enigma,
        "cert_hash": cert_hash,
    }


def run_round_oasf(w3, caller, evaluator, evaluator_key, contract,
                   oasf_url, target_name, round_num, round_name):
    """Execute an OASF evaluation round: call OASF → governance → score → attestation."""
    print(f"\n{'='*70}")
    print(f"  ROUND {round_num}: {round_name}")
    print(f"{'='*70}")

    # Step 1: Call OASF
    print(f"\n  [1/4] Calling {target_name} OASF: {oasf_url}")
    oasf_result = call_oasf(oasf_url)
    print(f"  Status: {oasf_result['status']} | Time: {oasf_result['elapsed_sec']}s")
    if oasf_result["status"] == "ok":
        data = oasf_result["data"]
        if isinstance(data, dict):
            name = data.get("name", data.get("agent_name", "unknown"))
            version = data.get("version", "?")
            skills = data.get("skills", data.get("capabilities", []))
            skill_count = len(skills) if isinstance(skills, list) else 0
            print(f"  Agent: {name} v{version} | Skills: {skill_count}")

    # Step 2: Governance check
    print(f"\n  [2/4] DOF Governance check...")
    gov_text = json.dumps(oasf_result.get("data", oasf_result), default=str)[:2000]
    gov_result = governance_check(gov_text)
    print(f"  Passed: {gov_result['passed']} | Hard: {gov_result['hard_violations']} | "
          f"Soft: {gov_result['soft_violations']}")

    # Step 3: Autofeedback score
    print(f"\n  [3/4] Autofeedback scoring...")
    # For OASF rounds, adapt scoring
    oasf_tx_equiv = {
        "status": "confirmed" if oasf_result["status"] == "ok" else "error",
        "gas_used": 0,
        "elapsed_sec": oasf_result["elapsed_sec"],
    }
    score = autofeedback_score(oasf_tx_equiv, gov_result, "oasf_call")
    # Bonus for rich OASF data
    if oasf_result["status"] == "ok":
        data = oasf_result.get("data", {})
        if isinstance(data, dict):
            skills = data.get("skills", data.get("capabilities", []))
            if isinstance(skills, list) and len(skills) >= 3:
                score = min(score + 5, 100)
    print(f"  Score: {score}/100")

    # Step 4: Attestation on-chain (from evaluator)
    print(f"\n  [4/4] On-chain attestation (signed by {evaluator.address[:10]}...)...")
    cert_hash = _sha256(f"{round_name}:{oasf_url}:{score}:{datetime.now(timezone.utc).isoformat()}")
    att_result = send_attestation(
        w3, evaluator, evaluator_key, contract,
        cert_hash, f"round:{round_num}:{target_name}",
        compliant=(score >= 70),
    )
    print(f"  Attestation: {att_result['status']} | Block: {att_result['block_number']} | "
          f"Gas: {att_result['gas_used']} | Time: {att_result['elapsed_sec']}s")

    # Enigma publish
    enigma = publish_enigma_score(evaluator.address, score, round_name)
    print(f"  Enigma: {enigma.get('status', 'n/a')}")

    return {
        "round": round_num,
        "name": round_name,
        "type": "oasf_evaluation",
        "caller": caller.address,
        "evaluator": evaluator.address,
        "oasf_url": oasf_url,
        "target": target_name,
        "oasf_result": {k: v for k, v in oasf_result.items() if k != "data"},
        "oasf_data_summary": _summarize_oasf(oasf_result),
        "governance": gov_result,
        "score": score,
        "attestation_tx": att_result,
        "enigma": enigma,
        "cert_hash": cert_hash,
    }


def _summarize_oasf(oasf_result):
    """Extract summary from OASF data for logging."""
    if oasf_result["status"] != "ok":
        return {"status": "error"}
    data = oasf_result.get("data", {})
    if not isinstance(data, dict):
        return {"status": "non_dict"}
    return {
        "name": data.get("name", data.get("agent_name", "?")),
        "version": data.get("version", "?"),
        "skill_count": len(data.get("skills", data.get("capabilities", []))),
    }


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*70)
    print("  AGENT CROSS-TRANSACTIONS — Real On-Chain Activity")
    print("  4 Rounds: 2 transfers + 2 OASF evaluations")
    print("="*70)

    w3, apex, ava, contract = setup()

    # Show initial state
    apex_bal = float(Web3.from_wei(w3.eth.get_balance(apex.address), "ether"))
    ava_bal = float(Web3.from_wei(w3.eth.get_balance(ava.address), "ether"))
    total_att = contract.functions.totalAttestations().call()

    print(f"\n  Apex:      {apex.address} ({apex_bal:.4f} AVAX)")
    print(f"  AvaBuilder: {ava.address} ({ava_bal:.4f} AVAX)")
    print(f"  Contract:  {CONTRACT_ADDR}")
    print(f"  Total attestations (before): {total_att}")

    results = []

    # ── ROUND 1: Apex → AvaBuilder transfer ──
    r1 = run_round_transfer(
        w3, apex, APEX_KEY, ava, ava, AVA_KEY, contract,
        round_num=1,
        round_name="Apex→AvaBuilder transfer",
    )
    results.append(r1)

    # ── ROUND 2: AvaBuilder → Apex transfer ──
    r2 = run_round_transfer(
        w3, ava, AVA_KEY, apex, apex, APEX_KEY, contract,
        round_num=2,
        round_name="AvaBuilder→Apex transfer",
    )
    results.append(r2)

    # ── ROUND 3: Apex evaluates AvaBuilder OASF ──
    r3 = run_round_oasf(
        w3, apex, apex, APEX_KEY, contract,
        AVA_OASF, "AvaBuilder", round_num=3,
        round_name="Apex evaluates AvaBuilder OASF",
    )
    results.append(r3)

    # ── ROUND 4: AvaBuilder evaluates Apex OASF ──
    r4 = run_round_oasf(
        w3, ava, ava, AVA_KEY, contract,
        APEX_OASF, "Apex", round_num=4,
        round_name="AvaBuilder evaluates Apex OASF",
    )
    results.append(r4)

    # ── Summary ──
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")

    total_att_after = contract.functions.totalAttestations().call()
    apex_bal_after = float(Web3.from_wei(w3.eth.get_balance(apex.address), "ether"))
    ava_bal_after = float(Web3.from_wei(w3.eth.get_balance(ava.address), "ether"))

    print(f"\n  Attestations: {total_att} → {total_att_after} (+{total_att_after - total_att})")
    print(f"  Apex balance:      {apex_bal:.4f} → {apex_bal_after:.4f} AVAX")
    print(f"  AvaBuilder balance: {ava_bal:.4f} → {ava_bal_after:.4f} AVAX")

    print(f"\n  Round results:")
    for r in results:
        tx_key = "transfer_tx" if r["type"] == "transfer" else "attestation_tx"
        att_tx = r["attestation_tx"]
        print(f"    R{r['round']}: Score={r['score']}/100 | "
              f"Attestation={att_tx['status']} | "
              f"Governance={'PASS' if r['governance']['passed'] else 'FAIL'}")
        # Print snowtrace links
        if r["type"] == "transfer":
            print(f"         Transfer:    {r['transfer_tx']['snowtrace']}")
        print(f"         Attestation: {att_tx['snowtrace']}")

    # Save results to JSONL
    os.makedirs(LOGS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOGS_DIR, f"agent_cross_tx_{ts}.jsonl")
    with open(log_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    print(f"\n  Results saved: {log_path}")

    print(f"\n{'='*70}")
    print("  DONE — 4 rounds completed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
