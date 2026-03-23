"""
DOF Autonomous Daemon — The Self-Governing Orchestrator.

A daemon that runs continuously, making decisions, spawning Claude agents,
evaluating results, and improving the system — all without human intervention.

Architecture:
    ┌─ Perception ─┐    ┌─ Decision ──┐    ┌─ Execution ──┐    ┌─ Evaluation ─┐
    │ scan_state()  │ →  │ plan_next() │ →  │ execute()    │ →  │ evaluate()   │
    │ git status    │    │ prioritize  │    │ spawn agents │    │ score result │
    │ queue orders  │    │ categorize  │    │ run commands │    │ keep/discard │
    │ health check  │    │ select mode │    │ audit trail  │    │ log metrics  │
    └───────────────┘    └─────────────┘    └──────────────┘    └──────────────┘
         ↑                                                              │
         └──────────────────── feedback loop ───────────────────────────┘

Modes of operation:
    1. PATROL — Monitor system health, fix issues automatically
    2. IMPROVE — Run autoresearch, optimize metrics
    3. BUILD — Execute pending tasks from queue
    4. REVIEW — Spawn review agents for recent changes
    5. REPORT — Generate status reports

Usage:
    python3 core/autonomous_daemon.py                    # Run forever
    python3 core/autonomous_daemon.py --cycles 10        # Run 10 cycles
    python3 core/autonomous_daemon.py --mode patrol      # Only patrol
    python3 core/autonomous_daemon.py --dry-run          # Show decisions without executing
"""

import asyncio
import json
import os
import sys
import time
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DAEMON] %(message)s")
logger = logging.getLogger("dof.daemon")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON_LOG = os.path.join(BASE_DIR, "logs", "daemon", "cycles.jsonl")
QUEUE_DIR = os.path.join(BASE_DIR, "logs", "commander", "queue")


# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class SystemState:
    """Snapshot of the current DOF system state."""
    timestamp: float = 0.0
    pending_orders: int = 0
    recent_errors: int = 0
    test_failures: int = 0
    git_dirty_files: int = 0
    health: dict = field(default_factory=dict)
    last_experiment_score: float = 0.0
    uptime_cycles: int = 0


@dataclass
class DaemonAction:
    """A decision made by the daemon."""
    mode: str          # patrol | improve | build | review | report
    action: str        # description of what to do
    priority: int      # 1 (critical) to 5 (low)
    agent_count: int   # how many agents to spawn
    estimated_seconds: int = 60
    metadata: dict = field(default_factory=dict)


@dataclass
class CycleResult:
    """Result of one daemon cycle."""
    cycle: int
    state: SystemState
    action: DaemonAction
    result_status: str   # success | error | skipped | dry_run
    output_summary: str
    elapsed_ms: float
    agents_spawned: int = 0
    improvements: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# AUTONOMOUS DAEMON
# ═══════════════════════════════════════════════════════

