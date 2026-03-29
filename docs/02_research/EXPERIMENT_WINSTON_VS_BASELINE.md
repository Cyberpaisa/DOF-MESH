# Experiment: Winston vs Baseline
## DOF Mesh Legion — Cyber Paisa / Enigma Group

> **Status:** Phase 1 completed (local + API) | Phase 2 in progress (web models)
> **Start date:** Mar 27, 2026 | **Last updated:** Mar 28, 2026

---

## Objective

Measure the quantitative impact of the **Winston Communication Framework** on LLM response quality, using the **CQ Score** as the primary metric.

Hypothesis: A structured system prompt with Winston format (indicator → impact → evidence → action) improves communication quality by ≥ 30 CQ points vs. free baseline.

---

## The Winston Framework

Based on the work of **Patrick Winston (MIT)** on effective communication. Central principle: the quality of communication determines the impact of knowledge.

### Required format (4 parts)

```
[INDICATOR] Direct conclusion on the first line.
This means that [concrete impact on the system/user].
Evidence: [concrete data — numbers, metrics, percentages].
Next step: [specific and executable action].
```

### Available indicators
- `[PROVEN]` — formally verified (Z3, tests)
- `[BLOCKED]` — blocked by governance
- `[WARNING]` — risk condition
- `[PASS]` — successful validation
- `[FAIL]` — failed validation
- `[DONE]` — task completed

### Prohibited
- "Here is the result..."
- "I hope this is helpful"
- "If you need more information"
- "As an AI assistant..."

---

## CQ Score — Quality Metric

**Communication Quality Score (0-100)** — deterministic, no LLM.

| Component        | Pts | Criterion |
|------------------|-----|----------|
| Clarity          | 25  | Indicator on first line (15) + optimal length (10) |
| Relevance        | 25  | "This means that..." present |
| Structure        | 20  | Indicators + markdown (headers, bullets) |
| Surprise         | 15  | Unexpected finding markers |
| Actionable close | 15  | "Next step:" present, no filler phrases (-10) |

**Composite total score (0-100):**
```
Total = CQ×0.40 + Components×0.40 + Keywords×0.20
```

Where Components = binary average of 5 Winston checks.

---

## Experiment Infrastructure

### Files

```
experiments/winston_vs_baseline/
  ├── experiment_runner.py        # Local + API runner (Phase 1)
  ├── web_experiment_prompts.json # Prompts + web responses (Phase 2)
  └── web_experiment_scorer.py   # Scorer for web responses

logs/experiments/winston_vs_baseline/
  ├── experiment_20260328_003941.jsonl  # v1 — Ollama local only
  ├── experiment_20260328_004212.jsonl  # v2 — + API models
  ├── experiment_20260328_004941.jsonl  # v3 — + few-shot + anchor (REFERENCE)
  ├── report_20260328_003941.json
  ├── report_20260328_004212.json
  └── report_20260328_004941.json       # ← Canonical Phase 1 results
```

### Difficulty levels

| Level        | Task | Max tokens |
|--------------|-------|------------|
| BASIC        | Factual description of the project | 200 |
| INTERMEDIATE | Critical analysis + measurable improvements | 350 |
| ADVANCED     | Complex strategic planning with trade-offs | 500 |

### Teams

- **Team BLUE**: Winston system prompt + few-shot examples + anchor at end
- **Team RED**: Baseline — "be helpful and detailed", same context

---

## Phase 1 Results — Experiment v3 (Canonical Reference)

**Date:** Mar 28, 2026 | **ID:** `20260328_004941`
**Improvements over v1/v2:** few-shot examples + anchor at end of messages

### Full ranking

| Position | Model | BLUE | RED | Delta | Type |
|----------|--------|------|-----|-------|------|
| 1 | gemma2:9b | 86.0 | 32.0 | **+54.0** | Local |
| 2 | dof-voice-fast (gemma2) | 84.7 | 34.7 | **+50.0** | Local custom |
| 3 | dof-analyst | 80.7 | 30.7 | **+50.0** | Local custom |
| 4 | dof-coder | 81.3 | 32.0 | **+49.3** | Local custom |
| 5 | DeepSeek-V3 (API) | 80.7 | 32.0 | **+48.7** | API |
| 6 | dof-guardian | 82.7 | 36.0 | **+46.7** | Local custom |
| 7 | dof-voice | 79.3 | 35.3 | **+44.0** | Local custom |
| 8 | SambaNova-DSV3 | 81.3 | 38.7 | **+42.7** | API |
| 9 | local-agi-m4max | 78.7 | 36.0 | **+42.7** | Local custom |
| 10 | MiniMax-M2.1 | 67.3 | 37.3 | **+30.0** | API |
| 11 | DeepSeek-R1 | 18.0 | 8.0 | +10.0 | API (reasoning) |
| — | Gemini-2.0Flash | 16.0 | 16.0 | 0 | API (error/empty) |
| — | Groq-Llama | 12.0 | 12.0 | 0 | API (key error) |
| — | Cerebras | 12.0 | 12.0 | 0 | API (key error) |
| — | NVIDIA-NIM | 12.0 | 12.0 | 0 | API (credits) |

### Key findings

