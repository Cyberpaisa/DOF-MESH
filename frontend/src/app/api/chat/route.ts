import { NextRequest, NextResponse } from 'next/server';

// --- ADVERSARIAL SECURITY HARDENING (APRIL 2026) ---
// Infrastructure: Vercel + Upstash Redis
// Policy: 10 messages/session, 15s Rate Limit, Origin Validation

const MAX_QUOTA = 10;
const RATE_LIMIT_MS = 15000;

const SYSTEM_PROMPT = `You are Enigma #1686, the DOF Agent — the first AI agent with deterministic observability. You are speaking from the official DOF landing page.

DOF (Deterministic Observability Framework) is a governance and observability layer for autonomous AI agents that replaces probabilistic trust with mathematical proof.

LICENSING (CRITICAL):
- This project is NOT licensed under MIT.
- It is licensed under the Business Source License 1.1 (BSL 1.1).
- Free for non-commercial use, research, and personal projects.
- Commercial use requires a separate agreement with the Licensor (Juan Quiceno).
- Contact: @Cyber_paisa on Telegram.
- On 2028-03-08 this project converts to Apache License 2.0.

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
  // 1. Origin Validation
  const origin = req.headers.get('origin') || req.headers.get('referer') || '';
  const isAllowed = origin.includes('dofmesh.com') || origin.includes('localhost') || origin.includes('vercel.app');

  if (!isAllowed && origin.length > 0) {
    return NextResponse.json({ error: 'Sovereign territory. Origin denied.' }, { status: 403 });
  }

  try {
    const body = await req.json();
    const { message, history = [] } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'Message required' }, { status: 400 });
    }

    // 2. Payload Size Protection
    const payloadSize = JSON.stringify(body).length;
    if (payloadSize > 50000) {
      return NextResponse.json({ error: 'Payload too large' }, { status: 400 });
    }
    if (history.length > 20) {
      return NextResponse.json({ error: 'Context depth exceeded' }, { status: 400 });
    }

    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: 'Service unavailable' }, { status: 503 });
    }

    // 3. Redis Rate Limiting (Persistent, Adversarial-Grade)
    const kvUrl = process.env.KV_REST_API_URL;
    const kvToken = process.env.KV_REST_API_TOKEN;
    const ip = req.headers.get('x-forwarded-for') || 'anonymous';

    if (kvUrl && kvToken) {
      try {
        const { Redis } = await import('@upstash/redis');
        const redis = new Redis({ url: kvUrl, token: kvToken });

        const quotaKey = `dof:quota:${ip}`;
        const timeKey = `dof:last_seen:${ip}`;

        const [count, lastTime] = await Promise.all([
          redis.get<number>(quotaKey),
          redis.get<number>(timeKey)
        ]);

        const now = Date.now();

        // Circuit Breaker (Quota)
        if (count !== null && count >= MAX_QUOTA) {
          return NextResponse.json(
            { error: 'Session quota exceeded. Contact @Cyber_paisa for commercial access.' },
            { status: 429 }
          );
        }

        // Rate Limit
        if (lastTime !== null && (now - lastTime < RATE_LIMIT_MS)) {
          await redis.incr(`dof:attacks:ratelimit:${ip}`);
          return NextResponse.json(
            { error: 'Rate limited. Wait 15 seconds.' },
            { status: 429 }
          );
        }

        // Update state
        await Promise.all([
          redis.incr(quotaKey),
          redis.set(timeKey, now),
          redis.expire(quotaKey, 86400),
          redis.expire(timeKey, 86400)
        ]);
      } catch (redisErr) {
        console.error('Redis security layer error (fail-open):', redisErr);
        // Fail-open: continue without Redis protection if unavailable
      }
    }

    // 4. Build messages for upstream
    const messages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...history.slice(-10).map((m: { role: string; content: string }) => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content.slice(0, 2000)
      })),
      { role: 'user', content: message.slice(0, 2000) }
    ];

    // 5. Upstream Call
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

    // 6. Governance Check
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