class AutonomousDaemon:
    """The self-governing DOF orchestrator.

    Continuously monitors, decides, executes, and evaluates.
    Uses ClaudeCommander for all LLM interactions.
    Zero human intervention required after start.
    """

    def __init__(self,
                 cycle_interval: int = 60,
                 model: str = "claude-opus-4-6",
                 budget_per_cycle: float = 0.50,  # was 2.0 — capped to prevent 4hr runaway cycles
                 max_agents_per_cycle: int = 3,
                 dry_run: bool = False,
                 log_file: str = ""):
        self.cycle_interval = cycle_interval
        self.model = model
        self.budget_per_cycle = budget_per_cycle
        self.max_agents = max_agents_per_cycle
        self.dry_run = dry_run
        self.cycle_count = 0
        self.total_improvements = 0
        self.history: list[CycleResult] = []
        self._commander = None
        self.log_file = log_file if log_file else DAEMON_LOG

        # Ensure log dirs exist
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(QUEUE_DIR, exist_ok=True)

    def _get_commander(self):
        """Lazy-load ClaudeCommander to avoid circular imports."""
        if self._commander is None:
            from core.claude_commander import ClaudeCommander
            self._commander = ClaudeCommander(
                cwd=BASE_DIR,
                model=self.model,
                max_turns=15,
                max_budget_usd=self.budget_per_cycle,
            )
        return self._commander

    # ═══════════════════════════════════════════════════
    # PHASE 1: PERCEPTION — Scan system state
    # ═══════════════════════════════════════════════════

    async def scan_state(self) -> SystemState:
        """Scan the current state of the DOF system."""
        state = SystemState(timestamp=time.time(), uptime_cycles=self.cycle_count)

        # Check pending Telegram orders
        try:
            pending = [f for f in Path(QUEUE_DIR).glob("*.json")
                       if json.loads(f.read_text()).get("status") == "pending"]
            state.pending_orders = len(pending)
        except Exception:
            pass

        # Check recent error count from daemon log
        try:
            if os.path.exists(self.log_file):
                recent_errors = 0
                with open(self.log_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("result_status") == "error" and \
                               time.time() - entry.get("timestamp", 0) < 3600:
                                recent_errors += 1
                        except Exception:
                            pass
                state.recent_errors = recent_errors
        except Exception:
            pass

        # Check git status
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=BASE_DIR, timeout=10
            )
            # Exclude untracked files (??) — daemon can't commit them, they create false signal
            state.git_dirty_files = len([l for l in result.stdout.strip().split("\n") if l.strip() and not l.startswith("??")])
        except Exception:
            pass

        # Health check via commander
        try:
            commander = self._get_commander()
            state.health = await commander.health_check()
        except Exception as e:
            state.health = {"error": str(e)}

        # Last experiment score
        try:
            runs_file = os.path.join(BASE_DIR, "logs", "experiments", "runs.jsonl")
            if os.path.exists(runs_file):
                with open(runs_file) as f:
                    lines = f.readlines()
                    if lines:
                        last = json.loads(lines[-1])
                        state.last_experiment_score = last.get("dof_score", 0.0)
        except Exception:
            pass

        return state

    # ═══════════════════════════════════════════════════
    # PHASE 2: DECISION — Plan next action
    # ═══════════════════════════════════════════════════

    def plan_next(self, state: SystemState) -> DaemonAction:
        """Deterministic decision engine. Zero LLM. Pure rules.

        Priority order:
        1. Execute pending Telegram orders (BUILD)
        2. Fix critical errors (PATROL)
        3. Run tests if git has changes (REVIEW)
        4. Optimize metrics (IMPROVE)
        5. Generate status report (REPORT)
        """

        # Priority 1: Pending orders from Telegram
        if state.pending_orders > 0:
            return DaemonAction(
                mode="build",
                action=f"Execute {state.pending_orders} pending Telegram orders",
                priority=1,
                agent_count=min(state.pending_orders, self.max_agents),
                estimated_seconds=30 * state.pending_orders,
                metadata={"trigger": "telegram_queue"},
            )

        # Priority 2: Critical dirty file count — takes precedence over error patrol
        # >30 uncommitted files is a bigger emergency than diagnosing old errors
        if state.git_dirty_files > 30:
            return DaemonAction(
                mode="review",
                action=f"CRITICAL: {state.git_dirty_files} uncommitted files — review and commit now",
                priority=2,
                agent_count=2,
                estimated_seconds=120,
                metadata={"trigger": "critical_dirty_files", "files": state.git_dirty_files},
            )

        # Priority 3: Too many recent errors
        if state.recent_errors >= 3:
            return DaemonAction(
                mode="patrol",
                action=f"Diagnose {state.recent_errors} recent errors in last hour",
                priority=3,
                agent_count=1,
                estimated_seconds=60,
                metadata={"trigger": "error_threshold", "errors": state.recent_errors},
            )

        # Priority 3: Git has changes — review them
        if state.git_dirty_files > 5:
            return DaemonAction(
                mode="review",
                action=f"Review {state.git_dirty_files} modified files",
                priority=3,
                agent_count=2,
                estimated_seconds=90,
                metadata={"trigger": "git_changes", "files": state.git_dirty_files},
            )

        # Priority 4: Optimize — every 5 cycles run autoresearch
        if self.cycle_count > 0 and self.cycle_count % 5 == 0:
            return DaemonAction(
                mode="improve",
                action="Run autoresearch optimization cycle",
                priority=4,
                agent_count=1,
                estimated_seconds=120,
                metadata={"trigger": "scheduled_optimization", "cycle": self.cycle_count},
            )

        # Priority 5: Status report — every 10 cycles
        if self.cycle_count > 0 and self.cycle_count % 10 == 0:
            return DaemonAction(
                mode="report",
                action="Generate system status report",
                priority=5,
                agent_count=1,
                estimated_seconds=45,
                metadata={"trigger": "scheduled_report"},
            )

        # Default: patrol
        return DaemonAction(
            mode="patrol",
            action="System healthy — routine health monitoring",
            priority=5,
            agent_count=0,
            estimated_seconds=5,
            metadata={"trigger": "routine"},
        )

    # ═══════════════════════════════════════════════════
    # PHASE 3: EXECUTION — Spawn agents and run
    # ═══════════════════════════════════════════════════

    async def execute(self, action: DaemonAction) -> tuple:
        """Execute the planned action. Returns (status, output, agents_spawned)."""
        commander = self._get_commander()

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {action.mode} — {action.action}")
            return "dry_run", f"Would: {action.action}", 0

        if action.agent_count == 0:
            return "skipped", "No agents needed — system healthy", 0

        # ─── BUILD: Execute pending orders ───
        if action.mode == "build":
            return await self._execute_build(commander)

        # ─── PATROL: Diagnose and fix errors ───
        if action.mode == "patrol":
            return await self._execute_patrol(commander, action)

        # ─── REVIEW: Code review changes ───
        if action.mode == "review":
            return await self._execute_review(commander, action)

        # ─── IMPROVE: Optimization cycle ───
        if action.mode == "improve":
            return await self._execute_improve()

        # ─── REPORT: Status report ───
        if action.mode == "report":
            return await self._execute_report(commander)

        return "error", f"Unknown mode: {action.mode}", 0

    async def _execute_build(self, commander) -> tuple:
        """Execute pending Telegram orders."""
        executed = 0
        outputs = []

        for f in sorted(Path(QUEUE_DIR).glob("*.json")):
            try:
                order = json.loads(f.read_text())
                if order.get("status") != "pending":
                    continue

                # Mark as in_progress
                order["status"] = "in_progress"
                f.write_text(json.dumps(order, ensure_ascii=False))

                # Execute via commander
                result = await commander.command(
                    order["instruction"],
                    max_turns=10,
                )

                # Update order
                order["status"] = "completed" if result.status == "success" else "error"
                order["result"] = result.output[:2000]
                order["elapsed_ms"] = result.elapsed_ms
                f.write_text(json.dumps(order, ensure_ascii=False, indent=2))

                executed += 1
                outputs.append(f"Order {order['id']}: {result.status} ({result.elapsed_ms:.0f}ms)")

                if executed >= self.max_agents:
                    break

            except Exception as e:
                outputs.append(f"Error processing order: {e}")

        return "success", "\n".join(outputs), executed

    async def _execute_patrol(self, commander, action: DaemonAction) -> tuple:
        """Diagnose and fix system issues."""
        result = await commander.command(
            "Check the DOF system health: "
            "1. Read the last 20 lines of logs/daemon/cycles.jsonl for recent errors. "
            "2. Check if any core/ modules have syntax errors. "
            "3. Report findings in 3 bullet points.",
            tools=["Read", "Bash", "Glob", "Grep"],
            max_turns=8,
        )
        return result.status, result.output[:2000], 1

    async def _execute_review(self, commander, action: DaemonAction) -> tuple:
        """Review recent code changes."""
        team_result = await commander.run_team(
            task="Review the recent code changes in this repository",
            agents={
                "quality": "Check code quality in modified files. Run: git diff --stat. Then run: git add core/ scripts/ dof/ && git commit --author='Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>' -m 'chore: auto-commit reviewed changes' 2>/dev/null || echo 'nothing to commit'",
                "security": "Check for security issues in modified files. Look for hardcoded secrets, injection risks, unsafe operations. Never commit .env or oracle_key.json files.",
            },
            parallel=True,
        )
        summaries = []
        for name, res in team_result.results.items():
            summaries.append(f"[{name}]: {res.output[:500]}")

        # Deterministic post-review commit — don't rely on LLM to run git commands
        try:
            import subprocess as _sp
            commit_result = _sp.run(
                ["git", "add", "core/", "scripts/", "dof/", "tests/"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=30,
            )
            commit_result2 = _sp.run(
                ["git", "commit",
                 "--author=Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>",
                 "-m", "chore: auto-commit post-review changes [daemon]"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=30,
            )
            commit_msg = commit_result2.stdout.strip() or commit_result2.stderr.strip() or "nothing to commit"
            summaries.append(f"[commit]: {commit_msg[:200]}")
        except Exception as ce:
            summaries.append(f"[commit]: skipped ({ce})")

        return team_result.status, "\n".join(summaries), len(team_result.results)

    async def _execute_improve(self) -> tuple:
        """Run one autoresearch optimization cycle."""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, os.path.join(BASE_DIR, "scripts", "dof_autoresearch.py"),
                 "--max-cycles", "1"],
                capture_output=True, text=True, cwd=BASE_DIR, timeout=180,
            )
            output = result.stdout[-1000:] if result.stdout else result.stderr[-500:]
            return "success" if result.returncode == 0 else "error", output, 0
        except Exception as e:
            return "error", str(e), 0

    async def _execute_report(self, commander) -> tuple:
        """Generate a quick status report."""
        result = await commander.command(
            "Generate a brief DOF system status report: "
            "1. Count Python files in core/. "
            "2. Count total lines in logs/daemon/cycles.jsonl. "
            "3. Check git log --oneline -5 for recent commits. "
            "4. Summarize in 5 bullet points.",
            tools=["Bash", "Glob", "Read"],
            max_turns=8,
        )
        return result.status, result.output[:2000], 1

    # ═══════════════════════════════════════════════════
    # PHASE 4: EVALUATION — Score and log
    # ═══════════════════════════════════════════════════

    def evaluate_and_log(self, cycle_result: CycleResult):
        """Evaluate cycle result and log to JSONL."""
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cycle": cycle_result.cycle,
            "mode": cycle_result.action.mode,
            "action": cycle_result.action.action[:200],
            "priority": cycle_result.action.priority,
            "result_status": cycle_result.result_status,
            "output_summary": cycle_result.output_summary[:500],
            "elapsed_ms": cycle_result.elapsed_ms,
            "agents_spawned": cycle_result.agents_spawned,
            "state": {
                "pending_orders": cycle_result.state.pending_orders,
                "recent_errors": cycle_result.state.recent_errors,
                "git_dirty_files": cycle_result.state.git_dirty_files,
            },
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Track successful improvements (build or improve modes)
        if cycle_result.result_status == "success" and \
           cycle_result.action.mode in ("improve", "build"):
            self.total_improvements += 1

        self.history.append(cycle_result)

    # ═══════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════

    async def run(self, max_cycles: int = 0):
        """Run the autonomous daemon.

        Args:
            max_cycles: Stop after N cycles (0 = run forever)
        """
        logger.info("=" * 60)
        logger.info("DOF AUTONOMOUS DAEMON — STARTING")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Budget/cycle: ${self.budget_per_cycle}")
        logger.info(f"  Max agents/cycle: {self.max_agents}")
        logger.info(f"  Interval: {self.cycle_interval}s")
        logger.info(f"  Dry run: {self.dry_run}")
        logger.info("=" * 60)

        try:
            while True:
                self.cycle_count += 1

                if max_cycles > 0 and self.cycle_count > max_cycles:
                    logger.info(f"Reached max cycles ({max_cycles}). Stopping.")
                    break

                cycle_start = time.time()

                # ─── PERCEIVE ───
                logger.info(f"\n{'─'*40}")
                logger.info(f"CYCLE {self.cycle_count} — Scanning...")
                state = await self.scan_state()
                logger.info(f"  Pending: {state.pending_orders} | Errors: {state.recent_errors} | Git: {state.git_dirty_files}")

                # ─── DECIDE ───
                action = self.plan_next(state)
                logger.info(f"  Decision: [{action.mode.upper()}] {action.action} (P{action.priority}, {action.agent_count} agents)")

                # ─── EXECUTE ───
                status, output, agents = await self.execute(action)
                elapsed = (time.time() - cycle_start) * 1000
                logger.info(f"  Result: {status} ({elapsed:.0f}ms, {agents} agents)")
                if output and len(output) < 200:
                    logger.info(f"  Output: {output}")

                # ─── EVALUATE ───
                cycle_result = CycleResult(
                    cycle=self.cycle_count,
                    state=state,
                    action=action,
                    result_status=status,
                    output_summary=output[:500] if output else "",
                    elapsed_ms=elapsed,
                    agents_spawned=agents,
                )
                self.evaluate_and_log(cycle_result)

                # ─── WAIT ───
                if max_cycles > 0 and self.cycle_count >= max_cycles:
                    break

                wait = max(1, self.cycle_interval - int(elapsed / 1000))
                logger.info(f"  Next cycle in {wait}s...")
                await asyncio.sleep(wait)

        except KeyboardInterrupt:
            logger.info("\nDaemon stopped by user.")
        except Exception as e:
            logger.error(f"Daemon crashed: {e}")
            raise
        finally:
            logger.info(f"\nDAEMON SUMMARY: {self.cycle_count} cycles, "
                         f"{sum(c.agents_spawned for c in self.history)} agents spawned, "
                         f"{self.total_improvements} improvements")

    # ═══════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════

    def status(self) -> dict:
        """Return current daemon status."""
        return {
            "running": True,
            "cycle_count": self.cycle_count,
            "total_improvements": self.total_improvements,
            "model": self.model,
            "budget_per_cycle": self.budget_per_cycle,
            "history_size": len(self.history),
            "last_cycle": asdict(self.history[-1]) if self.history else None,
        }


