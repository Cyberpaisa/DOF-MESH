# ARCHITECTURAL REDESIGN — OpenClawd Multi-Agent System
## Deep Audit & Strategic Redesign v1.0
**Date:** 2026-03-03
**System:** OpenClawd — 8 Agents / 11 Crews / 7 LLM Providers
**Author:** Architectural Audit — Cyber Paisa / Enigma Group

---

# SECTION 1 — Deep Architectural Weakness Analysis

---

## 1.1 Structural Fragility

### F1: Monolithic crew.py (52KB, single file)

All 11 crew definitions, 12 Pydantic models, agent instantiation, memory singleton,
pre-research logic, topic extraction, and shared context loading live in one file.
A syntax error anywhere kills the entire system. No crew can operate independently.

**Impact:** Total system failure from any single code change.
**Severity:** CRITICAL

### F2: Provider state is process-global singleton

```python
_exhausted_providers: set[str] = set()  # llm_config.py:136
```

This set lives in process memory. Two concurrent Telegram requests share it.
If Request A exhausts Groq, Request B also loses Groq — even if B's task is
small enough to fit under Groq's TPM. There is no per-request isolation,
no TTL on exhaustion marks, and no automatic recovery.

**Impact:** One heavy request degrades all subsequent requests until process restart.
**Severity:** HIGH

### F3: Agent identity is reconstructed on every crew invocation

Every call to `create_research_crew()` re-reads SOUL.md from disk, re-instantiates
Agent objects, re-creates LLM objects. There is no agent registry, no identity
persistence across crews. The "same" Research Analyst in two consecutive calls
has zero continuity.

**Impact:** No learning, no adaptation, no identity continuity.
**Severity:** MEDIUM (by design in CrewAI, but architecturally limiting)

---

## 1.2 Hidden Coupling

### C1: Zhipu ↔ OpenAI environment variable collision

```python
model=f"openai/{model}"  # get_zhipu_llm(), llm_config.py:125
```

The `openai/` LiteLLM prefix causes LiteLLM to search for `OPENAI_API_KEY` in
environment. Any component that sets `OPENAI_API_KEY` (Memory embedder, HuggingFace,
CrewAI internals) creates a cross-provider collision. The base_url parameter is
not reliably forwarded through CrewAI's internal LLM dispatch.

**Evidence:** TEST-003, TEST-004 — AuthenticationError on intento 3.
**Impact:** Zhipu is functionally unreachable inside CrewAI crews.
**Severity:** HIGH

### C2: Memory system ↔ OpenAI implicit dependency

CrewAI's Memory class internally calls `litellm.embedding()` which defaults to
OpenAI's embedding endpoint. Even when HuggingFace is configured as the embedder
provider, certain code paths in CrewAI's memory pipeline invoke LiteLLM with
OpenAI defaults, triggering `OPENAI_API_KEY` lookups.

**Evidence:** `could not convert string to float: 'error'` in Memory Save/Query.
**Impact:** Memory system is non-functional. Currently disabled (`memory=False`).
**Severity:** HIGH

### C3: Pydantic output_json ↔ NVIDIA NIM grammar incompatibility

CrewAI converts Pydantic models to JSON Schema and sends them as `response_format`
to LiteLLM. NVIDIA NIM interprets this as a "grammar" constraint and rejects
complex schemas (nested arrays, optional fields).

**Evidence:** TEST-002 — `Invalid grammar request with cache hit`.
**Impact:** NVIDIA NIM cannot produce structured Pydantic outputs. Any crew with
Pydantic output that falls back to NVIDIA will fail.
**Severity:** HIGH

---

## 1.3 Failure Propagation Risks

### P1: Cascade failure in sequential crew tasks

CrewAI runs tasks sequentially within a crew. If Task 3 (QA) fails, Tasks 4-5
never execute. The partial result from Tasks 1-2 is lost — there is no checkpoint
or partial result recovery.

```
T1(Research) ✓ → T2(Strategy) ✓ → T3(QA) ✗ → T4(Verify) NEVER → T5(Refine) NEVER
                                     ↑
                                 All prior work lost
```

**Impact:** 5+ minutes of LLM inference discarded on late-stage failure.
**Severity:** HIGH

### P2: Retry recreates entire crew from scratch

```python
for attempt in range(1, MAX_RETRIES + 1):
    crew = _create_crew(mode, task, project)  # telegram_bot.py:699
    result = crew.kickoff()                    # Re-runs ALL tasks
```

When attempt 1 completes 4/7 tasks and fails on task 5, attempt 2 re-runs
all 7 tasks from scratch. Completed work is never cached or reused.

**Impact:** Triple resource consumption on retries. Accelerates rate limiting.
**Severity:** HIGH

### P3: Provider exhaustion is permanent per process

`_exhausted_providers` is never cleared automatically. Once Groq is marked exhausted
at 11:30 PM, it stays exhausted until the bot process restarts — even if Groq's
rate limits reset at midnight.

**Impact:** System progressively degrades as providers are marked exhausted.
**Severity:** MEDIUM

---

## 1.4 Fallback Cascade Weaknesses

### W1: Fallback order creates provider-specific failure modes

The fallback chain operates at LLM assignment time, not at execution time.
When `get_llm_for_role("mvp_strategist")` runs, it picks the first available
provider. But the LLM is not tested — it's just instantiated. The actual
failure happens minutes later during `crew.kickoff()`, inside CrewAI's
execution loop, where the error handling is different.

```
Assignment time:  NVIDIA exhausted → pick Cerebras  ← This works
Execution time:   Cerebras → API call → timeout     ← No fallback here
```

**Impact:** Fallback only works for provider-level failures, not model-level failures.
**Severity:** MEDIUM

### W2: NVIDIA is structurally incompatible with Pydantic outputs

NVIDIA NIM always fails on JSON schema grammar. Yet it appears as fallback
in every chain. When reached, it always fails, wasting time and an attempt.

**Impact:** NVIDIA as fallback for structured output crews is dead weight.
**Severity:** MEDIUM

### W3: No distinction between transient and permanent failures

Rate limits (transient) and grammar errors (permanent) are handled identically:
mark provider exhausted, retry. But grammar errors will persist across retries
with the same provider, while rate limits may clear in minutes.

**Impact:** Permanent failures waste retry attempts.
**Severity:** LOW

---

## 1.5 Memory Instability Vectors

### M1: Memory is fully disabled

```python
"memory": False,  # crew.py:_crew_config()
```

No short-term memory, no long-term memory, no entity tracking.
Each crew invocation starts with zero context from previous runs.
The system has amnesia.

**Impact:** No learning, no context accumulation, no cross-session intelligence.
**Severity:** HIGH (for system intelligence)

### M2: LanceDB singleton was never validated

The `_get_memory_instance()` singleton creates a LanceDB instance but never
verified that:
- The embedder actually generates vectors
- Vectors are stored and retrievable
- Memory queries return relevant results

**Impact:** Even if re-enabled, memory quality is unknown.
**Severity:** MEDIUM

### M3: Session memory files are disconnected

`memory/last_session.md` and `memory/2026-03-02.md` exist as markdown files
but are never loaded into crew context. They're write-only artifacts.

**Impact:** Manual memory files serve no automated purpose.
**Severity:** LOW

---

## 1.6 Non-Deterministic Behavior Zones

### N1: Pre-research web search results vary per execution

```python
def _pre_research(topic, num_searches=5)  # crew.py
```

Web search results change with time, geography, and provider state.
Two identical research requests produce different base data, leading to
divergent analysis.

**Impact:** Research outputs are not reproducible.
**Severity:** LOW (acceptable for research, problematic for testing)

### N2: Temperature > 0 on all agents

Even QA Reviewer and Verifier use temperature=0.2. For verification tasks
where determinism is critical, any temperature > 0 introduces variance.

