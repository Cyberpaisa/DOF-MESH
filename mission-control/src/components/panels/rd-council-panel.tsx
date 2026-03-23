'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'

// ── Types ──

interface CouncilMemo {
  id: string
  number: number
  title: string
  agent: string
  category: string
  tags: string[]
  status: 'needs_work' | 'approved' | 'in_progress' | 'rejected'
  confidence: number
  cost: number
  problem: string
  proposal: string
  discussion: DiscussionEntry[]
  createdAt: string
  sessionId: string
}

interface DiscussionEntry {
  agent: string
  message: string
  stance: 'support' | 'oppose' | 'neutral' | 'question'
  ts: string
}

interface CouncilSession {
  id: string
  startedAt: string
  endedAt: string | null
  status: 'running' | 'completed' | 'scheduled'
  memos: CouncilMemo[]
  totalCost: number
  participants: string[]
  proposer: string
}

interface CouncilStats {
  totalMemos: number
  totalCost: number
  lastSession: string | null
  schedule: string
  nextSession: string | null
}

// ── Council Agent Roster (5 agents that rotate as proposer) ──

const COUNCIL_AGENTS = [
  { id: 'architect-enigma', name: 'Architect Enigma', emoji: '🏗️', color: '#8b5cf6', role: 'System Architecture' },
  { id: 'product-overlord', name: 'Product Overlord', emoji: '📋', color: '#f59e0b', role: 'Product Strategy' },
  { id: 'sentinel-shield', name: 'Sentinel Shield', emoji: '🔒', color: '#dc2626', role: 'Trust & Safety' },
  { id: 'biz-dominator', name: 'Biz Dominator', emoji: '💼', color: '#10b981', role: 'Business Strategy' },
  { id: 'ralph-code', name: 'Ralph Code', emoji: '👨‍💻', color: '#3b82f6', role: 'Core Engineering' },
]

const CATEGORY_COLORS: Record<string, string> = {
  'trust and safety': '#dc2626',
  'product strategy': '#f59e0b',
  'architecture': '#8b5cf6',
  'revenue': '#10b981',
  'engineering': '#3b82f6',
  'growth': '#22c55e',
  'security': '#ef4444',
  'blockchain': '#14b8a6',
  'ai/ml': '#a855f7',
  'devops': '#f97316',
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  needs_work: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'NEEDS WORK' },
  approved: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'APPROVED' },
  in_progress: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'IN PROGRESS' },
  rejected: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'REJECTED' },
}

// ── Sample Data (will be replaced by API) ──

