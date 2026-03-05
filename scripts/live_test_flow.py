#!/usr/bin/env python3
"""
Live End-to-End Test Flow — Full DOF Pipeline with Real Agents.

Tests the complete DOF governance pipeline for two real Enigma Scanner agents:
  - Agent #1687 (Apex Arbitrage): 0xcd595a299ad1d5D088B7764e9330f7B0be7ca983
  - Agent #1686 (AvaBuilder):     0x9b59db8e7534924e34baa67a86454125cb02206d

Pipeline: Governance → AST → Z3 → Metrics → Attestation → Enigma → Avalanche On-Chain

ERC-721 Contract: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
DOFValidationRegistry: 0x88f6043B091055Bbd896Fc8D2c6234A47C02C052
"""

import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# ─────────────────────────────────────────────────────────────────────
# Agent Definitions
# ─────────────────────────────────────────────────────────────────────

AGENTS = [
    {
        "name": "Apex Arbitrage",
        "token_id": 1687,
        "wallet": "0xcd595a299ad1d5D088B7764e9330f7B0be7ca983",
        "nft_address": "0xfc6f71502d24f04e0463452947cc152a0eb4de3c",
        "output": (
            "The arbitrage analysis has been completed for the AVAX/USDC pair. "
            "An opportunity was detected with a spread of 0.3% on TraderJoe vs Pangolin. "
            "The estimated profit is $12.50 and the execution time was 2.1s. "
            "The gas cost for this transaction is 0.008 AVAX. "
            "All positions have been closed with no residual exposure. "
            "This is the final summary of the arbitrage operation that was executed by the agent. "
            "Source: https://traderjoexyz.com https://pangolin.exchange"
        ),
        "code": "spread = (price_a - price_b) / price_a * 100",
        "metrics": {
            "SS": 0.92, "GCR": 1.0, "PFI": 0.15,
            "RP": 0.10, "SSR": 0.0, "ACR": 0.85,
        },
    },
    {
        "name": "AvaBuilder",
        "token_id": 1686,
        "wallet": "0x9b59db8e7534924e34baa67a86454125cb02206d",
        "nft_address": None,
        "output": (
            "The smart contract audit has been completed for DOFValidationRegistry.sol. "
            "There are 0 critical vulnerabilities and 0 high severity issues in the contract. "
            "The analysis suggests 2 gas optimizations: batch storage writes and calldata over memory. "
            "The test coverage is at 94% with all 12 unit tests passing. "
            "This audit was performed by the AvaBuilder agent as part of the verification process. "
            "The contract is safe for deployment on the Avalanche C-Chain network. "
            "Source: https://snowtrace.io/address/0x88f6043B091055Bbd896Fc8D2c6234A47C02C052"
        ),
        "code": "assert registry.totalAttestations() >= 0",
        "metrics": {
            "SS": 0.88, "GCR": 1.0, "PFI": 0.22,
            "RP": 0.18, "SSR": 0.0, "ACR": 0.90,
        },
    },
]

ERC721_CONTRACT = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REGISTRY_ADDRESS = "0x88f6043B091055Bbd896Fc8D2c6234A47C02C052"


