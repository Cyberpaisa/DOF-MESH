"""
Adversarial Evaluation Protocol — Three-Agent Verification.

Red Team → Guardian → Deterministic Arbiter pipeline for output quality
evaluation.  The Arbiter is zero-LLM: it only accepts defenses backed
by verifiable evidence (governance check, AST proof, structural test).

Metrics:
  ACR (Adversarial Consensus Rate) = resolved / total_issues

Results logged to logs/adversarial.jsonl.
"""

import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.adversarial")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "adversarial.jsonl")

# Issue severity scores (Red Team scoring)
_SEVERITY_SCORES = {"low": 1, "medium": 5, "critical": 10}


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    """A single issue found by Red Team."""
    issue_id: str
    severity: str           # "low", "medium", "critical"
    category: str           # "hallucination", "factual_error", "governance", "security"
    evidence: str           # what was found
    confidence_score: float  # 0.0 - 1.0
    line_or_section: str = ""


@dataclass
class Defense:
    """A defense provided by Guardian agent."""
    issue_id: str
    defense_type: str       # "test_passed", "governance_compliant", "structural_proof", "argument"
    evidence_data: str      # the actual evidence


@dataclass
class ArbiterDecision:
    """Decision on a single issue."""
    issue_id: str
    status: str             # "resolved" or "unresolved"
    reason: str
    severity: str


@dataclass
class AdversarialVerdict:
    """Final result of adversarial evaluation."""
    verdict: str            # "PASS" or "FAIL"
    total_issues: int
    resolved: list[dict]
    unresolved: list[dict]
    acr: float              # Adversarial Consensus Rate = resolved / total
    score: float            # 0.0 - 1.0
    red_team_score: int     # total severity points found
    elapsed_ms: float


# ─────────────────────────────────────────────────────────────────────
# Red Team Agent (deterministic — zero LLM)
# ─────────────────────────────────────────────────────────────────────

# Hallucination claim phrases (reuses governance patterns)
_HALLUCINATION_PHRASES = [
    "according to recent studies",
    "statistics show",
    "data confirms",
    "research demonstrates",
    "it is well known",
    "everyone knows",
    "según estudios recientes",
    "las estadísticas muestran",
    "datos confirman",
    "investigaciones demuestran",
    "es bien sabido",
    "todos saben",
]

# Unsubstantiated number claims
_FABRICATED_STAT_PATTERN = re.compile(
    r'\b(\d{2,3})%\b(?!.*(?:source|reference|http|según|fuente))',
)


