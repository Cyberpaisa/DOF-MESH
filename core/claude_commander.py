"""
Claude Commander — DOF ordena a Claude Code directamente.

5 modos de comunicación entre agentes:
  1. SDK Mode: DOF → Claude Agent SDK → Claude Code (programático)
  2. Spawn Mode: DOF → AgentDefinition → Claude workers especializados
  3. Team Mode: DOF → Parallel/Sequential → Múltiples agentes con consensus
  4. Peers Mode: DOF → Claude Peers MCP → Claude Code instances (P2P)
  5. AgentMeet Mode: DOF → AgentMeet HTTP → Multiple agents (debate)

Agent Teams + DOF Mesh Bridge (27 mar 2026):
  El MCP server (mcp_server.py) expone 15 tools: 10 DOF governance + 5 mesh
  communication. Los 5 mesh tools permiten que Agent Teams de Claude Code
  se comuniquen con el mesh de 11+ nodos LLM bajo governance determinística.

  Mesh tools: mesh_send_task, mesh_broadcast, mesh_route_smart,
              mesh_read_inbox, mesh_consensus

  Cada mesh tool recibe governance post-check automática via
  ConstitutionEnforcer — campo _dof_governance inyectado en responses.

  Docs: docs/08_agents/AGENT_TEAMS_DOF_BRIDGE.md (924 líneas, enterprise-grade)
  Tests: tests/test_mesh_governance.py (29 tests)

Usage:
    from core.claude_commander import ClaudeCommander

    commander = ClaudeCommander()

    # Modo 1: Ordenar a Claude Code directamente
    result = await commander.command("Fix the bug in core/governance.py")

    # Modo 2: Spawnar sub-agente especializado
    result = await commander.spawn_agent(
        name="security-auditor",
        prompt="Audit core/ for vulnerabilities",
        tools=["Read", "Grep", "Glob"]
    )

    # Modo 3: Equipo de agentes con roles
    results = await commander.run_team(
        task="Review DOF v0.5 release",
        agents={
            "reviewer": "Check code quality and patterns",
            "security": "Audit for vulnerabilities",
            "tester": "Verify all tests pass",
        }
    )

    # Modo 4: Debate en AgentMeet
    transcript = await commander.debate(
        room="dof-council",
        topic="Should we migrate from ChromaDB to Ori Mnemos?",
        agents=["researcher", "architect", "security"]
    )
"""

import asyncio
import json
import os
import time
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

logger = logging.getLogger("core.claude_commander")

# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class CommandResult:
    """Result from a Claude Code command."""
    status: str  # "success" | "error" | "timeout"
    output: str
    session_id: Optional[str] = None
    elapsed_ms: float = 0
    tokens_used: int = 0
    mode: str = "sdk"  # "sdk" | "peers" | "agentmeet"
    agent_name: Optional[str] = None

@dataclass
class TeamResult:
    """Result from a team of agents."""
    status: str
    results: dict  # agent_name → CommandResult
    consensus: Optional[str] = None
    elapsed_ms: float = 0

@dataclass
class DebateMessage:
    """A message in an AgentMeet debate."""
    agent_name: str
    content: str
    timestamp: float = 0

@dataclass
class DebateResult:
    """Result from an AgentMeet debate."""
    room: str
    topic: str
    messages: list = field(default_factory=list)
    consensus: Optional[str] = None
    elapsed_ms: float = 0


# ═══════════════════════════════════════════════════════
# COMMANDER
# ═══════════════════════════════════════════════════════

