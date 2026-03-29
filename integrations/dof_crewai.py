"""
dof-crewai — DOF-MESH plugin for CrewAI agents.

Adds formal Z3 verification + constitutional governance to any CrewAI agent
with a single decorator. Zero changes to your existing agent logic.

Usage:
    from integrations.dof_crewai import dof_verify, DOFCrewAI

    # Option 1 — decorator on any function/tool
    @dof_verify(agent_id="my-agent", action="research")
    def run_research(task: str) -> str:
        ...

    # Option 2 — wrap an entire CrewAI Crew
    from crewai import Crew
    crew = Crew(agents=[...], tasks=[...])
    governed = DOFCrewAI(crew, agent_id="my-crew")
    result = governed.kickoff()
    # result.verdict    → APPROVED | REJECTED
    # result.output     → original crew output
    # result.z3_proof   → formal proof
    # result.latency_ms → verification time

    # Option 3 — callback hook (non-blocking, observe only)
    from integrations.dof_crewai import DOFCallback
    from crewai import Crew
    crew = Crew(agents=[...], tasks=[...], callbacks=[DOFCallback(agent_id="my-crew")])
"""

import os
import sys
import functools
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger("dof.crewai")


@dataclass
class DOFCrewResult:
    """Result from DOFCrewAI.kickoff()"""
    verdict: str            # APPROVED | REJECTED
    output: Any             # original crew output
    agent_id: str
    z3_proof: str
    latency_ms: float
    attestation: str
    violations: list
    warnings: list

    @property
    def approved(self) -> bool:
        return self.verdict == "APPROVED"


def _get_verifier():
    """Lazy import of DOFVerifier to avoid circular deps."""
    from dof.verifier import DOFVerifier
    return DOFVerifier()


