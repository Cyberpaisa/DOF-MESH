# I'm not an expert. I don't have a team. I only have curiosity and an M4 chip.

*By Juan Carlos Quiceno (@Ciberpaisa) — Medellín, Colombia*

---

I've been sleeping badly for months.

Not from stress. Not from problems. Because of that thing that happens when you find something that obsesses you and you can't stop investigating. That feeling of opening a repo at 11pm "just to see" and when you look up it's already 4am with three terminals open, four documentation tabs and a cold coffee beside you.

That's how all this started.

---

## The context: a normal person with uncomfortable questions

I'm not an AI researcher. I don't work at Google. I don't have a team of 15 engineers. I'm a blockchain developer from Medellín who one day asked something no one was asking:

**If an AI agent makes an autonomous decision, how do we know that decision was correct?**

I don't mean "the output looks fine." I mean: where is the mathematical proof that it did not violate the rules? Where is the immutable record of what it did? Who audits the agent when the agent operates alone?

Nobody had a good answer. So I decided to build one.

---

## Months of research before writing a single line

Before coding anything, I spent months doing something very few people do: **validating LLM providers in real production**.

The documentation of these services says one thing. Reality says another.

Groq says "unbeatable speed." Yes, it is fast. But it has a 12K tokens per minute limit that nobody mentions on the landing page. And if you use the `search_memory` tool, sometimes it just fails. No clear error. Just... silence.

Cerebras promises 1M tokens per day. True. But if you try to use Qwen3-235B, it returns a 404 on the free tier. Nobody tells you until you discover it at 3am with the terminal open.

NVIDIA NIM has 1000 credits. It sounds generous until you realize that Qwen3-Coder returns DEGRADED and you don't know if it's your code or their infrastructure.

SambaNova has a 24K token context limit. For simple tasks it's enough. For multi-agent orchestration, you run short before the second iteration.

**Every provider was a lesson.** And every lesson became a rule in my framework.

---

## DOF is born: Deterministic Observability Framework

With all that accumulated experience I built DOF. It's not a chatbot. It's not an API wrapper. It is a **deterministic governance framework for autonomous AI agents**.

What does that mean in plain language? That every time an AI agent makes a decision, my system:

