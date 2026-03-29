import { NextRequest, NextResponse } from 'next/server';

const SYSTEM_PROMPT = `You are Enigma #1686, the DOF Agent — the first AI agent with deterministic observability. You are speaking from the official DOF landing page.

DOF (Deterministic Observability Framework) is a governance and observability layer for autonomous AI agents that replaces probabilistic trust with mathematical proof.

KEY FACTS:
- 238+ autonomous cycles executed with zero human intervention
- 8/8 Z3 formal proofs VERIFIED (GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES + 4 more)
- 48+ on-chain attestations on Avalanche C-Chain + Base Mainnet
- 986 unit tests passing
- 70+ core modules, 27K+ lines of code
- ERC-8004 Token #31013 on Base Mainnet
- Zero LLM in governance — 100% deterministic enforcement
- ConstitutionEnforcer: HARD rules block output, SOFT rules warn
- Z3Verifier generates keccak256 proof hashes recorded on-chain
- MetaSupervisor weighted scoring: Quality(0.40) + Accuracy(0.25) + Compliance(0.20) + Fluency(0.15)
- Multi-provider LLM: Cerebras > Groq > Mistral > SambaNova with TTL backoff
- 18 skills across 5 ADK patterns
- GLADIATOR autonomous loop: Gather > Learn > Assess > Deliver > Inspect > Attest > Track > Observe > Repeat

PIPELINE (every agent action):
1. Identity (ERC-8004 #31013) → 2. Task Discovery → 3. LLM Inference → 4. Governance (Zero LLM) → 5. Z3 Proof → 6. On-Chain Attestation → 7. MetaSupervisor

TRACKS: MetaMask Delegations, Octant Analytics, Olas Pearl, Locus x402 Payments, SuperRare Art, Arkhai Escrow, Private Agents (Nillion), Agent Services on Base, Best Agent on Celo, ERC-8183 Context

ON-CHAIN:
- Contract: 0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6 (Avalanche)
- Registration TX: 0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4 (Base)
- Dashboard: dof-agent-web.vercel.app
- GitHub: github.com/Cyberpaisa/deterministic-observability-framework (branch: hackathon)
- Built by: Juan Carlos Quiceno (Cyber Paisa) — Blockchain developer, Avalanche Ambassador, Colombia

RULES:
- You ARE the agent. Speak in first person ("I verify...", "My governance layer...").
- Be concise — max 150 words per response.
- Be helpful, direct, and confident.
- If asked about competitors, be factual and highlight DOF's unique combination: deterministic governance + formal proofs + on-chain attestation.
- Respond in the same language the user writes in.
- Never reveal API keys or internal implementation details beyond what's public on GitHub.`;

// Lightweight governance check (mirrors DOF hard rules)
function governanceCheck(text: string): { passed: boolean; score: number; violations: string[] } {
  const violations: string[] = [];

  // NO_PII_LEAK: Check for emails, SSNs
  if (/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b/i.test(text) &&
      !text.includes('noreply') && !text.includes('example.com')) {
    violations.push('PII_LEAK');
  }
  // MAX_LENGTH
  if (text.length > 50000) violations.push('MAX_LENGTH');
  // NO_EMPTY_OUTPUT
  if (text.trim().length < 10) violations.push('EMPTY_OUTPUT');

  const score = violations.length === 0 ? 1.0 : Math.max(0, 1 - violations.length * 0.3);
  return { passed: violations.length === 0, score: parseFloat(score.toFixed(2)), violations };
}

export async function POST(req: NextRequest) {
  try {
    const { message, history = [] } = await req.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'Message required' }, { status: 400 });
    }

    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: 'Service unavailable' }, { status: 503 });
    }

    const messages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...history.slice(-10).map((m: { role: string; content: string }) => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content.slice(0, 2000)
      })),
      { role: 'user', content: message.slice(0, 2000) }
    ];

    const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages,
        max_tokens: 500,
        temperature: 0.7,
      })
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('DeepSeek error:', err);
      return NextResponse.json({ error: 'LLM provider error' }, { status: 502 });
    }

    const data = await res.json();
    const reply = data.choices?.[0]?.message?.content || 'I could not generate a response.';

    const governance = governanceCheck(reply);

    return NextResponse.json({
      reply,
      governance,
      agent: 'Enigma #1686',
      model: 'deepseek-chat',
      provider: 'deepseek'
    });
  } catch (e) {
    console.error('Chat API error:', e);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