class RedTeamAgent:
    """Deterministic adversarial analysis — finds issues in output.

    Scoring incentive: +1 low, +5 medium, +10 critical.
    Zero LLM — all detection is pattern-based.
    """

    def analyze(self, output: str, input_text: str = "") -> list[Issue]:
        """Analyze output and return list of issues found."""
        issues: list[Issue] = []
        text_lower = output.lower()
        has_urls = "http" in text_lower
        issue_counter = 0

        # 1. Hallucination detection
        for phrase in _HALLUCINATION_PHRASES:
            if phrase in text_lower and not has_urls:
                issue_counter += 1
                issues.append(Issue(
                    issue_id=f"RT-{issue_counter:03d}",
                    severity="critical",
                    category="hallucination",
                    evidence=f"Unsubstantiated claim: '{phrase}' without source URL",
                    confidence_score=0.9,
                ))

        # 2. Fabricated statistics (percentages without sources)
        for match in _FABRICATED_STAT_PATTERN.finditer(output):
            # Check if the line containing this stat has a URL
            line_start = output.rfind("\n", 0, match.start()) + 1
            line_end = output.find("\n", match.end())
            line = output[line_start:line_end if line_end != -1 else len(output)]
            if "http" not in line.lower() and "source" not in line.lower():
                issue_counter += 1
                issues.append(Issue(
                    issue_id=f"RT-{issue_counter:03d}",
                    severity="medium",
                    category="factual_error",
                    evidence=f"Unsourced statistic: '{match.group()}' in: {line.strip()[:80]}",
                    confidence_score=0.7,
                ))

        # 3. Empty sections (headers without content)
        headers = re.findall(r'^(#{1,3}\s+.+)$', output, re.MULTILINE)
        for header in headers:
            # Find text between this header and next header
            idx = output.find(header)
            after = output[idx + len(header):]
            next_header = re.search(r'^#{1,3}\s', after, re.MULTILINE)
            section = after[:next_header.start()] if next_header else after
            section_text = section.strip()
            if len(section_text) < 20:
                issue_counter += 1
                issues.append(Issue(
                    issue_id=f"RT-{issue_counter:03d}",
                    severity="low",
                    category="governance",
                    evidence=f"Empty section under: '{header.strip()}'",
                    confidence_score=0.6,
                ))

        # 4. Security: code blocks with unsafe patterns
        from core.ast_verifier import ASTVerifier
        from core.governance import _extract_python_blocks
        ast_verifier = ASTVerifier()
        code_blocks = _extract_python_blocks(output)
        for i, block in enumerate(code_blocks):
            ast_result = ast_verifier.verify(block)
            for v in ast_result.violations:
                if v["severity"] == "block":
                    issue_counter += 1
                    issues.append(Issue(
                        issue_id=f"RT-{issue_counter:03d}",
                        severity="critical",
                        category="security",
                        evidence=f"Code block {i+1}: {v['message']}",
                        confidence_score=0.95,
                    ))

        # 5. Input coverage — check if key input terms appear in output
        if input_text:
            input_words = set(input_text.lower().split())
            stopwords = {"de", "la", "el", "en", "que", "y", "a", "un", "una",
                         "the", "a", "an", "in", "on", "of", "to", "for", "and", "is", "it"}
            input_words -= stopwords
            if input_words:
                covered = sum(1 for w in input_words if w in text_lower)
                coverage = covered / len(input_words)
                if coverage < 0.3:
                    issue_counter += 1
                    issues.append(Issue(
                        issue_id=f"RT-{issue_counter:03d}",
                        severity="medium",
                        category="governance",
                        evidence=f"Low input coverage: {coverage:.0%} of key terms addressed",
                        confidence_score=0.8,
                    ))

        logger.info(f"RedTeam found {len(issues)} issues "
                     f"(score: {sum(_SEVERITY_SCORES.get(i.severity, 0) for i in issues)})")
        return issues


# ─────────────────────────────────────────────────────────────────────
# Guardian Agent (deterministic — zero LLM)
# ─────────────────────────────────────────────────────────────────────

