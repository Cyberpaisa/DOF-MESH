# AGI Local Strategy — DOF v0.5 (March 2026)

> **Status**: Draft v1.0
> **Author**: Principal Agentic Engineer
> **Date**: March 22, 2026
> **Objective**: Maximize local inference for sovereignty, privacy, cost reduction, and consistent speed.

---

## 1. Hardware Profile

### MacBook Pro M4 Max — Relevant Specifications

| Component | Specification | Impact on Inference |
|---|---|---|
| CPU | 16 cores (12P + 4E) | Tokenization, pre/post processing |
| GPU | 40 cores Metal | Main inference via MLX/llama.cpp |
| Neural Engine | 16 cores, 19 TFLOPS FP16 @ 2.8W | Experimental — fine-tuning of models <1B |
| Unified RAM | **36 GB** | **CRITICAL CONSTRAINT** — defines model ceiling |
| SSD | 994 GB (432 GB free) | Sufficient for ~50 GGUF models |
| Memory Bandwidth | ~546 GB/s | Key factor for tok/s on large models |

### Hard Memory Limits

```
Total memory:            36 GB
- macOS + services:      ~4 GB
- DOF runtime (Python):  ~2 GB
- ChromaDB + embeddings: ~1 GB
- Available for LLM:     ~29 GB
- Maximum viable model:  ~20 GB (32B Q4_K_M)
```

**Fundamental rule**: A 70B model in Q4 needs ~43 GB. **DOES NOT FIT**. Do not attempt — causes catastrophic swap and the system freezes.

### Models That Fit vs Don't Fit

```
[OK]  8B  Q4  →  ~5 GB   ✓ RAM to spare for 2-3 simultaneous models
[OK]  14B Q4  →  ~9 GB   ✓ Fits with ample margin
[OK]  22B Q4  →  ~14 GB  ✓ Fits well, one model at a time
[OK]  32B Q4  →  ~20 GB  ✓ Fits just right, close heavy apps
[NO]  70B Q4  →  ~43 GB  ✗ DOES NOT FIT — not even with Q2
[NO]  70B Q2  →  ~35 GB  ✗ Fills all RAM, immediate swap
```

---

## 2. Inference Frameworks — Comparison

| Framework | Speed (7B) | Speed (32B) | Ease | OpenAI Compatible API | Best For |
|---|---|---|---|---|---|
| **MLX v0.31.1** | ~230 tok/s | ~45 tok/s | Medium | Via litellm | Maximum native Apple Silicon speed |
| **Ollama** | ~180 tok/s | ~35 tok/s | **High** | **Yes (native)** | Quick setup, 200+ models, easy integration |
| **llama.cpp** | ~200 tok/s | ~40 tok/s | Low | Via server mode | Maximum control, GGUF format, Metal backend |
| **vLLM-MLX** | **~525 tok/s** | ~80 tok/s | Medium | Yes | Production with continuous batching |
| **LM Studio** | ~180 tok/s | ~35 tok/s | **Very High** | Yes | GUI, visual model management, MLX engine |
| **ExoLabs** | Variable | Variable | Medium | Yes | P2P distributed inference between Macs |

### Recommendation for DOF

**Main stack**:
1. **Ollama** as base server — OpenAI-compatible API, easy to integrate with LiteLLM
2. **MLX** for benchmarks and tasks requiring maximum speed
3. **vLLM-MLX** when batching is needed (multiple concurrent agents)

**Reason**: Ollama has the best ease/performance ratio and its API is directly compatible with the `openai/` pattern already used by `litellm` in DOF.

---

## 3. Recommended Models for 36 GB

### Tier 1 — Fit easily (5-9 GB)

| Model | RAM | tok/s (MLX) | Strength | DOF Use Case |
|---|---|---|---|---|
| **Llama 3.3 8B Q4** | ~5 GB | ~230 | General, fast | Simple task agents |
| **Phi-4 14B Q4** | ~9 GB | ~120 | Reasoning, code | Security, verification |
| **Qwen3 8B Q4** | ~5 GB | ~220 | Multilingual, reasoning | Fast research |
| **Gemma 3 12B Q4** | ~8 GB | ~140 | Instructions, safety | Support agents |