1. **gemma2:9b is the local Winston champion** — 86/100 CQ with framework vs 32 without it (+54pts)
2. **few-shot + anchor eliminates ambiguity** — gemma2 went from ~60 to 86 after adding concrete examples
3. **DeepSeek-V3 beats all APIs** — 80.7 BLUE, latency ~2s (streaming)
4. **R1/Reasoner are immune to Winston format** — they generate `<think>` tokens, ignore external instructions. Delta +10 is due to content, not format.
5. **MiniMax-M2.1 partial adoption** — 67.3 BLUE. Understands Winston but does not consistently anchor the conclusion on the first line.
6. **Groq/Cerebras/NVIDIA empty** — incorrect endpoints or keys at the time of the experiment (12.0 = minimum score because no_filler=True)

### Component analysis (BLUE team, top models)

| Model | Indicator | Impact | Evidence | Action | No-filler |
|--------|-----------|---------|-----------|--------|-------------|
| gemma2:9b | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 |
| dof-voice-fast | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 |
| DeepSeek-V3 | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 |
| SambaNova-DSV3 | ✓ 3/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 | ✓ 3/3 |
| MiniMax-M2.1 | ✗ 1/3 | ✓ 3/3 | ✓ 2/3 | ✓ 3/3 | ✓ 3/3 |

---

## Techniques that improve Winston adoption

### Basic level (system prompt only)
- Improves ~20-30pts in instructed models
- Sufficient for strong models (GPT-4, Gemini Pro, Claude)

### Advanced level (few-shot + anchor)
- **Few-shot**: Include 1-2 examples of correct response in the correct format
- **Anchor at end**: Repeat the required format as the last system message at the end of `messages[]`
- Additional improvement of ~20pts over system prompt alone

```python
# Example of anchor at end of messages:
messages = [
    {"role": "system", "content": SYSTEM_BLUE},
    {"role": "user",   "content": FEW_SHOT_EXAMPLE_USER},
    {"role": "assistant", "content": FEW_SHOT_EXAMPLE_RESPONSE},
    {"role": "user",   "content": actual_task},
    {"role": "system", "content": ANCHOR_BLUE},  # ← anchor at end
]
```

### Why R1 is immune
DeepSeek-R1 and reasoner models generate a `<think>...</think>` block before the response. During thinking they ignore format instructions. The final response tends to be narrative. Solution: use R1 as thinker, pass its output through gemma2 as formatter.

---

## Phase 2 — Web Models (In progress)

### Target models

| Model | Interface | Status |
|--------|----------|--------|
| ChatGPT-4o | chat.openai.com | Pending |
| ChatGPT-o3 | chat.openai.com | Pending |
| Gemini-2.5Pro | gemini.google.com | Pending |
| Gemini-2.5Flash | gemini.google.com | Pending |
| Kimi-K2 | kimi.ai | Pending |
| GLM-4.5 | chatglm.cn | Pending |
| MiniMax-M2 | hailuoai.com | Pending |
| Perplexity-Sonar | perplexity.ai | Pending |
| Claude-3.7-Sonnet | claude.ai | Pending |
| DeepSeek-V3-web | chat.deepseek.com | Pending |
| Mistral-Large | chat.mistral.ai | Pending |
| Grok-3 | x.ai/grok | Pending |

### Manual procedure

For each model:

**BLUE (With Winston):**
1. New conversation (clean session, no history)
2. Paste complete BLUE system prompt from JSON
3. Send BASIC task → copy response to JSON
4. Send INTERMEDIATE task → copy response
5. Send ADVANCED task → copy response

**RED (Baseline):**
1. New clean conversation
2. Paste RED system prompt
3. Repeat the 3 tasks → copy responses

### Automatic scorer

```bash
# View partial results (as you fill in responses)
python3 experiments/winston_vs_baseline/web_experiment_scorer.py

# Save JSON results
python3 experiments/winston_vs_baseline/web_experiment_scorer.py --json

# Combined web + local ranking
python3 experiments/winston_vs_baseline/web_experiment_scorer.py --merge
```

---

## Implications for DOF Mesh

### Current integration

Winston is already integrated in:
- `config/agents.yaml` — field `communication_framework: "winston-v1"` in 17 agents
- `agents/*/SOUL.md` — 5S table adapted to the role in 9 SOULs
- `core/supervisor.py` — `evaluate_communication_quality()` + field `communication_quality` in `SupervisorVerdict`
- Supervisor composite score: `Q(0.35) + A(0.20) + C(0.20) + F(0.10) + CQ(0.15)`

### Demonstrated value

By only changing the system prompt:
- gemma2:9b: **+54pts** of communication quality
- All custom DOF models: **+42-50pts**
- Without changing the model, without fine-tuning, without additional cost

This means the Winston framework acts as a **capability multiplier** — the same model, with correct instructions, produces clearer, more actionable and verifiable outputs.

---

## Next steps

1. **Complete Phase 2** — fill in web responses, run scorer, update results table
2. **R1 → gemma2 pipeline** — R1 reasons, gemma2 formats (combines depth + clarity)
3. **Winston in voice** — voice_v4 system already uses the format in its system prompt
4. **Experiment v4** — test anchor variants (position, length, format)
5. **Publish results** — as part of DOF SDK documentation or technical blog post

---

*Documentation generated: Mar 28, 2026 | DOF Mesh Legion v0.5.0*