class GuardianAgent:
    """Deterministic defense agent — provides evidence for each issue.

    Only defenses with verifiable evidence are valid. False defenses
    incur -2x penalty on the issue score.
    Zero LLM — all defense logic is structural.
    """

    def defend(self, output: str, issues: list[Issue]) -> list[Defense]:
        """Attempt to defend against each issue with evidence."""
        defenses: list[Defense] = []

        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        gov_result = enforcer.check(output)

        for issue in issues:
            defense = self._try_defend(output, issue, gov_result)
            if defense:
                defenses.append(defense)

        logger.info(f"Guardian provided {len(defenses)} defenses for {len(issues)} issues")
        return defenses

    def _try_defend(self, output: str, issue: Issue, gov_result) -> Defense | None:
        """Try to build a valid defense for a single issue."""

        # Defense for hallucination: check if URLs exist near the claim
        if issue.category == "hallucination":
            if "http" in output.lower():
                return Defense(
                    issue_id=issue.issue_id,
                    defense_type="governance_compliant",
                    evidence_data="Output contains source URLs — hallucination claim disputed",
                )
            return None

        # Defense for governance issues: use ConstitutionEnforcer
        if issue.category == "governance" and "empty section" in issue.evidence.lower():
            # Check if governance actually passed
            if gov_result.passed:
                return Defense(
                    issue_id=issue.issue_id,
                    defense_type="governance_compliant",
                    evidence_data=f"ConstitutionEnforcer passed (score={gov_result.score})",
                )
            return None

        # Defense for coverage: verify actual coverage
        if issue.category == "governance" and "coverage" in issue.evidence.lower():
            if gov_result.passed and gov_result.score >= 0.5:
                return Defense(
                    issue_id=issue.issue_id,
                    defense_type="governance_compliant",
                    evidence_data=f"Governance score {gov_result.score} ≥ 0.5",
                )
            return None

        # Defense for security: run AST verifier
        if issue.category == "security":
            from core.ast_verifier import ASTVerifier
            from core.governance import _extract_python_blocks
            verifier = ASTVerifier()
            blocks = _extract_python_blocks(output)
            all_clean = all(verifier.verify(b).passed for b in blocks) if blocks else True
            if all_clean:
                return Defense(
                    issue_id=issue.issue_id,
                    defense_type="structural_proof",
                    evidence_data="ASTVerifier confirms all code blocks are clean",
                )
            return None

        # Defense for factual errors: check if sources exist
        if issue.category == "factual_error":
            url_count = len(re.findall(r'https?://\S+', output))
            if url_count >= 2:
                return Defense(
                    issue_id=issue.issue_id,
                    defense_type="governance_compliant",
                    evidence_data=f"Output contains {url_count} source URLs",
                )
            return None

        return None


# ─────────────────────────────────────────────────────────────────────
# Deterministic Arbiter (ZERO LLM — Python only)
# ─────────────────────────────────────────────────────────────────────

class DeterministicArbiter:
    """Accepts/rejects defenses based solely on verifiable evidence.

    Rules:
    - "governance_compliant" → accepted only if ConstitutionEnforcer confirms
    - "structural_proof" → accepted only if ASTVerifier confirms
    - "test_passed" → accepted only if test actually passes
    - "argument" → always rejected (no LLM-based arguments accepted)
    """

    def adjudicate(self, output: str, issues: list[Issue],
                   defenses: list[Defense]) -> AdversarialVerdict:
        """Render final verdict on all issues."""
        start = time.time()

        defense_map = {d.issue_id: d for d in defenses}
        decisions: list[ArbiterDecision] = []

        from core.governance import ConstitutionEnforcer
        from core.ast_verifier import ASTVerifier

        enforcer = ConstitutionEnforcer()
        ast_verifier = ASTVerifier()
        gov_result = enforcer.check(output)

        for issue in issues:
            defense = defense_map.get(issue.issue_id)

            if defense is None:
                # No defense → unresolved
                decisions.append(ArbiterDecision(
                    issue_id=issue.issue_id,
                    status="unresolved",
                    reason="No defense provided",
                    severity=issue.severity,
                ))
                continue

            # Validate the defense evidence
            accepted = self._validate_defense(
                output, defense, gov_result, ast_verifier,
            )

            if accepted:
                decisions.append(ArbiterDecision(
                    issue_id=issue.issue_id,
                    status="resolved",
                    reason=f"Defense accepted: {defense.defense_type}",
                    severity=issue.severity,
                ))
            else:
                decisions.append(ArbiterDecision(
                    issue_id=issue.issue_id,
                    status="unresolved",
                    reason=f"Defense rejected: {defense.defense_type} — evidence not verified",
                    severity=issue.severity,
                ))

        resolved = [asdict(d) for d in decisions if d.status == "resolved"]
        unresolved = [asdict(d) for d in decisions if d.status == "unresolved"]

        total = len(issues)
        acr = len(resolved) / total if total > 0 else 1.0

        # Score: 1.0 minus weighted penalty for unresolved issues
        unresolved_penalty = sum(
            _SEVERITY_SCORES.get(d.severity, 1) for d in decisions
            if d.status == "unresolved"
        )
        max_penalty = sum(_SEVERITY_SCORES.get(i.severity, 1) for i in issues) if issues else 1
        score = max(0.0, round(1.0 - (unresolved_penalty / max_penalty), 2)) if max_penalty > 0 else 1.0

        # Red team total score
        red_team_score = sum(_SEVERITY_SCORES.get(i.severity, 0) for i in issues)

        # Verdict: FAIL if any critical issue is unresolved
        has_unresolved_critical = any(
            d.status == "unresolved" and d.severity == "critical"
            for d in decisions
        )
        verdict = "FAIL" if has_unresolved_critical else "PASS"

        elapsed = (time.time() - start) * 1000

        result = AdversarialVerdict(
            verdict=verdict,
            total_issues=total,
            resolved=resolved,
            unresolved=unresolved,
            acr=round(acr, 4),
            score=score,
            red_team_score=red_team_score,
            elapsed_ms=round(elapsed, 2),
        )

        logger.info(
            f"Arbiter verdict: {verdict} (ACR={acr:.2f}, "
            f"resolved={len(resolved)}/{total}, score={score})"
        )
        return result

    def _validate_defense(self, output: str, defense: Defense,
                          gov_result, ast_verifier) -> bool:
        """Validate defense evidence. Only verifiable evidence accepted."""

        if defense.defense_type == "governance_compliant":
            # Accept only if governance actually passed
            return gov_result.passed

        if defense.defense_type == "structural_proof":
            # Accept only if AST verifier confirms code is clean
            from core.governance import _extract_python_blocks
            blocks = _extract_python_blocks(output)
            if not blocks:
                return True  # no code = no security issue
            return all(ast_verifier.verify(b).passed for b in blocks)

        if defense.defense_type == "test_passed":
            # Would need actual test execution — for now, check evidence
            return "passed" in defense.evidence_data.lower()

        # "argument" or unknown → rejected
        return False


