"""
dof-agentkit — DOF-MESH plugin for Coinbase AgentKit.

Adds formal Z3 verification + constitutional governance to any AgentKit agent.
AgentKit is Coinbase's SDK for AI agents on Base chain (github.com/coinbase/agentkit).

Usage:
    from integrations.dof_agentkit import DOFAgentKit, dof_action

    # Option 1 — decorator for individual AgentKit actions
    @dof_action(agent_id="my-base-agent", action="transfer_eth")
    def transfer(wallet, to, amount):
        return wallet.transfer(to, amount)

    # Option 2 — governed AgentKit wrapper
    from cdp_agentkit_core import CdpAgentkitWrapper
    agentkit = CdpAgentkitWrapper()
    governed = DOFAgentKit(agentkit, agent_id="my-base-agent")
    result = governed.run("Transfer 0.1 ETH to 0x...")
    print(result.verdict)    # APPROVED | REJECTED
    print(result.output)     # original agentkit output
    print(result.z3_proof)   # formal proof

    # Option 3 — LangChain tool wrapper (AgentKit uses LangChain tools)
    from integrations.dof_agentkit import DOFToolkit
    toolkit = DOFToolkit(agentkit_tools, agent_id="my-agent")
    governed_tools = toolkit.get_tools()  # drop-in replacement for agentkit.get_tools()
"""

import os
import sys
import functools
import logging
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

logger = logging.getLogger("dof.agentkit")

# Base chain ID (primary target)
BASE_CHAIN_ID = 8453

# ---------------------------------------------------------------------------
# Optional dependency: cdp-agentkit-core
# ---------------------------------------------------------------------------
try:
    from cdp_agentkit_core import CdpAgentkitWrapper as _CdpAgentkitWrapper  # type: ignore
    _AGENTKIT_AVAILABLE = True
except ImportError:
    _CdpAgentkitWrapper = None
    _AGENTKIT_AVAILABLE = False
    warnings.warn(
        "[DOF-AgentKit] cdp-agentkit-core not installed. "
        "DOFAgentKit and DOFToolkit will work in stub mode. "
        "Install with: pip install cdp-agentkit-core",
        ImportWarning,
        stacklevel=2,
    )

# Optional dependency: langchain_core (for StructuredTool compatibility)
try:
    from langchain_core.tools import BaseTool  # type: ignore
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    BaseTool = object  # fallback base class
    _LANGCHAIN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Lazy verifier factory (mirrors dof_crewai.py pattern)
# ---------------------------------------------------------------------------

def _get_verifier():
    """Lazy import of DOFVerifier to avoid circular deps."""
    from dof.verifier import DOFVerifier
    return DOFVerifier()


# ---------------------------------------------------------------------------
# DOFBlockedError
# ---------------------------------------------------------------------------

class DOFBlockedError(Exception):
    """
    Raised when DOF formal verification rejects an AgentKit action.

    Attributes:
        message:    Human-readable reason for the block.
        agent_id:   Agent identifier that triggered the block.
        action:     Action name that was blocked.
        violations: List of governance rule violations.
        z3_proof:   Formal Z3 proof summary at time of rejection.
    """

    def __init__(
        self,
        message: str,
        agent_id: str,
        action: str,
        violations: List[str],
        z3_proof: str,
    ):
        super().__init__(message)
        self.message = message
        self.agent_id = agent_id
        self.action = action
        self.violations = violations
        self.z3_proof = z3_proof

    def __repr__(self) -> str:
        return (
            f"DOFBlockedError(agent_id={self.agent_id!r}, action={self.action!r}, "
            f"violations={self.violations!r})"
        )


# ---------------------------------------------------------------------------
# DOFAgentKitResult
# ---------------------------------------------------------------------------