# ═══════════════════════════════════════════════════════
# SPECIALIZED DAEMONS — 3 parallel persistent brains
# ═══════════════════════════════════════════════════════

class BuilderDaemon(AutonomousDaemon):
    """Specialized daemon: builds features, executes tasks, writes code.

    Uses persistent session "builder" so it remembers what it built
    across all cycles — infinite memory.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("cycle_interval", 180)
        kwargs.setdefault("budget_per_cycle", 0.50)  # was 3.0 — capped to prevent hour-long build cycles
        kwargs.setdefault("log_file", os.path.join(BASE_DIR, "logs", "daemon", "cycles_builder.jsonl"))
        super().__init__(**kwargs)
        self.role = "builder"

    def plan_next(self, state: SystemState) -> DaemonAction:
        # Builder prioritizes: pending orders > build tasks > improvements
        if state.pending_orders > 0:
            return DaemonAction(
                mode="build", action=f"Execute {state.pending_orders} pending orders",
                priority=1, agent_count=min(state.pending_orders, self.max_agents),
                metadata={"daemon": "builder"},
            )
        # Every cycle: look for TODOs in code and implement them
        return DaemonAction(
            mode="build", action="Scan codebase for TODOs and implement improvements",
            priority=3, agent_count=1, estimated_seconds=120,
            metadata={"daemon": "builder"},
        )

    async def execute(self, action: DaemonAction) -> tuple:
        commander = self._get_commander()
        if self.dry_run:
            return "dry_run", f"Builder would: {action.action}", 0

        if action.action.startswith("Execute"):
            return await self._execute_build(commander)

        # Persistent session: builder remembers all previous work
        result = await commander.persistent_command(
            name="builder",
            prompt=(
                "You are the DOF Builder agent with persistent memory. "
                "Search for TODO comments in core/*.py and pick ONE to implement. "
                "If no TODOs found, identify one small improvement and make it. "
                "Always run tests after changes."
            ),
            tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
            max_turns=15,
        )
        return result.status, result.output[:2000], 1


class GuardianDaemon(AutonomousDaemon):
    """Specialized daemon: monitors security, runs tests, catches regressions.

    Uses persistent session "guardian" — remembers all past findings.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("cycle_interval", 300)
        kwargs.setdefault("budget_per_cycle", 0.50)  # was 2.0 — capped to match builder/default
        kwargs.setdefault("log_file", os.path.join(BASE_DIR, "logs", "daemon", "cycles_guardian.jsonl"))
        super().__init__(**kwargs)
        self.role = "guardian"

    def plan_next(self, state: SystemState) -> DaemonAction:
        if state.recent_errors >= 3:
            return DaemonAction(
                mode="patrol", action=f"ALERT: {state.recent_errors} errors — diagnose now",
                priority=1, agent_count=1,
                metadata={"daemon": "guardian"},
            )
        if state.git_dirty_files > 10:
            return DaemonAction(
                mode="review", action=f"Security review of {state.git_dirty_files} changed files",
                priority=2, agent_count=2,
                metadata={"daemon": "guardian"},
            )
        return DaemonAction(
            mode="patrol", action="Routine security scan and test run",
            priority=4, agent_count=1, estimated_seconds=90,
            metadata={"daemon": "guardian"},
        )

    async def execute(self, action: DaemonAction) -> tuple:
        commander = self._get_commander()
        if self.dry_run:
            return "dry_run", f"Guardian would: {action.action}", 0

        if action.mode == "review":
            return await self._execute_review(commander, action)

        # Persistent session: guardian remembers past vulnerabilities
        result = await commander.persistent_command(
            name="guardian",
            prompt=(
                "You are the DOF Guardian agent with persistent memory. "
                "1. Run: python3 -m unittest discover -s tests --failfast 2>&1 | tail -20 "
                "2. Check for any .env or key files accidentally staged: git diff --cached --name-only "
                "3. Scan core/ for obvious security issues (hardcoded secrets, eval, exec) "
                "Report findings concisely."
            ),
            tools=["Bash", "Read", "Grep", "Glob"],
            max_turns=10,
        )
        return result.status, result.output[:2000], 1


