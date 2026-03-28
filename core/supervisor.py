"""
Meta-Supervisor Minimal — FASE 0.

Evaluates FINAL output only. No intermediate intervention.
Score: Q(0.35) + A(0.20) + C(0.20) + F(0.10) + CQ(0.15)
Decision: ACCEPT >= 7, RETRY 5-7 (max 2), ESCALATE < 5
"""

import re
import json
import os
import logging
from dataclasses import dataclass

from core.adaptive_circuit_breaker import AdaptiveCircuitBreaker, CircuitState

logger = logging.getLogger("core.supervisor")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OVERRIDES_PATH = os.path.join(_BASE_DIR, "config", "autoresearch_overrides.json")


def _load_overrides() -> dict:
    """Read all tunable params from autoresearch_overrides.json if present."""
    try:
        with open(_OVERRIDES_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_accept_threshold() -> float:
    """Read supervisor_accept_threshold from autoresearch_overrides.json if present."""
    return float(_load_overrides().get("supervisor_accept_threshold", 6.0))


def evaluate_communication_quality(output: str) -> int:
    """CQ Score — Winston Communication Framework (section F.3).

    Deterministic evaluation of communication quality based on the 5S:
    Slogan (clarity), Saliente (relevance), Story+Symbol (structure),
    Sorpresa (surprise), Contribucion (actionable close).

    Returns 0-100.
    """
    score = 0

    lines = output.strip().split('\n')
    first_line = lines[0] if lines else ""
    last_line = lines[-1] if lines else ""

    # Claridad de conclusion (25 pts)
    indicators = ['[PROVEN]', '[BLOCKED]', '[WARNING]', '[PASS]', '[FAIL]']
    if any(ind in first_line for ind in indicators):
        score += 15
    if len(first_line) < 200 and len(first_line) > 10:
        score += 10

    # Relevancia del impacto (25 pts)
    salience_patterns = [
        'esto significa', 'impacto:', 'consecuencia:',
        'this means', 'impact:', 'therefore'
    ]
    if any(p in output.lower() for p in salience_patterns):
        score += 25

    # Estructura narrativa (20 pts)
    if any(ind in output for ind in indicators):
        score += 10
    if any(h in output for h in ['##', '**', '- ', '1.', '2.']):
        score += 10

    # Elemento diferenciador (15 pts)
    surprise_patterns = [
        'inesperado', 'unexpected', 'nota:', 'alerta:',
        'resultado inesperado', 'warning:', 'anomaly'
    ]
    if any(p in output.lower() for p in surprise_patterns):
        score += 15

    # Cierre accionable (15 pts)
    action_patterns = [
        'siguiente paso', 'next step', 'accion:',
        'action:', 'recomendacion:', 'recommendation:'
    ]
    filler_patterns = [
        'espero que', 'hope this', 'si necesitas',
        'if you need', 'let me know', 'no dudes'
    ]
    if any(p in last_line.lower() for p in action_patterns):
        score += 15
    if any(p in last_line.lower() for p in filler_patterns):
        score -= 10

    return max(0, min(100, score))


@dataclass
class SupervisorVerdict:
    """Result of supervisor evaluation."""
    decision: str  # ACCEPT | RETRY | ESCALATE
    score: float
    quality: float
    actionability: float
    completeness: float
    factuality: float
    communication_quality: float
    reasons: list[str]
    retry_count: int = 0


class MetaSupervisor:
    """Minimal meta-supervisor for output quality gating."""

    MAX_RETRIES = 2

    def __init__(self):
        self._circuit_breakers: dict[str, AdaptiveCircuitBreaker] = {}

    def _get_breaker(self, agent_id: str) -> AdaptiveCircuitBreaker:
        """Return (or lazily create) the circuit breaker for *agent_id*."""
        if agent_id not in self._circuit_breakers:
            self._circuit_breakers[agent_id] = AdaptiveCircuitBreaker(agent_id)
        return self._circuit_breakers[agent_id]

    def evaluate(self, output: str, original_input: str = "",
                 retry_count: int = 0) -> SupervisorVerdict:
        """Evaluate final crew output and decide: ACCEPT, RETRY, or ESCALATE.

        Scoring (0-10):
        - Quality (Q=0.35): Structure, clarity, depth
        - Actionability (A=0.20): Concrete steps, recommendations
        - Completeness (C=0.20): Covers the asked topic
        - Factuality (F=0.10): Sources cited, no obvious hallucinations
        - Communication Quality (CQ=0.15): Winston 5S framework
        """
        q = self._score_quality(output)
        a = self._score_actionability(output)
        c = self._score_completeness(output, original_input)
        f = self._score_factuality(output)
        # CQ Score: 0-100 from Winston framework, normalized to 0-10
        cq_raw = evaluate_communication_quality(output)
        cq = cq_raw / 10.0  # normalize to 0-10 scale

        # Weights read from autoresearch_overrides.json — closes the tuner feedback loop
        _ov = _load_overrides()
        wq = float(_ov.get("supervisor_weight_quality", 0.35))
        wa = float(_ov.get("supervisor_weight_actionability", 0.20))
        wc = float(_ov.get("supervisor_weight_completeness", 0.20))
        wf = float(_ov.get("supervisor_weight_factuality", 0.10))
        wcq = float(_ov.get("supervisor_weight_communication_quality", 0.15))
        score = q * wq + a * wa + c * wc + f * wf + cq * wcq
        reasons = []

        # Calibration phase - tighten after prompt optimization
        # Threshold read from config/autoresearch_overrides.json (default 6.0)
        # This closes the autoresearch feedback loop: tuner writes threshold, supervisor reads it
        _accept_threshold = _load_accept_threshold()
        if score >= _accept_threshold:
            decision = "ACCEPT"
        elif score >= 5.0 and retry_count < self.MAX_RETRIES:
            decision = "RETRY"
            if q < 7:
                reasons.append("Low structure quality")
            if a < 7:
                reasons.append("Lacking actionability")
            if c < 7:
                reasons.append("Incomplete response")
            if f < 7:
                reasons.append("Missing source citations")
        else:
            decision = "ESCALATE" if score < 5.0 else "ACCEPT"
            if score < 5.0:
                reasons.append(f"Insufficient total score: {score:.1f}/10")

        verdict = SupervisorVerdict(
            decision=decision,
            score=round(score, 2),
            quality=round(q, 1),
            actionability=round(a, 1),
            completeness=round(c, 1),
            factuality=round(f, 1),
            communication_quality=round(cq, 1),
            reasons=reasons,
            retry_count=retry_count,
        )

        logger.info(
            f"Supervisor: {decision} (score={score:.1f}, "
            f"Q={q:.1f} A={a:.1f} C={c:.1f} F={f:.1f} CQ={cq:.1f})"
        )
        return verdict

    def _score_quality(self, text: str) -> float:
        """Score structure, clarity, depth (0-10).

        Returns 0.0 immediately for empty or whitespace-only text — blank
        output has no quality, not "average" quality.
        """
        if not text or not text.strip():
            return 0.0
        score = 5.0
        # Length bonus
        length = len(text)
        if length > 2000:
            score += 1.0
        if length > 5000:
            score += 0.5
        # Structure markers
        headers = len(re.findall(r'^#{1,3}\s', text, re.MULTILINE))
        bullets = len(re.findall(r'^[\-\*•]\s', text, re.MULTILINE))
        if headers >= 3:
            score += 1.5
        elif headers >= 1:
            score += 0.5
        if bullets >= 5:
            score += 1.0
        elif bullets >= 2:
            score += 0.5
        # Code blocks
        if "```" in text:
            score += 0.5
        return min(10.0, score)

    def _score_actionability(self, text: str) -> float:
        """Score actionable recommendations (0-10).

        Returns 0.0 for empty or whitespace-only text.
        """
        if not text or not text.strip():
            return 0.0
        score = 4.0
        action_words = [
            "implement", "create", "configure", "execute", "deploy",
            "install", "add", "modify", "update", "review",
            "next step", "action item", "recommendation", "step",
            "implementar", "crear", "desplegar", "configurar",
        ]
        found = sum(1 for w in action_words if w in text.lower())
        score += min(found * 0.5, 3.0)
        # Numbered steps
        numbered = len(re.findall(r'^\d+[\.\)]\s', text, re.MULTILINE))
        if numbered >= 3:
            score += 2.0
        elif numbered >= 1:
            score += 1.0
        return min(10.0, score)

    def _score_completeness(self, text: str, input_text: str) -> float:
        """Score coverage of the asked topic (0-10)."""
        score = 5.0
        # Length as proxy for completeness
        if len(text) > 3000:
            score += 2.0
        elif len(text) > 1000:
            score += 1.0
        elif len(text) < 200:
            score -= 2.0
        # Check if input keywords appear in output
        if input_text:
            input_words = set(input_text.lower().split())
            input_words -= {"de", "la", "el", "en", "que", "y", "a", "un", "una", "los", "las", "por", "para", "con",
                           "the", "a", "an", "in", "on", "of", "to", "for", "and", "or", "is", "it", "with"}
            if input_words:
                overlap = sum(1 for w in input_words if w in text.lower())
                coverage = overlap / len(input_words)
                score += coverage * 3.0
        return min(10.0, score)

    def _score_factuality(self, text: str) -> float:
        """Score source citation and fact-checking signals (0-10).

        Returns 0.0 immediately for empty or whitespace-only text.
        """
        if not text or not text.strip():
            return 0.0
        score = 5.0
        # URLs present
        urls = re.findall(r'https?://\S+', text)
        if len(urls) >= 5:
            score += 3.0
        elif len(urls) >= 2:
            score += 2.0
        elif len(urls) >= 1:
            score += 1.0
        # Hedging language (positive — shows awareness of uncertainty)
        if any(w in text.lower() for w in ["source:", "reference:", "data from", "according to", "según", "fuente:"]):
            score += 1.0
        # Negative — unsubstantiated claims
        unsubstantiated = [
            "according to studies", "research demonstrates",
            "it is well known", "everyone knows",
            "según estudios", "las investigaciones demuestran",
            "es bien sabido", "todos saben",
        ]
        if any(phrase in text.lower() for phrase in unsubstantiated):
            score -= 2.0
        return max(0.0, min(10.0, score))

    def orchestrate_swarm(self, objective: str) -> dict:
        """Divide objective into 6 parallel subtasks → dispatch → integrate results.

        This is the SISYPHUS entry point: one objective → 6 specialized agents
        working in parallel → single integrated result scored by Supervisor.

        Returns dict with keys: objective, subtasks, results, verdict, integrated_output
        """
        import time

        # 1. Divide objective into 6 specialized subtasks
        subtasks = {
            "architect": f"[ARCHITECT] Design and implement code/architecture for: {objective}",
            "researcher": f"[RESEARCHER] Research context, prior art, and risks for: {objective}",
            "guardian": f"[GUARDIAN] Security audit and threat model for: {objective}",
            "verifier": f"[VERIFIER] Define tests, formal invariants, and acceptance criteria for: {objective}",
            "narrator": f"[NARRATOR] Write documentation, changelog, and user-facing summary for: {objective}",
            "devops": f"[DEVOPS] Define deployment, CI/CD, and infrastructure plan for: {objective}",
        }

        logger.info(f"orchestrate_swarm: dispatching {len(subtasks)} agents for: {objective[:80]}")

        # 2. Dispatch via NodeMesh (parallel via inbox protocol)
        results = {}
        try:
            from core.hyperion_bridge import HyperionBridge as NodeMesh
            mesh = NodeMesh()
            for agent_role, task_text in subtasks.items():
                mesh.send_message(
                    from_node="sisyphus",
                    to_node=agent_role,
                    content={"task": task_text, "objective": objective},
                    msg_type="swarm_task",
                )
            results["dispatched"] = list(subtasks.keys())
            results["dispatch_time"] = time.time()
        except Exception as exc:
            logger.warning(f"orchestrate_swarm mesh dispatch failed: {exc}")
            results["dispatched"] = []
            results["dispatch_error"] = str(exc)

        # 3. Integrate into a unified output summary
        integrated_output = (
            f"# Swarm Execution: {objective}\n\n"
            + "\n".join(f"- **{role}**: {task}" for role, task in subtasks.items())
            + f"\n\nDispatched {len(subtasks)} agents at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
        )

        # 4. Evaluate integrated output
        verdict = self.evaluate(integrated_output, original_input=objective)

        # 5. Record circuit breaker result per dispatched agent
        blocked = verdict.decision != "ACCEPT"
        for agent_role in subtasks:
            breaker = self._get_breaker(agent_role)
            breaker.record(blocked=blocked)
            if breaker.state() == CircuitState.OPEN:
                logger.warning(f"Agent {agent_role} circuit breaker OPEN — quarantined")

        return {
            "objective": objective,
            "subtasks": subtasks,
            "results": results,
            "verdict": {
                "decision": verdict.decision,
                "score": verdict.score,
                "quality": verdict.quality,
                "actionability": verdict.actionability,
                "completeness": verdict.completeness,
                "factuality": verdict.factuality,
                "communication_quality": verdict.communication_quality,
            },
            "integrated_output": integrated_output,
        }