@dataclass
class DOFAgentKitResult:
    """
    Result returned by DOFAgentKit.run() after governance verification.

    Fields:
        verdict:    "APPROVED" | "REJECTED"
        output:     Original AgentKit output (str or any)
        agent_id:   Agent identifier
        z3_proof:   Formal Z3 proof summary
        latency_ms: Total verification latency in milliseconds
        attestation: keccak256-like hash of this verification decision
        violations: List of governance rule violations (empty if APPROVED)
        warnings:   Non-blocking governance warnings
    """
    verdict: str
    output: Any
    agent_id: str
    z3_proof: str
    latency_ms: float
    attestation: str
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def approved(self) -> bool:
        """True iff verdict is APPROVED."""
        return self.verdict == "APPROVED"


# ---------------------------------------------------------------------------
# dof_action decorator
# ---------------------------------------------------------------------------

def dof_action(
    agent_id: str,
    action: str,
    trust_score: float = 0.9,
    block_on_reject: bool = True,
):
    """
    Decorator that wraps any AgentKit action function with DOF governance.

    Performs a pre-execution check before calling the function and a
    post-execution check on the result. If either check is REJECTED and
    block_on_reject is True, raises DOFBlockedError.

    Args:
        agent_id:        Agent identifier (logged + attested on-chain).
        action:          Action name for the verification record.
        trust_score:     Trust score forwarded to Z3Gate (0.0–1.0).
        block_on_reject: If True, raise DOFBlockedError on REJECTED verdict.

    Example:
        @dof_action(agent_id="base-agent-1687", action="transfer_eth")
        def transfer(wallet, to, amount):
            return wallet.transfer(to, amount)
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            verifier = _get_verifier()

            pre_params = {
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
                "function": fn.__name__,
                "chain_id": BASE_CHAIN_ID,
            }

            # --- Pre-check ---
            pre_result = verifier.verify_action(
                agent_id=agent_id,
                action=f"{action}:pre",
                params=pre_params,
                trust_score=trust_score,
            )

            if pre_result.verdict == "REJECTED":
                logger.warning(
                    "[DOF-AgentKit] PRE-CHECK REJECTED %s/%s — %s",
                    agent_id, action, pre_result.violations,
                )
                if block_on_reject:
                    raise DOFBlockedError(
                        message=f"DOF blocked {agent_id}/{action} before execution: "
                                f"{pre_result.violations}",
                        agent_id=agent_id,
                        action=action,
                        violations=pre_result.violations,
                        z3_proof=pre_result.z3_proof,
                    )
            else:
                logger.debug(
                    "[DOF-AgentKit] pre-check OK %s/%s (%.1fms)",
                    agent_id, action, pre_result.latency_ms,
                )

            # --- Execute original action ---
            output = fn(*args, **kwargs)

            # --- Post-check ---
            post_params = {
                **pre_params,
                "output_type": type(output).__name__,
                "output_preview": str(output)[:200] if output is not None else "",
            }
            post_result = verifier.verify_action(
                agent_id=agent_id,
                action=f"{action}:post",
                params=post_params,
                trust_score=trust_score,
            )

            if post_result.verdict == "REJECTED":
                logger.warning(
                    "[DOF-AgentKit] POST-CHECK REJECTED %s/%s — %s",
                    agent_id, action, post_result.violations,
                )
                if block_on_reject:
                    raise DOFBlockedError(
                        message=f"DOF blocked output of {agent_id}/{action}: "
                                f"{post_result.violations}",
                        agent_id=agent_id,
                        action=action,
                        violations=post_result.violations,
                        z3_proof=post_result.z3_proof,
                    )
            else:
                logger.info(
                    "[DOF-AgentKit] APPROVED %s/%s (%.1fms) proof=%s...",
                    agent_id, action, post_result.latency_ms,
                    post_result.z3_proof[:40],
                )

            return output

        # Metadata markers (queryable by runtime or tests)
        wrapper._dof_verified = True
        wrapper._dof_agent_id = agent_id
        wrapper._dof_action = action
        wrapper._dof_trust_score = trust_score
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# DOFAgentKit — governed wrapper over CdpAgentkitWrapper
# ---------------------------------------------------------------------------

class DOFAgentKit:
    """
    Governed wrapper over Coinbase's CdpAgentkitWrapper.

    Runs the underlying AgentKit normally, then passes its output through
    DOF formal verification (Z3 + Constitution). Optionally blocks on
    REJECTED verdict.

    If cdp-agentkit-core is not installed, the class still instantiates and
    can be used as a stub (useful for unit testing without the dependency).

    Args:
        agentkit:        CdpAgentkitWrapper instance (or any object with .run()).
        agent_id:        Agent identifier for attestation records.
        trust_score:     Trust score forwarded to Z3Gate (0.0–1.0).
        block_on_reject: If True, raise DOFBlockedError on REJECTED verdict.
                         Defaults to False (non-blocking) so production agents
                         can inspect results before halting.

    Example:
        from cdp_agentkit_core import CdpAgentkitWrapper
        agentkit = CdpAgentkitWrapper()
        governed = DOFAgentKit(agentkit, agent_id="my-base-agent")
        result = governed.run("Check my ETH balance")
        if result.approved:
            print(result.output)
    """

    def __init__(
        self,
        agentkit: Any,
        agent_id: str,
        trust_score: float = 0.9,
        block_on_reject: bool = False,
    ):
        if not _AGENTKIT_AVAILABLE:
            logger.warning(
                "[DOF-AgentKit] cdp-agentkit-core not available — running in stub mode."
            )
        self.agentkit = agentkit
        self.agent_id = agent_id
        self.trust_score = trust_score
        self.block_on_reject = block_on_reject
        self._verifier = _get_verifier()

    def run(self, prompt: str) -> DOFAgentKitResult:
        """
        Execute the AgentKit prompt and verify the output with DOF.

        Args:
            prompt: Natural language instruction for the AgentKit agent.

        Returns:
            DOFAgentKitResult with verdict, output, z3_proof, etc.

        Raises:
            DOFBlockedError: If verdict is REJECTED and block_on_reject is True.
        """
        # Execute underlying AgentKit
        raw_output = None
        if self.agentkit is not None and hasattr(self.agentkit, "run"):
            raw_output = self.agentkit.run(prompt)
        else:
            # Stub mode — agentkit not available or has no .run()
            logger.warning(
                "[DOF-AgentKit] agentkit.run() not available — output will be None."
            )

        output_str = str(raw_output) if raw_output is not None else ""

        # Verify output
        result = self._verifier.verify_action(
            agent_id=self.agent_id,
            action="agentkit:run",
            params={
                "prompt_length": len(prompt),
                "prompt_preview": prompt[:200],
                "output_length": len(output_str),
                "output_preview": output_str[:300],
                "chain_id": BASE_CHAIN_ID,
            },
            trust_score=self.trust_score,
        )

        logger.info(
            "[DOF-AgentKit] run verdict=%s agent=%s (%.1fms)",
            result.verdict, self.agent_id, result.latency_ms,
        )

        governed = DOFAgentKitResult(
            verdict=result.verdict,
            output=raw_output,
            agent_id=self.agent_id,
            z3_proof=result.z3_proof,
            latency_ms=result.latency_ms,
            attestation=result.attestation,
            violations=result.violations,
            warnings=result.warnings,
        )

        if result.verdict == "REJECTED" and self.block_on_reject:
            raise DOFBlockedError(
                message=f"DOF blocked agentkit.run() for {self.agent_id}: "
                        f"{result.violations}",
                agent_id=self.agent_id,
                action="agentkit:run",
                violations=result.violations,
                z3_proof=result.z3_proof,
            )

        return governed

    def get_verified_tools(self) -> List[Any]:
        """
        Return the underlying AgentKit tools wrapped with DOF verification.

        Each tool's .run() / .__call__() is wrapped with dof_action so every
        tool invocation is pre- and post-checked automatically.

        Returns:
            List of tools with DOF governance applied. Returns empty list if
            AgentKit is not available or has no get_tools() method.
        """
        if self.agentkit is None or not hasattr(self.agentkit, "get_tools"):
            logger.warning(
                "[DOF-AgentKit] get_verified_tools(): agentkit has no get_tools()."
            )
            return []

        raw_tools = self.agentkit.get_tools()
        toolkit = DOFToolkit(raw_tools, agent_id=self.agent_id, trust_score=self.trust_score)
        return toolkit.get_tools()


# ---------------------------------------------------------------------------
# DOFToolkit — wraps a list of LangChain-compatible tools with DOF governance
# ---------------------------------------------------------------------------

class _DOFWrappedTool(BaseTool):
    """
    Internal LangChain-compatible tool that wraps another tool with DOF checks.

    Not intended for direct instantiation — use DOFToolkit.get_tools() instead.
    """

    # These are declared as class vars to satisfy LangChain's BaseModel
    name: str = "dof_wrapped_tool"
    description: str = "DOF-governed tool"

    def __init__(self, tool: Any, agent_id: str, trust_score: float = 0.9, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "_wrapped_tool", tool)
        object.__setattr__(self, "_dof_agent_id", agent_id)
        object.__setattr__(self, "_dof_trust_score", trust_score)
        # Mirror name/description from wrapped tool
        tool_name = getattr(tool, "name", "unknown_tool")
        tool_desc = getattr(tool, "description", "AgentKit tool")
        object.__setattr__(self, "name", f"dof_{tool_name}")
        object.__setattr__(self, "description", f"[DOF-governed] {tool_desc}")

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        wrapped_tool = object.__getattribute__(self, "_wrapped_tool")
        agent_id = object.__getattribute__(self, "_dof_agent_id")
        trust_score = object.__getattribute__(self, "_dof_trust_score")
        tool_name = getattr(wrapped_tool, "name", "unknown_tool")

        verifier = _get_verifier()

        pre_params = {
            "tool": tool_name,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys()),
            "chain_id": BASE_CHAIN_ID,
        }

        # Pre-check
        pre_result = verifier.verify_action(
            agent_id=agent_id,
            action=f"tool:{tool_name}:pre",
            params=pre_params,
            trust_score=trust_score,
        )
        if pre_result.verdict == "REJECTED":
            logger.warning(
                "[DOF-AgentKit] TOOL PRE-CHECK REJECTED %s/%s — %s",
                agent_id, tool_name, pre_result.violations,
            )
            raise DOFBlockedError(
                message=f"DOF blocked tool {tool_name} for {agent_id}: "
                        f"{pre_result.violations}",
                agent_id=agent_id,
                action=f"tool:{tool_name}",
                violations=pre_result.violations,
                z3_proof=pre_result.z3_proof,
            )

        # Execute wrapped tool
        if hasattr(wrapped_tool, "_run"):
            output = wrapped_tool._run(*args, **kwargs)
        elif callable(wrapped_tool):
            output = wrapped_tool(*args, **kwargs)
        else:
            output = None

        # Post-check
        output_str = str(output) if output is not None else ""
        post_params = {
            **pre_params,
            "output_type": type(output).__name__,
            "output_preview": output_str[:200],
        }
        post_result = verifier.verify_action(
            agent_id=agent_id,
            action=f"tool:{tool_name}:post",
            params=post_params,
            trust_score=trust_score,
        )
        if post_result.verdict == "REJECTED":
            logger.warning(
                "[DOF-AgentKit] TOOL POST-CHECK REJECTED %s/%s — %s",
                agent_id, tool_name, post_result.violations,
            )
            raise DOFBlockedError(
                message=f"DOF blocked output of tool {tool_name} for {agent_id}: "
                        f"{post_result.violations}",
                agent_id=agent_id,
                action=f"tool:{tool_name}",
                violations=post_result.violations,
                z3_proof=post_result.z3_proof,
            )

        logger.info(
            "[DOF-AgentKit] TOOL APPROVED %s/%s (%.1fms)",
            agent_id, tool_name, post_result.latency_ms,
        )
        return output

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """Async variant — delegates to synchronous _run."""
        return self._run(*args, **kwargs)


class _SimpleDOFTool:
    """
    Fallback tool wrapper when LangChain is not available.

    Mimics the LangChain StructuredTool interface (name, description, run/invoke)
    so it can be used in non-LangChain setups.
    """

    def __init__(self, tool: Any, agent_id: str, trust_score: float = 0.9):
        self._wrapped_tool = tool
        self._dof_agent_id = agent_id
        self._dof_trust_score = trust_score
        tool_name = getattr(tool, "name", "unknown_tool")
        tool_desc = getattr(tool, "description", "AgentKit tool")
        self.name = f"dof_{tool_name}"
        self.description = f"[DOF-governed] {tool_desc}"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with DOF governance checks."""
        tool_name = getattr(self._wrapped_tool, "name", "unknown_tool")
        verifier = _get_verifier()

        pre_params = {
            "tool": tool_name,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys()),
            "chain_id": BASE_CHAIN_ID,
        }

        pre_result = verifier.verify_action(
            agent_id=self._dof_agent_id,
            action=f"tool:{tool_name}:pre",
            params=pre_params,
            trust_score=self._dof_trust_score,
        )
        if pre_result.verdict == "REJECTED":
            raise DOFBlockedError(
                message=f"DOF blocked tool {tool_name}: {pre_result.violations}",
                agent_id=self._dof_agent_id,
                action=f"tool:{tool_name}",
                violations=pre_result.violations,
                z3_proof=pre_result.z3_proof,
            )

        if hasattr(self._wrapped_tool, "run"):
            output = self._wrapped_tool.run(*args, **kwargs)
        elif callable(self._wrapped_tool):
            output = self._wrapped_tool(*args, **kwargs)
        else:
            output = None

        output_str = str(output) if output is not None else ""
        post_result = verifier.verify_action(
            agent_id=self._dof_agent_id,
            action=f"tool:{tool_name}:post",
            params={**pre_params, "output_preview": output_str[:200]},
            trust_score=self._dof_trust_score,
        )
        if post_result.verdict == "REJECTED":
            raise DOFBlockedError(
                message=f"DOF blocked output of tool {tool_name}: {post_result.violations}",
                agent_id=self._dof_agent_id,
                action=f"tool:{tool_name}",
                violations=post_result.violations,
                z3_proof=post_result.z3_proof,
            )

        return output

    # Alias for LangChain-style callers
    invoke = run
    __call__ = run


