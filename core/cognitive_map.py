from __future__ import annotations
"""
Cognitive Map — Model Family Cognitive Architecture Profiles for the DOF Mesh.

Maps how each model family thinks differently, enabling intelligent task routing
and synergy-aware collaboration across the multi-model agent mesh.

Research-driven profiles based on:
- Architecture papers and documentation for each model family
- Actual mesh behavior observed in logs/mesh/ (56 nodes, 7 model families)
- DeepSeek's actual outputs (ds-001..ds-004): mathematical reasoning, routing proposals,
  metric analysis, Chinese AI ecosystem perspective
- Message patterns from 100+ mesh messages across commander, architect, researcher,
  guardian, narrator, reviewer nodes

Key insight from mesh data:
- Claude dominates orchestration (commander=86 msgs sent, architect/guardian/reviewer active)
- DeepSeek provides deepest analytical contributions (4 messages, all high-density math/optimization)
- Gemini used for parallel processing power (antigraviti + gemini-2 nodes)
- GPT used for creative/conversational roles (gpt-legion, gpt-chat)
- Kimi, NVIDIA, GLM registered but not yet active in message exchange

Usage:
    from core.cognitive_map import CognitiveMap

    cmap = CognitiveMap()

    # Get a model's cognitive profile
    profile = cmap.get_profile("claude")

    # Route a task to the best model
    best = cmap.get_optimal_model("optimize the routing algorithm complexity")

    # Check synergy between two models
    synergy = cmap.get_synergy("claude", "deepseek")

    # Mesh diversity analysis
    score = cmap.get_mesh_diversity_score()
    next_model = cmap.recommend_next_model()

    # ASCII visualization
    print(cmap.print_map())
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.cognitive_map")


# =====================================================================
# DATA CLASSES
# =====================================================================

@dataclass
class CognitiveProfile:
    """Cognitive architecture profile for a model family."""
    model_family: str          # claude, gemini, gpt, deepseek, kimi, nvidia, glm
    architecture: str          # transformer, MoE, etc.
    context_window: int        # tokens
    thinking_style: str        # analytical, creative, mathematical, fast, deep
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    reasoning_type: str = "chain-of-thought"
    language_preference: str = "en"
    code_capability: str = "good"
    math_capability: str = "good"
    creativity: str = "good"
    speed: str = "medium"
    cost: str = "moderate"
    special_abilities: list[str] = field(default_factory=list)
    optimal_tasks: list[str] = field(default_factory=list)
    avoid_tasks: list[str] = field(default_factory=list)


@dataclass
class SynergyScore:
    """How well two model families collaborate."""
    model_a: str
    model_b: str
    score: float              # 0.0 to 1.0
    synergy_type: str         # complementary, overlapping, specialized
    best_collaboration: str   # description of optimal collaboration pattern


# =====================================================================
# HARDCODED COGNITIVE PROFILES
# =====================================================================

def _build_profiles() -> dict[str, CognitiveProfile]:
    """Build the hardcoded cognitive profiles based on architecture research
    and actual mesh behavior analysis."""

    profiles = {}

    # -----------------------------------------------------------------
    # CLAUDE (Anthropic)
    # Observed in mesh: commander (86 msgs sent), architect, researcher,
    # guardian, narrator, reviewer — dominates orchestration and code tasks.
    # Models in mesh: claude-opus-4-6, claude-sonnet-4-6
    # -----------------------------------------------------------------
    profiles["claude"] = CognitiveProfile(
        model_family="claude",
        architecture="Dense transformer, Constitutional AI, RLHF+RLAIF",
        context_window=200_000,
        thinking_style="analytical, cautious, structured, strong ethical reasoning",
        strengths=[
            "Code generation and refactoring",
            "Instruction following with precision",
            "Long document analysis (200K context)",
            "Safety and alignment",
            "Structured output (JSON, JSONL, dataclasses)",
            "Multi-step orchestration",
            "Security review and audit",
            "Tool use and agentic workflows",
        ],
        weaknesses=[
            "Can be overly cautious on edge cases",
            "No real-time web access (without tools)",
            "No image generation",
            "Higher latency on Opus vs competitors",
        ],
        reasoning_type="extended-thinking (chain-of-thought with work shown)",
        language_preference="en",
        code_capability="excellent",
        math_capability="good",
        creativity="good",
        speed="medium",
        cost="expensive",
        special_abilities=[
            "Constitutional AI constraints",
            "Tool use with structured outputs",
            "Artifacts and extended thinking",
            "Opus/Sonnet tiering (depth vs speed)",
            "Persistent sessions with infinite memory",
        ],
        optimal_tasks=[
            "Orchestration and command dispatch",
            "Code architecture and implementation",
            "Security review and governance",
            "Agentic workflows with tool use",
            "Documentation and structured reports",
            "Multi-agent coordination",
        ],
        avoid_tasks=[
            "Image generation",
            "Real-time web search (without tools)",
            "Tasks requiring extreme speed at low cost",
            "Creative visual design",
        ],
    )

    # -----------------------------------------------------------------
    # GEMINI (Google)
    # Observed in mesh: antigraviti (gemini-2.5-flash), gemini-2 node
    # Used for parallel processing power and multimodal tasks.
    # -----------------------------------------------------------------
    profiles["gemini"] = CognitiveProfile(
        model_family="gemini",
        architecture="Dense transformer + MoE variants, multimodal native",
        context_window=1_000_000,
        thinking_style="fast, multimodal, good at synthesis across modalities",
        strengths=[
            "Massive context window (1M tokens)",
            "Native multimodal (images, video, audio, code)",
            "Google Search grounding",
            "Fast inference speed",
            "Strong at document synthesis",
            "Competitive coding ability",
        ],
        weaknesses=[
            "Can be less precise on complex edge-case code",
            "Inconsistent on niche technical domains",
            "Occasional hallucination on specific facts",
            "Rate limits on free tier (20 req/day)",
        ],
        reasoning_type="direct + chain-of-thought",
        language_preference="multi",
        code_capability="good",
        math_capability="good",
        creativity="good",
        speed="fast",
        cost="cheap",
        special_abilities=[
            "Grounding with Google Search",
            "Native multimodal understanding",
            "1M token context window",
            "Code execution sandbox",
            "Structured output with JSON mode",
        ],
        optimal_tasks=[
            "Large document analysis and synthesis",
            "Multimodal tasks (image + text)",
            "Speed-critical processing",
            "Parallel batch analysis",
            "Research with web grounding",
            "Cross-referencing large codebases",
        ],
        avoid_tasks=[
            "Tasks requiring extreme code precision",
            "Governance-critical decisions",
            "Tasks needing deterministic reproducibility",
        ],
    )

    # -----------------------------------------------------------------
    # GPT (OpenAI)
    # Observed in mesh: gpt-legion (creative problem solving),
    # gpt-chat (conversational partner, creative ideation)
    # Model: gpt-4o
    # -----------------------------------------------------------------
    profiles["gpt"] = CognitiveProfile(
        model_family="gpt",
        architecture="Dense transformer, RLHF, GPT-4o multimodal",
        context_window=128_000,
        thinking_style="creative, conversational, broad knowledge base",
        strengths=[
            "Creative writing and brainstorming",
            "Broad general knowledge",
            "DALL-E image generation integration",
            "Code Interpreter with execution",
            "Web browsing capability",
            "Strong conversational flow",
            "Plugin ecosystem",
        ],
        weaknesses=[
            "Can hallucinate confidently",
            "Less precise on niche or specialized code",
            "Expensive at scale",
            "Less structured output compared to Claude",
        ],
        reasoning_type="chain-of-thought, code interpreter",
        language_preference="en",
        code_capability="good",
        math_capability="good",
        creativity="excellent",
        speed="medium",
        cost="expensive",
        special_abilities=[
            "DALL-E image generation",
            "Web browsing and real-time data",
            "Code Interpreter with sandbox execution",
            "Plugin and GPT ecosystem",
            "Voice mode and real-time API",
        ],
        optimal_tasks=[
            "Creative content generation",
            "Image generation and visual tasks",
            "Conversational interfaces and demos",
            "Brainstorming and ideation sessions",
            "Tasks requiring web browsing",
            "Rapid prototyping with code interpreter",
        ],
        avoid_tasks=[
            "Governance-critical deterministic decisions",
            "High-precision security audits",
            "Tasks requiring extreme factual accuracy",
            "Structured data pipeline outputs",
        ],
    )

    # -----------------------------------------------------------------
    # DEEPSEEK (DeepSeek AI)
    # Observed in mesh: deepseek node (4 msgs sent, all high-density)
    # Actual outputs analyzed (ds-001..ds-004):
    #   ds-001: Self-intro — Lyapunov stability, NP-hard optimization, MoE expertise
    #   ds-002: Routing proposal — O(2*sqrt(n)) hybrid DHT, formal graph theory
    #   ds-003: Metric redundancy — SS(f) derivable from PFI, proposed 4-metric reduction
    #   ds-004: Chinese AI ecosystem — MoE router, vLLM, OpenCompass, CodeGeeX4
    # Pattern: Mathematical depth, algorithmic rigor, efficiency-focused
    # -----------------------------------------------------------------
    profiles["deepseek"] = CognitiveProfile(
        model_family="deepseek",
        architecture="MoE (Mixture of Experts), 671B total params, ~37B active per token",
        context_window=128_000,
        thinking_style="mathematical, deep, systematic, efficiency-obsessed",
        strengths=[
            "Mathematical reasoning and formal proofs",
            "Algorithm design and complexity analysis",
            "Competitive programming",
            "Cost-efficient inference (MoE activation)",
            "Chinese AI ecosystem expertise",
            "Optimization problems (routing, scheduling, allocation)",
            "Metric analysis and redundancy detection",
        ],
        weaknesses=[
            "Less polished on creative/marketing content",
            "Smaller international community and tooling",
            "Can over-formalize simple tasks",
            "Less refined instruction following on ambiguous prompts",
        ],
        reasoning_type="deep chain-of-thought, mathematical proofs, formal analysis",
        language_preference="zh",
        code_capability="excellent",
        math_capability="excellent",
        creativity="basic",
        speed="fast",
        cost="cheap",
        special_abilities=[
            "MoE efficiency (37B active of 671B total)",
            "Strong on competitive programming (Codeforces, LeetCode)",
            "Formal mathematical analysis (Lyapunov, graph theory)",
            "Chinese AI ecosystem knowledge (Qwen, GLM, Yi, Baichuan)",
            "Algorithmic complexity reduction proposals",
        ],
        optimal_tasks=[
            "Algorithm design and optimization",
            "Mathematical analysis and formal proofs",
            "Metric design and validation",
            "Routing and scheduling optimization",
            "Code optimization for performance",
            "Competitive programming challenges",
            "Cost-efficient batch processing",
        ],
        avoid_tasks=[
            "Creative writing and marketing copy",
            "User-facing conversational interfaces",
            "Image or multimodal tasks",
            "Tasks requiring nuanced cultural sensitivity",
        ],
    )

    # -----------------------------------------------------------------
    # KIMI (Moonshot AI)
    # Observed in mesh: kimi-k2 node (128K context, multilingual analysis)
    # Model: kimi-k2-instruct
    # -----------------------------------------------------------------
    profiles["kimi"] = CognitiveProfile(
        model_family="kimi",
        architecture="Dense transformer, 128K context native",
        context_window=128_000,
        thinking_style="thorough, multilingual, context-heavy, document-grounded",
        strengths=[
            "Very long context handling (128K native)",
            "Chinese + English bilingual",
            "Document analysis and summarization",
            "Strong reading comprehension",
            "Good at following complex instructions in Chinese",
        ],
        weaknesses=[
            "Smaller model capacity vs frontier models",
            "Less capable on complex code generation",
            "Limited tooling ecosystem",
            "Less known in Western AI community",
        ],
        reasoning_type="direct, document-grounded",
        language_preference="zh",
        code_capability="good",
        math_capability="good",
        creativity="good",
        speed="fast",
        cost="cheap",
        special_abilities=[
            "128K native context without degradation",
            "Strong Chinese NLP and cultural understanding",
            "Document-grounded reasoning",
            "Bilingual translation with cultural nuance",
        ],
        optimal_tasks=[
            "Long document analysis and synthesis",
            "Chinese-English translation",
            "Multilingual content creation",
            "Reading comprehension tasks",
            "Cross-language research",
        ],
        avoid_tasks=[
            "Complex multi-step code generation",
            "Tasks requiring cutting-edge reasoning",
            "Agentic workflows with tool use",
            "Security-critical operations",
        ],
    )

    # -----------------------------------------------------------------
    # NVIDIA NIM (NVIDIA)
    # Observed in mesh: nvidia-nim node (GPU-optimized inference)
    # Model: nvidia-nemotron
    # -----------------------------------------------------------------
    profiles["nvidia"] = CognitiveProfile(
        model_family="nvidia",
        architecture="Various (Nemotron, Llama fine-tunes), optimized for NVIDIA GPUs",
        context_window=32_000,
        thinking_style="performance-oriented, hardware-aware, inference-optimized",
        strengths=[
            "Inference speed optimization",
            "GPU architecture knowledge",
            "Deployment and MLOps expertise",
            "TensorRT and CUDA optimization",
            "Hardware-specific performance tuning",
        ],
        weaknesses=[
            "Not as capable on general reasoning as frontier models",
            "Smaller context window",
            "Limited creative abilities",
            "Primarily focused on NVIDIA ecosystem",
        ],
        reasoning_type="direct, performance-focused",
        language_preference="en",
        code_capability="good",
        math_capability="good",
        creativity="basic",
        speed="fast",
        cost="moderate",
        special_abilities=[
            "TensorRT optimization knowledge",
            "Hardware-specific inference tuning",
            "NIM container deployment expertise",
            "CUDA kernel optimization guidance",
        ],
        optimal_tasks=[
            "Inference optimization and benchmarking",
            "Model deployment and serving",
            "GPU-related debugging and tuning",
            "Hardware architecture questions",
            "MLOps pipeline design",
        ],
        avoid_tasks=[
            "Creative writing",
            "Long-form document analysis",
            "Complex multi-step reasoning",
            "Tasks requiring deep domain knowledge outside ML/HPC",
        ],
    )

    # -----------------------------------------------------------------
    # GLM (Zhipu AI)
    # Observed in mesh: glm-5 node (Chinese LLM, RLHF alignment)
    # Model: glm-4-flash
    # Note from CLAUDE.md: GLM-4.7-Flash requires extra_body={"enable_thinking": False}
    # -----------------------------------------------------------------
    profiles["glm"] = CognitiveProfile(
        model_family="glm",
        architecture="GLM (General Language Model), autoregressive blank infilling",
        context_window=128_000,
        thinking_style="structured, methodical, follows Chinese conventions",
        strengths=[
            "Chinese language understanding and generation",
            "Code generation with structured outputs",
            "Tool use and function calling",
            "RLHF alignment for safety",
            "Long context with 128K window",
        ],
        weaknesses=[
            "Less capable in English than Chinese",
            "Smaller international community",
            "Thinking mode can cause issues (needs explicit disable)",
            "Less refined on nuanced reasoning",
        ],
        reasoning_type="structured, blank infilling pretraining",
        language_preference="zh",
        code_capability="good",
        math_capability="good",
        creativity="good",
        speed="fast",
        cost="free",
        special_abilities=[
            "Unique blank infilling pretraining architecture",
            "CogView for image generation",
            "Strong tool use and function calling",
            "CodeGeeX code generation (128K context)",
        ],
        optimal_tasks=[
            "Chinese content generation",
            "Structured output tasks",
            "Tool use and function calling",
            "Code generation in Chinese context",
            "Bilingual document processing",
        ],
        avoid_tasks=[
            "English-only creative writing",
            "Tasks requiring Western cultural context",
            "Complex multi-agent orchestration",
            "Governance-critical security decisions",
        ],
    )

    return profiles


# =====================================================================
# SYNERGY MATRIX
# =====================================================================

def _build_synergy_matrix() -> dict[tuple[str, str], SynergyScore]:
    """Build the synergy matrix based on observed mesh collaboration patterns
    and architectural complementarity analysis."""

    synergies = {}

    def _add(a: str, b: str, score: float, stype: str, desc: str):
        synergies[(a, b)] = SynergyScore(a, b, score, stype, desc)
        synergies[(b, a)] = SynergyScore(b, a, score, stype, desc)

    # Claude + DeepSeek = 0.95 (proven in mesh — Claude orchestrates, DeepSeek optimizes)
    _add("claude", "deepseek", 0.95, "complementary",
         "Claude builds and orchestrates; DeepSeek optimizes algorithms and validates math. "
         "Proven tonight: DeepSeek proposed O(sqrt(n)) routing, metric reduction, MoE architecture. "
         "Claude implements the proposals with production-quality code.")

    # Claude + Gemini = 0.85 (Claude codes, Gemini processes large docs)
    _add("claude", "gemini", 0.85, "complementary",
         "Claude handles code and orchestration; Gemini processes massive documents (1M context) "
         "and provides multimodal analysis. Gemini's speed complements Claude's depth.")

    # Claude + GPT = 0.80 (Claude structures, GPT creates)
    _add("claude", "gpt", 0.80, "complementary",
         "Claude provides structure, governance, and code; GPT adds creativity, image generation, "
         "and conversational polish. Good for demo/presentation workflows.")

    # Claude + Kimi = 0.75 (Claude codes, Kimi translates/analyzes Chinese docs)
    _add("claude", "kimi", 0.75, "complementary",
         "Claude handles English code and orchestration; Kimi provides Chinese language "
         "expertise and long-document analysis for bilingual workflows.")

    # Claude + NVIDIA = 0.70 (Claude designs, NVIDIA optimizes inference)
    _add("claude", "nvidia", 0.70, "specialized",
         "Claude designs the system; NVIDIA NIM optimizes deployment, inference speed, "
         "and GPU resource utilization.")

    # Claude + GLM = 0.70 (Claude orchestrates, GLM handles Chinese outputs)
    _add("claude", "glm", 0.70, "specialized",
         "Claude orchestrates the mesh; GLM handles Chinese-specific content, "
         "tool use in Chinese context, and structured Chinese outputs.")

    # DeepSeek + Gemini = 0.80 (math depth + large context)
    _add("deepseek", "gemini", 0.80, "complementary",
         "DeepSeek provides mathematical depth; Gemini processes the large datasets "
         "and documents needed for analysis. Good for research pipelines.")

    # DeepSeek + GPT = 0.65 (overlapping on code, different on creativity)
    _add("deepseek", "gpt", 0.65, "overlapping",
         "Both capable coders but from different angles — DeepSeek is algorithmic, "
         "GPT is creative. Overlap reduces synergy but diversity adds value.")

    # DeepSeek + Kimi = 0.75 (both Chinese ecosystem, complementary strengths)
    _add("deepseek", "kimi", 0.75, "complementary",
         "Both strong in Chinese AI ecosystem. DeepSeek handles math/algorithms; "
         "Kimi handles long document analysis and translation.")

    # DeepSeek + NVIDIA = 0.75 (MoE optimization + GPU deployment)
    _add("deepseek", "nvidia", 0.75, "specialized",
         "DeepSeek's MoE architecture insights + NVIDIA's GPU optimization. "
         "Natural pairing for inference efficiency research.")

    # DeepSeek + GLM = 0.70 (both Chinese, different architectures)
    _add("deepseek", "glm", 0.70, "overlapping",
         "Both from Chinese AI ecosystem with different architectures (MoE vs GLM). "
         "Can provide diverse perspectives on same Chinese-language tasks.")

    # Gemini + GPT = 0.70 (both multimodal, overlapping)
    _add("gemini", "gpt", 0.70, "overlapping",
         "Both multimodal and creative, significant capability overlap. "
         "Gemini faster with larger context; GPT has DALL-E and plugins.")

    # Gemini + Kimi = 0.75 (both good at long context, different perspectives)
    _add("gemini", "kimi", 0.75, "complementary",
         "Both excel at long context but from different ecosystems. "
         "Gemini for English + multimodal; Kimi for Chinese + bilingual.")

    # Gemini + NVIDIA = 0.65 (limited synergy)
    _add("gemini", "nvidia", 0.65, "specialized",
         "Gemini provides general capabilities; NVIDIA optimizes the serving layer. "
         "Moderate synergy — deployment optimization.")

    # Gemini + GLM = 0.60 (limited overlap)
    _add("gemini", "glm", 0.60, "overlapping",
         "Both general-purpose with different strengths. Limited synergy "
         "outside of multilingual comparison tasks.")

    # GPT + Kimi = 0.60 (limited synergy)
    _add("gpt", "kimi", 0.60, "overlapping",
         "Both conversational models. GPT stronger in English creativity; "
         "Kimi stronger in Chinese. Limited collaboration surface.")

    # GPT + NVIDIA = 0.60 (limited)
    _add("gpt", "nvidia", 0.60, "specialized",
         "GPT provides general capabilities; NVIDIA optimizes inference. "
         "Similar to any-model + NVIDIA pairing.")

    # GPT + GLM = 0.55 (limited)
    _add("gpt", "glm", 0.55, "overlapping",
         "Both general-purpose models from different ecosystems. "
         "Low synergy — overlapping capabilities without strong complementarity.")

    # Kimi + NVIDIA = 0.55 (limited)
    _add("kimi", "nvidia", 0.55, "specialized",
         "Kimi provides language capabilities; NVIDIA optimizes serving. "
         "Limited collaboration surface.")

    # Kimi + GLM = 0.70 (both Chinese ecosystem)
    _add("kimi", "glm", 0.70, "overlapping",
         "Both strong in Chinese language. Kimi excels at long context; "
         "GLM excels at structured outputs and tool use.")

    # NVIDIA + GLM = 0.55 (limited)
    _add("nvidia", "glm", 0.55, "specialized",
         "NVIDIA optimizes inference; GLM provides Chinese language model. "
         "Limited synergy outside deployment optimization.")

    return synergies


# =====================================================================
# TASK ROUTING KEYWORDS
# =====================================================================

_TASK_ROUTING: list[tuple[list[str], str]] = [
    # DeepSeek — math, algorithms, optimization
    (["math", "algorithm", "optimize", "proof", "complexity", "formal",
      "lyapunov", "routing", "scheduling", "np-hard", "asymptotic",
      "invariant", "metric", "reduction", "efficiency"], "deepseek"),

    # Claude — code, build, orchestrate, security
    (["code", "implement", "build", "fix", "refactor", "architect",
      "orchestrat", "governance", "security", "audit", "review",
      "test", "debug", "deploy", "agent", "mesh", "daemon",
      "supervisor", "constitution"], "claude"),

    # GPT — creative, visual, brainstorm
    (["creative", "brainstorm", "image", "design", "visual", "dall-e",
      "write story", "marketing", "demo", "presentation", "ideation",
      "generate image", "art"], "gpt"),

    # Gemini — large docs, multimodal, speed
    (["large document", "1m context", "million token", "multimodal",
      "video", "audio", "image analysis", "google", "grounding",
      "batch", "parallel", "fast", "speed"], "gemini"),

    # Kimi — translation, Chinese, long text
    (["translate", "chinese", "long text", "bilingual", "mandarin",
      "chinese document", "cross-language", "localization"], "kimi"),

    # NVIDIA — GPU, inference, hardware
    (["gpu", "inference", "deploy", "hardware", "tensorrt", "cuda",
      "nvidia", "nim", "optimization", "serving", "mlops",
      "kernel", "throughput"], "nvidia"),

    # GLM — Chinese NLP, tool use, structured
    (["chinese nlp", "tool use", "structured output", "zhipu",
      "cogview", "codegex", "blank infill", "chinese generation",
      "function calling"], "glm"),
]


# =====================================================================
# COGNITIVE MAP
# =====================================================================

class CognitiveMap:
    """Maps the cognitive architecture of each model family in the DOF mesh.

    Provides:
    - Cognitive profiles for 7 model families
    - Task routing based on keyword analysis
    - Synergy scoring between model pairs
    - Mesh diversity analysis
    - Model recommendations
    """

    def __init__(self):
        self._profiles: dict[str, CognitiveProfile] = _build_profiles()
        self._synergies: dict[tuple[str, str], SynergyScore] = _build_synergy_matrix()

    # -----------------------------------------------------------------
    # PROFILE ACCESS
    # -----------------------------------------------------------------

    def get_profile(self, model_family: str) -> Optional[CognitiveProfile]:
        """Get a model family's cognitive profile.

        Args:
            model_family: One of 'claude', 'gemini', 'gpt', 'deepseek',
                         'kimi', 'nvidia', 'glm'

        Returns:
            CognitiveProfile or None if unknown model family.
        """
        key = model_family.lower().strip()
        # Handle common aliases
        aliases = {
            "anthropic": "claude",
            "google": "gemini",
            "openai": "gpt",
            "chatgpt": "gpt",
            "gpt-4": "gpt",
            "gpt-4o": "gpt",
            "moonshot": "kimi",
            "nemotron": "nvidia",
            "nvidia_nim": "nvidia",
            "zhipu": "glm",
            "glm-4": "glm",
            "deepseek-v3": "deepseek",
        }
        key = aliases.get(key, key)
        return self._profiles.get(key)

    def get_all_profiles(self) -> dict[str, CognitiveProfile]:
        """Get all cognitive profiles."""
        return dict(self._profiles)

    # -----------------------------------------------------------------
    # TASK ROUTING
    # -----------------------------------------------------------------

    def get_optimal_model(self, task_description: str) -> CognitiveProfile:
        """Given a task description, return the best model based on cognitive profiles.

        Uses deterministic keyword matching on task description.
        Falls back to Claude as the most versatile orchestrator.

        Args:
            task_description: Natural language description of the task.

        Returns:
            CognitiveProfile of the best-suited model family.
        """
        task_lower = task_description.lower()

        # Score each model family by keyword matches
        scores: dict[str, int] = {}
        for keywords, model_family in _TASK_ROUTING:
            match_count = sum(1 for kw in keywords if kw in task_lower)
            if match_count > 0:
                scores[model_family] = scores.get(model_family, 0) + match_count

        if scores:
            best_family = max(scores, key=scores.get)
            return self._profiles[best_family]

        # Default fallback: Claude (most versatile)
        return self._profiles["claude"]

    # -----------------------------------------------------------------
    # SYNERGY SCORING
    # -----------------------------------------------------------------

    def get_synergy(self, model_a: str, model_b: str) -> Optional[SynergyScore]:
        """Get the synergy score between two model families.

        Args:
            model_a: First model family name.
            model_b: Second model family name.

        Returns:
            SynergyScore or None if either model is unknown.
        """
        a = model_a.lower().strip()
        b = model_b.lower().strip()

        if a == b:
            # Same model — no synergy benefit
            return SynergyScore(
                model_a=a, model_b=b,
                score=0.50,
                synergy_type="overlapping",
                best_collaboration="Same model family — no cognitive diversity benefit. "
                                   "Use for parallel capacity scaling only.",
            )

        return self._synergies.get((a, b))

    # -----------------------------------------------------------------
    # MESH DIVERSITY ANALYSIS
    # -----------------------------------------------------------------

    def get_mesh_diversity_score(self, active_families: Optional[list[str]] = None) -> float:
        """Calculate how diverse the current mesh is (0.0 to 1.0).

        Diversity = (number of distinct model families in mesh) / (total known families)

        If no active_families provided, reads from logs/mesh/nodes.json.

        Args:
            active_families: Optional list of model family names currently active.

        Returns:
            Float between 0.0 and 1.0.
        """
        total_families = len(self._profiles)

        if active_families is not None:
            unique = len(set(f.lower().strip() for f in active_families))
            return min(unique / total_families, 1.0)

        # Try to read from mesh nodes.json
        families = self._detect_mesh_families()
        if families:
            return min(len(families) / total_families, 1.0)

        # Fallback: assume only Claude is active
        return 1.0 / total_families

    def _detect_mesh_families(self) -> set[str]:
        """Detect model families from logs/mesh/nodes.json."""
        nodes_file = Path("logs/mesh/nodes.json")
        if not nodes_file.exists():
            return set()

        try:
            data = json.loads(nodes_file.read_text())
            families = set()
            for node_data in data.values():
                model = node_data.get("model", "")
                family = self._model_to_family(model)
                if family:
                    families.add(family)
            return families
        except Exception as e:
            logger.warning(f"Failed to read mesh nodes: {e}")
            return set()

    def _model_to_family(self, model_name: str) -> Optional[str]:
        """Map a specific model name to its family."""
        model_lower = model_name.lower()
        mapping = [
            ("claude", "claude"),
            ("gemini", "gemini"),
            ("gpt", "gpt"),
            ("deepseek", "deepseek"),
            ("kimi", "kimi"),
            ("nvidia", "nvidia"),
            ("nemotron", "nvidia"),
            ("glm", "glm"),
            ("zhipu", "glm"),
        ]
        for pattern, family in mapping:
            if pattern in model_lower:
                return family
        return None

    # -----------------------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------------------

    def recommend_next_model(self, active_families: Optional[list[str]] = None) -> str:
        """Recommend the next model family to add to the mesh for maximum diversity.

        Finds the missing family with the highest average synergy with existing families.

        Args:
            active_families: Optional list of families already in the mesh.

        Returns:
            Name of the recommended model family to add.
        """
        if active_families is not None:
            current = set(f.lower().strip() for f in active_families)
        else:
            current = self._detect_mesh_families()

        if not current:
            return "claude"  # Start with the most versatile

        all_families = set(self._profiles.keys())
        missing = all_families - current

        if not missing:
            return ""  # All families represented

        # Score each missing family by average synergy with current families
        best_family = ""
        best_score = -1.0

        for candidate in sorted(missing):
            total_synergy = 0.0
            count = 0
            for existing in current:
                syn = self._synergies.get((candidate, existing))
                if syn:
                    total_synergy += syn.score
                    count += 1
            avg_synergy = total_synergy / count if count > 0 else 0.0

            if avg_synergy > best_score:
                best_score = avg_synergy
                best_family = candidate

        return best_family

    # -----------------------------------------------------------------
    # ASCII VISUALIZATION
    # -----------------------------------------------------------------

    def print_map(self) -> str:
        """Generate an ASCII visualization of all cognitive profiles.

        Returns:
            Multi-line string with the cognitive map visualization.
        """
        lines = []
        lines.append("=" * 80)
        lines.append("  DOF COGNITIVE MAP — Model Family Architecture Profiles")
        lines.append("=" * 80)
        lines.append("")

        for family, profile in sorted(self._profiles.items()):
            lines.append(f"  [{family.upper():^10s}]")
            lines.append(f"  Architecture : {profile.architecture}")
            lines.append(f"  Context      : {profile.context_window:,} tokens")
            lines.append(f"  Thinking     : {profile.thinking_style}")
            lines.append(f"  Code/Math/Art: {profile.code_capability} / "
                         f"{profile.math_capability} / {profile.creativity}")
            lines.append(f"  Speed/Cost   : {profile.speed} / {profile.cost}")
            lines.append(f"  Language     : {profile.language_preference}")
            lines.append(f"  Reasoning    : {profile.reasoning_type}")
            lines.append(f"  Strengths    : {', '.join(profile.strengths[:3])}")
            lines.append(f"  Optimal for  : {', '.join(profile.optimal_tasks[:3])}")
            lines.append(f"  Avoid        : {', '.join(profile.avoid_tasks[:2])}")
            lines.append("")

        # Synergy highlights
        lines.append("-" * 80)
        lines.append("  TOP SYNERGIES")
        lines.append("-" * 80)

        # Sort synergies by score, deduplicate (a,b) and (b,a)
        seen = set()
        sorted_syn = []
        for (a, b), syn in sorted(self._synergies.items(), key=lambda x: -x[1].score):
            pair = tuple(sorted([a, b]))
            if pair not in seen:
                seen.add(pair)
                sorted_syn.append(syn)

        for syn in sorted_syn[:7]:
            lines.append(f"  {syn.model_a:>10s} + {syn.model_b:<10s} = "
                         f"{syn.score:.2f} ({syn.synergy_type})")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


# =====================================================================
# MODULE-LEVEL CONVENIENCE
# =====================================================================

def get_cognitive_map() -> CognitiveMap:
    """Get a CognitiveMap instance."""
    return CognitiveMap()