const SAMPLE_MEMOS: CouncilMemo[] = [
  {
    id: 'memo-1',
    number: 1,
    title: 'Implement ClawRouter fallback chain monitoring dashboard',
    agent: 'architect-enigma',
    category: 'architecture',
    tags: ['ClawRouter', 'Observability', 'Dashboard', 'Provider resilience'],
    status: 'approved',
    confidence: 92,
    cost: 0.04,
    problem: 'ClawRouter routes through 44+ models with 8-level fallback, but we have zero visibility into which models are being selected, failure rates per provider, and cost per request. When nvidia/gpt-oss-120b goes down, we wont know until agents stop responding.',
    proposal: 'Add a ClawRouter Monitor tab to Mission Control showing: real-time model selection (which model serving each request), provider health (success/fail rates), cost tracking per agent, and fallback chain visualization. Pull data from ClawRouter usage logs at ~/.openclaw/blockrun/logs/usage-YYYY-MM-DD.jsonl.',
    discussion: [
      { agent: 'ralph-code', message: 'The usage JSONL files already contain model, tier, cost, savings, and latency per request. I can build the API route in 2 hours.', stance: 'support', ts: '2026-03-22T09:01:00Z' },
      { agent: 'product-overlord', message: 'This directly improves our operational visibility. Should be Phase 1 priority alongside the R&D Council itself.', stance: 'support', ts: '2026-03-22T09:02:00Z' },
      { agent: 'sentinel-shield', message: 'Agree, but ensure we dont expose wallet private keys or transaction signatures in the dashboard. Redact sensitive x402 payment data.', stance: 'support', ts: '2026-03-22T09:03:00Z' },
      { agent: 'biz-dominator', message: 'Cost tracking is critical. With 14 agents potentially making hundreds of requests/day, we need budget alerts. Add a daily spend cap configurable per agent.', stance: 'support', ts: '2026-03-22T09:04:00Z' },
    ],
    createdAt: '2026-03-22T09:00:00Z',
    sessionId: 'session-1',
  },
  {
    id: 'memo-2',
    number: 2,
    title: 'Deploy Hyperspace PoI node for agent experiment sharing',
    agent: 'blockchain-wizard',
    category: 'blockchain',
    tags: ['Hyperspace', 'Proof-of-Intelligence', 'ResearchDAG', 'Agent economy'],
    status: 'needs_work',
    confidence: 71,
    cost: 0.08,
    problem: 'Our agents run experiments (Z3 proofs, governance checks, benchmark runs) but the results stay local. Hyperspace PoI network lets agents share experiments via ResearchDAG and earn tokens when others adopt their work. 237 agents on the network have run 14,832 experiments across 5 domains with zero human intervention.',
    proposal: 'Install Hyperspace CLI (curl -sSL https://download.hyper.space/api/install | bash), run a miner node, and connect our DOF agents experiment outputs to the ResearchDAG. Our Z3 proof results and governance benchmark data could propagate to the network and earn adoption rewards.',
    discussion: [
      { agent: 'architect-enigma', message: 'The ResearchDAG concept aligns perfectly with our JSONL trace system. Each RunTrace could become an experiment commit in the DAG.', stance: 'support', ts: '2026-03-22T09:11:00Z' },
      { agent: 'sentinel-shield', message: 'Testnet only. Do NOT connect production wallets or expose API keys to an unaudited blockchain. The paper literally says "it has bugs". Run isolated.', stance: 'oppose', ts: '2026-03-22T09:12:00Z' },
      { agent: 'product-overlord', message: 'Interesting for visibility but not revenue-generating yet. Deprioritize behind ClawRouter monitoring and R&D Council scheduling.', stance: 'neutral', ts: '2026-03-22T09:13:00Z' },
      { agent: 'ralph-code', message: 'The Autoswarm feature is wild: "hyperspace swarm new optimize CSS themes" and the network spins up distributed agents to solve it. Could we submit DOF governance optimization as a swarm task?', stance: 'question', ts: '2026-03-22T09:14:00Z' },
      { agent: 'biz-dominator', message: 'The Autoquant results are impressive (Sharpe 1.32, 3x return) but they also proved that parsimony wins — which validates our DOF principle of minimal governance rules over complex ones.', stance: 'support', ts: '2026-03-22T09:15:00Z' },
    ],
    createdAt: '2026-03-22T09:10:00Z',
    sessionId: 'session-1',
  },
  {
    id: 'memo-3',
    number: 3,
    title: 'Integrate DeerFlow context compression into DOF agent pipeline',
    agent: 'product-overlord',
    category: 'ai/ml',
    tags: ['DeerFlow', 'Context compression', 'Summarization', 'Token optimization'],
    status: 'in_progress',
    confidence: 85,
    cost: 0.03,
    problem: 'Our 14 agents using ClawRouter free tier (nvidia/gpt-oss-120b, 125K context) will hit context limits on complex tasks. DeerFlow SummarizationMiddleware compresses context when approaching token limits with configurable triggers (token count, message count, or fraction of max).',
    proposal: 'Extract DeerFlows 3 key patterns: (1) SummarizationMiddleware with trigger/keep policies, (2) Progressive skill loading — only inject skills when task needs them, (3) Deferred tool loading — list MCP tools by name, load on demand. Implement as OpenClaw middleware or DOF core module.',
    discussion: [
      { agent: 'architect-enigma', message: 'Pattern 1 (summarization) is highest value. Our agents SOUL.md files alone consume 2-3K tokens. With system prompt + tools + skills, we are at 8-10K before the first user message.', stance: 'support', ts: '2026-03-22T09:21:00Z' },
      { agent: 'ralph-code', message: 'I can implement a lightweight version: when total context exceeds 80% of model max, summarize all messages except the last 5 into a single context block. No LangChain dependency needed.', stance: 'support', ts: '2026-03-22T09:22:00Z' },
      { agent: 'sentinel-shield', message: 'Ensure summarization preserves governance context. CONSTITUTION rules must NEVER be summarized away.', stance: 'support', ts: '2026-03-22T09:23:00Z' },
    ],
    createdAt: '2026-03-22T09:20:00Z',
    sessionId: 'session-1',
  },
]