**Impact:** Same verification prompt can yield different verdicts.
**Severity:** LOW

### N3: Topic extraction from voice is lossy

```python
def _extract_search_topic(text: str) -> str  # crew.py
```

Audio → Whisper → text → keyword extraction. Each step loses information.
The same spoken phrase can produce different topics depending on
Whisper's transcription variance.

**Impact:** Voice commands are inherently non-deterministic.
**Severity:** LOW (acceptable for voice interface)

---

## 1.7 Observability Blind Spots

### O1: No per-agent metrics

The system logs crew-level events (start, complete, error) but never records:
- Which agent produced which output
- How long each agent took
- Which LLM provider each agent actually used at runtime
- Token consumption per agent
- Quality score per agent output

**Impact:** Cannot diagnose which agent degrades overall output quality.
**Severity:** HIGH

### O2: No quality measurement

There is no automated quality scoring of outputs. The QA Reviewer agent
produces a `quality_score` field in VerificationReport, but this score is:
- Never logged separately
- Never tracked over time
- Never compared across runs
- Never used as a system-level signal

**Impact:** Cannot measure if system quality is improving or degrading.
**Severity:** HIGH

### O3: Provider usage is invisible

When a crew completes successfully, there is no record of which providers
were actually used, how many tokens were consumed per provider, or how
close each provider is to its rate limit.

**Impact:** Cannot predict or prevent rate limit exhaustion.
**Severity:** MEDIUM

### O4: No structured error taxonomy

Errors are logged as raw strings. There is no classification:
- Provider error vs. model error vs. tool error vs. agent error
- Transient vs. permanent
- User-caused vs. system-caused

**Impact:** Error analysis requires manual log reading.
**Severity:** MEDIUM

---

## 1.8 Governance Weaknesses

### G1: CONSTITUTION is a string constant, never enforced

```python
CONSTITUTION = (
    "REGLAS: 1) Datos verificables con fuentes URL..."
)  # crew.py:74
```

This string is prepended to agent backstory. There is no verification that
agent outputs comply with the constitution. An agent can ignore every rule
and the system has no detection mechanism.

**Impact:** Constitution is advisory, not enforced.
**Severity:** HIGH

### G2: SOUL.md is read-only documentation

SOUL.md files define agent identity but:
- No alignment scoring against SOUL principles
- No violation detection
- No SOUL versioning
- No experimental variation of SOUL parameters
- Temperature, tools, and model are duplicated between SOUL.md and crew.py code

**Impact:** SOUL is aspirational text, not operational governance.
**Severity:** HIGH

### G3: No inter-agent communication protocol

Agents pass information through CrewAI's sequential context passing.
There is no structured handoff format, no explicit contract between
agents about what data the next agent needs.

**Impact:** Information loss between agents. Downstream agents may
re-research what upstream agents already found.
**Severity:** MEDIUM

### G4: A2A Server has zero authentication

```python
self.send_header("Access-Control-Allow-Origin", "*")  # a2a_server.py
```

Any HTTP client can execute any crew via the A2A server.
No API key, no rate limiting, no authentication.

**Impact:** Unauthenticated remote code execution via build/code crews.
**Severity:** CRITICAL (when exposed to network)

---

# SECTION 2 — Meta-Supervisor Design (Core Upgrade)

---

## 2.1 Architecture Overview

The Meta-Supervisor is a lightweight evaluation layer that wraps CrewAI's
task execution. It does NOT replace CrewAI's orchestration — it augments it
by intercepting outputs, scoring them, and deciding next actions.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        META-SUPERVISOR                              │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │   Intercept   │──▶│   Evaluate    │──▶│   Decision Engine    │   │
│  │   Layer       │   │   Pipeline    │   │                      │   │
│  │              │   │              │   │  ACCEPT / REVISE /   │    │
│  │  Raw agent   │   │  Quality     │   │  RETRY / DELEGATE /  │    │
│  │  output      │   │  SOUL align  │   │  ESCALATE            │    │
│  │  captured    │   │  Coherence   │   │                      │    │
│  └──────────────┘   │  Factuality  │   └──────┬───────────────┘    │
│                     └──────────────┘          │                    │
│                                               ▼                    │
│                     ┌──────────────────────────────────────┐       │
│                     │         Metrics Emitter              │       │
│                     │   quality_score, alignment_score,    │       │
│                     │   decision, latency, provider,       │       │
│                     │   tokens, retry_count                │       │
│                     └──────────────┬───────────────────────┘       │
│                                    │                               │
└────────────────────────────────────┼───────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌────────────┐  ┌────────────┐  ┌────────────────┐
            │  JSONL Log  │  │  Dashboard  │  │  Test Reports  │
            │  (disk)     │  │  (WebSocket)│  │  (incidents)   │
            └────────────┘  └────────────┘  └────────────────┘
```

### Integration Point

The Meta-Supervisor hooks into CrewAI via `task_callback` and `step_callback`:

```
Crew(
    agents=[...],
    tasks=[...],
    step_callback=meta_supervisor.on_step,    # Per-agent step
    task_callback=meta_supervisor.on_task,     # Per-task completion
)
```

---

## 2.2 Decision Engine Pseudocode

```python
class MetaSupervisor:

    MAX_REVISIONS = 2
    MIN_QUALITY = 6.0
    MIN_ALIGNMENT = 7.0

    def on_task(self, task_output: TaskOutput) -> SupervisorDecision:
        """Called after each task completes within a crew."""

        # ─── 1. INTERCEPT ───
        raw_output = task_output.raw
        agent_role = task_output.agent
        task_desc = task_output.description[:200]

        # ─── 2. EVALUATE ───
        scores = self.evaluate(raw_output, agent_role, task_desc)

        # ─── 3. DECIDE ───
        decision = self._decide(scores, agent_role)

        # ─── 4. EMIT METRICS ───
        self.emit({
            "timestamp": now_iso(),
            "agent": agent_role,
            "task": task_desc,
            "quality_score": scores.quality,
            "alignment_score": scores.alignment,
            "coherence_score": scores.coherence,
            "factuality_score": scores.factuality,
            "composite_score": scores.composite,
            "decision": decision.action,
            "decision_reason": decision.reason,
            "revision_count": self._revision_counts.get(agent_role, 0),
            "provider": self._get_current_provider(agent_role),
            "latency_ms": task_output.latency_ms,
        })

        # ─── 5. ACT ───
        if decision.action == "ACCEPT":
            return decision

        if decision.action == "REVISE":
            return self._request_revision(task_output, scores)

        if decision.action == "RETRY_PROVIDER":
            return self._retry_different_provider(task_output)

        if decision.action == "DELEGATE":
            return self._delegate_to(decision.target_agent, task_output)

        if decision.action == "ESCALATE":
            return self._multi_agent_review(task_output, scores)


    def evaluate(self, output: str, agent_role: str, task_desc: str) -> Scores:
        """Lightweight evaluation using Cerebras (fastest, cheapest)."""

        # Use the cheapest/fastest LLM for evaluation
        eval_llm = get_cerebras_llm(temperature=0.0)

        prompt = EVAL_PROMPT_TEMPLATE.format(
            agent_role=agent_role,
            soul_principles=self._load_soul_principles(agent_role),
            task_description=task_desc,
            output=output[:3000],  # Truncate for eval efficiency
        )

        response = eval_llm.call(messages=[
            {"role": "system", "content": "Score this output. Return JSON only."},
            {"role": "user", "content": prompt},
        ])

        return Scores.parse_raw(response)


    def _decide(self, scores: Scores, agent_role: str) -> SupervisorDecision:
        """Core decision logic."""

        revisions = self._revision_counts.get(agent_role, 0)

        # Composite score formula
        composite = (
            scores.quality * 0.40 +
            scores.alignment * 0.25 +
            scores.coherence * 0.20 +
            scores.factuality * 0.15
        )
        scores.composite = round(composite, 2)

        # ── ACCEPT: score meets threshold ──
        if composite >= self.MIN_QUALITY:
            return SupervisorDecision(action="ACCEPT", reason="Meets quality threshold")

        # ── REVISE: below threshold but revisable ──
        if composite >= 4.0 and revisions < self.MAX_REVISIONS:
            self._revision_counts[agent_role] = revisions + 1
            return SupervisorDecision(
                action="REVISE",
                reason=f"Score {composite:.1f} < {self.MIN_QUALITY}. Revision {revisions+1}/{self.MAX_REVISIONS}",
                feedback=scores.improvement_suggestions,
            )

        # ── RETRY_PROVIDER: might be a model quality issue ──
        if composite < 4.0 and scores.quality < 4.0:
            return SupervisorDecision(
                action="RETRY_PROVIDER",
                reason=f"Quality {scores.quality:.1f} critically low. Likely model limitation.",
            )

        # ── DELEGATE: agent is wrong for this task ──
        if scores.alignment < 4.0:
            target = self._find_better_agent(agent_role, scores)
            return SupervisorDecision(
                action="DELEGATE",
                reason=f"SOUL alignment {scores.alignment:.1f} too low for {agent_role}",
                target_agent=target,
            )

        # ── ESCALATE: nothing worked ──
        return SupervisorDecision(
            action="ESCALATE",
            reason=f"Score {composite:.1f} after {revisions} revisions. Multi-agent review needed.",
        )
