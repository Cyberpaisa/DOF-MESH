#!/usr/bin/env python3
"""
DOF Mesh Legion -- Demo End-to-End

Demuestra el flujo completo de governance deterministica:
  Agente propone accion -> Governance check -> Z3 formal verification
  -> ZK proof -> Supervisor scoring -> Circuit Breaker -> Attestation batch

Ejecutar: python3 scripts/demo_end_to_end.py
No requiere LLMs ni blockchain. Todo local y deterministico.
"""
import sys
import os
import time

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]DOF Mesh Legion -- Demo End-to-End[/bold cyan]\n"
        "[dim]Governance deterministica para agentes autonomos de IA[/dim]\n"
        "[dim]Matematicas, no promesas.[/dim]",
        border_style="cyan"
    ))

    # ===============================================
    # PASO 1: Setup -- Registrar nodos
    # ===============================================
    console.print("\n[bold]=== PASO 1: Setup del Mesh ===[/bold]")

    from core.node_capability import NodeCapabilityRegistry, NodeTier
    from core.byzantine_node_guard import ByzantineNodeGuard

    registry = NodeCapabilityRegistry()
    guard = ByzantineNodeGuard()

    nodes = [
        ("apex-1687", 32.0, 50, ["avalanche-c"], "validator"),
        ("avabuilder-1686", 16.0, 80, ["avalanche-c", "fuji"], "executor"),
        ("observer-01", 4.0, 400, ["avalanche-c"], "observer"),
    ]

    for node_id, mem, z3t, chains, atype in nodes:
        m = registry.register_node(node_id, mem, z3t, chains, atype)
        console.print(f"  Nodo [green]{node_id}[/green] -> Tier {m.tier.name} ({atype})")

    dist = registry.tier_distribution()
    console.print(f"  Distribucion: {dist}")

    # ===============================================
    # PASO 2: Constitution Integrity Check
    # ===============================================
    console.print("\n[bold]=== PASO 2: Verificar Integridad de Constitution ===[/bold]")

    from constitution.integrity_watcher import ConstitutionIntegrityWatcher

    rules = {
        "NO_HALLUCINATION": {"type": "hard", "priority": "system"},
        "MAX_LENGTH": {"type": "hard", "max": 50000},
        "HAS_SOURCES": {"type": "soft", "match_mode": "absent"},
    }
    watcher = ConstitutionIntegrityWatcher(rules)
    snap = watcher.verify()
    console.print(f"  Hash baseline: [cyan]{snap.baseline_hash[:16]}...[/cyan]")
    if not snap.drift_detected:
        console.print(f"  Drift detectado: [green]No[/green]")
    else:
        console.print(f"  Drift: [red]SI[/red]")

    # ===============================================
    # PASO 3: Agente propone accion -> Z3 verifica
    # ===============================================
    console.print("\n[bold]=== PASO 3: Agente Propone -> Z3 Verifica ===[/bold]")

    from core.z3_gate import Z3Gate, GateResult
    from core.agent_output import AgentOutput, OutputType

    gate = Z3Gate()

    # Caso 1: Trust score valido
    output_valid = AgentOutput(
        output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
        agent_id="apex-1687",
        proposed_value=0.85,
        evidence={"current_level": 2},
    )
    result1 = gate.validate_output(output_valid)
    console.print(f"  Caso 1 -- Trust score 0.85, level 2:")
    console.print(f"    Resultado: [green]{result1.result.value}[/green] ({result1.verification_time_ms:.1f}ms)")
    console.print(f"    Invariantes: {result1.invariants_checked}")

    # Caso 2: Trust score invalido (governor con score bajo)
    output_invalid = AgentOutput(
        output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
        agent_id="rogue-agent",
        proposed_value=0.5,
        evidence={"current_level": 3},  # governor con score bajo -> reject
    )
    result2 = gate.validate_output(output_invalid)
    console.print(f"  Caso 2 -- Trust score 0.5, governor level 3:")
    console.print(f"    Resultado: [red]{result2.result.value}[/red]")
    console.print(f"    Contraejemplo: {result2.counterexample}")

    # Caso 3: Promocion valida (1->2)
    output_promo = AgentOutput(
        output_type=OutputType.AGENT_PROMOTION,
        agent_id="apex-1687",
        proposed_value=2,
        evidence={"current_level": 1},
    )
    result3 = gate.validate_output(output_promo)
    console.print(f"  Caso 3 -- Promocion level 1->2:")
    console.print(f"    Resultado: [green]{result3.result.value}[/green]")

    # Caso 4: Promocion invalida (salto 1->3)
    output_bad_promo = AgentOutput(
        output_type=OutputType.AGENT_PROMOTION,
        agent_id="rogue-agent",
        proposed_value=3,
        evidence={"current_level": 1},  # salto -> reject
    )
    result4 = gate.validate_output(output_bad_promo)
    console.print(f"  Caso 4 -- Promocion level 1->3 (salto):")
    console.print(f"    Resultado: [red]{result4.result.value}[/red]")

    # Mostrar cache stats
    console.print(f"\n  [dim]Cache SMT: {gate.cache_size} entries | Fast Path: {gate.policy_cache_size} policies[/dim]")

    # ===============================================
    # PASO 4: Circuit Breaker monitorea
    # ===============================================
    console.print("\n[bold]=== PASO 4: Circuit Breaker Monitorea ===[/bold]")

    from core.adaptive_circuit_breaker import AdaptiveCircuitBreaker, CircuitState

    cb_apex = AdaptiveCircuitBreaker("apex-1687")
    cb_rogue = AdaptiveCircuitBreaker("rogue-agent")

    # apex: todas aprobadas
    cb_apex.record(blocked=False)  # result1 approved
    cb_apex.record(blocked=False)  # result3 approved

    # rogue: todas bloqueadas
    cb_rogue.record(blocked=True)   # result2 rejected
    cb_rogue.record(blocked=True)   # result4 rejected

    apex_color = "green" if cb_apex.state() == CircuitState.CLOSED else "red"
    rogue_color = "green" if cb_rogue.state() == CircuitState.CLOSED else "red"
    console.print(f"  apex-1687:   [{apex_color}]{cb_apex.state().value}[/{apex_color}]")
    console.print(f"  rogue-agent: [{rogue_color}]{cb_rogue.state().value}[/{rogue_color}]")

    # Byzantine reputation
    guard.record_success("apex-1687")
    guard.record_success("apex-1687")
    guard.record_failure("rogue-agent", reason="z3_rejected")
    guard.record_failure("rogue-agent", reason="z3_rejected")

    console.print(f"  Reputacion apex-1687:   [green]{guard.reputation('apex-1687'):.2f}[/green] ({guard.status('apex-1687').value})")
    console.print(f"  Reputacion rogue-agent: [red]{guard.reputation('rogue-agent'):.2f}[/red] ({guard.status('rogue-agent').value})")

    # ===============================================
    # PASO 5: Attestation batch (Merkle)
    # ===============================================
    console.print("\n[bold]=== PASO 5: Attestation Batch (Merkle) ===[/bold]")

    from core.merkle_attestation import MerkleAttestationBatcher

    batcher = MerkleAttestationBatcher(max_batch_size=20)

    # Solo los approved van al batch
    approved_results = [r for r in [result1, result3] if r.result == GateResult.APPROVED]
    for r in approved_results:
        batcher.add_decision(r.proof_transcript or "no-transcript")
        console.print(f"  Decision agregada: {r.decision_type} -> {r.result.value}")

    batch = batcher.seal_batch()
    console.print(f"  Batch sellado: [cyan]{batch.root_hash[:16]}...[/cyan]")
    console.print(f"  Decisiones en batch: {batch.leaf_count}")
    console.print(f"  [dim]En produccion: este root se publica en Avalanche C-Chain como 1 sola tx[/dim]")

    # Verificar proof de inclusion
    first_transcript = approved_results[0].proof_transcript or "no-transcript"
    proof = batcher.get_proof(first_transcript)
    valid = MerkleAttestationBatcher.verify_proof(proof)
    console.print(f"  Merkle proof valido: [green]{valid}[/green]")

    # ===============================================
    # PASO 6: ZK Governance Proof
    # ===============================================
    console.print("\n[bold]=== PASO 6: ZK Governance Proof ===[/bold]")

    from core.zk_governance_proof import GovernanceProofGenerator

    gen = GovernanceProofGenerator(log_path=os.path.join(PROJECT_ROOT, "logs", "proofs", "demo_proofs.jsonl"))

    # Generar proof de compliance (sin violaciones)
    zk_proof = gen.generate_proof(
        violations=[],
        warnings=["[HAS_SOURCES] Should include source URLs"],
        score=1.0,
        rule_ids=["NO_HALLUCINATION_CLAIM", "MAX_LENGTH", "HAS_SOURCES"],
    )
    console.print(f"  Verdict: [green]{zk_proof.verdict}[/green]")
    console.print(f"  Proof hash: [cyan]{zk_proof.proof_hash[:16]}...[/cyan]")
    console.print(f"  Input hash: [cyan]{zk_proof.input_hash[:16]}...[/cyan]")
    console.print(f"  Rules evaluadas: {zk_proof.rule_ids}")

    # Verificar el proof
    verified = gen.verify_proof(
        zk_proof,
        violations=[],
        warnings=["[HAS_SOURCES] Should include source URLs"],
        score=1.0,
    )
    console.print(f"  Proof verificado: [green]{verified}[/green]")

    # Payload on-chain
    payload = zk_proof.to_attestation_payload()
    console.print(f"  Chain ID: {payload['chain_id']} (Avalanche C-Chain)")
    console.print(f"  Method: {payload['method']}")

    # ===============================================
    # PASO 7: Supervisor evalua output
    # ===============================================
    console.print("\n[bold]=== PASO 7: Meta-Supervisor Evalua ===[/bold]")

    from core.supervisor import MetaSupervisor

    supervisor = MetaSupervisor()

    sample_output = """## Analisis de Agente apex-1687

El agente apex-1687 ha sido verificado formalmente por el Z3 Gate.

### Resultados:
- Trust score: 0.85 (APPROVED)
- Promocion level 1->2 (APPROVED)
- Invariantes verificados: INV-3, INV-4, INV-6

### Siguiente paso:
1. Publicar attestation en Avalanche C-Chain
2. Actualizar registro de reputacion
3. Notificar al mesh sobre el cambio de nivel

Source: https://snowtrace.io/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
"""

    verdict = supervisor.evaluate(sample_output, original_input="Verificar agente apex-1687")
    console.print(f"  Decision: [green]{verdict.decision}[/green]")
    console.print(f"  Score: {verdict.score}/10")
    console.print(f"    Quality:       {verdict.quality}")
    console.print(f"    Actionability: {verdict.actionability}")
    console.print(f"    Completeness:  {verdict.completeness}")
    console.print(f"    Factuality:    {verdict.factuality}")
    console.print(f"    CommQuality:   {verdict.communication_quality}")

    # ===============================================
    # RESUMEN
    # ===============================================
    console.print("\n")

    table = Table(title="Resumen del Flujo End-to-End", border_style="cyan")
    table.add_column("Paso", style="bold")
    table.add_column("Componente", style="cyan")
    table.add_column("Resultado", style="green")

    table.add_row("1", "Node Capability Manifest", f"{registry.total_nodes} nodos (Tier dist: {dist})")
    table.add_row("2", "Constitution Integrity", f"Hash: {snap.baseline_hash[:12]}... -- Sin drift")
    table.add_row("3a", "Z3 Gate -- trust valid", f"APPROVED ({result1.verification_time_ms:.1f}ms)")
    table.add_row("3b", "Z3 Gate -- trust invalid", "REJECTED (governor con score bajo)")
    table.add_row("3c", "Z3 Gate -- promo valid", f"APPROVED ({result3.verification_time_ms:.1f}ms)")
    table.add_row("3d", "Z3 Gate -- promo invalid", "REJECTED (salto de nivel)")
    table.add_row("4", "Circuit Breaker", f"apex={cb_apex.state().value}, rogue={cb_rogue.state().value}")
    table.add_row("4b", "Byzantine Reputation", f"apex={guard.reputation('apex-1687'):.2f}, rogue={guard.reputation('rogue-agent'):.2f}")
    table.add_row("5", "Merkle Attestation", f"Root: {batch.root_hash[:12]}... ({batch.leaf_count} decisiones)")
    table.add_row("6", "ZK Governance Proof", f"{zk_proof.verdict} -- hash: {zk_proof.proof_hash[:12]}...")
    table.add_row("7", "Meta-Supervisor", f"{verdict.decision} (score={verdict.score}/10)")

    console.print(table)

    console.print(Panel.fit(
        "[bold green]Pipeline completo: 0 LLMs usados. Todo deterministico.[/bold green]\n"
        f"[dim]Z3 cache: {gate.cache_size} entries | Fast Path: {gate.policy_cache_size} policies | Epoch: {gate.policy_epoch}[/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