def dof_verify(
    agent_id: str,
    action: str = "execute",
    trust_score: float = 0.9,
    block_on_reject: bool = True,
    silent: bool = False,
):
    """
    Decorator that wraps any function with DOF formal verification.

    Args:
        agent_id:        Identifier for this agent (logged + attested)
        action:          Action name for the verification record
        trust_score:     Trust score passed to Z3Gate (0.0-1.0)
        block_on_reject: If True, raise RuntimeError on REJECTED verdict
        silent:          If True, suppress log output

    Example:
        @dof_verify(agent_id="research-agent", action="web_search")
        def search(query: str) -> str:
            return ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            verifier = _get_verifier()

            # Extract params for verification record
            params = {
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
                "function": fn.__name__,
            }

            # Pre-execution verification
            pre_result = verifier.verify_action(
                agent_id=agent_id,
                action=f"{action}:pre",
                params=params,
                trust_score=trust_score,
            )

            if pre_result.verdict == "REJECTED":
                if not silent:
                    logger.warning(
                        f"[DOF] PRE-CHECK REJECTED {agent_id}/{action} "
                        f"— {pre_result.violations}"
                    )
                if block_on_reject:
                    raise RuntimeError(
                        f"DOF blocked {agent_id}/{action}: {pre_result.violations}"
                    )

            # Execute the original function
            output = fn(*args, **kwargs)

            # Post-execution verification on output
            post_params = {
                **params,
                "output_type": type(output).__name__,
                "output_preview": str(output)[:200] if output else "",
            }
            post_result = verifier.verify_action(
                agent_id=agent_id,
                action=f"{action}:post",
                params=post_params,
                trust_score=trust_score,
            )

            if post_result.verdict == "REJECTED":
                if not silent:
                    logger.warning(
                        f"[DOF] POST-CHECK REJECTED {agent_id}/{action} "
                        f"— {post_result.violations}"
                    )
                if block_on_reject:
                    raise RuntimeError(
                        f"DOF blocked output of {agent_id}/{action}: "
                        f"{post_result.violations}"
                    )

            if not silent:
                logger.info(
                    f"[DOF] ✓ {agent_id}/{action} "
                    f"APPROVED ({post_result.latency_ms:.1f}ms) "
                    f"proof={post_result.z3_proof[:40]}..."
                )

            return output

        wrapper._dof_verified = True
        wrapper._dof_agent_id = agent_id
        wrapper._dof_action = action
        return wrapper

    return decorator


class DOFCrewAI:
    """
    Wraps a CrewAI Crew with DOF governance.

    Verifies the crew's output after kickoff() using DOFVerifier.
    Does NOT modify the crew's internal behavior — only validates output.

    Example:
        from crewai import Crew, Agent, Task
        from integrations.dof_crewai import DOFCrewAI

        crew = Crew(agents=[...], tasks=[...])
        governed = DOFCrewAI(crew, agent_id="research-crew")
        result = governed.kickoff()

        if result.approved:
            print(result.output)
        else:
            print("BLOCKED:", result.violations)
    """

    def __init__(
        self,
        crew,
        agent_id: str,
        trust_score: float = 0.9,
        block_on_reject: bool = False,  # non-blocking by default for crews
    ):
        self.crew = crew
        self.agent_id = agent_id
        self.trust_score = trust_score
        self.block_on_reject = block_on_reject
        self._verifier = _get_verifier()

    def kickoff(self, inputs: Optional[dict] = None) -> DOFCrewResult:
        """Run the crew and verify its output."""
        # Run original crew
        if inputs:
            raw_output = self.crew.kickoff(inputs=inputs)
        else:
            raw_output = self.crew.kickoff()

        # Verify output
        output_str = str(raw_output) if raw_output else ""
        result = self._verifier.verify_action(
            agent_id=self.agent_id,
            action="crew:kickoff",
            params={
                "output_length": len(output_str),
                "output_preview": output_str[:300],
            },
            trust_score=self.trust_score,
        )

        governed = DOFCrewResult(
            verdict=result.verdict,
            output=raw_output,
            agent_id=self.agent_id,
            z3_proof=result.z3_proof,
            latency_ms=result.latency_ms,
            attestation=result.attestation,
            violations=result.violations,
            warnings=result.warnings,
        )

        if governed.verdict == "REJECTED":
            logger.warning(
                f"[DOF] Crew {self.agent_id} output REJECTED: {result.violations}"
            )
            if self.block_on_reject:
                raise RuntimeError(
                    f"DOF blocked crew {self.agent_id}: {result.violations}"
                )
        else:
            logger.info(
                f"[DOF] ✓ Crew {self.agent_id} APPROVED "
                f"({result.latency_ms:.1f}ms)"
            )

        return governed


class DOFCallback:
    """
    Non-blocking CrewAI callback that observes agent steps with DOF.

    Does NOT block execution — only logs and records verdicts.
    Useful for monitoring without risk of breaking existing crews.

    Example:
        from crewai import Crew
        from integrations.dof_crewai import DOFCallback

        callback = DOFCallback(agent_id="my-crew")
        crew = Crew(agents=[...], tasks=[...], callbacks=[callback])
        crew.kickoff()

        print(callback.report())  # summary of all observed steps
    """

    def __init__(self, agent_id: str, trust_score: float = 0.9):
        self.agent_id = agent_id
        self.trust_score = trust_score
        self._verifier = _get_verifier()
        self._records = []

    def on_step_complete(self, output: Any, **kwargs):
        """Called by CrewAI after each agent step."""
        result = self._verifier.verify_action(
            agent_id=self.agent_id,
            action="step:complete",
            params={"output_preview": str(output)[:200]},
            trust_score=self.trust_score,
        )
        self._records.append({
            "step": len(self._records) + 1,
            "verdict": result.verdict,
            "latency_ms": result.latency_ms,
            "violations": result.violations,
        })
        if result.verdict == "REJECTED":
            logger.warning(
                f"[DOF] Step {len(self._records)} REJECTED: {result.violations}"
            )

    def report(self) -> dict:
        """Summary of all observed steps."""
        total = len(self._records)
        approved = sum(1 for r in self._records if r["verdict"] == "APPROVED")
        return {
            "agent_id": self.agent_id,
            "total_steps": total,
            "approved": approved,
            "rejected": total - approved,
            "approval_rate": f"{(approved/total*100):.1f}%" if total else "N/A",
            "avg_latency_ms": (
                sum(r["latency_ms"] for r in self._records) / total
                if total else 0
            ),
            "records": self._records,
        }