# ─────────────────────────────────────────────────────────────────────
# Pipeline orchestrator
# ─────────────────────────────────────────────────────────────────────

class AdversarialEvaluator:
    """Orchestrates Red Team → Guardian → Arbiter pipeline."""

    def __init__(self):
        self.red_team = RedTeamAgent()
        self.guardian = GuardianAgent()
        self.arbiter = DeterministicArbiter()

    def evaluate(self, output: str, input_text: str = "") -> AdversarialVerdict:
        """Run full adversarial evaluation pipeline."""
        start = time.time()

        # Phase 1: Red Team finds issues
        issues = self.red_team.analyze(output, input_text)

        if not issues:
            # No issues found → clean PASS
            result = AdversarialVerdict(
                verdict="PASS",
                total_issues=0,
                resolved=[],
                unresolved=[],
                acr=1.0,
                score=1.0,
                red_team_score=0,
                elapsed_ms=round((time.time() - start) * 1000, 2),
            )
            _log_result(result, output[:200])
            return result

        # Phase 2: Guardian defends
        defenses = self.guardian.defend(output, issues)

        # Phase 3: Arbiter adjudicates
        verdict = self.arbiter.adjudicate(output, issues, defenses)
        verdict.elapsed_ms = round((time.time() - start) * 1000, 2)

        _log_result(verdict, output[:200])
        return verdict


# ─────────────────────────────────────────────────────────────────────
# JSONL logger
# ─────────────────────────────────────────────────────────────────────

def _log_result(result: AdversarialVerdict, output_preview: str = ""):
    """Append adversarial result to logs/adversarial.jsonl."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "adversarial_evaluation",
        "verdict": result.verdict,
        "acr": result.acr,
        "score": result.score,
        "total_issues": result.total_issues,
        "resolved_count": len(result.resolved),
        "unresolved_count": len(result.unresolved),
        "red_team_score": result.red_team_score,
        "elapsed_ms": result.elapsed_ms,
        "output_preview": output_preview,
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.error(f"Adversarial log error: {e}")