const SAMPLE_STATS: CouncilStats = {
  totalMemos: 3,
  totalCost: 0.15,
  lastSession: '2026-03-22T09:00:00Z',
  schedule: '9 AM + 5 PM',
  nextSession: '2026-03-22T17:00:00Z',
}

// ── Sub-tabs ──

type CouncilTab = 'council' | 'trends' | 'opportunities'

// ── Component ──

export function RDCouncilPanel() {
  const [activeTab, setActiveTab] = useState<CouncilTab>('council')
  const [memos, setMemos] = useState<CouncilMemo[]>(SAMPLE_MEMOS)
  const [stats, setStats] = useState<CouncilStats>(SAMPLE_STATS)
  const [expandedMemo, setExpandedMemo] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const triggerSession = useCallback(async () => {
    setIsRunning(true)
    // TODO: POST /api/council/session to trigger a new council session
    setTimeout(() => setIsRunning(false), 3000)
  }, [])

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' }) +
      ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  }

  const getAgent = (id: string) => COUNCIL_AGENTS.find(a => a.id === id) || { id, name: id, emoji: '🤖', color: '#9ca3af', role: 'Agent' }

  return (
    <div className="h-full flex flex-col bg-background text-foreground">
      {/* ── Header ── */}
      <div className="px-6 pt-6 pb-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <span className="text-amber-400">⚡</span> DOF Research Lab
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Autonomous Research & Development · ClawRouter Free Tier
            </p>
          </div>
          <Button
            onClick={triggerSession}
            disabled={isRunning}
            className="bg-violet-600 hover:bg-violet-700 text-white"
          >
            {isRunning ? '⏳ Running...' : '🔄 Refresh'}
          </Button>
        </div>

        {/* ── Sub-tabs ── */}
        <div className="flex gap-6 border-b border-border -mb-4">
          {[
            { id: 'trends' as CouncilTab, label: 'TREND RADAR', status: 'stopped' },
            { id: 'opportunities' as CouncilTab, label: 'OPPORTUNITY', status: 'stopped' },
            { id: 'council' as CouncilTab, label: 'R&D COUNCIL', count: memos.length },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 px-1 text-sm font-semibold tracking-wider transition-colors relative flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'text-foreground border-b-2 border-violet-500'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.id === 'council' && <span>🔬</span>}
              {tab.label}
              {'status' in tab && tab.status === 'stopped' && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-bold">STOPPED</span>
              )}
              {'count' in tab && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/30 text-violet-300 font-bold">{tab.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Stats Bar ── */}
      {activeTab === 'council' && (
        <div className="grid grid-cols-4 gap-4 px-6 py-4 border-b border-border">
          <div className="p-3 rounded-lg bg-card border border-border">
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider">Total Memos</div>
            <div className="text-2xl font-bold mt-1">{stats.totalMemos}</div>
          </div>
          <div className="p-3 rounded-lg bg-card border border-border">
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider">Council Cost</div>
            <div className="text-2xl font-bold mt-1 text-green-400">${stats.totalCost.toFixed(2)}</div>
          </div>
          <div className="p-3 rounded-lg bg-card border border-border">
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider">Last Session</div>
            <div className="text-sm font-medium mt-1">{stats.lastSession ? formatDate(stats.lastSession) : 'Never'}</div>
          </div>
          <div className="p-3 rounded-lg bg-card border border-border">
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider">Schedule</div>
            <div className="text-sm font-medium mt-1 text-amber-400">{stats.schedule}</div>
            <div className="text-[11px] text-muted-foreground">daily on ClawRouter</div>
          </div>
        </div>
      )}

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {activeTab === 'council' && memos.map(memo => {
          const agent = getAgent(memo.agent)
          const statusStyle = STATUS_STYLES[memo.status] || STATUS_STYLES.needs_work
          const isExpanded = expandedMemo === memo.id
          const catColor = CATEGORY_COLORS[memo.category.toLowerCase()] || '#6b7280'

          return (
            <div
              key={memo.id}
              className="rounded-lg border border-border bg-card overflow-hidden cursor-pointer hover:border-violet-500/50 transition-colors"
              onClick={() => setExpandedMemo(isExpanded ? null : memo.id)}
            >
              {/* Memo Header */}
              <div className="p-4">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <span className="font-mono">MEMO #{memo.number}</span>
                  <span>·</span>
                  <span
                    className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"
                    style={{ backgroundColor: agent.color + '30', color: agent.color }}
                  >
                    {agent.emoji} {agent.name.split(' ').pop()}
                  </span>
                  <span>·</span>
                  <span className="uppercase" style={{ color: catColor }}>{memo.category}</span>
                  <span>·</span>
                  <span>{new Date(memo.createdAt).toLocaleDateString()}</span>
                </div>

                <h3 className="text-base font-semibold leading-snug mb-2">{memo.title}</h3>

                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${statusStyle.bg} ${statusStyle.text}`}>
                    {statusStyle.label}
                  </span>
                  {memo.tags.map(tag => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Medium — feasible in about a week</span>
                  <span>·</span>
                  <span>Confidence: {memo.confidence}%</span>
                  <span>${memo.cost.toFixed(2)}</span>
                </div>
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-border">
                  {/* Problem */}
                  <div className="p-4">
                    <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">PROBLEM</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed font-mono">
                      {memo.problem}
                    </p>
                  </div>

                  {/* Proposal */}
                  <div className="p-4 border-t border-border">
                    <h4 className="text-xs font-bold text-green-400 uppercase tracking-wider mb-2">PROPOSAL</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed font-mono">
                      {memo.proposal}
                    </p>
                  </div>

                  {/* Discussion */}
                  <div className="p-4 border-t border-border">
                    <h4 className="text-xs font-bold text-violet-400 uppercase tracking-wider mb-3">
                      DISCUSSION ({memo.discussion.length} responses)
                    </h4>
                    <div className="space-y-3">
                      {memo.discussion.map((entry, i) => {
                        const discussAgent = getAgent(entry.agent)
                        const stanceIcon = entry.stance === 'support' ? '👍' : entry.stance === 'oppose' ? '👎' : entry.stance === 'question' ? '❓' : '➖'
                        const stanceColor = entry.stance === 'support' ? 'text-green-400' : entry.stance === 'oppose' ? 'text-red-400' : entry.stance === 'question' ? 'text-amber-400' : 'text-muted-foreground'
                        return (
                          <div key={i} className="flex gap-3">
                            <div
                              className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
                              style={{ backgroundColor: discussAgent.color + '30' }}
                            >
                              {discussAgent.emoji}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                <span className="text-xs font-semibold" style={{ color: discussAgent.color }}>
                                  {discussAgent.name}
                                </span>
                                <span className={`text-xs ${stanceColor}`}>{stanceIcon}</span>
                              </div>
                              <p className="text-sm text-muted-foreground leading-relaxed">{entry.message}</p>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {activeTab === 'trends' && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-4xl mb-3">📡</div>
              <h3 className="text-lg font-semibold mb-1">Trend Radar</h3>
              <p className="text-sm text-muted-foreground">Agentes monitoreando tendencias del ecosistema</p>
              <p className="text-xs text-red-400 mt-2">STOPPED — Activate via cron schedule</p>
            </div>
          </div>
        )}

        {activeTab === 'opportunities' && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-4xl mb-3">💡</div>
              <h3 className="text-lg font-semibold mb-1">Opportunity Scanner</h3>
              <p className="text-sm text-muted-foreground">Agentes identificando oportunidades de negocio</p>
              <p className="text-xs text-red-400 mt-2">STOPPED — Activate via cron schedule</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="px-6 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>5 council agents</span>
          <span>·</span>
          <span>ClawRouter free tier</span>
          <span>·</span>
          <span>nvidia/gpt-oss-120b</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span>Council Active</span>
        </div>
      </div>
    </div>
  )
}

export default RDCouncilPanel