**Advantage**: 2-3 Tier 1 models can run simultaneously without issues.

### Tier 2 — Fit well (14-20 GB)

| Model | RAM | tok/s (MLX) | Strength | DOF Use Case |
|---|---|---|---|---|
| **Qwen3 32B Q4** | ~20 GB | ~45 | **BEST general for 36GB** | Oracle, Architect, Strategist |
| **DeepSeek-R1 Distill 32B Q4** | ~20 GB | ~40 | Deep chain-of-thought | Complex reasoning tasks |
| **Codestral 22B Q4** | ~14 GB | ~65 | Specialized code | Code generation and review |

**Constraint**: Only ONE Tier 2 model at a time. When loading Qwen3 32B, ~9 GB remains for the system.

### Tier 3 — Tight, use with care

| Model | RAM | tok/s (MLX) | Note |
|---|---|---|---|
| **Qwen3-Coder MoE** | ~10 GB active | ~90 | MoE activates only 2 experts at a time |
| **Mixtral 8x7B Q4** | ~26 GB | ~25 | Very tight, leaves no margin |

### Do Not Fit — DO NOT attempt

| Model | RAM Required | Reason |
|---|---|---|
| Llama 3.3 70B Q4 | ~43 GB | Exceeds 36 GB by 7 GB |
| Qwen3 72B Q4 | ~44 GB | Exceeds 36 GB by 8 GB |
| DeepSeek-V3 671B | ~350 GB | Impossible on any Mac |
| Any model >45B | >30 GB | Catastrophic swap |

---

## 4. Hybrid Local + Cloud Strategy

### 80/20 Rule

```
80% of inferences → LOCAL (Ollama/MLX)
20% of inferences → CLOUD (Groq, Cerebras, NVIDIA NIM)
```

### Routing Decision Tree

```
                    ┌─────────────────┐
                    │  Incoming task   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Sensitive data? │
                    └────┬────────┬───┘
                    Yes  │        │ No
                         │        │
                ┌────────▼───┐    │
                │ LOCAL ONLY │    │
                │ (never cloud)   │
                └────────────┘    │
                         ┌────────▼────────┐
                         │ Context > 24K?  │
                         └────┬────────┬───┘
                         Yes  │        │ No
                              │        │
                     ┌────────▼───┐  ┌─▼──────────────┐
                     │ Cloud 70B+ │  │ Complexity?     │
                     │ (Groq/NVIDIA)  │                │
                     └────────────┘  └──┬─────────┬───┘
                                   High │         │ Low
                                        │         │
                              ┌─────────▼──┐  ┌──▼─────────┐
                              │ Local 32B   │  │ Local 8B    │
                              │ Qwen3-32B   │  │ Llama 3.3   │
                              └─────────────┘  └─────────────┘
```

### Fallback Chain

```python
# Fallback order in providers.py
FALLBACK_CHAIN = [
    "ollama/qwen3:32b-q4_K_M",      # 1. Local — best model
    "ollama/phi4:14b-q4_K_M",        # 2. Local — fast fallback
    "ollama/llama3.3:8b-q4_K_M",     # 3. Local — ultra-fast
    "groq/llama-3.3-70b-versatile",  # 4. Cloud — Groq free tier
    "cerebras/llama-3.3-70b",        # 5. Cloud — Cerebras free tier
    "nvidia_nim/qwen3-32b",          # 6. Cloud — NVIDIA NIM
    "clawrouter/auto",               # 7. ClawRouter — last resort
]
```

### Privacy Policy

| Data Type | Allowed in Cloud | Local Model Required |
|---|---|---|
| Project source code | No | Qwen3 32B / Codestral 22B |
| API keys, credentials | **NEVER** | Any local |
| User data | No | Any local |
| Public research queries | Yes | Optional |
| Generic technical documentation | Yes | Optional |
| DOF governance metrics | No | Phi-4 14B |

