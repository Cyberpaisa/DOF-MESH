"""
Crew Runner — Integrates FASE 0 + FASE 1 infrastructure.

Wraps crew.kickoff() with:
  - Provider resilience (TTL, backoff, auto-recovery)
  - Step-level checkpointing
  - Structured metrics logging
  - Constitution enforcement
  - Meta-supervisor quality gating
  - 3-retry with provider rotation
  - Run-level observability (RunTrace with UUID, tokens, derived metrics)

Usage:
    from core.crew_runner import run_crew
    result = run_crew("research", crew, input_text="ERC-8004 market analysis")
"""

import os
import time
import uuid
import logging
from typing import Any

from core.providers import ProviderManager, BayesianProviderSelector
from core.checkpointing import CheckpointManager
from core.metrics import MetricsLogger
from core.governance import ConstitutionEnforcer
from core.supervisor import MetaSupervisor
from core.observability import (
    RunTrace, StepTrace, RunTraceStore, compute_derived_metrics,
    estimate_tokens, get_session_id, DETERMINISTIC_MODE, TokenTracker,
)
from core.execution_dag import ExecutionDAG
from core.loop_guard import LoopGuard

logger = logging.getLogger("core.crew_runner")

MAX_RETRIES = 3


def run_crew(crew_name: str, crew: Any, input_text: str = "",
             max_retries: int = MAX_RETRIES, skip_supervisor: bool = False,
             mode: str = "production", crew_factory=None,
             adversarial_mode: bool = False,
             contract_path: str = "",
             governed_memory: bool = False,
             oracle_mode: bool = False) -> dict:
    """Execute a crew with full FASE 0 + FASE 1 infrastructure.

    Args:
        crew_factory: Optional callable() -> Crew. When provided, the crew is
            rebuilt on each retry so exhausted providers are skipped and new
            LLMs are assigned. If None, the same crew object is reused.
        adversarial_mode: When True, run Red Team → Guardian → Arbiter
            evaluation after successful execution.
        contract_path: Optional path to a TASK_CONTRACT.md file. When provided,
            preconditions are checked before kickoff and quality gates +
            postconditions are verified after execution.
        governed_memory: When True, store execution results in GovernedMemoryStore
            (success → "knowledge", failure → "errors").
        oracle_mode: When True, create an ERC-8004 attestation certificate
            after successful execution (ACCEPT). Only COMPLIANT attestations
            are published on-chain.

    Returns dict with:
        status, output, run_id, summary, supervisor, governance,
        retries, elapsed_ms, trace_path, adversarial (if enabled),
        contract (if contract_path provided), attestation (if oracle_mode)
    """
    pm = ProviderManager()
    bayesian = BayesianProviderSelector()
    metrics = MetricsLogger()
    checkpoint = CheckpointManager()
    enforcer = ConstitutionEnforcer()
    supervisor = MetaSupervisor()
    trace_store = RunTraceStore()
    token_tracker = TokenTracker()

    memory_store = None
    if governed_memory:
        try:
            from core.memory_governance import GovernedMemoryStore
            memory_store = GovernedMemoryStore()
        except Exception as e:
            logger.warning(f"GovernedMemoryStore init failed: {e} — continuing without memory")

    run_id = str(uuid.uuid4())
    checkpoint.run_id = run_id
    start = time.time()

    # Initialize RunTrace
    trace = RunTrace(
        run_id=run_id,
        session_id=get_session_id(),
        crew_name=crew_name,
        mode=mode,
        timestamp_start=time.strftime("%Y-%m-%dT%H:%M:%S"),
        start_epoch=start,
        deterministic=DETERMINISTIC_MODE,
        input_text=input_text[:500],
        input_hash=checkpoint._hash_input(input_text),
    )

    # Initialize Execution DAG and Loop Guard
    dag = ExecutionDAG()
    dag.add_node("crew_start", "AGENT", {"agent_name": crew_name, "run_id": run_id})
    loop_guard = LoopGuard(max_iterations=max_retries + 1)

    metrics.log_crew_start(run_id, crew_name, input_text)
    logger.info(f"[{run_id[:8]}] Starting crew '{crew_name}' (providers: {pm.get_active()})")

    # ─── Contract: load and check preconditions ──────────────────
    contract = None
    if contract_path:
        from core.task_contract import TaskContract
        try:
            contract = TaskContract.from_file(contract_path)
            pre_ctx = {
                "topic_provided": bool(input_text),
                "providers_available": len(pm.get_active()) > 0,
            }
            pre_ok, pre_failures = contract.check_preconditions(pre_ctx)
            if not pre_ok:
                logger.warning(f"[{run_id[:8]}] Contract preconditions FAILED: {pre_failures}")
                return {
                    "status": "contract_breach",
                    "output": "",
                    "error": f"Precondition failures: {pre_failures}",
                    "run_id": run_id,
                    "contract": {"phase": "preconditions", "failures": pre_failures},
                    "retries": 0,
                    "elapsed_ms": (time.time() - start) * 1000,
                }
        except FileNotFoundError:
            logger.warning(f"[{run_id[:8]}] Contract file not found: {contract_path}")
            contract = None

    last_error = ""
    output = ""
    retry_count = 0
    prev_provider = ""

    for attempt in range(1, max_retries + 1):
        step_id = f"{crew_name}_attempt_{attempt}"
        active = pm.get_active()

        # Rebuild crew on retry if factory is available
        if attempt > 1 and crew_factory is not None:
            logger.info(f"[{run_id[:8]}] Rebuilding crew with active providers: {active}")
            try:
                crew = crew_factory()
            except Exception as e:
                logger.error(f"[{run_id[:8]}] crew_factory failed: {e}")
                last_error = f"crew_factory error: {e}"
                break

        if not active:
            logger.error(f"[{run_id[:8]}] No providers available, attempt {attempt}")
            metrics.log_agent_step(run_id, crew_name, "none", 0, "no_providers", attempt)
            step = StepTrace(
                step_index=len(trace.steps),
                agent=crew_name,
                provider="none",
                status="failed",
                error="no_providers_available",
                retries=attempt - 1,
                token_input=estimate_tokens(input_text),
            )
            trace.steps.append(step)
            break

        current_provider = ",".join(active)
        checkpoint.start_step(step_id, crew_name, crew_name,
                              provider=current_provider, input_text=input_text)

        # L0 Triage — deterministic pre-LLM filter (zero LLM cost)
        try:
            from core.l0_triage import L0Triage
            triage = L0Triage()
            triage_result = triage.evaluate(
                input_text=input_text,
                attempt=attempt,
                active_providers=active,
                prev_errors=[s.error for s in trace.steps if s.error] if trace.steps else None,
            )
            if not triage_result.proceed:
                logger.warning(
                    f"[{run_id[:8]}] L0 Triage SKIP at attempt {attempt}: {triage_result.reason}"
                )
                metrics.log_agent_step(run_id, crew_name, "l0_triage", 0, f"skip:{triage_result.reason}", attempt)
                continue
        except ImportError:
            pass  # L0 triage not available, proceed normally

        try:
            step_start = time.time()
            result = crew.kickoff()
            step_ms = (time.time() - step_start) * 1000

            output = result.raw if hasattr(result, "raw") else str(result)

            # Guard: silent empty-output from provider — treat as retriable failure
            # Prevents "" from reaching governance and poisoning governance_compliance_rate
            if not output or len(output.strip()) < 10:
                logger.warning(
                    f"[{run_id[:8]}] Provider '{current_provider}' returned empty output "
                    f"at attempt {attempt} — logging EmptyOutput, retrying"
                )
                last_error = "empty_output_from_provider"
                metrics.log_agent_step(
                    run_id, crew_name, current_provider, step_ms, "empty_output", attempt
                )
                trace.steps.append(StepTrace(
                    step_index=len(trace.steps),
                    agent=crew_name,
                    provider=current_provider,
                    latency_ms=round(step_ms, 1),
                    retries=attempt - 1,
                    status="failed",
                    error="empty_output_from_provider",
                    error_class="EmptyOutput",
                    token_input=estimate_tokens(input_text),
                ))
                continue  # skips governance — retries with next provider

            # Log token usage
            token_tracker.log_call(
                provider=current_provider,
                model=crew_name,
                prompt_tokens=estimate_tokens(input_text),
                completion_tokens=estimate_tokens(output),
                latency_ms=step_ms,
            )

            # Loop Guard check
            guard_result = loop_guard.check(output, attempt - 1)
            if guard_result.status == "LOOP_DETECTED":
                logger.warning(
                    f"[{run_id[:8]}] LoopGuard: output loop detected at attempt {attempt} "
                    f"(similarity={guard_result.similarity_score:.3f} with attempt {guard_result.matched_iteration + 1})"
                )
                # Break out — don't retry with identical output
                break

            # DAG: add step node and edges
            step_node_id = f"step_{attempt}"
            dag.add_node(step_node_id, "AGENT", {
                "agent_name": f"{crew_name}_attempt_{attempt}",
                "provider": current_provider,
                "duration_ms": round(step_ms, 1),
            })
            dag.nodes[step_node_id].duration_ms = round(step_ms, 1)
            dag.nodes[step_node_id].status = "COMPLETED"
            prev_dag_node = "crew_start" if attempt == 1 else f"step_{attempt - 1}"
            dag.add_edge(prev_dag_node, step_node_id, "DELEGATES")

            checkpoint.complete_step(step_id, output[:2000])
            metrics.log_agent_step(run_id, crew_name, current_provider, step_ms, "ok", attempt)

            # Governance check
            gov_result = enforcer.check(output)
            metrics.log_governance(run_id, gov_result.passed, gov_result.score, gov_result.violations)

            # Generar ZK proof de la decisión de governance
            try:
                from core.zk_governance_proof import GovernanceProofGenerator
                gen = GovernanceProofGenerator()
                proof = gen.generate_proof_from_result(gov_result)
                logger.info(f"[{run_id[:8]}] ZK proof: {proof.proof_hash[:16]}... verdict={proof.verdict}")
            except Exception as e:
                logger.debug(f"ZK proof skip: {e}")

            # DAG: governance node
            gov_node_id = f"gov_{attempt}"
            dag.add_node(gov_node_id, "GOVERNANCE", {
                "agent_name": f"governance_{attempt}",
                "passed": gov_result.passed,
                "score": gov_result.score,
            })
            dag.nodes[gov_node_id].status = "COMPLETED"
            dag.add_edge(step_node_id, gov_node_id, "VERIFIES")

            # Supervisor evaluation
            sup_verdict = None
            if not skip_supervisor:
                sup_verdict = supervisor.evaluate(output, input_text, retry_count)
                metrics.log_supervisor(run_id, sup_verdict.decision, {
                    "score": sup_verdict.score,
                    "Q": sup_verdict.quality,
                    "A": sup_verdict.actionability,
                    "C": sup_verdict.completeness,
                    "F": sup_verdict.factuality,
                })

            # Build step trace
            step = StepTrace(
                step_index=len(trace.steps),
                agent=crew_name,
                provider=current_provider,
                latency_ms=round(step_ms, 1),
                retries=attempt - 1,
                status="completed",
                supervisor_score=sup_verdict.score if sup_verdict else 0.0,
                governance_passed=gov_result.passed,
                token_input=estimate_tokens(input_text),
                token_output=estimate_tokens(output),
                provider_switched=(prev_provider != "" and prev_provider != current_provider),
            )
            trace.steps.append(step)
            prev_provider = current_provider

            if not gov_result.passed:
                logger.warning(f"[{run_id[:8]}] Governance BLOCKED: {gov_result.violations}")
                if attempt < max_retries:
                    retry_count = attempt
                    continue
                output = f"Governance warnings: {gov_result.violations}\n\n{output}"

            if sup_verdict and sup_verdict.decision == "RETRY" and attempt < max_retries:
                logger.info(f"[{run_id[:8]}] Supervisor RETRY: {sup_verdict.reasons}")
                retry_count = attempt
                continue

            if sup_verdict and sup_verdict.decision == "ESCALATE":
                trace.status = "escalated"
                trace.supervisor_score_final = sup_verdict.score
                trace.supervisor_decision = sup_verdict.decision
                trace.output_len = len(output)
                trace.end_epoch = time.time()
                trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
                trace_path = trace_store.save(trace)

                elapsed_ms = (time.time() - start) * 1000
                metrics.log_crew_end(run_id, crew_name, "escalated", elapsed_ms, len(output))

                return {
                    "status": "escalated",
                    "output": output,
                    "run_id": run_id,
                    "summary": checkpoint.get_summary(),
                    "supervisor": {"decision": sup_verdict.decision, "score": sup_verdict.score, "reasons": sup_verdict.reasons},
                    "governance": {"passed": gov_result.passed, "score": gov_result.score},
                    "retries": attempt - 1,
                    "elapsed_ms": elapsed_ms,
                    "trace_path": trace_path,
                    "bayesian": bayesian.get_all_confidences(),
                    "dag": None,
                    "token_tracker": token_tracker.to_dict(),
                }

            # Success — update Bayesian beliefs
            for p in current_provider.split(","):
                bayesian.record_success(p.strip())

            trace.status = "ok"
            trace.supervisor_score_final = sup_verdict.score if sup_verdict else 0.0
            trace.supervisor_decision = sup_verdict.decision if sup_verdict else "skipped"
            trace.output_len = len(output)
            trace.end_epoch = time.time()
            trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
            trace_path = trace_store.save(trace)

            elapsed_ms = (time.time() - start) * 1000
            metrics.log_crew_end(run_id, crew_name, "ok", elapsed_ms, len(output))

            # Save DAG
            try:
                dag_cycles = dag.detect_cycles()
                dag_cp = dag.critical_path()
                dag_path = dag.save()
                logger.info(f"[{run_id[:8]}] DAG saved: {len(dag.nodes)} nodes, {len(dag.edges)} edges, {len(dag_cycles)} cycles")
            except Exception as e:
                logger.warning(f"DAG save failed: {e}")
                dag_path = ""
                dag_cycles = []
                dag_cp = {}

            result_dict = {
                "status": "ok",
                "output": output,
                "run_id": run_id,
                "summary": checkpoint.get_summary(),
                "supervisor": {
                    "decision": sup_verdict.decision if sup_verdict else "skipped",
                    "score": sup_verdict.score if sup_verdict else 0,
                    "reasons": sup_verdict.reasons if sup_verdict else [],
                } if sup_verdict else None,
                "governance": {"passed": gov_result.passed, "score": gov_result.score},
                "retries": attempt - 1,
                "elapsed_ms": elapsed_ms,
                "trace_path": trace_path,
                "bayesian": bayesian.get_all_confidences(),
                "dag": {
                    "dag_id": dag.dag_id,
                    "nodes": len(dag.nodes),
                    "edges": len(dag.edges),
                    "cycles": dag_cycles,
                    "critical_path": dag_cp,
                    "dag_path": dag_path,
                },
                "token_tracker": token_tracker.to_dict(),
            }

            # Adversarial evaluation (optional)
            if adversarial_mode:
                from core.adversarial import AdversarialEvaluator
                adv = AdversarialEvaluator()
                adv_result = adv.evaluate(output, input_text)
                result_dict["adversarial"] = {
                    "verdict": adv_result.verdict,
                    "acr": adv_result.acr,
                    "score": adv_result.score,
                    "total_issues": adv_result.total_issues,
                    "resolved": len(adv_result.resolved),
                    "unresolved": len(adv_result.unresolved),
                }

            # Governed memory: store successful result
            if memory_store:
                try:
                    summary = output[:2000]
                    memory_store.add(
                        content=summary,
                        category="knowledge",
                        metadata={
                            "task": crew_name,
                            "run_id": run_id,
                            "score": sup_verdict.score if sup_verdict else 0.0,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Memory store (success) failed: {e}")

            # Contract: verify quality gates and postconditions
            if contract:
                contract_ctx = {
                    "supervisor_score": sup_verdict.score if sup_verdict else 0.0,
                    "input_text": input_text,
                    "log_path": os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "logs", "execution_log.jsonl",
                    ),
                }
                contract_result = contract.is_fulfilled(output, contract_ctx)
                result_dict["contract"] = {
                    "fulfilled": contract_result.fulfilled,
                    "passed_gates": contract_result.passed_gates,
                    "failed_gates": contract_result.failed_gates,
                    "evidence": contract_result.evidence,
                }
                if not contract_result.fulfilled:
                    logger.warning(
                        f"[{run_id[:8]}] Contract NOT fulfilled: "
                        f"{contract_result.failed_gates}"
                    )

            # Oracle attestation (optional)
            if oracle_mode:
                try:
                    from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationRegistry
                    from core.oags_bridge import OAGSIdentity

                    signer = CertificateSigner()
                    identity = OAGSIdentity()
                    bridge = OracleBridge(signer, identity)

                    # Collect metrics for attestation
                    derived = compute_derived_metrics(trace)
                    attestation_metrics = {
                        "SS": derived.get("stability_score", 0.0),
                        "GCR": derived.get("governance_compliance_rate", 0.0),
                        "PFI": derived.get("provider_failure_index", 0.0),
                        "RP": derived.get("recovery_probability", 0.0),
                        "SSR": derived.get("supervisor_score_reliability", 0.0),
                    }

                    cert = bridge.create_attestation(
                        task_id=run_id,
                        metrics=attestation_metrics,
                    )

                    # Persist to registry
                    registry = AttestationRegistry()
                    registry.add(cert)

                    result_dict["attestation"] = {
                        "certificate_hash": cert.certificate_hash,
                        "governance_status": cert.governance_status,
                        "z3_verified": cert.z3_verified,
                        "publishable": bridge.should_publish(cert),
                    }

                    # Publish to Enigma Scanner if attestation is publishable
                    if bridge.should_publish(cert):
                        enigma_result = bridge.publish_to_enigma(cert)
                        result_dict["enigma"] = enigma_result
                except Exception as e:
                    logger.warning(f"Oracle attestation failed: {e}")
                    result_dict["attestation"] = {"error": str(e)}

            return result_dict

        except Exception as e:
            error_str = str(e)
            step_ms = (time.time() - step_start) * 1000
            last_error = error_str

            checkpoint.fail_step(step_id, error_str)
            metrics.log_agent_step(run_id, crew_name, current_provider, step_ms, "error", attempt)

            # Step trace for failure
            step = StepTrace(
                step_index=len(trace.steps),
                agent=crew_name,
                provider=current_provider,
                latency_ms=round(step_ms, 1),
                retries=attempt - 1,
                status="failed",
                error=error_str[:200],
                token_input=estimate_tokens(input_text),
                token_output=0,
                provider_switched=(prev_provider != "" and prev_provider != current_provider),
            )
            trace.steps.append(step)
            prev_provider = current_provider

            # Update Bayesian beliefs for failure
            detected = pm.detect_provider(error_str)
            if detected:
                bayesian.record_failure(detected)

            # Detect and mark exhausted provider
            if detected:
                classified = pm.classify_error(error_str)
                pm.mark_exhausted(detected, error_str)
                metrics.log_provider_event(detected, "exhausted", error_str,
                                           pm._providers[detected].ttl_seconds)

            if attempt < max_retries:
                retry_count = attempt
                continue

    # All retries exhausted
    trace.status = "error"
    trace.end_epoch = time.time()
    trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
    trace_path = trace_store.save(trace)

    elapsed_ms = (time.time() - start) * 1000
    metrics.log_crew_end(run_id, crew_name, "error", elapsed_ms, 0)

    # Governed memory: store error
    if memory_store:
        try:
            error_summary = f"Crew '{crew_name}' failed after {max_retries} retries. Error: {last_error[:500]}"
            memory_store.add(
                content=error_summary,
                category="errors",
                metadata={"task": crew_name, "run_id": run_id, "error_class": "terminal_failure"},
            )
        except Exception as e:
            logger.warning(f"Memory store (error) failed: {e}")

    return {
        "status": "error",
        "output": "",
        "error": last_error[:500],
        "run_id": run_id,
        "summary": checkpoint.get_summary(),
        "supervisor": None,
        "governance": None,
        "retries": max_retries,
        "elapsed_ms": elapsed_ms,
        "trace_path": trace_path,
        "bayesian": bayesian.get_all_confidences(),
        "dag": None,
        "token_tracker": token_tracker.to_dict(),
    }


# ── CrewRunner class (for test compatibility) ──────────────────────────────────

class CrewRunner:
    """Singleton crew runner."""

    _instance = None
    _class_lock = __import__("threading").Lock()

    _SENTINEL = object()

    def __new__(cls, name=_SENTINEL):
        if name is not cls._SENTINEL:
            raise TypeError(f"CrewRunner() takes no arguments, got {type(name).__name__}")
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._running = False
                    cls._instance = inst
        return cls._instance

    def __init__(self, name=None):
        pass

    def run(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