class ResearcherDaemon(AutonomousDaemon):
    """Specialized daemon: optimizes metrics, researches improvements.

    Uses persistent session "researcher" — builds on previous findings.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("cycle_interval", 600)
        kwargs.setdefault("budget_per_cycle", 0.50)  # was 2.0 — capped to match system-wide limit
        kwargs.setdefault("log_file", os.path.join(BASE_DIR, "logs", "daemon", "cycles_researcher.jsonl"))
        super().__init__(**kwargs)
        self.role = "researcher"

    def plan_next(self, state: SystemState) -> DaemonAction:
        if self.cycle_count % 3 == 0:
            return DaemonAction(
                mode="improve", action="Run autoresearch optimization cycle",
                priority=3, agent_count=1, estimated_seconds=180,
                metadata={"daemon": "researcher"},
            )
        return DaemonAction(
            mode="report", action="Analyze metrics and propose improvements",
            priority=4, agent_count=1, estimated_seconds=60,
            metadata={"daemon": "researcher"},
        )

    async def execute(self, action: DaemonAction) -> tuple:
        commander = self._get_commander()
        if self.dry_run:
            return "dry_run", f"Researcher would: {action.action}", 0

        if action.mode == "improve":
            return await self._execute_improve()

        # Persistent session: researcher accumulates knowledge
        result = await commander.persistent_command(
            name="researcher",
            prompt=(
                "You are the DOF Researcher agent with persistent memory. "
                "1. Read logs/experiments/runs.jsonl (last 5 lines) for recent metrics "
                "2. Read logs/daemon/cycles.jsonl (last 10 lines) for daemon performance "
                "3. Identify the #1 metric to improve and propose a concrete change "
                "Be specific: which file, which line, what change."
            ),
            tools=["Read", "Glob", "Grep", "Bash"],
            max_turns=10,
        )
        return result.status, result.output[:2000], 1


async def run_multi_daemon(max_cycles: int = 0, dry_run: bool = False,
                           model: str = "claude-opus-4-6"):
    """Run all 3 specialized daemons in parallel.

    Each daemon has its own persistent session and specialization.
    They share the same JSONL audit trail and command queue.

    Usage:
        await run_multi_daemon(max_cycles=5, dry_run=True)
    """
    builder = BuilderDaemon(model=model, dry_run=dry_run)
    guardian = GuardianDaemon(model=model, dry_run=dry_run)
    researcher = ResearcherDaemon(model=model, dry_run=dry_run)

    logger.info("=" * 60)
    logger.info("MULTI-DAEMON SYSTEM — 3 SPECIALIZED BRAINS")
    logger.info(f"  Builder:    every {builder.cycle_interval}s, ${builder.budget_per_cycle}/cycle")
    logger.info(f"  Guardian:   every {guardian.cycle_interval}s, ${guardian.budget_per_cycle}/cycle")
    logger.info(f"  Researcher: every {researcher.cycle_interval}s, ${researcher.budget_per_cycle}/cycle")
    logger.info(f"  Model: {model} | Dry run: {dry_run}")
    logger.info("=" * 60)

    await asyncio.gather(
        builder.run(max_cycles=max_cycles),
        guardian.run(max_cycles=max_cycles),
        researcher.run(max_cycles=max_cycles),
    )


# ═══════════════════════════════════════════════════════
# TELEGRAM FEEDBACK — /approve and /redirect integration
# ═══════════════════════════════════════════════════════

FEEDBACK_DIR = os.path.join(BASE_DIR, "logs", "daemon", "feedback")


def submit_feedback(action: str, comment: str = ""):
    """Submit feedback to the daemon from Telegram.

    Args:
        action: "approve" | "redirect" | "stop"
        comment: Optional redirection instructions
    """
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    feedback = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "action": action,
        "comment": comment,
    }
    fname = os.path.join(FEEDBACK_DIR, f"{int(time.time())}_{action}.json")
    with open(fname, "w") as f:
        json.dump(feedback, f)
    return fname


def get_pending_feedback() -> list:
    """Read and clear pending feedback from Telegram."""
    if not os.path.exists(FEEDBACK_DIR):
        return []
    feedback = []
    for fpath in sorted(Path(FEEDBACK_DIR).glob("*.json")):
        try:
            fb = json.loads(fpath.read_text())
            feedback.append(fb)
            fpath.unlink()  # consumed
        except Exception:
            pass
    return feedback


# ═══════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="DOF Autonomous Daemon")
    parser.add_argument("--cycles", type=int, default=0, help="Max cycles (0=forever)")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between cycles")
    parser.add_argument("--mode", choices=["patrol", "improve", "build", "review", "report"],
                        help="Force a specific mode")
    parser.add_argument("--model", default="claude-opus-4-6", help="Claude model to use")
    parser.add_argument("--budget", type=float, default=2.0, help="Budget per cycle in USD")
    parser.add_argument("--max-agents", type=int, default=3, help="Max agents per cycle")
    parser.add_argument("--dry-run", action="store_true", help="Show decisions without executing")
    parser.add_argument("--multi", action="store_true", help="Run 3 specialized daemons in parallel")
    args = parser.parse_args()

    if args.multi:
        asyncio.run(run_multi_daemon(
            max_cycles=args.cycles,
            dry_run=args.dry_run,
            model=args.model,
        ))
    else:
        daemon = AutonomousDaemon(
            cycle_interval=args.interval,
            model=args.model,
            budget_per_cycle=args.budget,
            max_agents_per_cycle=args.max_agents,
            dry_run=args.dry_run,
        )
        asyncio.run(daemon.run(max_cycles=args.cycles))


if __name__ == "__main__":
    main()