class DOFToolkit:
    """
    Wraps a list of AgentKit (LangChain-compatible) tools with DOF governance.

    Acts as a drop-in replacement for agentkit.get_tools() — each tool
    returned by get_tools() will pre- and post-check every invocation via
    DOF formal verification.

    Args:
        tools:       List of LangChain StructuredTool objects from AgentKit.
        agent_id:    Agent identifier for attestation records.
        trust_score: Trust score forwarded to Z3Gate (0.0–1.0).

    Example:
        from cdp_agentkit_core import CdpAgentkitWrapper
        agentkit = CdpAgentkitWrapper()
        toolkit = DOFToolkit(agentkit.get_tools(), agent_id="base-agent")
        governed_tools = toolkit.get_tools()
        # governed_tools is a drop-in replacement — pass to LangChain executor
    """

    def __init__(
        self,
        tools: List[Any],
        agent_id: str,
        trust_score: float = 0.9,
    ):
        self._tools = tools or []
        self.agent_id = agent_id
        self.trust_score = trust_score

    def get_tools(self) -> List[Any]:
        """
        Return the list of tools wrapped with DOF governance.

        Uses LangChain-compatible _DOFWrappedTool when langchain_core is
        available; falls back to _SimpleDOFTool otherwise.
        """
        wrapped = []
        for tool in self._tools:
            try:
                if _LANGCHAIN_AVAILABLE:
                    w = _DOFWrappedTool(
                        tool=tool,
                        agent_id=self.agent_id,
                        trust_score=self.trust_score,
                    )
                else:
                    w = _SimpleDOFTool(
                        tool=tool,
                        agent_id=self.agent_id,
                        trust_score=self.trust_score,
                    )
                wrapped.append(w)
            except Exception as exc:
                logger.warning(
                    "[DOF-AgentKit] Could not wrap tool %s: %s",
                    getattr(tool, "name", repr(tool)), exc,
                )
        return wrapped