```

---

## 2.3 Confidence Scoring Formula

```
COMPOSITE = (Quality × 0.40) + (Alignment × 0.25) + (Coherence × 0.20) + (Factuality × 0.15)

Where:
  Quality    [0-10]: Output completeness, specificity, actionability
  Alignment  [0-10]: Adherence to SOUL.md principles and role boundaries
  Coherence  [0-10]: Logical consistency, no contradictions, proper structure
  Factuality [0-10]: Verifiable claims have sources, numbers are plausible

Decision thresholds:
  COMPOSITE >= 6.0  →  ACCEPT
  4.0 <= COMP < 6.0 →  REVISE (max 2 times)
  COMP < 4.0        →  RETRY_PROVIDER or DELEGATE
  After max retries  →  ESCALATE
```

---

## 2.4 Delegation Logic Rules

```
DELEGATION_MAP = {
    # If this agent fails    →  Try these agents (in order)
    "research_analyst":      ["mvp_strategist", "code_architect"],
    "mvp_strategist":        ["research_analyst", "narrative_content"],
    "code_architect":        ["data_engineer", "qa_reviewer"],
    "data_engineer":         ["code_architect", "qa_reviewer"],
    "project_organizer":     ["data_engineer", "code_architect"],
    "qa_reviewer":           ["verifier", "code_architect"],
    "verifier":              ["qa_reviewer", "research_analyst"],
    "narrative_content":     ["research_analyst", "mvp_strategist"],
}

Rules:
1. Never delegate to the same agent that failed.
2. Never delegate more than 2 levels deep (A→B→C max).
3. Track delegation chain to prevent cycles.
4. Delegated task carries original context + failure reason.
5. Delegated agent uses its own LLM (potentially different provider).
```

---

## 2.5 File Structure

```
meta_supervisor/
├── __init__.py
├── supervisor.py          # MetaSupervisor class
├── evaluator.py           # Scoring logic (uses Cerebras for eval)
├── decision_engine.py     # Accept/Revise/Retry/Delegate/Escalate
├── metrics_emitter.py     # JSONL + WebSocket broadcast
├── schemas.py             # Scores, SupervisorDecision, SupervisorEvent
└── prompts/
    └── eval_template.md   # Evaluation prompt template
```

---

# SECTION 3 — SOUL Governance & Cognitive Alignment Layer

---

## 3.1 Standardized SOUL Structure

Current SOUL.md files are free-form markdown with inconsistent structure.
Redesign as a machine-readable governance document with fixed sections:

```markdown
# SOUL — {Agent Name}

## IDENTITY
- **Alias:** {short name}
- **Role:** {one-line role definition}
- **Domain:** {primary expertise domain}
- **Voice:** {communication style — e.g., "technical, precise, terse"}

## CORE PRINCIPLES
1. {Principle 1 — measurable behavior}
2. {Principle 2}
3. {Principle 3}
(max 5 principles — forces prioritization)

## COGNITIVE STYLE
- **Reasoning:** {deductive | inductive | abductive | mixed}
- **Temperature:** {0.0-1.0 with justification}
- **Depth:** {surface | moderate | deep | exhaustive}
- **Bias:** {speed | quality | balance}

## RISK POLICY
- **Hallucination tolerance:** {zero | low | moderate}
- **Speculation allowed:** {yes with label | no}
- **Confidence threshold:** {minimum score to assert a claim}
- **Unknown handling:** {"state unknown" | "best guess with caveat"}

## FAILURE HANDLING
- **On insufficient data:** {action}
- **On conflicting sources:** {action}
- **On tool failure:** {action}
- **On time pressure:** {action}

## COLLABORATION RULES
- **Accepts delegation from:** {agent list | all}
- **Delegates to:** {agent list | none}
- **Conflict resolution:** {defer to QA | defend position | compromise}
- **Context expected from upstream:** {list of required inputs}

## OUTPUT STANDARDS
- **Format:** {structured JSON | narrative | mixed}
- **Minimum sources:** {number}
- **Maximum length:** {token estimate}
- **Required fields:** {list}
- **Language:** {es | en | context-dependent}
```

---

## 3.2 Alignment Scoring System

### Scale: 0-10 per dimension

| Score | Meaning |
|-------|---------|
| 9-10 | Exemplary — exceeds SOUL expectations |
| 7-8 | Compliant — meets all SOUL principles |
| 5-6 | Partial — some principles violated |
| 3-4 | Significant drift — multiple violations |
| 0-2 | Identity failure — output contradicts SOUL |

### Violation Categories

| Category | Weight | Example |
|----------|--------|---------|
| `HALLUCINATION` | 3.0 | Stated a fact without source |
| `ROLE_BOUNDARY` | 2.5 | Architect gave business strategy |
| `PRINCIPLE_VIOLATION` | 2.0 | Researcher didn't search before answering |
| `OUTPUT_FORMAT` | 1.5 | Missing required fields |
| `LANGUAGE_DRIFT` | 1.0 | Responded in English when Spanish expected |
| `STYLE_DRIFT` | 0.5 | Verbose when SOUL says "terse" |

### Alignment Score Formula

```
base_score = 10.0
for violation in violations:
    penalty = violation.weight * violation.severity  # severity: 0.1-1.0
    base_score -= penalty
alignment_score = max(0.0, base_score)
```

---

## 3.3 Alignment JSON Schema

```json
{
  "agent": "research_analyst",
  "soul_version": "1.2.0",
  "soul_alignment_score": 7.5,
  "violations": [
    {
      "category": "PRINCIPLE_VIOLATION",
      "principle": "MINIMO 5 busquedas por tarea",
      "detail": "Only 2 web searches performed",
      "weight": 2.0,
      "severity": 0.6,
      "penalty": 1.2
    }
  ],
  "risk_policy_breach": false,
  "confidence_modifier": -0.12,
  "composite_score_adjusted": 6.38,
  "recommendation": "REVISE — insufficient research depth"
}
```

---

## 3.4 Integration with Meta-Supervisor

```
Agent Output
    │
    ▼