---

## 5. Agent-to-Model Mapping

### Optimal Assignment

| # | Agent | Role | Local Model | RAM | Reason | Cloud Fallback |
|---|---|---|---|---|---|---|
| 1 | **Synthesis (Oracle)** | Main orchestrator | Qwen3 32B Q4 | 20 GB | Complex reasoning, synthesis | Groq Llama 70B |
| 2 | **Architect** | Systems design | Qwen3 32B Q4 / Codestral 22B | 20/14 GB | Code + architecture | NVIDIA Qwen3 |
| 3 | **Researcher** | Research | Qwen3 32B Q4 | 20 GB | Wide context needed | Groq Llama 70B |
| 4 | **Sentinel** | Security | Phi-4 14B Q4 | 9 GB | Fast checks, no need for 32B | Cerebras Llama |
| 5 | **Scout** | Web gathering | Llama 3.3 8B Q4 | 5 GB | Simple tasks, speed | Groq Llama 8B |
| 6 | **Narrative** | Creative writing | Qwen3 32B Q4 | 20 GB | Requires literary quality | Groq Llama 70B |
| 7 | **Strategist** | Planning | Qwen3 32B Q4 | 20 GB | Strategic reasoning | NVIDIA Qwen3 |
| 8 | **Designer** | Visual design | Phi-4 14B Q4 + SD local | 9 GB + 4 GB | UI code + image generation | Cerebras |
| 9 | **Organizer** | Task management | Llama 3.3 8B Q4 | 5 GB | Simple tasks, fast | Groq Llama 8B |
| 10 | **QA Reviewer** | Code review | Phi-4 14B Q4 | 9 GB | Efficient code analysis | Cerebras |
| 11 | **Verifier** | Formal verification | Phi-4 14B Q4 | 9 GB | Deterministic verification | Cerebras |
| 12 | **Data Engineer** | Data processing | Qwen3 32B Q4 | 20 GB | Complex transformations | NVIDIA Qwen3 |

### Concurrency Constraint

```
RULE: Only ONE 32B model can be loaded at a time.

Scenario A — Complex active agent:
  [Qwen3 32B: 20 GB] + [System: 7 GB] + [Free: 9 GB]
  → Can run ONE Tier 1 agent (8B) in parallel

Scenario B — Multiple simple agents:
  [Phi-4 14B: 9 GB] + [Llama 8B: 5 GB] + [Llama 8B: 5 GB] + [System: 7 GB]
  → Three lightweight agents in parallel = 10 GB free

Scenario C — Swarm mode:
  [4x Llama 8B: 20 GB] + [System: 7 GB]
  → Four ultra-fast agents in parallel = 9 GB free
```

### Preload Strategy

```python
# In crew_runner.py — preload model before running crew
MODEL_PRELOAD_MAP = {
    "high_reasoning": "qwen3:32b-q4_K_M",     # Oracle, Researcher, Strategist
    "coding":         "codestral:22b-q4_K_M",  # Architect
    "fast_check":     "phi4:14b-q4_K_M",       # Sentinel, QA, Verifier
    "simple_task":    "llama3.3:8b-q4_K_M",    # Scout, Organizer
}
```

---

## 6. Apple Neural Engine (ANE) — Research

### Current Status (March 2026)

The M4 Max Neural Engine offers 19 TFLOPS in FP16 at only 2.8W of consumption, but its use for LLMs is still experimental.

### Key Advances

| Researcher / Paper | Achievement | DOF Relevance |
|---|---|---|
| **@maderix** (reverse engineering) | Training at 91 ms/step on ANE | Apple said it was "impossible" — proved otherwise |
| **Orion** (arXiv:2603.06728) | 170 tok/s GPT-2 124M on ANE, training of 110M transformers | First viable framework for fine-tuning on ANE |
| **CoreML + coremltools** | Conversion of PyTorch models to ANE | Official Apple pipeline, stable |