# ---------------------------------------------------------------------------
# DOFWalletGuard — governance layer for wallet operations
# ---------------------------------------------------------------------------

# ETH price approximation used for USD conversion (override via env var)
_ETH_PRICE_USD = float(os.environ.get("DOF_ETH_PRICE_USD", "3000.0"))
_HIGH_VALUE_TRUST_THRESHOLD = 0.95


class DOFWalletGuard:
    """
    Governance layer for wallet operations on Base chain.

    Verifies transfers and contract calls with DOF before signing.
    Enforces a maximum amount limit and automatically raises the required
    trust_score threshold for high-value operations.

    Args:
        wallet:          AgentKit wallet object (e.g. CdpAgentkitWrapper or
                         any object with transfer() / contract_call() methods).
        agent_id:        Agent identifier for attestation records.
        max_amount_usd:  Maximum allowed USD value per operation (default 1000).
                         Operations exceeding this limit require trust_score > 0.95.

    Example:
        from cdp_agentkit_core import CdpAgentkitWrapper
        agentkit = CdpAgentkitWrapper()
        guard = DOFWalletGuard(agentkit, agent_id="base-agent", max_amount_usd=500.0)
        receipt = guard.safe_transfer(to="0xABC...", amount=0.05, token="ETH")
    """

    def __init__(
        self,
        wallet: Any,
        agent_id: str,
        max_amount_usd: float = 1000.0,
    ):
        self.wallet = wallet
        self.agent_id = agent_id
        self.max_amount_usd = max_amount_usd
        self._verifier = _get_verifier()

    def _usd_value(self, amount: float, token: str) -> float:
        """Approximate USD value of the given amount for a token."""
        token = token.upper()
        price_map = {
            "ETH": _ETH_PRICE_USD,
            "WETH": _ETH_PRICE_USD,
            "USDC": 1.0,
            "USDT": 1.0,
            "DAI": 1.0,
            "CBETH": _ETH_PRICE_USD,  # cbETH ≈ ETH for guard purposes
        }
        return amount * price_map.get(token, 1.0)

    def _effective_trust_score(
        self, amount: float, token: str, base_score: float = 0.9
    ) -> float:
        """
        Return the trust score required for this operation.

        If the USD value exceeds max_amount_usd, enforces a stricter threshold
        of 0.95 regardless of the base_score passed in.
        """
        usd = self._usd_value(amount, token)
        if usd > self.max_amount_usd:
            logger.warning(
                "[DOF-AgentKit] High-value operation: $%.2f > max $%.2f — "
                "enforcing trust_score > %.2f",
                usd, self.max_amount_usd, _HIGH_VALUE_TRUST_THRESHOLD,
            )
            return max(base_score, _HIGH_VALUE_TRUST_THRESHOLD)
        return base_score

    def safe_transfer(
        self,
        to: str,
        amount: float,
        token: str = "ETH",
        trust_score: float = 0.9,
    ) -> Any:
        """
        Verify the transfer with DOF before signing it on-chain.

        Args:
            to:          Destination address (0x…).
            amount:      Token amount (in token units, e.g. 0.1 for 0.1 ETH).
            token:       Token symbol (ETH, USDC, USDT, DAI, cbETH…).
            trust_score: Base trust score. Auto-raised to 0.95 if amount > max_amount_usd.

        Returns:
            Transfer receipt or response from the underlying wallet.

        Raises:
            DOFBlockedError: If DOF rejects the transfer.
            ValueError:      If amount is zero or negative.
        """
        if amount <= 0:
            raise ValueError(f"[DOF-AgentKit] Transfer amount must be > 0, got {amount}")

        effective_score = self._effective_trust_score(amount, token, trust_score)
        usd_value = self._usd_value(amount, token)

        params = {
            "to": to,
            "amount": amount,
            "token": token,
            "usd_value_approx": round(usd_value, 2),
            "chain_id": BASE_CHAIN_ID,
            "exceeds_limit": usd_value > self.max_amount_usd,
        }

        result = self._verifier.verify_action(
            agent_id=self.agent_id,
            action="wallet:transfer",
            params=params,
            trust_score=effective_score,
        )

        logger.info(
            "[DOF-AgentKit] safe_transfer verdict=%s %s %s→%s (%.1fms)",
            result.verdict, amount, token, to[:10] + "...", result.latency_ms,
        )

        if result.verdict == "REJECTED":
            raise DOFBlockedError(
                message=(
                    f"DOF blocked transfer of {amount} {token} to {to} "
                    f"(≈${usd_value:.2f}): {result.violations}"
                ),
                agent_id=self.agent_id,
                action="wallet:transfer",
                violations=result.violations,
                z3_proof=result.z3_proof,
            )

        # Execute transfer on-chain
        if self.wallet is not None and hasattr(self.wallet, "transfer"):
            return self.wallet.transfer(to, amount, token)

        logger.warning(
            "[DOF-AgentKit] wallet.transfer() not available — returning verification result."
        )
        return result

    def safe_contract_call(
        self,
        contract: str,
        method: str,
        params: Optional[dict] = None,
        trust_score: float = 0.9,
    ) -> Any:
        """
        Verify a contract call with DOF before executing it on-chain.

        Args:
            contract:    Contract address (0x…).
            method:      Contract method name (e.g. "mint", "swap").
            params:      Method parameters dict (serialisable values).
            trust_score: Trust score forwarded to Z3Gate.

        Returns:
            Transaction receipt or response from the underlying wallet.

        Raises:
            DOFBlockedError: If DOF rejects the contract call.
        """
        params = params or {}

        verify_params = {
            "contract": contract,
            "method": method,
            "param_keys": list(params.keys()),
            "chain_id": BASE_CHAIN_ID,
        }
        # Include numeric amounts for high-value detection
        for k, v in params.items():
            if isinstance(v, (int, float)):
                verify_params[k] = v

        result = self._verifier.verify_action(
            agent_id=self.agent_id,
            action=f"wallet:contract:{method}",
            params=verify_params,
            trust_score=trust_score,
        )

        logger.info(
            "[DOF-AgentKit] safe_contract_call verdict=%s %s.%s (%.1fms)",
            result.verdict, contract[:10] + "...", method, result.latency_ms,
        )

        if result.verdict == "REJECTED":
            raise DOFBlockedError(
                message=(
                    f"DOF blocked {method}() on {contract} for {self.agent_id}: "
                    f"{result.violations}"
                ),
                agent_id=self.agent_id,
                action=f"wallet:contract:{method}",
                violations=result.violations,
                z3_proof=result.z3_proof,
            )

        # Execute contract call on-chain
        if self.wallet is not None and hasattr(self.wallet, "contract_call"):
            return self.wallet.contract_call(contract, method, params)

        logger.warning(
            "[DOF-AgentKit] wallet.contract_call() not available — returning verification result."
        )
        return result
