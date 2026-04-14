from __future__ import annotations
"""
DOF Sovereign Skill Engine v2.0

Modular skill engine for the Legion of 13 Agents with:
- Dynamic skill loading from manifest.json
- 5 ADK skill patterns: ToolWrapper, Generator, Reviewer, Inversion, Pipeline
- Routing audit log (detect confusion when delta < 0.05)
- Skill health monitoring (detect degradation week-over-week)
- Skill reuse tracking (GLADIATOR pattern: create → use → refine → merge)
- Temperature cascade on retry (MiroFish pattern)

Zero external dependencies. All deterministic.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("SovereignSkillEngine")


# ─── Skill Patterns (5 ADK Patterns) ────────────────────────────

SKILL_PATTERNS = {
    "tool-wrapper": "Inject library/framework expertise on demand. Load references/ only when needed.",
    "generator": "Produce structured output from templates in assets/. Style from references/.",
    "reviewer": "Evaluate input against a rubric in references/review-checklist.md. Score by severity.",
    "inversion": "Agent interviews user before acting. Phase-gated questions, no premature execution.",
    "pipeline": "Strict sequential workflow with checkpoints. Cannot skip steps.",
}


# ─── Dataclasses ─────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Audit record for skill routing decisions."""
    timestamp: str
    request_summary: str
    selected_skill: str
    selected_score: float
    runner_up_skill: str
    runner_up_score: float
    confusion: bool  # True if delta < 0.05
    outcome: str = "pending"  # pending, accepted, corrected


@dataclass
class SkillHealth:
    """Weekly health snapshot for a skill."""
    skill_name: str
    week: str
    invocations: int = 0
    successes: int = 0
    failures: int = 0
    avg_score: float = 0.0
    format_drift_pct: float = 0.0
    degraded: bool = False


@dataclass
class SkillUsageRecord:
    """Track skill creation and reuse (GLADIATOR pattern)."""
    skill_name: str
    created_at: str
    times_used: int = 0
    times_refined: int = 0
    last_used: str = ""
    token_savings_pct: float = 0.0  # Compared to no-skill baseline


# ─── Sovereign Skill Engine v2.0 ────────────────────────────────