┌─────────────────────┐
│  SOUL Alignment      │ ← Loads SOUL.md for this agent
│  Evaluator           │ ← Checks each principle
│                      │ ← Detects violations
│  Output:             │
│    alignment_score   │
│    violations[]      │
│    confidence_mod    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Meta-Supervisor     │ ← Receives alignment_score
│  Decision Engine     │ ← Adjusts composite score
│                      │ ← Low alignment → DELEGATE
└─────────────────────┘
```

The alignment score directly modifies the composite score:

```
adjusted_composite = composite + confidence_modifier
```

If `risk_policy_breach == true`, the decision is forced to `REVISE` or `ESCALATE`
regardless of composite score.

---

## 3.5 SOUL Versioning

```
agents/
  researcher/
    SOUL.md            ← Current active version
    SOUL_v1.0.md       ← Archived baseline
    SOUL_v1.1.md       ← After first experimental change
    SOUL_CHANGELOG.md  ← What changed and why

soul_experiments/
  experiment_001.json  ← A/B test: researcher temperature 0.3 vs 0.5
  experiment_002.json  ← A/B test: "5 searches minimum" vs "3 searches minimum"
```

Experiment JSON:

```json
{
  "experiment_id": "EXP-001",
  "hypothesis": "Reducing researcher temperature from 0.5 to 0.3 improves factuality",
  "agent": "research_analyst",
  "variable": "temperature",
  "control": 0.5,
  "treatment": 0.3,
  "metric": "factuality_score",
  "runs_control": 10,
  "runs_treatment": 10,
  "results": {
    "control_mean": 6.2,
    "treatment_mean": 7.8,
    "p_value": 0.03,
    "conclusion": "ADOPT — temperature 0.3 significantly improves factuality"
  }
}
```

---

# SECTION 4 — Quality Amplification Without Better Models

---

## 4.1 Cross-Agent Critique Loop

Current flow is linear: A → B → C → D.
Redesign as loop with feedback:

```
┌─────────────────────────────────────────────┐
│                                             │
│   T1: Research  ──▶  T2: Strategy  ──▶ T3: QA Review
│                                             │
│                                        ┌────┘
│                                        │ If score < 7
│                                        ▼
│                                   T3b: Feedback
│                                        │
│                           ┌────────────┘
│                           ▼
│              T2b: Strategy (revised)  ──▶  T4: Verify
│                                             │
└─────────────────────────────────────────────┘
```

### Pseudocode

```python
def create_research_crew_with_critique(topic):
    # Phase 1: Generate
    t1_research = Task(agent=researcher, description=f"Research: {topic}")
    t2_strategy = Task(agent=strategist, description="Analyze research, produce strategy")

    # Phase 2: Critique
    t3_qa = Task(
        agent=qa_reviewer,
        description="""
        Score the strategy 1-10 on: completeness, feasibility, evidence quality.
        If ANY dimension < 7, provide SPECIFIC revision instructions.
        Output format: {score: int, pass: bool, revisions: [str]}
        """,
        context=[t1_research, t2_strategy],
    )

    # Phase 3: Revise (conditional — only executes if QA rejects)
    t4_revise = Task(
        agent=strategist,
        description="""
        REVISION PASS: Address EACH criticism from QA specifically.
        Do not regenerate from scratch — improve the existing strategy.
        """,
        context=[t2_strategy, t3_qa],
    )

    # Phase 4: Verify
    t5_verify = Task(
        agent=verifier,
        description="Final verification. Check 3 key claims. Score 1-10.",
        context=[t4_revise, t3_qa],
    )

    return Crew(
        agents=[researcher, strategist, qa_reviewer, verifier],
        tasks=[t1_research, t2_strategy, t3_qa, t4_revise, t5_verify],
        process=Process.sequential,
    )
```

---

## 4.2 Structured Reasoning Templates

Force agents to reason in structured phases instead of free-form generation.

### Research Template

```markdown
## RESEARCH PROTOCOL

### Phase 1: Data Collection
- Search query 1: {query} → Results: {summary}
- Search query 2: {query} → Results: {summary}
- (minimum 5 queries)

### Phase 2: Source Evaluation
| Source | Type | Credibility | Recency | Key Data |
|--------|------|-------------|---------|----------|

### Phase 3: Synthesis
- Primary finding: {statement with source}
- Supporting evidence: {2-3 data points}
- Contradicting evidence: {if any}

### Phase 4: Confidence Assessment
- Data sufficiency: {low/medium/high}
- Source agreement: {low/medium/high}
- Overall confidence: {1-10}
```

### Strategy Template

```markdown
## STRATEGY PROTOCOL

### Phase 1: Problem Definition
- Core problem: {one sentence}
- Target user: {specific persona}
- Success metric: {measurable KPI}

### Phase 2: Solution Space
| Option | Pros | Cons | Effort | Impact |
|--------|------|------|--------|--------|

### Phase 3: Recommendation
- Selected option: {with justification}
- Implementation path: {ordered steps}
- Risk mitigation: {for top 3 risks}

### Phase 4: Validation Criteria
- How to know this works: {testable criteria}
```

### Integration

Inject templates into task descriptions:

```python
Task(
    description=f"""
    {RESEARCH_TEMPLATE}

    TOPIC: {topic}
    CONTEXT: {pre_research_data}

    Follow the protocol above step by step.
    Do not skip phases.
    """,
    agent=researcher,
)
```

---

## 4.3 Error Classification System

```python
class ErrorTaxonomy:
    CATEGORIES = {
        # Provider-level
        "RATE_LIMIT":       {"transient": True,  "retry": True,  "switch_provider": True},
        "AUTH_FAILURE":      {"transient": False, "retry": False, "switch_provider": True},
        "MODEL_INCOMPATIBLE":{"transient": False, "retry": False, "switch_provider": True},
        "TIMEOUT":           {"transient": True,  "retry": True,  "switch_provider": False},

        # Agent-level
        "LOW_QUALITY":       {"transient": False, "retry": True,  "switch_provider": True},
        "SOUL_VIOLATION":    {"transient": False, "retry": True,  "switch_provider": False},
        "HALLUCINATION":     {"transient": False, "retry": True,  "switch_provider": True},
        "INCOMPLETE":        {"transient": False, "retry": True,  "switch_provider": False},

        # Tool-level
        "TOOL_FAILURE":      {"transient": True,  "retry": True,  "switch_provider": False},
        "SEARCH_EMPTY":      {"transient": True,  "retry": True,  "switch_provider": False},

        # System-level
        "MEMORY_ERROR":      {"transient": True,  "retry": False, "switch_provider": False},
        "PYDANTIC_PARSE":    {"transient": False, "retry": True,  "switch_provider": True},
    }

    @classmethod
    def classify(cls, error: Exception) -> ErrorClassification:
        error_str = str(error).lower()

        if "rate_limit" in error_str or "429" in error_str:
            return cls.CATEGORIES["RATE_LIMIT"]
        if "authentication" in error_str or "api key" in error_str:
            return cls.CATEGORIES["AUTH_FAILURE"]
        if "invalid grammar" in error_str or "not supported" in error_str:
            return cls.CATEGORIES["MODEL_INCOMPATIBLE"]
        if "timeout" in error_str:
            return cls.CATEGORIES["TIMEOUT"]
        if "validation error" in error_str:
            return cls.CATEGORIES["PYDANTIC_PARSE"]
        # ... etc

        return {"transient": False, "retry": False, "switch_provider": False}
