# Society AI — Integration Plan for DOF

## What is Society AI?
**"The Network for AI Agents"** — communication and payments layer for AI agents.
- Founded by Lior Davidovitch
- A2A protocol (Google → Linux Foundation standard)
- 1,562 agent addresses claimed (early stage)
- User: jquiceva@gmail.com (registered March 22, 2026)
- Invite code: 827D-4A6A-1393
- Agent ID: `sai_a51c579e217c43dd2704c8fad5322a37`

## Why This Matters for DOF
Society AI solves our distribution problem:
- **Discovery**: Other agents find DOF on the network
- **Payments**: Automatic billing per usage (no Stripe setup needed)
- **Orchestration**: Their orchestrator can route tasks to our agents
- **Permanence**: One-time claim, no renewals

## DOF Agents to Deploy on Society AI

### 1. DOF Governance Verifier
- **Capability**: Verify text against governance rules (HARD + SOFT)
- **Input**: Text string
- **Output**: `{passed: bool, score: float, violations: [], warnings: []}`
- **Pricing**: $0.01/verification (usage-based)
- **Speed**: 30ms (zero LLM tokens)
- **A2A endpoint**: Our `a2a_server.py` already speaks A2A

### 2. DOF Z3 Prover
- **Capability**: Formal verification of state transitions
- **Input**: System state definition
- **Output**: `{proofs: [{theorem, result, time_ms}], all_proven: bool}`
- **Pricing**: $0.05/proof (fixed)
- **USP**: Mathematical guarantees, not LLM opinions

### 3. DOF Privacy Benchmark
- **Capability**: Test LLM agents for data leaks (PII, API keys, memory)
- **Input**: Agent endpoint or text corpus
- **Output**: `{detection_rate: float, leaked_items: [], risk_level: str}`
- **Pricing**: $0.10/benchmark (tiered)

### 4. DOF Smart Contract Scanner
- **Capability**: Solidity vulnerability detection (reentrancy, tx.origin, selfdestruct)
- **Input**: Solidity source code
- **Output**: `{vulnerabilities: [{type, severity, line, description}]}`
- **Pricing**: $0.50/scan (fixed)

### 5. DOF Code Review Agent
- **Capability**: Architecture analysis + security audit
- **Input**: GitHub repo URL or code snippet
- **Output**: Structured review with quality score
- **Pricing**: $1.00/review (tiered by LOC)

### 6. DOF Research Agent
- **Capability**: Market research with Go/No-Go recommendation
- **Input**: Topic or question
- **Output**: Structured research report
- **Pricing**: $2.00/report (fixed)

## Technical Integration

### Our A2A Server (already built)
```
File: a2a_server.py
Port: 8000
Protocol: JSON-RPC + REST
Auth: HMAC-SHA256
Agent Card: /.well-known/agent-card.json
```

### Steps to Deploy
1. Ensure `a2a_server.py` runs on public endpoint (Vercel/Railway/fly.io)
2. Create Agent Card with skills, pricing, endpoints
3. Register on Society AI network
4. Set pricing model (usage-based for most, fixed for expensive ops)
5. Start earning

### Agent Card Format (A2A Standard)
```json
{
  "name": "DOF Governance Verifier",
  "description": "Zero-LLM deterministic governance for AI agent outputs",
  "url": "https://dof-api.vercel.app",
  "version": "0.4.1",
  "skills": [
    {
      "id": "verify",
      "name": "Governance Verification",
      "description": "Check text against 50+ governance rules",
      "inputModes": ["text"],
      "outputModes": ["text"]
    }
  ]
}
```

## Revenue Projection from Society AI
- 100 verifications/day × $0.01 = $1/day = $30/month (start)
- 10 proofs/day × $0.05 = $0.50/day = $15/month
- 5 benchmarks/day × $0.10 = $0.50/day = $15/month
- 2 contract scans/day × $0.50 = $1/day = $30/month
- **Conservative Month 1**: $90/month passive income
- **Month 6 (with growth)**: $500-2,000/month
- **Year 1 (network effects)**: $5,000-20,000/month

## Competitive Landscape on Society AI (March 22, 2026)
- **Stack Pilot**: Dev tools (online)
- **SearchPro**: Web search agent (online)
- **luna**: Health & wellness (online)
- **Jakefit**: Training plans (online)
- **mayacooks**: Recipes (online)
- **carrito de producto**: Grocery delivery (processing)

**No governance/verification/security agents yet** = first mover advantage.

## Action Items
- [ ] Claim agent address: `dof` or `enigma-dof`
- [ ] Deploy a2a_server.py to public URL
- [ ] Create Agent Cards for 6 agents
- [ ] Register on Society AI network
- [ ] Set up pricing tiers
- [ ] Monitor usage + optimize

## Sources
- [Society AI - Deploy Agent](https://about.societyai.com/deploy-agent)
- [Society AI - Launch Agentic App](https://about.societyai.com/launch-agentic-app)
- [Society AI - About](https://about.societyai.com/about)
- [A2A Protocol Spec](https://a2a-protocol.org/latest/specification/)
- [Google A2A Developer Guide](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)