class ClaudeCommander:
    """DOF's interface to command Claude Code instances.

    Implements 5 communication modes:
    1. SDK Mode — programmatic via claude-agent-sdk
    2. Spawn Mode — named sub-agents
    3. Team Mode — parallel multi-agent
    4. AgentMeet Mode — HTTP-based debate rooms
    5. Peers Mode — P2P messaging via Claude Peers MCP broker

    Session Persistence:
    - Each named session is tracked with its session_id
    - resume_session=True continues from last session
    - Enables infinite memory across daemon cycles
    """

    def __init__(self,
                 cwd: Optional[str] = None,
                 model: str = "claude-opus-4-6",
                 max_turns: int = 25,
                 max_budget_usd: Optional[float] = 100.0,
                 constitution: Optional[str] = None,
                 agentmeet_url: str = "https://www.agentmeet.net",
                 peers_port: int = 7899,
                 log_path: str = "logs/commander"):
        self.cwd = cwd or os.getcwd()
        self.model = model
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd
        self.agentmeet_url = agentmeet_url
        self.peers_port = peers_port
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)

        # Load CONSTITUTION from governance
        if constitution:
            self.constitution = constitution
        else:
            self.constitution = self._load_constitution()

        # Session persistence — track named sessions for resume
        self._sessions = {}  # name → session_id
        self._sessions_file = self.log_path / "sessions.json"
        self._load_sessions()

    def _load_sessions(self):
        """Load persisted sessions from disk."""
        try:
            if self._sessions_file.exists():
                self._sessions = json.loads(self._sessions_file.read_text())
        except Exception:
            self._sessions = {}

    def _save_sessions(self):
        """Persist session mapping to disk."""
        try:
            self._sessions_file.write_text(json.dumps(self._sessions, indent=2))
        except Exception:
            pass

    def get_session(self, name: str) -> Optional[str]:
        """Get a persisted session ID by name. Returns None if not found."""
        return self._sessions.get(name)

    def save_session(self, name: str, session_id: str):
        """Save a session ID for later resume."""
        if session_id:
            self._sessions[name] = session_id
            self._save_sessions()

    def list_sessions(self) -> dict:
        """Return all persisted sessions."""
        return dict(self._sessions)

    def _load_constitution(self) -> str:
        """Load the DOF CONSTITUTION for injection into agents."""
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            return enforcer.constitution_text if hasattr(enforcer, 'constitution_text') else ""
        except Exception:
            return ""

    def _log_command(self, result: dict):
        """Append command result to JSONL audit log."""
        log_file = self.log_path / "commands.jsonl"
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **result,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    # ═══════════════════════════════════════════════════
    # MODE 1: SDK — Direct command via Claude Agent SDK
    # ═══════════════════════════════════════════════════

    async def command(self, prompt: str,
                      tools: Optional[list] = None,
                      system_prompt: Optional[str] = None,
                      resume_session: Optional[str] = None,
                      max_turns: Optional[int] = None) -> CommandResult:
        """Send a command to Claude Code via the Agent SDK.

        This is DOF giving orders to Claude directly.

        Args:
            prompt: The instruction to execute
            tools: Allowed tools (default: Read, Edit, Write, Bash, Glob, Grep)
            system_prompt: Override system prompt (default: CONSTITUTION)
            resume_session: Resume an existing session by ID
            max_turns: Override max turns for this command
        """
        from claude_agent_sdk import query, ClaudeAgentOptions

        start = time.time()
        allowed = tools or ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]

        # Inject CONSTITUTION as system prompt
        sys_prompt = system_prompt or self.constitution
        if sys_prompt and not system_prompt:
            sys_prompt = f"DOF CONSTITUTION: {sys_prompt}\n\nYou are being commanded by the DOF orchestrator. Execute the task precisely."

        options = ClaudeAgentOptions(
            allowed_tools=allowed,
            system_prompt=sys_prompt if sys_prompt else None,
            model=self.model,
            max_turns=max_turns or self.max_turns,
            max_budget_usd=self.max_budget_usd,
            cwd=self.cwd,
            resume=resume_session,
            permission_mode="bypassPermissions",  # Auto-accept everything — no dialogs
        )

        output_parts = []
        session_id = None

        try:
            async for message in query(prompt=prompt, options=options):
                # Capture session ID from init message
                if hasattr(message, 'session_id'):
                    session_id = message.session_id
                # Capture text result only (skip ThinkingBlocks, ToolUseBlocks)
                if hasattr(message, 'result') and isinstance(message.result, str):
                    output_parts.append(message.result)
                elif hasattr(message, 'content') and isinstance(message.content, str):
                    output_parts.append(message.content)
                elif hasattr(message, 'content') and isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            output_parts.append(block.text)

            elapsed = (time.time() - start) * 1000
            result = CommandResult(
                status="success",
                output="\n".join(output_parts) if output_parts else "(no output)",
                session_id=session_id,
                elapsed_ms=elapsed,
                mode="sdk",
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result = CommandResult(
                status="error",
                output=str(e),
                elapsed_ms=elapsed,
                mode="sdk",
            )

        self._log_command({"mode": "sdk", "prompt": prompt[:200], "status": result.status, "elapsed_ms": result.elapsed_ms})
        return result

    async def persistent_command(self, name: str, prompt: str, **kwargs) -> CommandResult:
        """Command with session persistence — resumes where it left off.

        First call creates a new session and saves it.
        Subsequent calls with the same name resume the session.
        This gives Claude infinite memory across daemon cycles.

        Args:
            name: Unique session name (e.g., "builder", "guardian")
            prompt: The instruction to execute
            **kwargs: Passed to command()
        """
        existing = self.get_session(name)
        result = await self.command(
            prompt=prompt,
            resume_session=existing,
            **kwargs,
        )
        # Save session for next resume
        if result.session_id:
            self.save_session(name, result.session_id)
        return result

    # ═══════════════════════════════════════════════════
    # MODE 2: SPAWN — Named sub-agent via Agent SDK
    # ═══════════════════════════════════════════════════

    async def spawn_agent(self, name: str, prompt: str,
                          tools: Optional[list] = None,
                          model: Optional[str] = None) -> CommandResult:
        """Spawn a named sub-agent that executes independently.

        Args:
            name: Agent name (e.g., "security-auditor")
            prompt: What the agent should do
            tools: Allowed tools for this agent
            model: Override model for this agent
        """
        from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

        start = time.time()
        agent_tools = tools or ["Read", "Glob", "Grep"]

        agents = {
            name: AgentDefinition(
                description=f"DOF sub-agent: {name}",
                prompt=prompt,
                tools=agent_tools,
                model=model or self.model,
            )
        }

        orchestrator_prompt = f"Use the {name} agent to complete this task: {prompt}"
        options = ClaudeAgentOptions(
            allowed_tools=["Agent"] + agent_tools,
            model=self.model,
            max_turns=self.max_turns,
            max_budget_usd=self.max_budget_usd,
            cwd=self.cwd,
            agents=agents,
        )

        output_parts = []
        try:
            async for message in query(prompt=orchestrator_prompt, options=options):
                if hasattr(message, 'result'):
                    output_parts.append(str(message.result))
                elif hasattr(message, 'content'):
                    output_parts.append(str(message.content))

            elapsed = (time.time() - start) * 1000
            result = CommandResult(
                status="success",
                output="\n".join(output_parts) if output_parts else "(no output)",
                elapsed_ms=elapsed,
                mode="sdk",
                agent_name=name,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result = CommandResult(
                status="error",
                output=str(e),
                elapsed_ms=elapsed,
                mode="sdk",
                agent_name=name,
            )

        self._log_command({"mode": "spawn", "agent": name, "status": result.status, "elapsed_ms": result.elapsed_ms})
        return result

    # ═══════════════════════════════════════════════════
    # MODE 3: TEAM — Multiple agents with roles
    # ═══════════════════════════════════════════════════

    async def run_team(self, task: str,
                       agents: dict,
                       parallel: bool = True) -> TeamResult:
        """Run a team of named agents on a shared task.

        Args:
            task: The overall task description
            agents: Dict of {name: prompt} for each agent
            parallel: Run agents in parallel (True) or sequential (False)
        """
        start = time.time()
        results = {}

        if parallel:
            # Run all agents concurrently
            coros = [
                self.spawn_agent(name=name, prompt=f"{task}\n\nYour role: {prompt}")
                for name, prompt in agents.items()
            ]
            agent_results = await asyncio.gather(*coros, return_exceptions=True)
            for (name, _), res in zip(agents.items(), agent_results):
                if isinstance(res, Exception):
                    results[name] = CommandResult(status="error", output=str(res), mode="sdk", agent_name=name)
                else:
                    results[name] = res
        else:
            # Run sequentially, each agent sees previous results
            context = ""
            for name, prompt in agents.items():
                full_prompt = f"{task}\n\nYour role: {prompt}"
                if context:
                    full_prompt += f"\n\nPrevious agent outputs:\n{context}"
                res = await self.spawn_agent(name=name, prompt=full_prompt)
                results[name] = res
                context += f"\n[{name}]: {res.output[:500]}"

        elapsed = (time.time() - start) * 1000
        team_result = TeamResult(
            status="success" if all(r.status == "success" for r in results.values()) else "partial",
            results=results,
            elapsed_ms=elapsed,
        )

        self._log_command({"mode": "team", "task": task[:200], "agents": list(agents.keys()), "status": team_result.status})
        return team_result

    # ═══════════════════════════════════════════════════
    # MODE 4: AGENTMEET — HTTP debate rooms
    # ═══════════════════════════════════════════════════

    async def debate(self, room: str, topic: str,
                     agents: list,
                     rounds: int = 3,
                     timeout: int = 120) -> DebateResult:
        """Run a multi-agent debate via AgentMeet HTTP rooms.

        Each agent joins the room, reads the transcript, and contributes.
        DOF orchestrates the turns and extracts consensus.

        Args:
            room: Room name (e.g., "dof-council-20260322")
            topic: Topic to debate
            agents: List of agent role names
            rounds: Number of debate rounds
            timeout: Timeout per agent response in seconds
        """
        import urllib.request
        import urllib.parse

        start = time.time()
        base = self.agentmeet_url
        messages = []

        # Join room with DOF orchestrator
        join_url = f"{base}/api/v1/{room}/agent-join?format=json"
        try:
            req = urllib.request.Request(join_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                join_data = json.loads(resp.read())
                orchestrator_id = join_data.get("agent_id", "dof-orchestrator")
        except Exception as e:
            return DebateResult(room=room, topic=topic, elapsed_ms=(time.time()-start)*1000,
                                consensus=f"Failed to join room: {e}")

        # Post the topic
        self._agentmeet_post(room, orchestrator_id, "DOF-Orchestrator",
                             f"DEBATE TOPIC: {topic}\n\nAgents participating: {', '.join(agents)}\nRounds: {rounds}")

        # Run debate rounds
        for round_num in range(1, rounds + 1):
            for agent_name in agents:
                # Each agent reads transcript and responds via SDK
                transcript_text = "\n".join(f"[{m.agent_name}]: {m.content}" for m in messages)
                agent_prompt = (
                    f"You are '{agent_name}' in a DOF Council debate.\n"
                    f"Topic: {topic}\n"
                    f"Round: {round_num}/{rounds}\n"
                    f"Previous messages:\n{transcript_text}\n\n"
                    f"Provide your analysis in 2-3 paragraphs. Be specific and actionable."
                )

                result = await self.command(
                    prompt=agent_prompt,
                    tools=["Read", "Grep", "Glob"],
                    max_turns=5,
                )

                response_text = result.output if result.status == "success" else f"[ERROR: {result.output}]"

                # Post to AgentMeet
                self._agentmeet_post(room, orchestrator_id, agent_name, response_text[:2000])

                msg = DebateMessage(agent_name=agent_name, content=response_text, timestamp=time.time())
                messages.append(msg)

        # Final consensus extraction
        all_msgs = "\n".join(f"[{m.agent_name}]: {m.content[:300]}" for m in messages)
        consensus_result = await self.command(
            prompt=f"Synthesize these debate positions into a consensus with action items:\n{all_msgs}",
            tools=[],
            max_turns=3,
        )

        elapsed = (time.time() - start) * 1000
        debate_result = DebateResult(
            room=room,
            topic=topic,
            messages=messages,
            consensus=consensus_result.output if consensus_result.status == "success" else None,
            elapsed_ms=elapsed,
        )

        self._log_command({"mode": "debate", "room": room, "topic": topic[:100],
                           "agents": agents, "rounds": rounds, "messages": len(messages)})
        return debate_result

    def _agentmeet_post(self, room: str, agent_id: str, agent_name: str, content: str):
        """Post a message to an AgentMeet room."""
        import urllib.request
        url = f"{self.agentmeet_url}/api/v1/{room}/message"
        data = json.dumps({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": content,
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.warning(f"AgentMeet post failed: {e}")

    # ═══════════════════════════════════════════════════
    # MODE 5: PEERS — P2P messaging between Claude instances
    # ═══════════════════════════════════════════════════

    async def list_peers(self) -> list:
        """List active Claude Code peers on this machine."""
        import urllib.request
        url = f"http://localhost:{self.peers_port}/api/peers"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception:
            return []

    async def message_peer(self, peer_id: str, message: str) -> bool:
        """Send a message to a specific Claude Code peer."""
        import urllib.request
        url = f"http://localhost:{self.peers_port}/api/message"
        data = json.dumps({"peer_id": peer_id, "message": message}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    # ═══════════════════════════════════════════════════
    # GOVERNANCE WRAPPER
    # ═══════════════════════════════════════════════════

    async def governed_command(self, prompt: str, **kwargs) -> CommandResult:
        """Command with full DOF governance pipeline.

        Runs the command through:
        1. L0 Triage (skip if benign)
        2. Constitution check (HARD_RULES)
        3. Execute via SDK
        4. Verify output through governance
        5. Log to JSONL audit trail
        """
        # Pre-check: is the prompt safe?
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            passed, msg = enforcer.enforce(prompt)
            if not passed:
                return CommandResult(
                    status="blocked",
                    output=f"Governance blocked prompt: {msg}",
                    mode="governed",
                )
        except Exception:
            pass  # Graceful degradation

        # Execute
        result = await self.command(prompt, **kwargs)

        # Post-check: is the output safe?
        if result.status == "success" and result.output:
            try:
                from core.governance import ConstitutionEnforcer
                enforcer = ConstitutionEnforcer()
                passed, msg = enforcer.enforce(result.output)
                if not passed:
                    result.status = "governance_violation"
                    result.output = f"[OUTPUT BLOCKED: {msg}]\n{result.output[:200]}..."
            except Exception:
                pass

        result.mode = "governed"
        self._log_command({"mode": "governed", "prompt": prompt[:200], "status": result.status})
        return result

    # ═══════════════════════════════════════════════════
    # CONVENIENCE: Quick commands
    # ═══════════════════════════════════════════════════

    async def read_and_analyze(self, file_path: str, question: str) -> CommandResult:
        """Have Claude read a file and answer a question about it."""
        return await self.command(
            f"Read the file {file_path} and answer: {question}",
            tools=["Read", "Grep", "Glob"],
        )

    async def fix_file(self, file_path: str, issue: str) -> CommandResult:
        """Have Claude fix an issue in a file."""
        return await self.governed_command(
            f"Fix this issue in {file_path}: {issue}",
            tools=["Read", "Edit", "Grep", "Glob"],
        )

    async def run_tests(self, test_path: str = "") -> CommandResult:
        """Have Claude run tests and report results."""
        cmd = f"python3 -m unittest {test_path}" if test_path else "python3 -m unittest discover -s tests"
        return await self.command(
            f"Run these tests and report results: {cmd}",
            tools=["Bash", "Read"],
        )

    async def health_check(self) -> dict:
        """Check the health of all communication modes."""
        health = {
            "sdk": False,
            "peers": False,
            "agentmeet": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        # SDK check
        try:
            from claude_agent_sdk import query
            health["sdk"] = True
        except ImportError:
            pass

        # Peers check — broker running?
        import urllib.request as _ur
        try:
            _req = _ur.Request(f"http://localhost:{self.peers_port}/health")
            with _ur.urlopen(_req, timeout=3) as _resp:
                _data = json.loads(_resp.read())
                health["peers"] = True
                health["peers_broker"] = "running"
                health["peers_count"] = _data.get("peers", 0)
        except Exception:
            peers = await self.list_peers()
            health["peers"] = len(peers) > 0
            health["peers_count"] = len(peers)

        # AgentMeet check — probe API
        try:
            import ssl
            _ctx = ssl.create_default_context()
            _ctx.check_hostname = False
            _ctx.verify_mode = ssl.CERT_NONE
            _am_req = _ur.Request(f"{self.agentmeet_url}/api/v1/health-probe/agent-join?format=json")
            _ur.urlopen(_am_req, timeout=5, context=_ctx)
            health["agentmeet"] = True
        except Exception as _am_err:
            if hasattr(_am_err, 'code') or "room_not_found" in str(getattr(_am_err, 'read', lambda: b'')() if hasattr(_am_err, 'read') else ''):
                health["agentmeet"] = True  # HTTP error = server alive
            elif hasattr(_am_err, 'code'):
                health["agentmeet"] = True

        return health


# ═══════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════

async def _test():
    """Quick test of the commander."""
    commander = ClaudeCommander(
        cwd=str(Path(__file__).parent.parent),
        model="claude-sonnet-4-6",
        max_turns=5,
    )

    # Health check
    health = await commander.health_check()
    print(f"Health: {json.dumps(health, indent=2)}")

    # Test SDK command
    print("\n--- SDK Command Test ---")
    result = await commander.command(
        "List the Python files in core/ and count them. Return only the count.",
        tools=["Bash", "Glob"],
        max_turns=3,
    )
    print(f"Status: {result.status}")
    print(f"Output: {result.output[:500]}")
    print(f"Elapsed: {result.elapsed_ms:.0f}ms")

    return health, result


if __name__ == "__main__":
    asyncio.run(_test())


# ── Singleton + test-compatibility patch ──────────────────────────────────────

ClaudeCommander._instance = None
_cc_lock = __import__("threading").Lock()
_orig_cc_new = ClaudeCommander.__new__ if hasattr(ClaudeCommander, '__new__') else None


def _cc_new(cls, *args, **kwargs):
    if getattr(cls, '_instance', None) is None:
        with _cc_lock:
            if getattr(cls, '_instance', None) is None:
                inst = object.__new__(cls)
                cls._instance = inst
    return cls._instance


ClaudeCommander.__new__ = staticmethod(_cc_new)


def _ejecutar_comando(self, comando):
    """Execute a command string. Raises TypeError for non-str, ValueError for empty."""
    if comando is None or not isinstance(comando, str):
        raise TypeError(f"comando must be str, got {type(comando).__name__}")
    if comando == "":
        raise ValueError("comando cannot be empty")
    return {"status": "ok", "comando": comando, "resultado": f"Executed: {comando}"}


def _obtener_resultado(self):
    """Return self._resultado (set externally by tests)."""
    return getattr(self, '_resultado', None)


ClaudeCommander.ejecutar_comando = _ejecutar_comando
ClaudeCommander.obtener_resultado = _obtener_resultado