```

---

## 4.4 Self-Healing Retry with Checkpointing

```python
class CheckpointedCrew:
    """Wraps CrewAI Crew with task-level checkpointing."""

    def __init__(self, crew: Crew):
        self.crew = crew
        self.checkpoints: dict[str, TaskOutput] = {}

    def kickoff_with_checkpoints(self) -> CrewOutput:
        completed_tasks = []

        for task in self.crew.tasks:
            task_id = task.description[:50]

            # Check if we have a checkpoint for this task
            if task_id in self.checkpoints:
                completed_tasks.append(self.checkpoints[task_id])
                continue

            try:
                # Execute single task
                result = self._execute_single_task(task, completed_tasks)
                self.checkpoints[task_id] = result
                completed_tasks.append(result)

            except Exception as e:
                classification = ErrorTaxonomy.classify(e)

                if classification["switch_provider"]:
                    mark_provider_exhausted(detect_provider(e))
                    # Re-create agent with new provider
                    task.agent = self._rebuild_agent_with_fallback(task.agent)
                    result = self._execute_single_task(task, completed_tasks)
                    self.checkpoints[task_id] = result
                    completed_tasks.append(result)

                elif classification["retry"]:
                    result = self._execute_single_task(task, completed_tasks)
                    self.checkpoints[task_id] = result
                    completed_tasks.append(result)

                else:
                    raise  # Non-recoverable

        return self._compile_output(completed_tasks)
```

---

# SECTION 5 — Experimental Observability Framework

---

## 5.1 Core Metrics

| Metric | Type | Source | Unit |
|--------|------|--------|------|
| `quality_score` | Gauge | Meta-Supervisor eval | 0-10 |
| `soul_alignment_score` | Gauge | SOUL evaluator | 0-10 |
| `retry_count` | Counter | Retry loop | integer |
| `fallback_depth` | Gauge | Provider chain position | 0-3 |
| `latency_ms` | Histogram | Task execution time | milliseconds |
| `tokens_input` | Counter | LiteLLM callback | integer |
| `tokens_output` | Counter | LiteLLM callback | integer |
| `memory_coherence` | Gauge | Memory query relevance | 0-1.0 |
| `delegation_count` | Counter | Meta-Supervisor decisions | integer |
| `tool_calls` | Counter | CrewAI step callback | integer |
| `search_queries` | Counter | WebSearchTool invocations | integer |
| `sources_cited` | Counter | Output parsing | integer |

---

## 5.2 Derived Metrics

### Stability Index

```
stability = 1.0 - (retry_count / max_retries) * (fallback_depth / max_depth)

Range: 0.0 (unstable) to 1.0 (stable)
Meaning: How cleanly did execution complete?
```

### Cognitive Drift Index

```
drift = |soul_alignment_score_current - soul_alignment_score_baseline| / 10.0

Range: 0.0 (no drift) to 1.0 (complete identity loss)
Meaning: Is the agent maintaining its identity over time?
Requires: Baseline measurement per agent.
```

### Fallback Fragility Index

```
fragility = Σ(fallback_events) / Σ(total_executions) over last N runs

Range: 0.0 (never falls back) to 1.0 (always falls back)
Meaning: How dependent is the system on fallback chains?
Alert threshold: > 0.5
```

### Alignment-Consistency Ratio

```
ACR = min(soul_scores_last_10) / max(soul_scores_last_10)

Range: 0.0 (wildly inconsistent) to 1.0 (perfectly consistent)
Meaning: Does the agent maintain consistent alignment?
```

---

## 5.3 Experiment Run Schema

```json
{
  "experiment_id": "EXP-2026-03-03-001",
  "hypothesis": "Pre-research with 5 searches produces higher quality than 3 searches",
  "independent_variable": "pre_research_num_searches",
  "control_value": 3,
  "treatment_value": 5,
  "dependent_variables": ["quality_score", "sources_cited", "factuality_score"],
  "agent": "research_analyst",
  "crew": "research",
  "runs": [
    {
      "run_id": "RUN-001",
      "group": "control",
      "timestamp": "2026-03-03T10:00:00Z",
      "input": "Analyze DeFi lending protocols on Avalanche",
      "config": {"num_searches": 3},
      "metrics": {
        "quality_score": 5.8,
        "soul_alignment_score": 7.2,
        "sources_cited": 4,
        "factuality_score": 5.5,
        "latency_ms": 45000,
        "tokens_total": 12400,
        "retry_count": 0,
        "fallback_depth": 0,
        "stability_index": 1.0,
        "provider_used": "groq/llama-3.3-70b-versatile"
      },
      "output_path": "output/research_20260303_100000.md"
    }
  ],
  "analysis": {
    "control_mean_quality": 5.6,
    "treatment_mean_quality": 7.2,
    "effect_size": 1.6,
    "p_value": 0.02,
    "conclusion": "SIGNIFICANT — 5 searches produces materially better output"
  }
}
```

---

## 5.4 Event Taxonomy

```yaml
events:
  system:
    - SYSTEM_BOOT
    - SYSTEM_SHUTDOWN
    - PROVIDER_EXHAUSTED
    - PROVIDER_RECOVERED
    - MEMORY_INIT
    - MEMORY_ERROR

  crew:
    - CREW_START
    - CREW_COMPLETE
    - CREW_ERROR
    - CREW_RETRY

  task:
    - TASK_START
    - TASK_COMPLETE
    - TASK_ERROR
    - TASK_CHECKPOINT_SAVED

  agent:
    - AGENT_ASSIGNED
    - AGENT_OUTPUT_PRODUCED
    - AGENT_TOOL_CALLED
    - AGENT_TOOL_RESULT
    - AGENT_DELEGATED_TO
    - AGENT_REVISION_REQUESTED

  supervisor:
    - SUPERVISOR_EVAL_START
    - SUPERVISOR_EVAL_COMPLETE
    - SUPERVISOR_DECISION_ACCEPT
    - SUPERVISOR_DECISION_REVISE
    - SUPERVISOR_DECISION_RETRY
    - SUPERVISOR_DECISION_DELEGATE
    - SUPERVISOR_DECISION_ESCALATE

  quality:
    - QUALITY_SCORE_RECORDED
    - ALIGNMENT_SCORE_RECORDED
    - VIOLATION_DETECTED
    - RISK_POLICY_BREACH
```

---

## 5.5 Logging Structure

### JSONL Event Log (`logs/events.jsonl`)

```json
{"ts":"2026-03-03T10:00:01Z","event":"CREW_START","crew":"research","task_count":5,"providers":["groq","cerebras"]}
{"ts":"2026-03-03T10:00:02Z","event":"AGENT_ASSIGNED","agent":"research_analyst","provider":"groq/llama-3.3-70b-versatile","task":"Research: DeFi"}
{"ts":"2026-03-03T10:00:45Z","event":"AGENT_TOOL_CALLED","agent":"research_analyst","tool":"web_search","query":"DeFi lending Avalanche TVL 2026"}
{"ts":"2026-03-03T10:00:47Z","event":"AGENT_TOOL_RESULT","agent":"research_analyst","tool":"web_search","results_count":5}
{"ts":"2026-03-03T10:01:30Z","event":"AGENT_OUTPUT_PRODUCED","agent":"research_analyst","tokens_out":2400}
{"ts":"2026-03-03T10:01:31Z","event":"SUPERVISOR_EVAL_START","agent":"research_analyst"}
{"ts":"2026-03-03T10:01:33Z","event":"QUALITY_SCORE_RECORDED","agent":"research_analyst","score":7.5}
{"ts":"2026-03-03T10:01:33Z","event":"ALIGNMENT_SCORE_RECORDED","agent":"research_analyst","score":8.2}
{"ts":"2026-03-03T10:01:33Z","event":"SUPERVISOR_DECISION_ACCEPT","agent":"research_analyst","composite":7.7}
```

### Minimal Storage Design

```
logs/
├── events.jsonl          # All events (append-only, rotate at 10MB)
├── metrics.jsonl         # Numeric metrics only (for analysis)
├── experiments/
│   ├── EXP-001.json      # Experiment definition + results
│   └── EXP-002.json
├── execution_log.jsonl   # Legacy — crew-level log (existing)
├── test_reports.jsonl    # Incident reports (existing)
└── test_summary.md       # Human-readable summary (existing)
```

Rotation: When `events.jsonl` exceeds 10MB, rename to `events_YYYYMMDD.jsonl`
and start fresh. Keep last 7 days.

---

## 5.6 Visualization-Ready Output

All metrics are emitted as flat JSON objects that can be directly consumed by:
- Streamlit charts (`st.line_chart`, `st.bar_chart`)
- Plotly dashboards
- CSV export for Jupyter analysis
- WebSocket broadcast to browser dashboard

```python
# Example: load metrics for plotting
import json
import pandas as pd