### Capabilities vs Limitations

```
WHAT THE ANE CAN DO TODAY:
  ✓ Inference of models <1B parameters
  ✓ Experimental fine-tuning of ~100M parameter models
  ✓ Local embeddings (all-MiniLM-L6-v2 already runs partially on ANE)
  ✓ Fast text classification
  ✓ 19 TFLOPS @ 2.8W = extreme energy efficiency

WHAT THE ANE CANNOT DO (YET):
  ✗ Models >1B parameters (internal memory limitation)
  ✗ Arbitrary attention (limited KV-cache)
  ✗ Be the main runtime of an LLM agent
  ✗ Replace GPU for inference of 8B+ models
```

### DOF Roadmap for ANE

1. **Short term (Q1 2026)**: Embeddings on ANE via CoreML for `memory_manager.py`
2. **Medium term (Q2 2026)**: LoRA adapters for agent personalization — fine-tune Phi-4 LoRA on ANE
3. **Long term (Q3-Q4 2026)**: Classification/routing models on ANE for `skill_engine.py`

---

## 7. SuperLocalMemory V3 — Integration (arXiv:2603.14588)

### Connection with DOF

SuperLocalMemory V3 proposes a memory management framework for LLM agents using differential geometry, aligned with DOF's deterministic observability principles.

### Fisher-Rao — Already Implemented

```python
# core/fisher_rao.py — ALREADY EXISTS in DOF
# Fisher-Rao metric to measure distance between agent memory distributions

class FisherRaoMetric:
    """
    Calculates the geodesic distance between memory states
    using the Fisher-Rao metric in the space of distributions.

    Use in DOF: detect drift between what an agent "remembers"
    vs what it should remember according to its SOUL.md
    """
    def compute_distance(self, p: Distribution, q: Distribution) -> float:
        # Geodesic distance in the statistical manifold
        ...
```

### Langevin Memory Lifecycle (Roadmap)

```
Active Memory (Hot)     → Frequent access, in RAM
    ↓ τ_warm = 1 hour
Warm Memory             → Recent access, in local ChromaDB
    ↓ τ_cold = 24 hours
Cold Memory             → Infrequent access, compressed on disk
    ↓ τ_archive = 7 days
Archived Memory         → Reference only, compressed JSONL

Transition governed by Langevin dynamics:
  dM/dt = -∇V(M) + σ·dW
  where V(M) = relevance potential, σ = thermal noise
```

### Sheaf Cohomology (Roadmap)

```
Purpose: Detect contradictions between memory types

Example:
  - Episodic memory: "The Sentinel agent approved output X"
  - Semantic memory: "HARD_RULE_7 prohibits outputs like X"
  → Cohomology H¹ ≠ 0 → CONTRADICTION DETECTED → escalate to governance

DOF Integration:
  - core/governance.py detects violations in real time
  - SuperLocalMemory V3 would detect contradictions in historical memory
  - Complementary, not substitutes
```

### Key Advantage: Zero-LLM Memory Retrieval

```
CURRENT MODEL (with LLM):
  Query → Embedding (LLM) → ChromaDB → Re-ranking (LLM) → Result
  Latency: ~500ms | Cost: tokens consumed | Privacy: depends on provider

SLM-V3 MODEL (without LLM):
  Query → Fisher-Rao distance → Geodesic search → Result
  Latency: ~5ms | Cost: $0 | Privacy: 100% local

  → Completely deterministic and local retrieval
  → Aligned with DOF principle: "Zero LLM for governance"
```

---

## 8. Setup Commands

### Local Stack Installation