def main():
    console.print(Panel(
        "[bold cyan]DOF Live End-to-End Test Flow[/bold cyan]\n"
        "Full pipeline: Governance → AST → Z3 → Metrics → Attestation → Enigma → Avalanche",
        title="Deterministic Observability Framework",
    ))

    # ─── SETUP ────────────────────────────────────────────────────────
    console.print("\n[bold yellow]SETUP[/bold yellow]\n")

    from core.governance import ConstitutionEnforcer, load_constitution
    from core.ast_verifier import ASTVerifier
    from core.z3_verifier import Z3Verifier
    from core.oags_bridge import OAGSIdentity
    from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationRegistry
    from core.enigma_bridge import EnigmaBridge
    from core.avalanche_bridge import AvalancheBridge
    from core.memory_governance import GovernedMemoryStore

    # Load constitution
    const_path = os.path.join(BASE_DIR, "dof.constitution.yml")
    if os.path.exists(const_path):
        load_constitution(const_path)
        console.print("  [green]✓[/green] Constitution loaded")
    else:
        console.print("  [yellow]![/yellow] dof.constitution.yml not found — using defaults")

    enforcer = ConstitutionEnforcer()
    ast_verifier = ASTVerifier()
    z3_verifier = Z3Verifier()
    oags = OAGSIdentity()
    signer = CertificateSigner()
    oracle = OracleBridge(signer, oags)
    registry = AttestationRegistry()
    memory = GovernedMemoryStore()

    enigma = EnigmaBridge()
    console.print(f"  [green]✓[/green] EnigmaBridge: {'[green]ONLINE[/green]' if enigma.is_online else '[yellow]OFFLINE[/yellow]'}")

    avax = AvalancheBridge()
    console.print(f"  [green]✓[/green] AvalancheBridge: {'[green]ONLINE[/green]' if avax.is_online else '[yellow]OFFLINE[/yellow]'}")

    if avax.is_online:
        balance = avax.get_balance()
        console.print(f"  [green]✓[/green] Wallet balance: [cyan]{balance:.6f} AVAX[/cyan]")
        total_before = avax.total_attestations()
        console.print(f"  [green]✓[/green] On-chain attestations: [cyan]{total_before}[/cyan]")

    console.print(f"\n  ERC-721 Contract: [cyan]{ERC721_CONTRACT}[/cyan]")
    console.print(f"  DOFValidationRegistry: [cyan]{REGISTRY_ADDRESS}[/cyan]")

    # ─── PROCESS EACH AGENT ───────────────────────────────────────────
    results = []
    total_gas = 0

    for agent in AGENTS:
        console.print(f"\n{'─' * 70}")
        console.print(Panel(
            f"[bold]{agent['name']}[/bold] — Agent #{agent['token_id']}\n"
            f"Wallet: {agent['wallet']}\n"
            f"NFT: {agent.get('nft_address') or 'N/A'}",
            title=f"Agent #{agent['token_id']}",
        ))

        agent_result = {
            "name": agent["name"],
            "token_id": agent["token_id"],
            "wallet": agent["wallet"],
        }

        # ─── GOVERNANCE ───────────────────────────────────────────────
        console.print("\n  [bold magenta]GOVERNANCE CHECK[/bold magenta]")
        gov_result = enforcer.check(agent["output"])
        status_color = "green" if gov_result.passed else "red"
        console.print(f"    Status: [{status_color}]{'PASS' if gov_result.passed else 'FAIL'}[/{status_color}]")
        console.print(f"    Score: [cyan]{gov_result.score:.2f}[/cyan]")
        if gov_result.violations:
            for v in gov_result.violations:
                console.print(f"    [red]VIOLATION: {v}[/red]")
        else:
            console.print(f"    Violations: [green]0[/green]")
        if gov_result.warnings:
            for w in gov_result.warnings:
                console.print(f"    [yellow]WARNING: {w}[/yellow]")
        else:
            console.print(f"    Warnings: [green]0[/green]")

        agent_result["governance"] = {
            "passed": gov_result.passed,
            "score": gov_result.score,
            "violations": gov_result.violations,
            "warnings": gov_result.warnings,
        }

        if not gov_result.passed:
            console.print("    [red]NON-COMPLIANT — skipping attestation[/red]")
            agent_result["status"] = "non_compliant"
            results.append(agent_result)
            continue

        # ─── AST CHECK ────────────────────────────────────────────────
        console.print("\n  [bold magenta]AST VERIFICATION[/bold magenta]")
        ast_result = ast_verifier.verify(agent["code"])
        console.print(f"    Score: [cyan]{ast_result.score:.2f}[/cyan]")
        console.print(f"    Passed: [green]{ast_result.passed}[/green]")
        if ast_result.violations:
            for v in ast_result.violations:
                console.print(f"    [yellow]Issue: {v}[/yellow]")
        else:
            console.print(f"    Violations: [green]0[/green]")

        agent_result["ast"] = {
            "score": ast_result.score,
            "passed": ast_result.passed,
            "violations": ast_result.violations,
        }

        # ─── Z3 VERIFICATION ─────────────────────────────────────────
        console.print("\n  [bold magenta]Z3 FORMAL VERIFICATION[/bold magenta]")
        z3_results = z3_verifier.verify_all()
        all_verified = True
        for r in z3_results:
            status = "VERIFIED" if r.result == "VERIFIED" else "FAILED"
            color = "green" if r.result == "VERIFIED" else "red"
            console.print(f"    [{color}]{status}[/{color}]  {r.theorem_name}  ({r.proof_time_ms:.2f}ms)")
            if r.result != "VERIFIED":
                all_verified = False
        console.print(f"    All verified: [{'green' if all_verified else 'red'}]{all_verified}[/{'green' if all_verified else 'red'}]")

        agent_result["z3"] = {
            "all_verified": all_verified,
            "theorems": [{"name": r.theorem_name, "result": r.result, "ms": r.proof_time_ms} for r in z3_results],
        }

        # ─── METRICS ─────────────────────────────────────────────────
        console.print("\n  [bold magenta]METRICS[/bold magenta]")
        metrics = agent["metrics"]
        for k, v in metrics.items():
            console.print(f"    {k}: [cyan]{v:.2f}[/cyan]")

        # ─── ATTESTATION ─────────────────────────────────────────────
        console.print("\n  [bold magenta]ATTESTATION[/bold magenta]")
        task_id = f"live_test_agent_{agent['token_id']}"
        cert = oracle.create_attestation(
            task_id=task_id,
            metrics=metrics,
            z3_results=[{"result": r.result} for r in z3_results],
        )
        console.print(f"    Certificate: [dim]{cert.certificate_hash[:32]}...[/dim]")
        console.print(f"    Governance: [green]{cert.governance_status}[/green]")
        console.print(f"    Z3 Verified: [green]{cert.z3_verified}[/green]")
        publishable = oracle.should_publish(cert)
        console.print(f"    Publishable: [green]{publishable}[/green]")

        # Save to registry
        registry.add(cert)

        agent_result["attestation"] = {
            "certificate_hash": cert.certificate_hash,
            "governance_status": cert.governance_status,
            "z3_verified": cert.z3_verified,
            "publishable": publishable,
        }

        # ─── ENIGMA PUBLISH ──────────────────────────────────────────
        console.print("\n  [bold magenta]ENIGMA PUBLISH[/bold magenta]")
        if enigma.is_online:
            try:
                # Use wallet address as agent_id for Enigma
                enigma_metrics = {
                    "SS": metrics["SS"],
                    "GCR": metrics["GCR"],
                    "PFI": metrics["PFI"],
                    "AST_score": ast_result.score,
                    "ACR": metrics.get("ACR", 0.0),
                }
                snapshot = {
                    "certificate_hash": cert.certificate_hash,
                    "task_id": task_id,
                    "agent_name": agent["name"],
                    "token_id": agent["token_id"],
                    "wallet": agent["wallet"],
                }
                trust_score = enigma.publish_trust_score(
                    agent_id=agent["wallet"],
                    metrics=enigma_metrics,
                    snapshot_data=snapshot,
                )
                console.print(f"    [green]PUBLISHED[/green] to enigma-dev")
                console.print(f"    overall={trust_score.overall_score:.2f} "
                              f"uptime={trust_score.uptime_score:.2f} "
                              f"proxy={trust_score.proxy_score:.2f} "
                              f"oz_match={trust_score.oz_match_score:.2f} "
                              f"community={trust_score.community_score:.2f}")
                agent_result["enigma"] = {"status": "published", "overall_score": trust_score.overall_score}
            except Exception as e:
                console.print(f"    [red]FAILED: {e}[/red]")
                agent_result["enigma"] = {"status": "error", "error": str(e)}
        else:
            console.print(f"    [yellow]OFFLINE — skipping Enigma publish[/yellow]")
            agent_result["enigma"] = {"status": "offline"}

        # ─── AVALANCHE ON-CHAIN ───────────────────────────────────────
        console.print("\n  [bold magenta]AVALANCHE ON-CHAIN[/bold magenta]")
        if avax.is_online and publishable:
            try:
                console.print(f"    Sending to Avalanche C-Chain...")
                compliant = cert.governance_status == "COMPLIANT"
                tx_result = avax.send_attestation(
                    certificate_hash=cert.certificate_hash,
                    agent_id=agent["wallet"].lower().replace("0x", "").ljust(64, "0"),
                    compliant=compliant,
                )
                if tx_result["status"] == "confirmed":
                    console.print(f"    [green]CONFIRMED[/green]")
                    console.print(f"    TX: [cyan]{tx_result['tx_hash']}[/cyan]")
                    console.print(f"    Block: [cyan]{tx_result['block_number']}[/cyan]")
                    console.print(f"    Gas: [cyan]{tx_result['gas_used']}[/cyan]")
                    console.print(f"    Snowtrace: [dim]https://snowtrace.io/tx/{tx_result['tx_hash']}[/dim]")
                    total_gas += tx_result["gas_used"]
                    agent_result["avalanche"] = tx_result
                else:
                    console.print(f"    [red]{tx_result['status']}: {tx_result.get('error', '')}[/red]")
                    agent_result["avalanche"] = tx_result
            except Exception as e:
                console.print(f"    [red]FAILED: {e}[/red]")
                agent_result["avalanche"] = {"status": "error", "error": str(e)}

            # ─── VERIFY ON-CHAIN ──────────────────────────────────────
            if agent_result.get("avalanche", {}).get("status") == "confirmed":
                console.print("\n  [bold magenta]ON-CHAIN VERIFY[/bold magenta]")
                verify_result = avax.verify_on_chain(cert.certificate_hash)
                if verify_result["status"] == "found":
                    console.print(f"    [green]EXISTS[/green] on-chain")
                    console.print(f"    Compliant: [green]{verify_result['compliant']}[/green]")
                    console.print(f"    Timestamp: [cyan]{verify_result['timestamp']}[/cyan]")
                    console.print(f"    Submitter: [dim]{verify_result['submitter']}[/dim]")
                else:
                    console.print(f"    [yellow]{verify_result['status']}[/yellow]")
                agent_result["on_chain_verify"] = verify_result
        elif not avax.is_online:
            console.print(f"    [yellow]OFFLINE — skipping on-chain publish[/yellow]")
            agent_result["avalanche"] = {"status": "offline"}
        else:
            console.print(f"    [yellow]Not publishable — skipping[/yellow]")
            agent_result["avalanche"] = {"status": "skipped"}

        # ─── MEMORY ───────────────────────────────────────────────────
        console.print("\n  [bold magenta]MEMORY[/bold magenta]")
        try:
            summary = (
                f"Agent #{agent['token_id']} ({agent['name']}): "
                f"governance={cert.governance_status}, SS={metrics['SS']}, GCR={metrics['GCR']}, "
                f"z3_verified={cert.z3_verified}, cert={cert.certificate_hash[:16]}..."
            )
            entry = memory.add(content=summary, category="knowledge")
            console.print(f"    [green]Saved[/green] memory ID: [dim]{entry.id}[/dim]")
            agent_result["memory_id"] = entry.id
        except Exception as e:
            console.print(f"    [yellow]Memory save: {e}[/yellow]")

        agent_result["status"] = "completed"
        results.append(agent_result)

    # ─── SUMMARY ──────────────────────────────────────────────────────
    console.print(f"\n{'═' * 70}")
    console.print(Panel("[bold cyan]SUMMARY[/bold cyan]", title="Results"))

    summary_table = Table(title="Agent Results", show_lines=True)
    summary_table.add_column("Agent", style="bold")
    summary_table.add_column("Governance", justify="center")
    summary_table.add_column("Z3", justify="center")
    summary_table.add_column("Enigma", justify="center")
    summary_table.add_column("Avalanche TX", justify="center")

    for r in results:
        gov = r.get("governance", {})
        gov_str = f"[green]PASS ({gov.get('score', 0):.2f})[/green]" if gov.get("passed") else "[red]FAIL[/red]"

        z3 = r.get("z3", {})
        z3_str = f"[green]4/4[/green]" if z3.get("all_verified") else "[red]FAIL[/red]"

        enigma_status = r.get("enigma", {}).get("status", "?")
        enigma_str = f"[green]{enigma_status}[/green]" if enigma_status == "published" else f"[yellow]{enigma_status}[/yellow]"

        avax_status = r.get("avalanche", {}).get("status", "?")
        if avax_status == "confirmed":
            tx = r["avalanche"].get("tx_hash", "")[:12]
            avax_str = f"[green]{tx}...[/green]"
        else:
            avax_str = f"[yellow]{avax_status}[/yellow]"

        summary_table.add_row(
            f"#{r['token_id']} {r['name']}",
            gov_str, z3_str, enigma_str, avax_str,
        )

    console.print(summary_table)

    if total_gas > 0:
        console.print(f"\n  Total gas used: [cyan]{total_gas:,}[/cyan]")

    if avax.is_online:
        total_after = avax.total_attestations()
        balance_after = avax.get_balance()
        console.print(f"  On-chain attestations: [cyan]{total_after}[/cyan]")
        console.print(f"  Wallet balance: [cyan]{balance_after:.6f} AVAX[/cyan]")

    console.print(f"\n  Contract: [dim]https://snowtrace.io/address/{REGISTRY_ADDRESS}[/dim]")

    for r in results:
        tx_hash = r.get("avalanche", {}).get("tx_hash", "")
        if tx_hash:
            console.print(f"  #{r['token_id']}: [dim]https://snowtrace.io/tx/{tx_hash}[/dim]")

    # ─── SAVE RESULTS ─────────────────────────────────────────────────
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    results_path = os.path.join(logs_dir, "live_test_results.json")
    output_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "registry_address": REGISTRY_ADDRESS,
        "erc721_contract": ERC721_CONTRACT,
        "agents": results,
        "total_gas": total_gas,
    }
    with open(results_path, "w") as f:
        json.dump(output_data, f, indent=2, default=str)
    console.print(f"\n  Results saved: [dim]{results_path}[/dim]")
    console.print()


if __name__ == "__main__":
    main()