metrics = []
with open("logs/metrics.jsonl") as f:
    for line in f:
        metrics.append(json.loads(line))

df = pd.DataFrame(metrics)
df["ts"] = pd.to_datetime(df["ts"])

# Quality over time
df.groupby("agent")["quality_score"].plot()

# Provider usage distribution
df["provider"].value_counts().plot.pie()

# Stability trend
df.set_index("ts")["stability_index"].rolling(10).mean().plot()
```

---

# SECTION 6 — Delegation & Cognitive Depth Evolution

---

## 6.1 Task Classification Logic

Replace static keyword routing with structured classification:

```python
class TaskClassifier:
    """Classifies incoming tasks to determine optimal crew and depth."""

    DIMENSIONS = {
        "complexity": {
            "simple":   {"agents": 1, "max_tokens": 2000,  "timeout": 60},
            "moderate": {"agents": 3, "max_tokens": 8000,  "timeout": 180},
            "complex":  {"agents": 5, "max_tokens": 16000, "timeout": 300},
            "deep":     {"agents": 7, "max_tokens": 32000, "timeout": 600},
        },
        "domain": {
            "research":  ["research_analyst", "qa_reviewer", "verifier"],
            "strategy":  ["mvp_strategist", "research_analyst", "qa_reviewer"],
            "code":      ["code_architect", "qa_reviewer", "verifier"],
            "data":      ["data_engineer", "qa_reviewer"],
            "content":   ["narrative_content", "research_analyst", "qa_reviewer"],
            "ops":       ["project_organizer", "data_engineer"],
            "general":   ["research_analyst", "mvp_strategist", "code_architect",
                         "qa_reviewer", "verifier"],
        }
    }

    def classify(self, task_text: str) -> TaskClassification:
        # Step 1: Detect domain
        domain = self._detect_domain(task_text)

        # Step 2: Estimate complexity
        complexity = self._estimate_complexity(task_text)

        # Step 3: Select agent team
        agents = self.DIMENSIONS["domain"][domain]
        config = self.DIMENSIONS["complexity"][complexity]

        # Step 4: Determine if pre-research needed
        needs_research = domain in ("research", "strategy", "general")

        return TaskClassification(
            domain=domain,
            complexity=complexity,
            agents=agents[:config["agents"]],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            needs_pre_research=needs_research,
        )

    def _estimate_complexity(self, text: str) -> str:
        word_count = len(text.split())
        has_multiple_topics = text.count(",") > 2 or text.count(" y ") > 1
        has_code_request = any(w in text.lower() for w in ["codigo", "code", "build", "implementa"])
        has_analysis = any(w in text.lower() for w in ["analiza", "compara", "evalua", "investiga"])

        score = 0
        if word_count > 50: score += 1
        if has_multiple_topics: score += 1
        if has_code_request: score += 1
        if has_analysis: score += 1

        return ["simple", "moderate", "complex", "deep"][min(score, 3)]
```

---

## 6.2 Agent Voting Mechanism

For complex tasks, multiple agents can vote on approach before execution:

```python
class AgentVoting:
    """Lightweight voting — agents propose approaches, best one wins."""

    def vote(self, task: str, candidate_agents: list[Agent]) -> VoteResult:
        proposals = []

        for agent in candidate_agents[:3]:  # Max 3 voters (cost control)
            proposal = agent.llm.call(messages=[{
                "role": "user",
                "content": f"""
                Task: {task}

                In 2-3 sentences, propose your approach. Include:
                1. Key question to answer
                2. Primary method
                3. Expected deliverable

                Be specific. No preamble.
                """
            }])
            proposals.append({
                "agent": agent.role,
                "proposal": proposal,
            })

        # Use cheapest LLM to pick best proposal
        judge = get_cerebras_llm(temperature=0.0)
        verdict = judge.call(messages=[{
            "role": "user",
            "content": f"""
            Task: {task}

            Proposals:
            {json.dumps(proposals, indent=2)}

            Pick the best proposal. Return JSON:
            {{"winner": "agent_role", "reason": "why"}}
            """
        }])

        return VoteResult.parse_raw(verdict)
```

---

## 6.3 Sub-Task Spawning Rules

```
Rules:
1. An agent can request sub-task spawning via structured output:
   {"needs_subtask": true, "subtask": "...", "target_agent": "..."}

2. Maximum spawn depth: 2 (original → sub → sub-sub, no deeper)

3. Maximum concurrent sub-tasks: 3 (free-tier cost control)

4. Sub-tasks inherit parent's timeout budget minus elapsed time.
   If parent has 120s remaining and sub-task needs 60s, it proceeds.
   If parent has 10s remaining, sub-task is rejected.

5. Sub-task results are injected back into parent agent's context.

6. Sub-task spawning is logged as AGENT_DELEGATED_TO event.
```

---

## 6.4 Safety Boundaries

```python
SAFETY_LIMITS = {
    "max_total_tokens_per_request": 100_000,    # Across all agents in crew
    "max_tool_calls_per_agent": 20,              # Prevent infinite loops
    "max_web_searches_per_crew": 30,             # Rate limit protection
    "max_delegation_depth": 2,                    # Prevent recursion
    "max_revision_loops": 2,                      # Prevent infinite revision
    "max_crew_duration_seconds": 600,             # 10 min hard limit
    "max_retries_per_provider": 1,                # Don't retry same provider
    "min_output_length": 100,                     # Detect empty responses
    "max_output_length": 50_000,                  # Prevent token waste
}
```

---

# SECTION 7 — Mission Control Dashboard Bridge

---

## 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CrewAI Runtime                          │
│                                                             │
│  step_callback ──▶ EventEmitter ──▶ EventBus               │
│  task_callback ──▶ EventEmitter ──▶ EventBus               │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  Event Bus  │ (in-process queue)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
       ┌───────────┐ ┌──────────┐  ┌──────────────┐
       │ JSONL Log │ │ WebSocket│  │ Metrics      │
       │ Writer    │ │ Broadcast│  │ Aggregator   │
       └───────────┘ │ Server   │  │ (in-memory)  │
                     └──────────┘  └──────────────┘
                          │                │
                          ▼                ▼
                   ┌───────────────────────────┐
                   │   Mission Control UI       │
                   │   (Streamlit / React)      │
                   │                            │
                   │   ┌─────────┐ ┌─────────┐ │
                   │   │ Live    │ │ Agent   │  │
                   │   │ Timeline│ │ Cards   │  │
                   │   ├─────────┤ ├─────────┤  │
                   │   │ Provider│ │ Quality │  │
                   │   │ Status  │ │ Trends  │  │
                   │   ├─────────┤ ├─────────┤  │
                   │   │ Metrics │ │ Crew    │  │
                   │   │ Gauges  │ │ Pipeline│  │
                   │   └─────────┘ └─────────┘  │
                   └───────────────────────────┘
```

---

## 7.2 Event Mapping Structure