```bash
# ============================================
# 1. Install MLX (native Apple Silicon framework)
# ============================================
pip install mlx mlx-lm

# Verify installation
python3 -c "import mlx; print(f'MLX version: {mlx.__version__}')"

# ============================================
# 2. Install Ollama (model server)
# ============================================
brew install ollama

# Start server (leave running in background)
ollama serve &

# Verify
curl http://localhost:11434/api/tags

# ============================================
# 3. Download recommended models
# ============================================

# Tier 1 — Fast models (download all)
ollama pull llama3.3:8b-q4_K_M        # ~5 GB
ollama pull phi4:14b-q4_K_M           # ~9 GB

# Tier 2 — Main model (download most used)
ollama pull qwen3:32b-q4_K_M          # ~20 GB — MAIN MODEL
ollama pull codestral:22b-q4_K_M      # ~14 GB — For coding

# ============================================
# 4. Verify downloaded models
# ============================================
ollama list

# ============================================
# 5. Quick inference test
# ============================================

# Test Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:32b-q4_K_M",
  "prompt": "Explain the Fisher-Rao metric in 3 sentences.",
  "stream": false
}'

# Test MLX (models in MLX format)
mlx_lm.generate \
  --model mlx-community/Qwen3-32B-4bit \
  --prompt "What is deterministic observability?" \
  --max-tokens 200

# ============================================
# 6. LiteLLM Proxy (to integrate with DOF)
# ============================================
pip install litellm

# Start proxy that exposes OpenAI-compatible API
litellm --model ollama/qwen3:32b-q4_K_M --port 4000 &

# Verify proxy
curl http://localhost:4000/v1/models

# ============================================
# 7. Configure DOF to use local models
# ============================================

# In .env add:
# OLLAMA_BASE_URL=http://localhost:11434
# LITELLM_PROXY_URL=http://localhost:4000
# LOCAL_INFERENCE_PRIORITY=true
```

### Full Verification Script

```bash
#!/bin/bash
# verify_local_stack.sh — Verify that the entire local stack works

echo "=== DOF Local Inference Stack Verification ==="

# 1. Ollama
echo -n "Ollama server: "
curl -s http://localhost:11434/api/tags > /dev/null && echo "OK" || echo "FAIL"

# 2. Available models
echo "Installed models:"
ollama list 2>/dev/null || echo "  Ollama not available"

# 3. MLX
echo -n "MLX: "
python3 -c "import mlx; print(f'v{mlx.__version__}')" 2>/dev/null || echo "FAIL"

# 4. Available RAM
echo -n "Free RAM: "
python3 -c "
import subprocess
result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
total = int(result.stdout.split(':')[1].strip()) / (1024**3)
print(f'{total:.0f} GB total')
"

# 5. Inference test
echo -n "Local inference: "
RESPONSE=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "llama3.3:8b-q4_K_M",
  "prompt": "Say OK",
  "stream": false
}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','FAIL')[:20])")
echo "$RESPONSE"

echo "=== Verification complete ==="
```

---

## 9. Cost Analysis

### Monthly Comparison

| Scenario | Monthly Cost | Speed | Privacy | Availability | Rate Limits |
|---|---|---|---|---|---|
| **100% Cloud (current)** | ~$0 (free tiers) | Variable (50-200 tok/s) | Low | Depends on APIs | **Yes** — 12K TPM Groq, 1M/day Cerebras |
| **80% Local / 20% Cloud** | ~$5 (electricity) | Consistent 45-230 tok/s | **High** | 99.9% (local) | Minimal |
| **100% Local** | ~$5 (electricity) | Consistent | **Maximum** | 100% | **Zero** |

### Electricity Consumption Breakdown

```
MacBook Pro M4 Max under LLM inference:
  - Idle:                    ~15W
  - 8B inference (GPU):      ~35W
  - 32B inference (GPU):     ~55W
  - 32B inference (GPU+ANE): ~50W (future)

Estimated inference hours: ~8h/day × 30 days = 240h/month
Average consumption: 45W × 240h = 10.8 kWh/month
Colombia electricity cost: ~$800 COP/kWh ≈ $0.20 USD/kWh
Monthly cost: 10.8 × $0.20 = $2.16 USD/month
```

### ROI vs Cloud Rate Limits