class SovereignSkillEngine:
    """
    Modular skill engine for the Legion of 13 Agents.

    Features:
    - Dynamic loading from core/skills/*/manifest.json
    - Agent authorization (per-skill allowlists + universal tags)
    - 5 ADK skill patterns support
    - Routing audit log with confusion detection
    - Skill health monitoring with degradation alerts
    - Skill reuse tracking (create → use → refine loop)
    """

    def __init__(self, skills_path="./core/skills"):
        self.skills_path = Path(skills_path)
        self.registry: dict[str, dict] = {}
        self.skills_path.mkdir(parents=True, exist_ok=True)

        # Monitoring state
        self._routing_log: list[RoutingDecision] = []
        self._health: dict[str, SkillHealth] = {}
        self._usage: dict[str, SkillUsageRecord] = {}
        self._invocation_scores: dict[str, list[float]] = defaultdict(list)

        # Audit log path
        self._audit_path = Path("logs/skill_audit.jsonl")
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)

    # ─── Core Loading ────────────────────────────────────────────

    def register_skill(self, name: str, manifest: dict):
        """Registers a new technical skill from a manifest."""
        self.registry[name] = manifest
        # Initialize usage tracking
        if name not in self._usage:
            self._usage[name] = SkillUsageRecord(
                skill_name=name,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        logger.info(f"Skill '{name}' registered — pattern: {manifest.get('pattern', 'default')}")

    def load_skills(self):
        """Loads all skills from the skills directory."""
        count = 0
        for skill_dir in sorted(self.skills_path.iterdir()):
            if skill_dir.is_dir():
                manifest_path = skill_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            self.register_skill(manifest['name'], manifest)
                            count += 1
                    except Exception as e:
                        logger.error(f"Failed to load skill from {skill_dir}: {e}")
        logger.info(f"Loaded {count} skills from {self.skills_path}")
        return count

    # ─── Agent Authorization ─────────────────────────────────────

    def get_skills_for_agent(self, agent_id: str) -> list[str]:
        """Returns authorized skill names for a specific agent."""
        authorized = []
        for name, manifest in self.registry.items():
            tags = manifest.get("tags", [])
            agents = manifest.get("authorized_agents", [])
            if "universal" in tags or agent_id in agents:
                authorized.append(name)
        return authorized

    # Backward compat alias
    get_skill_for_agent = get_skills_for_agent

    # ─── Skill Routing with Audit ────────────────────────────────

    def route_skill(self, request: str, agent_id: str) -> tuple[str | None, RoutingDecision | None]:
        """
        Route a request to the best-matching skill for an agent.
        Uses keyword matching (deterministic, no LLM).
        Logs routing decision for audit.
        """
        authorized = self.get_skills_for_agent(agent_id)
        if not authorized:
            return None, None

        # Score each skill by keyword overlap (deterministic)
        scores: list[tuple[str, float]] = []
        request_lower = request.lower()
        request_words = set(request_lower.split())

        for skill_name in authorized:
            manifest = self.registry[skill_name]
            # Build keyword set from name, description, tags, capabilities
            keywords = set()
            keywords.update(manifest.get("name", "").lower().replace("-", " ").split())
            keywords.update(manifest.get("description", "").lower().split())
            for tag in manifest.get("tags", []):
                keywords.add(tag.lower())
            for cap in manifest.get("capabilities", {}).values():
                keywords.update(cap.lower().split()[:10])  # First 10 words of each capability

            # Jaccard-like score
            overlap = len(request_words & keywords)
            total = len(request_words | keywords) or 1
            score = overlap / total
            scores.append((skill_name, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        if not scores or scores[0][1] == 0:
            return None, None

        selected = scores[0]
        runner_up = scores[1] if len(scores) > 1 else ("none", 0.0)
        delta = selected[1] - runner_up[1]

        decision = RoutingDecision(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            request_summary=request[:100],
            selected_skill=selected[0],
            selected_score=round(selected[1], 4),
            runner_up_skill=runner_up[0],
            runner_up_score=round(runner_up[1], 4),
            confusion=delta < 0.05,
        )

        self._routing_log.append(decision)
        self._log_audit("routing", {
            "selected": selected[0],
            "score": round(selected[1], 4),
            "runner_up": runner_up[0],
            "delta": round(delta, 4),
            "confusion": delta < 0.05,
            "agent": agent_id,
        })

        # Track usage
        if selected[0] in self._usage:
            self._usage[selected[0]].times_used += 1
            self._usage[selected[0]].last_used = decision.timestamp

        return selected[0], decision

    # ─── Skill Health Monitoring ─────────────────────────────────

    def record_invocation(self, skill_name: str, success: bool, score: float = 1.0):
        """Record a skill invocation result for health monitoring."""
        if skill_name not in self._health:
            self._health[skill_name] = SkillHealth(
                skill_name=skill_name,
                week=time.strftime("%Y-W%W", time.gmtime()),
            )

        health = self._health[skill_name]
        health.invocations += 1
        if success:
            health.successes += 1
        else:
            health.failures += 1

        self._invocation_scores[skill_name].append(score)

        # Recompute average
        scores = self._invocation_scores[skill_name]
        health.avg_score = round(sum(scores) / len(scores), 2)

        self._log_audit("invocation", {
            "skill": skill_name,
            "success": success,
            "score": score,
            "avg_score": health.avg_score,
            "total": health.invocations,
        })

    def check_degradation(self, threshold_pct: float = 10.0) -> list[str]:
        """
        Check for skill degradation.
        Returns list of degraded skill names (avg_score dropped > threshold%).
        """
        degraded = []
        for name, health in self._health.items():
            scores = self._invocation_scores.get(name, [])
            if len(scores) < 10:
                continue  # Not enough data

            # Compare first half vs second half
            mid = len(scores) // 2
            first_avg = sum(scores[:mid]) / mid
            second_avg = sum(scores[mid:]) / (len(scores) - mid)

            if first_avg > 0:
                drop_pct = ((first_avg - second_avg) / first_avg) * 100
                if drop_pct > threshold_pct:
                    health.degraded = True
                    degraded.append(name)
                    logger.warning(
                        f"Skill '{name}' degraded: {first_avg:.2f} → {second_avg:.2f} "
                        f"({drop_pct:.1f}% drop)"
                    )

        return degraded

    def get_routing_confusion_report(self) -> list[RoutingDecision]:
        """Return all routing decisions flagged as confused (delta < 0.05)."""
        return [d for d in self._routing_log if d.confusion]

    # ─── Skill Refinement (GLADIATOR Loop) ───────────────────────

    def refine_skill(self, skill_name: str, updates: dict):
        """
        Refine a skill manifest with new data.
        GLADIATOR pattern: work → create skill → reuse → refine → merge.
        """
        if skill_name not in self.registry:
            logger.error(f"Cannot refine unknown skill: {skill_name}")
            return False

        manifest = self.registry[skill_name]
        # Apply updates (merge capabilities, rules, etc.)
        for key, value in updates.items():
            if key == "capabilities" and isinstance(value, dict):
                manifest.setdefault("capabilities", {}).update(value)
            elif key == "rules" and isinstance(value, list):
                existing = manifest.get("rules", [])
                manifest["rules"] = list(dict.fromkeys(existing + value))
            else:
                manifest[key] = value

        # Bump version
        version = manifest.get("version", "1.0.0")
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        manifest["version"] = ".".join(parts)

        # Track refinement
        if skill_name in self._usage:
            self._usage[skill_name].times_refined += 1

        # Persist
        skill_dir = self.skills_path / skill_name.replace("-", "_")
        if skill_dir.exists():
            with open(skill_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=4)

        self._log_audit("refinement", {
            "skill": skill_name,
            "version": manifest["version"],
            "updates": list(updates.keys()),
        })

        logger.info(f"Skill '{skill_name}' refined → v{manifest['version']}")
        return True

    def merge_skills(self, source_skill: str, target_skill: str):
        """
        Merge capabilities from source into target.
        GLADIATOR merge pattern: after competition, winner absorbs loser's knowledge.
        """
        if source_skill not in self.registry or target_skill not in self.registry:
            return False

        source = self.registry[source_skill]
        target = self.registry[target_skill]

        # Merge capabilities
        for key, value in source.get("capabilities", {}).items():
            if key not in target.get("capabilities", {}):
                target.setdefault("capabilities", {})[key] = value

        # Merge rules (deduplicated)
        source_rules = source.get("rules", [])
        target_rules = target.get("rules", [])
        target["rules"] = list(dict.fromkeys(target_rules + source_rules))

        self._log_audit("merge", {
            "source": source_skill,
            "target": target_skill,
            "capabilities_merged": len(source.get("capabilities", {})),
        })

        logger.info(f"Merged '{source_skill}' → '{target_skill}'")
        return True

    # ─── Temperature Cascade (MiroFish Pattern) ─────────────────

    @staticmethod
    def get_retry_temperature(attempt: int, base: float = 0.7) -> float:
        """
        Temperature cascade: reduce on each retry for more deterministic output.
        Attempt 0: 0.7, Attempt 1: 0.5, Attempt 2: 0.3, Attempt 3+: 0.1
        """
        cascade = [base, 0.5, 0.3, 0.1]
        return cascade[min(attempt, len(cascade) - 1)]

    # ─── Status & Reporting ──────────────────────────────────────

    def status(self) -> dict:
        """Full engine status for dashboard/API."""
        degraded = self.check_degradation()
        confused = self.get_routing_confusion_report()

        return {
            "total_skills": len(self.registry),
            "skills": list(self.registry.keys()),
            "patterns_supported": list(SKILL_PATTERNS.keys()),
            "health": {
                name: {
                    "invocations": h.invocations,
                    "success_rate": round(h.successes / h.invocations, 2) if h.invocations > 0 else 0,
                    "avg_score": h.avg_score,
                    "degraded": h.degraded,
                }
                for name, h in self._health.items()
            },
            "routing_confusion_count": len(confused),
            "degraded_skills": degraded,
            "usage": {
                name: {
                    "times_used": u.times_used,
                    "times_refined": u.times_refined,
                    "token_savings_pct": u.token_savings_pct,
                }
                for name, u in self._usage.items()
            },
        }

    # ─── Audit Logging ───────────────────────────────────────────

    def _log_audit(self, event_type: str, details: dict):
        """Append to JSONL audit log."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": f"skill.{event_type}",
            "details": details,
            "hash": hashlib.sha256(
                json.dumps(details, sort_keys=True).encode()
            ).hexdigest()[:16],
        }
        try:
            with open(self._audit_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Skill audit log write failed: {e}")


# ─── Singleton ───────────────────────────────────────────────────

_engine = None

def get_skill_engine() -> SovereignSkillEngine:
    global _engine
    if _engine is None:
        _engine = SovereignSkillEngine()
        _engine.load_skills()
    return _engine


# ─── CLI Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = SovereignSkillEngine()
    count = engine.load_skills()
    print(f"Sovereign Skill Engine v2.0 — {count} skills loaded")

    # Test routing
    for agent in ["organizer-os", "blockchain-wizard", "moltbook", "ralph-code"]:
        skills = engine.get_skills_for_agent(agent)
        print(f"  {agent}: {len(skills)} skills → {skills}")

    # Test routing with audit
    skill, decision = engine.route_skill("blockchain attestation ERC-8004", "blockchain-wizard")
    if decision:
        print(f"\n  Routed to: {skill} (score={decision.selected_score}, confusion={decision.confusion})")

    # Test temperature cascade
    for attempt in range(4):
        temp = engine.get_retry_temperature(attempt)
        print(f"  Retry {attempt}: temperature={temp}")

    # Status
    status = engine.status()
    print(f"\n  Status: {json.dumps(status, indent=2)}")