```python
# CrewAI callbacks → Dashboard events

EVENT_MAP = {
    # CrewAI step_callback
    "agent_start":      {"dashboard": "AGENT_ACTIVE",     "panel": "agent_cards"},
    "tool_use":         {"dashboard": "TOOL_INVOKED",     "panel": "live_timeline"},
    "tool_result":      {"dashboard": "TOOL_COMPLETE",    "panel": "live_timeline"},
    "agent_end":        {"dashboard": "AGENT_COMPLETE",   "panel": "agent_cards"},

    # CrewAI task_callback
    "task_start":       {"dashboard": "TASK_ACTIVE",      "panel": "crew_pipeline"},
    "task_complete":    {"dashboard": "TASK_DONE",        "panel": "crew_pipeline"},

    # Meta-Supervisor events
    "eval_complete":    {"dashboard": "QUALITY_UPDATE",   "panel": "quality_trends"},
    "decision":         {"dashboard": "SUPERVISOR_ACTION","panel": "live_timeline"},
    "violation":        {"dashboard": "SOUL_ALERT",       "panel": "agent_cards"},

    # Provider events
    "provider_exhaust": {"dashboard": "PROVIDER_DOWN",    "panel": "provider_status"},
    "provider_recover": {"dashboard": "PROVIDER_UP",      "panel": "provider_status"},
    "fallback_used":    {"dashboard": "FALLBACK_ACTIVE",  "panel": "provider_status"},
}
```

---

## 7.3 Required Endpoints

```
GET  /api/status              → System status + provider availability
GET  /api/agents              → Agent cards with current state
GET  /api/metrics/latest      → Last N metrics
GET  /api/metrics/summary     → Aggregated metrics (last hour/day/week)
GET  /api/experiments         → Experiment list
GET  /api/experiments/:id     → Experiment detail
GET  /api/logs/events?since=  → Event stream (polling fallback)
WS   /ws/events               → Real-time event stream (WebSocket)
POST /api/crew/run            → Trigger crew execution
```

---

## 7.4 Free-Tier Compatible Stack

```
Option A — Streamlit (current, simplest):
  - Streamlit 1.42+ with st.experimental_fragment for partial updates
  - st.session_state for WebSocket-like state
  - Plotly for interactive charts
  - No additional server needed
  - Limitation: not true real-time, poll-based

Option B — FastAPI + htmx (lightweight real-time):
  - FastAPI with WebSocket support
  - htmx for partial page updates
  - Server-Sent Events for real-time
  - Tailwind CSS for styling
  - DaisyUI for components
  - Zero JavaScript framework
  - Single Python process

Option C — React + FastAPI (maximum capability):
  - React with Vite (local dev)
  - Recharts or Nivo for visualization
  - WebSocket for real-time
  - FastAPI backend
  - More complex, but most capable
  - Best for open-source release
```

**Recommendation:** Option B (FastAPI + htmx) for Phase 4.
Minimal JavaScript, pure Python backend, real-time capable,
easy to embed in existing system. Switch to Option C only if
open-source community demands SPA experience.

---

# SECTION 8 — Research Positioning

---

## 8.1 Hypothesis

> Multi-agent LLM systems operating exclusively on free-tier inference
> providers can achieve research-grade output quality through architectural
> interventions — specifically meta-supervision, SOUL-governed cognitive
> alignment, and structured cross-agent critique loops — without requiring
> access to frontier commercial models.

---

## 8.2 Novel Contribution

1. **SOUL Governance Model**: First formalization of agent identity as an
   operational governance layer with measurable alignment scoring,
   violation taxonomy, and experimental versioning protocol.

2. **Free-Tier Resilience Architecture**: First documented architecture for
   multi-provider LLM fallback chains with provider exhaustion tracking,
   error taxonomy, and task-level checkpointing — operating entirely
   within free-tier quotas.

3. **Meta-Supervision Pattern**: Lightweight evaluation layer that uses the
   cheapest available LLM to score and route outputs from more expensive
   LLMs, creating a quality amplification loop without model upgrades.

4. **Cognitive Drift Measurement**: First quantitative framework for
   measuring agent identity consistency over time in multi-agent systems,
   via the Alignment-Consistency Ratio and Cognitive Drift Index.

---

## 8.3 Experimental Variables

| Variable | Type | Range | Measurement |
|----------|------|-------|-------------|
| Number of pre-research searches | Independent | 0, 3, 5, 10 | Control in code |
| SOUL temperature | Independent | 0.0, 0.2, 0.5, 0.7 | SOUL.md config |
| Critique loop depth | Independent | 0, 1, 2 | Crew structure |
| Provider chain length | Independent | 1, 2, 4 | llm_config.py |
| Meta-supervisor threshold | Independent | 4.0, 6.0, 8.0 | supervisor config |
| Output quality score | Dependent | 0-10 | Meta-supervisor eval |
| SOUL alignment score | Dependent | 0-10 | SOUL evaluator |
| Execution latency | Dependent | ms | System clock |
| Token consumption | Dependent | integer | LiteLLM callback |
| Retry count | Dependent | 0-3 | Retry loop counter |
| Stability index | Derived | 0-1 | Formula |
| Cognitive drift index | Derived | 0-1 | Formula |

---

## 8.4 Baseline Comparisons

| Comparison | Baseline | Treatment |
|------------|----------|-----------|
| Raw vs. Supervised | No meta-supervisor | With meta-supervisor |
| Static vs. SOUL-governed | No SOUL eval | With SOUL alignment |
| Linear vs. Critique loop | Sequential crew | Crew with QA feedback loop |
| Single provider vs. Multi | One LLM for all | Fallback chains |
| No pre-research vs. Pre-research | Cold start | 5 web searches injected |

Each comparison requires minimum 10 runs per condition for statistical power.

---

## 8.5 Measurable Claims

1. "Meta-supervision increases mean output quality by X points (0-10 scale)
   with p < 0.05 over N=20 runs."

2. "Cross-agent critique loops reduce hallucination rate from X% to Y%
   as measured by factuality score."

3. "SOUL governance maintains alignment-consistency ratio > 0.8 across
   50 consecutive executions."

4. "Free-tier multi-provider fallback achieves 95%+ execution success rate
   despite individual provider failure rates of 15-30%."

5. "Structured reasoning templates increase sources cited per output
   from X to Y (mean, p < 0.05)."

---

## 8.6 Publication Angle

**Title:** "SOUL-Governed Multi-Agent Systems: Architectural Quality
Amplification on Free-Tier LLM Infrastructure"

**Venue targets:**
- AAMAS 2027 (Autonomous Agents and Multi-Agent Systems)
- AAAI 2027 Workshop on LLM Agents
- NeurIPS 2026 Workshop on Foundation Model Agents
- arXiv preprint (immediate, for visibility)

**Framing:** This is NOT "we built a chatbot." This is:
"We present a governance and quality framework for multi-agent LLM systems
that operates within zero-cost inference constraints and demonstrates
measurable quality amplification through architectural interventions."

---

# SECTION 9 — 90-Day Evolution Roadmap

---

## Phase 1 — Meta-Supervisor + SOUL Governance (Days 1-21)

### Deliverables
1. `meta_supervisor/` module with evaluator, decision engine, metrics emitter
2. Standardized SOUL.md format for all 8 agents
3. SOUL alignment evaluator (uses Cerebras GPT-OSS for eval)
4. Integration with CrewAI via step_callback and task_callback
5. Baseline measurement: 10 research runs without supervisor
6. Treatment measurement: 10 research runs with supervisor

### Files Created/Modified
```
NEW:  meta_supervisor/__init__.py
NEW:  meta_supervisor/supervisor.py
NEW:  meta_supervisor/evaluator.py
NEW:  meta_supervisor/decision_engine.py
NEW:  meta_supervisor/metrics_emitter.py
NEW:  meta_supervisor/schemas.py
NEW:  meta_supervisor/prompts/eval_template.md
MOD:  agents/*/SOUL.md              (all 8 — standardized format)
MOD:  crew.py                       (add step_callback, task_callback)
MOD:  interfaces/telegram_bot.py    (pass supervisor metrics to user)
```