```
CURRENT PROBLEM:
  Groq:     12,000 tokens/minute → agent waits 5+ min between calls
  Cerebras: 1M tokens/day → exhausted in ~3 complete runs
  NVIDIA:   1000 total credits → not sustainable

LOCAL SOLUTION:
  Ollama Qwen3 32B: NO LIMITS
  → An agent can generate 45 tok/s × 60s = 2,700 tok/min
  → 2,700 × 60 min = 162,000 tok/hour
  → 162,000 × 24h = 3.8M tok/day
  → 13.5x more than Cerebras free tier
```

---

## 10. Risks and Mitigations

### Risk Matrix

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **RAM pressure with 32B model** | High | Medium | Close heavy apps (Chrome, Docker). Monitor with `Activity Monitor`. Pre-check script before loading model. |
| R2 | **Lower quality than 70B cloud** | Medium | Medium | Compensate with better prompting, explicit chain-of-thought, more detailed CONSTITUTION. Benchmark local vs cloud periodically. |
| R3 | **ANE still experimental** | High | Low | Don't depend on ANE for production. Use only for embeddings and light classification. Keep GPU as main runtime. |
| R4 | **Single point of failure** | Medium | High | Maintain cloud fallback chain. Model backups on external disk. Automatic recovery script. |
| R5 | **Corrupt or incompatible model** | Low | Medium | Verify checksums after download. Keep previous model version. `ollama rm` + re-download if it fails. |
| R6 | **macOS update breaks MLX** | Low | High | Don't update macOS without verifying MLX compatibility. Pin MLX version in requirements.txt. |
| R7 | **Excessive swap degrades performance** | Medium | High | Monitor system `memory_pressure`. Automatic kill if swap > 4 GB. |

### RAM Monitoring Script

```bash
#!/bin/bash
# monitor_ram.sh — Alert if memory pressure is critical

while true; do
  PRESSURE=$(memory_pressure 2>/dev/null | grep "System-wide" | awk '{print $NF}')

  if [[ "$PRESSURE" == *"critical"* ]]; then
    echo "[ALERT] CRITICAL memory pressure — consider unloading 32B model"
    osascript -e 'display notification "Critical RAM — unload model" with title "DOF Monitor"'
  fi

  sleep 30
done
```

### Contingency Plan

```
IF the local model fails:
  1. Log the error in logs/metrics/local_inference_errors.jsonl
  2. Automatic fallback to cloud (Groq → Cerebras → NVIDIA)
  3. Increase backoff TTL for the local model (5 → 10 → 20 min)
  4. Notify via Telegram to operator
  5. If 3 consecutive failures → deactivate local model for 1 hour

IF the machine freezes:
  1. Force quit the Python process (Activity Monitor)
  2. ollama stop (kills the loaded model)
  3. Check logs in logs/checkpoints/ — DOF has recovery by step
  4. Restart from last valid checkpoint
```

---

## Executive Summary

```
CURRENT STATE:    100% cloud, rate-limited, no privacy
TARGET STATE:     80% local, no rate limits, full sovereignty

MAIN MODEL:  Qwen3 32B Q4 via Ollama (~20 GB, ~45 tok/s)
FAST MODELS: Phi-4 14B, Llama 3.3 8B (concurrency)
FRAMEWORK:   Ollama + LiteLLM proxy + MLX for benchmarks

COST:         ~$2 USD/month in electricity
PRIVACY:      Sensitive data NEVER leaves the machine
SPEED:        Consistent, no waiting for rate limits
AVAILABILITY: 99.9% — does not depend on external APIs

NEXT STEPS:
  1. Install Ollama + download Qwen3 32B Q4
  2. Configure LiteLLM proxy on port 4000
  3. Update providers.py with local-first fallback chain
  4. Benchmark: local vs cloud on 5 DOF metrics
  5. Migrate agents one by one, starting with Sentinel (low risk)
```

---

> *"Computational sovereignty is not a luxury — it is a requirement for observability systems that claim to be truly deterministic."*