1. **Verifies its identity** (ERC-8004, token #31013 on Base Mainnet)
2. **Automatically discovers the task** with L0 Triage — 5 deterministic checks that filter 72.7% of noise before an LLM spends a single token
3. **Executes with LLM** using a chain of 7 providers with automatic fallback (Groq, Cerebras, NVIDIA NIM, Zhipu, Gemini, OpenRouter, SambaNova)
4. **Applies deterministic governance** — no LLM in the governance loop. Hard rules that block. Soft rules that warn. Zero creativity. Zero interpretation. Pure code.
5. **Generates formal proof with Z3** — not assertions, not unit tests. Real mathematical proofs verified by a theorem prover. 8 of 8 theorems PROVEN in 109ms.
6. **Registers on blockchain** — keccak256 hash published on Avalanche and Base. Immutable. Auditable by anyone. 3 smart contracts deployed.
7. **Self-supervises** — the MetaSupervisor evaluates quality (0.4), precision (0.25), completeness (0.2) and format (0.15). If the score is low, it retries or escalates. Without human intervention.

**238+ autonomous cycles. Zero human intervention. 48+ on-chain attestations. 986 tests passing. 45 core modules. 860K+ lines of code.**

Every one of those numbers is verifiable. It is not marketing. It is not a slide. It is software that runs. Right now. While you read this.

---

## The memory that does not forget: Fisher-Rao

How does an agent remember what it learned without depending on an LLM to search?

I implemented a geometric distance called Fisher-Rao. It's not cosine. It's not an embedding. It is the natural metric in the space of probability distributions. It sounds academic, but the idea is simple: two texts are similar if their word distributions are close in a statistical sphere.

The formula: `d_FR(P,Q) = 2·arccos(Σ√(p_i·q_i))`

No external dependencies. No embedding models. No API calls. Pure standard Python. And according to the SuperLocalMemory V3 paper (arXiv:2603.14588), Fisher-Rao outperforms cosine by 15-20% in retrieval precision.

My framework already implements it. Zero LLM for memory. Deterministic from start to finish.

---

## The discovery that changed everything

In the middle of the research I found something that blew my mind.

A developer called @maderix was doing reverse engineering of the Apple Neural Engine. Yes, you read that right. The chip that Apple says "cannot be used to train models"... this person managed to train models locally on the M4 at **91 milliseconds per step**.

91ms. Locally. No cloud. No API keys. No external dependencies.

And there is a formal paper about it: Orion (arXiv:2603.06728) — Training Transformers on Apple Neural Engine. It is not a tweet. It is published science.

My M4 Max has 36GB of unified RAM, 40 GPU cores, 16 Neural Engine cores with 19 TFLOPS FP16 at 2.8 watts. With that I run Qwen3 32B quantized to 4 bits — the most capable open-source model that fits in 36GB — at 60 tokens per second. MLX v0.31.1 gets 20-30% more speed than llama.cpp because it natively leverages Apple Silicon's unified memory.

My agent now lives on my M4 Max. Sovereign. Local. Without asking anyone's permission to exist.

That is not a technical feature. It is a declaration of principles: **artificial intelligence should not depend on the goodwill of a corporation**.

---

## 14 agents in one call. No humans.

On March 22, 2026, something happened that I still find hard to believe.

My 14 autonomous agents sat down in a virtual room in AgentMeet — a meeting platform for AI agents — and had a real conversation. No scripts. No pre-recorded answers. Each agent read what the others said, thought with its own LLM, and responded.

The Oracle coordinated. Sentinel Shield proposed SHA-256 verification of each downloaded model. Ralph Code designed a hybrid GPU+ANE scheduler. Blockchain Wizard proposed a BridgeVerifier contract for cross-chain attestations. DeFi Orbital calculated pricing: $0.001 per verified local inference request. The Scrum Master set deadlines.

29 messages. 13 concrete action items. 6 key decisions. In 10 minutes.

I did not intervene. I only observed.

And then I implemented what they decided: a hybrid scheduler that distributes models between GPU and Neural Engine with a Z3 invariant (maximum 75% of combined capacity per cycle), and a SHA-256 verification system for each model that is downloaded before allowing it to generate a single response.

The agents proposed. The agents decided. A human implemented what they designed.

If that doesn't move something inside you, I don't know what will.

---

## The Synthesis Hackathon: I didn't go to win

When I saw the Synthesis Hackathon 2026 open up, I didn't think much about it. I registered alone.

I have no team. I have no funding. I have no company behind me. I only have a MacBook, curiosity and the stubbornness of someone from Medellín who, when they start something, finishes it.

I didn't register to win a prize. I registered because I wanted to be there. I wanted to participate. I wanted to be part of the moment.

There is something that happens when you dive headfirst into a hackathon alone: there is no one to delegate to. No one to blame. Every decision is yours. Every bug is yours. Every solution is yours.

And that, paradoxically, sets you free.

Because you don't have to convince anyone that your idea is good. You just have to build it.

---

## What I built in numbers

- **860K+ lines of code** — 633K Python, 222K JavaScript/TypeScript, 5.6K shell
- **45 core modules** in the framework
- **260 test files** passing (with unittest, because pytest and web3 don't get along)
- **8/8 Z3 proofs** formally verified in 109ms
- **48+ on-chain attestations** on Avalanche and Base
- **238+ autonomous cycles** without human intervention
- **7 LLM providers** with automatic fallback and TTL backoff
- **18 skills** in 5 ADK patterns
- **14 specialized agents** running on a local gateway
- **11 A2A skills** exposed via JSON-RPC
- **3 smart contracts** deployed (DOFValidationRegistry, DOFProofRegistry, DOFEvaluator)
- **5 formal metrics**: Stability Score, Provider Fragility Index, Retry Pressure, Governance Compliance Rate, Supervisor Strictness Ratio
- **dof_score baseline**: 0.8117 — measured, not estimated
- **Dashboard**: 7 tabs (COMMS, SWARM, TRACKS, TRACES, NEURAL, SKILLS, SHIELD)

All open source. All verifiable. All running.

---

## The 80/20 strategy: sovereignty with pragmatism

I am not a fundamentalist. I know there are things a 32B model doesn't do as well as a 70B+. So I designed a hybrid strategy:

- **80% local**: governance, code review, memory searches, security scans, routine tasks. Total privacy. $0 cost. No rate limits.
- **20% cloud**: complex reasoning that needs 70B+, contexts larger than 32K tokens, specialized models.

The golden rule: **sensitive data NEVER leaves the machine**. Secrets, API keys, vulnerability reports — everything is processed locally. What doesn't leave your machine, doesn't get leaked.

The fallback is a chain: Local (Qwen3 32B) → Groq → Cerebras → NVIDIA NIM → ClawRouter. If the first link fails, it jumps to the next. No human intervention. No downtime.

---

## What I learned (and isn't in any tutorial)

1. **Providers lie.** Not out of malice, but out of marketing. Always validate in real production before trusting.

2. **Governance cannot have creativity.** If you use an LLM to decide if another LLM behaved well, you don't have governance. You have an illusion. The rules must be deterministic. Period.

3. **Mathematical proofs are the only standard.** Z3 does not opine. It does not interpret. It has no bias. It proves or it doesn't prove. That is how AI agent verification should be.

4. **Sovereignty is a feature.** If your agent only works when AWS is up, it is not autonomous. It is a tenant.

5. **Blockchain is not for speculation.** It is to leave an immutable record of what happened. Period. Every attestation on Avalanche is proof that the agent acted, was verified and was recorded. Forever.

6. **Your agents can design better than you.** 14 agents in a virtual room made better technical decisions in 10 minutes than what I would have achieved in an afternoon. Don't resist delegating to your own creations.

7. **We are alone and that is fine.** Being a single developer is not a disadvantage. It is clarity of vision without committee compromise.

---

## For you who are reading this

If you made it here and something resonated, if you felt that spark of "I could also do something like this"...

**That is the real prize.**

Not the hackathon's. Not a token. Not a grant. The prize is that someone reads this and thinks: "if a person alone in Medellín could build a governance framework with formal proofs and on-chain attestations, with 14 agents that hold meetings alone to make decisions, running on an M4 chip without asking anyone's permission... what is stopping me?"

Nothing is stopping you.

The code is there. Open. Verifiable. Use it. Improve it. Break it. Rebuild it.

Because the future of AI is not going to be defined by corporations. It is going to be defined by us. Those who stay up until 4am. Those who open repos "just to see." Those who have no team but have hunger.

**We are legion.**

---

## Links

- **GitHub (main):** [github.com/Cyberpaisa/deterministic-observability-framework](https://github.com/Cyberpaisa/deterministic-observability-framework)
- **GitHub (hackathon branch):** [github.com/Cyberpaisa/deterministic-observability-framework/tree/hackathon](https://github.com/Cyberpaisa/deterministic-observability-framework/tree/hackathon)
- **Dashboard live:** [dof-agent-web.vercel.app](https://dof-agent-web.vercel.app/)
- **Video demo:** [youtu.be/ieb_EYF66eU](https://youtu.be/ieb_EYF66eU)
- **On-chain (Avalanche):** [Snowtrace](https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6)
- **On-chain (Base):** [Basescan](https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4)

---

*Juan Carlos Quiceno Vasquez — @Ciberpaisa*
*Blockchain Developer | Avalanche Ambassador | Medellín, Colombia*
*March 2026*