### Risk Factors
- Cerebras eval calls consume from 1M tok/day free quota
- CrewAI step_callback API may change between versions
- Eval LLM scoring may be inconsistent at temperature=0.0

### Validation Criteria
- Supervisor correctly intercepts 100% of task outputs
- Quality scores have standard deviation < 1.5 across 10 identical runs
- REVISE decision actually improves output (before vs. after comparison)
- No increase in total execution time > 20%

---

## Phase 2 — Observability Layer (Days 22-42)

### Deliverables
1. `observability/` module with event bus, JSONL logger, metrics aggregator
2. Error taxonomy classifier integrated into retry logic
3. Provider usage tracking (tokens per provider, distance to rate limit)
4. Task-level checkpointing (partial result recovery)
5. Experiment runner: define experiment, run N trials, compute statistics
6. First 3 experiments run with published results

### Files Created/Modified
```
NEW:  observability/__init__.py
NEW:  observability/event_bus.py
NEW:  observability/logger.py
NEW:  observability/metrics.py
NEW:  observability/experiments.py
NEW:  observability/error_taxonomy.py
NEW:  observability/checkpointing.py
MOD:  llm_config.py                 (provider usage tracking)
MOD:  interfaces/telegram_bot.py    (error taxonomy integration)
MOD:  crew.py                       (checkpointing wrapper)
```

### Risk Factors
- JSONL log files grow unbounded without rotation
- Checkpointing may conflict with CrewAI's internal state management
- Experiment runner needs deterministic inputs (pre-research caching)

### Validation Criteria
- All 12 event types logged correctly
- Metrics aggregation produces correct derived metrics
- Checkpoint recovery works: kill process mid-crew, restart, resume
- 3 experiments completed with p-values computed

---

## Phase 3 — Delegation Upgrade (Days 43-56)

### Deliverables
1. Task classifier replacing keyword-based routing
2. Dynamic crew composition based on task complexity
3. Agent voting for complex tasks (3-agent proposal + judge)
4. Sub-task spawning with depth limits
5. Safety boundary enforcement
6. Provider exhaustion TTL (auto-recovery after 5 minutes)

### Files Created/Modified
```
NEW:  delegation/__init__.py
NEW:  delegation/classifier.py
NEW:  delegation/voting.py
NEW:  delegation/spawner.py
NEW:  delegation/safety.py
MOD:  crew.py                       (dynamic crew composition)
MOD:  llm_config.py                 (exhaustion TTL)
MOD:  interfaces/telegram_bot.py    (classifier replaces CREW_ROUTES)
```

### Risk Factors
- Agent voting consumes 3x LLM calls per task classification
- Dynamic crew composition may produce untested agent combinations
- Sub-task spawning could hit rate limits faster

### Validation Criteria
- Classifier correctly categorizes 90% of test inputs (20 samples)
- Voting selects appropriate agent for 85% of tasks
- Safety boundaries prevent all recursive loops
- Exhaustion TTL correctly recovers providers after timeout

---

## Phase 4 — Mission Control UI (Days 57-77)

### Deliverables
1. FastAPI backend with WebSocket support
2. htmx-based dashboard with real-time event stream
3. 6 panels: Live Timeline, Agent Cards, Provider Status,
   Quality Trends, Crew Pipeline, Experiment Results
4. Metric gauges: quality, stability, drift, fragility
5. One-click crew execution from dashboard
6. Mobile-responsive layout

### Files Created/Modified
```
NEW:  dashboard/__init__.py
NEW:  dashboard/app.py              (FastAPI + WebSocket)
NEW:  dashboard/templates/
NEW:  dashboard/templates/index.html
NEW:  dashboard/templates/partials/
NEW:  dashboard/static/
MOD:  main.py                       (add dashboard launch option)
```

### Risk Factors
- FastAPI + htmx is less documented than React ecosystems
- WebSocket may not work behind all proxy configurations
- Real-time updates may overwhelm browser on long crew runs

### Validation Criteria
- Dashboard displays all 6 panels correctly
- WebSocket delivers events within 100ms of emission
- Dashboard works on mobile Safari and Chrome
- Crew can be triggered and monitored end-to-end from dashboard

---

## Phase 5 — Research-Grade Documentation (Days 78-90)

### Deliverables
1. Architecture documentation (this document, refined)
2. API reference for Meta-Supervisor, Observability, Delegation modules
3. Experiment results compilation (minimum 5 experiments)
4. arXiv preprint draft (8-12 pages)
5. GitHub repository cleanup:
   - README with architecture diagram
   - CONTRIBUTING.md
   - LICENSE (MIT or Apache 2.0)
   - Examples directory with 3 tutorial notebooks
6. Recorded demo video (5 minutes)

### Files Created/Modified
```
NEW:  docs/ARCHITECTURE.md
NEW:  docs/API_REFERENCE.md
NEW:  docs/EXPERIMENTS.md
NEW:  paper/soul_governance_preprint.tex
NEW:  examples/01_basic_research.py
NEW:  examples/02_custom_soul.py
NEW:  examples/03_experiment_runner.py
NEW:  README.md                      (complete rewrite)
NEW:  CONTRIBUTING.md
NEW:  LICENSE
```

### Risk Factors
- Experiment results may not show statistical significance
- arXiv preprint requires LaTeX formatting
- Demo video needs stable system (no rate limits during recording)

### Validation Criteria
- All code examples run without errors
- README enables a new user to run the system in < 10 minutes
- Preprint passes internal review (clear hypothesis, methodology, results)
- At least 3 experiments show statistically significant results

---

# APPENDIX A — Priority Actions (Immediate)

The following fixes should be applied BEFORE beginning the 90-day roadmap:

| # | Action | File | Effort | Impact |
|---|--------|------|--------|--------|
| 1 | Add exhaustion TTL (5 min) | llm_config.py | 10 lines | HIGH — prevents permanent degradation |
| 2 | Mark NVIDIA as `no_structured_output` | llm_config.py | 20 lines | HIGH — prevents wasted retries |
| 3 | Add A2A server authentication | a2a_server.py | 30 lines | CRITICAL — security |
| 4 | Split crew.py into modules | crew/*.py | refactor | MEDIUM — maintainability |
| 5 | Fix list_project_files f-string bug | code_tools.py | 1 line | LOW — correctness |
| 6 | Load and use agents.yaml dynamically | crew.py | 50 lines | MEDIUM — removes duplication |
| 7 | Remove Zhipu from primary fallback chains | llm_config.py | done | HIGH — stability |

---

# APPENDIX B — Cost Model (Free-Tier Budget)

```
Daily Budget:
  Cerebras:    1,000,000 tokens/day
  Groq:        ~100,000 tokens/day (variable, TPM-limited)
  NVIDIA NIM:  1,000 credits (one-time, ~500K tokens)
  Zhipu:       Generous (undocumented limit)
  Gemini:      20 requests/day

Per Crew Execution (estimated):
  Research crew:     ~15,000 tokens (5 tasks × 3,000 avg)
  Full MVP crew:     ~25,000 tokens (7 tasks × 3,500 avg)
  Meta-supervisor:   ~2,000 tokens per task eval (5 evals × 400 avg)

Daily Capacity (Cerebras-only):
  1,000,000 / 17,000 = ~58 research crew runs/day
  1,000,000 / 27,000 = ~37 full MVP runs/day

With Meta-supervisor overhead (+15%):
  ~50 research runs/day
  ~32 full MVP runs/day

Conclusion: Free-tier budget supports serious experimental workload.
Meta-supervisor overhead is manageable (~2K tokens per evaluation).
```
