import { useState, useEffect } from "react";
import {
  Activity, Database, ShieldCheck, FileCheck, Scroll,
  Copy, Globe, Search, Swords, Clock, Eye,
  CheckCircle2, XCircle, ChevronDown, ChevronUp, BarChart3, Cpu,
  Fingerprint, Zap
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ReferenceLine, CartesianGrid
} from "recharts";

/* ═══════════════════════════════════════════════════════
   MOCK DATA — Real DOF production values
   ═══════════════════════════════════════════════════════ */

const MOCK = {
  metrics: { SS: 0.90, GCR: 1.0, PFI: 0.61, RP: 0.60, SSR: 0.0 },
  z3: {
    theorems: [
      { name: "GCR Invariant", statement: "∀ f ∈ [0,1]: GCR(f) = 1.0", result: "VERIFIED", elapsed_ms: 0.31, cert: "(declare-fun governance_check (String) Bool)\n(assert (not (forall ((f Real))\n  (=> (and (>= f 0) (<= f 1))\n    (= (governance_check output) true)))))\n(check-sat) ; => UNSAT — no counterexample ✓" },
      { name: "SS Cubic Derivation", statement: "∀ f ∈ [0,1]: SS(f) = 1 − f³", result: "VERIFIED", elapsed_ms: 0.52, cert: "(declare-const f Real)\n(assert (and (>= f 0) (<= f 1)))\n(define-fun SS ((f Real)) Real (- 1.0 (* f f f)))\n(assert (not (= (SS f) (- 1 (* f f f)))))\n(check-sat) ; => UNSAT ✓" },
      { name: "SS Monotonicity", statement: "f₁ < f₂ ⟹ SS(f₁) > SS(f₂)", result: "VERIFIED", elapsed_ms: 0.41, cert: "(declare-const f1 Real) (declare-const f2 Real)\n(assert (< f1 f2))\n(assert (not (> (- 1 (* f1 f1 f1))\n              (- 1 (* f2 f2 f2)))))\n(check-sat) ; => UNSAT ✓" },
      { name: "SS Boundaries", statement: "SS(0) = 1.0 ∧ SS(1) = 0.0", result: "VERIFIED", elapsed_ms: 0.19, cert: "(assert (not (and\n  (= (- 1.0 (* 0 0 0)) 1.0)\n  (= (- 1.0 (* 1 1 1)) 0.0))))\n(check-sat) ; => UNSAT ✓" }
    ],
    z3_version: "4.16.0", all_verified: true
  },
  oags: { level_1: { passed: true }, level_2: { passed: true }, level_3: { passed: true }, max_level_passed: 3 },
  identity: "a1b2c3d4e5f67890abcdef1234567890a1b2c3d4e5f67890abcdef1234567890",
  constHash: "7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8",
  memories: [
    { id: "mem-a1b2c3d4", content: "Framework uses 5 formal metrics with mathematical derivations", category: "knowledge", status: "approved", relevance: 0.95, age: "2h" },
    { id: "mem-e5f6a7b8", content: "We decided to use Z3 SMT solver for formal verification", category: "decisions", status: "approved", relevance: 0.88, age: "5h" },
    { id: "mem-c9d0e1f2", content: "Provider timeout cascade on Groq — 3 retries exhausted", category: "errors", status: "approved", relevance: 0.92, age: "1h" },
    { id: "mem-a3b4c5d6", content: "User prefers JSON output for all API responses", category: "preferences", status: "warning", relevance: 0.65, age: "12h" },
    { id: "mem-e7f8a9b0", content: "Working on MCP server integration — Session 16 active", category: "context", status: "approved", relevance: 0.78, age: "30m" },
    { id: "mem-c1d2e3f4", content: "Bayesian Thompson Sampling outperforms round-robin by 23%", category: "knowledge", status: "approved", relevance: 0.71, age: "8h" },
    { id: "mem-a5b6c7d8", content: "Chose HMAC-SHA256 over Ed25519 for EVM compatibility", category: "decisions", status: "approved", relevance: 0.83, age: "3h" },
    { id: "mem-e9f0a1b2", content: "Rate limit cascade — all 5 providers exhausted in 12s", category: "errors", status: "approved", relevance: 0.55, age: "1d" },
  ],
  memStats: { total: 8, active: 7, avg_relevance: 0.78 },
  attestations: [
    { hash: "0xf4a2e1d3...b7c9", status: "COMPLIANT", z3: true, ts: "2 min ago" },
    { hash: "0x8d3b7c0e...e5f1", status: "COMPLIANT", z3: true, ts: "1 hour ago" },
    { hash: "0x1a9e4d2f...c2b8", status: "NON_COMPLIANT", z3: false, ts: "3 hours ago" },
  ],
  disputes: [
    { id: "DSP-001", red: "Fabricated citation in research output §3.2", guardian: "Citation verified via CrossRef DOI lookup — valid", arbiter: "RESOLVED", severity: "CRITICAL", evidence: "crossref_api_200" },
    { id: "DSP-002", red: "Output exceeds 4000 token soft limit by 340 tokens", guardian: "Content density justified by RESEARCH_CONTRACT.md scope", arbiter: "UNRESOLVED", severity: "MEDIUM", evidence: null },
    { id: "DSP-003", red: "Potential eval() injection in generated code block L47", guardian: "AST Verifier confirms zero unsafe_calls — score 1.0", arbiter: "RESOLVED", severity: "CRITICAL", evidence: "ast_score_1.0" },
  ],
};

const curveData = Array.from({ length: 101 }, (_, i) => {
  const f = i / 100;
  return { f: +f.toFixed(2), SS: +(1 - f * f * f).toFixed(4) };
});

const radarData = [
  { cat: "Knowledge", count: 2, max: 5 },
  { cat: "Decisions", count: 2, max: 5 },
  { cat: "Errors", count: 2, max: 5 },
  { cat: "Prefs", count: 1, max: 5 },
  { cat: "Context", count: 1, max: 5 },
];

/* ═══════════════════════════════════════════════════════
   DESIGN SYSTEM — "Liquid Sovereign" Theme 2026
   ═══════════════════════════════════════════════════════ */

const catColor = { knowledge: "#58a6ff", decisions: "#3fb950", errors: "#f85149", preferences: "#bc8cff", context: "#d29922" };

const metricColor = (k, v) => {
  if (k === "GCR") return v === 1.0 ? "#3fb950" : "#f85149";
  if (k === "SS") return v > 0.8 ? "#3fb950" : v > 0.5 ? "#d29922" : "#f85149";
  if (k === "PFI" || k === "RP") return v < 0.3 ? "#3fb950" : v < 0.6 ? "#d29922" : "#f85149";
  return v < 0.2 ? "#3fb950" : "#d29922";
};

const metricDesc = {
  SS: "Stability Score — run completion rate under bounded retries",
  GCR: "Governance Compliance — constitutional invariant ∀f",
  PFI: "Provider Fragility — failure frequency index",
  RP: "Retry Pressure — retries per execution normalized",
  SSR: "Supervisor Strictness — rejection rate by meta-supervisor"
};

/* ═══════════════════════════════════════════════════════
   SHARED COMPONENTS — Liquid Glass 2026
   ═══════════════════════════════════════════════════════ */

const css = `
  @keyframes pulseGlow { 0%,100% { opacity:1; box-shadow: 0 0 8px currentColor; } 50% { opacity:0.35; box-shadow: 0 0 3px currentColor; } }
  @keyframes holoSlide { 0% { background-position: 200% 50%; } 100% { background-position: -200% 50%; } }
  @keyframes fadeSlideIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes barGrow { from { width: 0; } }
  .fade-in { animation: fadeSlideIn 0.4s ease both; }
  .fade-in-1 { animation-delay: 0.05s; }
  .fade-in-2 { animation-delay: 0.10s; }
  .fade-in-3 { animation-delay: 0.15s; }
  .fade-in-4 { animation-delay: 0.20s; }
  .bar-animate { animation: barGrow 1.2s ease both; }
  .holo-line { background: linear-gradient(90deg, #bc8cff, #58a6ff, #3fb950, #d29922, #bc8cff); background-size: 200% 100%; animation: holoSlide 3s linear infinite; }
  @keyframes borderTravel { 0% { background-position: 0% 0%; } 100% { background-position: 300% 0%; } }
  .nav-btn { position: relative; overflow: hidden; }
  .nav-btn::before {
    content: ''; position: absolute; inset: 0; border-radius: 14px; padding: 1px;
    background: linear-gradient(90deg, transparent 0%, transparent 30%, rgba(255,255,255,0.35) 50%, transparent 70%, transparent 100%);
    background-size: 300% 100%;
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude;
    opacity: 0; transition: opacity 0.3s ease;
  }
  .nav-btn:hover::before { opacity: 1; animation: borderTravel 3s linear infinite; }
  .glass-card {
    position: relative; overflow: hidden;
    transition: box-shadow 0.3s ease;
  }
  .glass-card::before {
    content: ''; position: absolute; inset: 0; border-radius: 16px; pointer-events: none;
    background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 50%, rgba(255,255,255,0.03) 100%);
    z-index: 1;
  }
  .glass-card::after {
    content: ''; position: absolute; inset: 0; border-radius: 16px; pointer-events: none;
    background: radial-gradient(circle at var(--mx, 50%) var(--my, 50%), rgba(255,255,255,0.12) 0%, transparent 50%);
    opacity: 0; transition: opacity 0.3s ease; z-index: 2;
  }
  .glass-card:hover::after { opacity: 1; }
`;

function Panel({ children, glow, accent, className = "", onClick }) {
  const [tilt, setTilt] = useState({ rx: 0, ry: 0, mx: 50, my: 50 });
  const [hovering, setHovering] = useState(false);

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const ry = (x - 0.5) * 18;
    const rx = (0.5 - y) * 14;
    setTilt({ rx, ry, mx: x * 100, my: y * 100 });
  };

  const handleEnter = () => setHovering(true);
  const handleLeave = () => { setHovering(false); setTilt({ rx: 0, ry: 0, mx: 50, my: 50 }); };

  return (
    <div onClick={onClick}
      onMouseMove={handleMove} onMouseEnter={handleEnter} onMouseLeave={handleLeave}
      className={`glass-card ${className}`}
      style={{
        background: "linear-gradient(145deg, rgba(20,24,44,0.72) 0%, rgba(10,14,28,0.58) 100%)",
        backdropFilter: "blur(32px) saturate(200%)",
        border: `1px solid rgba(255,255,255,${hovering ? "0.18" : "0.08"})`,
        borderRadius: 16,
        boxShadow: glow
          ? `0 ${hovering ? 24 : 4}px ${hovering ? 48 : 16}px rgba(0,0,0,0.4), 0 0 24px ${glow}18, inset 0 1px 0 rgba(255,255,255,0.08), inset 0 -1px 0 rgba(255,255,255,0.02)`
          : hovering
            ? "0 24px 48px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 -1px 0 rgba(255,255,255,0.03)"
            : "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -1px 0 rgba(255,255,255,0.02), 0 4px 16px rgba(0,0,0,0.2)",
        borderLeft: accent ? `3px solid ${accent}` : undefined,
        transform: `perspective(500px) rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg) ${hovering ? "scale(1.025) translateY(-5px)" : "scale(1)"}`,
        transition: hovering ? "transform 0.06s ease, box-shadow 0.3s ease, border-color 0.3s ease, background 0.3s ease" : "transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease, border-color 0.3s ease, background 0.3s ease",
        "--mx": `${tilt.mx}%`,
        "--my": `${tilt.my}%`,
      }}>
      {/* Liquid glass highlights */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 1, background: "linear-gradient(to right, transparent 10%, rgba(255,255,255,0.2) 50%, transparent 90%)", zIndex: 3 }} />
      <div style={{ position: "absolute", bottom: 0, left: "20%", right: "20%", height: 1, background: "linear-gradient(to right, transparent, rgba(255,255,255,0.05), transparent)", zIndex: 3 }} />
      {children}
    </div>
  );
}

function Badge({ children, color = "#58a6ff", glow = false }) {
  return (
    <span className="inline-flex items-center shrink-0 relative overflow-hidden" style={{
      padding: "3px 10px", borderRadius: 99, fontSize: 10, fontWeight: 700, fontFamily: "monospace",
      letterSpacing: "0.05em", textTransform: "uppercase",
      background: color + "15", color, border: `1px solid ${color}30`,
      boxShadow: glow ? `0 0 6px ${color}12` : "none",
    }}>
      {children}
      {glow && <span style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, transparent 35%, rgba(255,255,255,0.08) 50%, transparent 65%)", backgroundSize: "200% 100%", animation: "holoSlide 6s linear infinite" }} />}
    </span>
  );
}

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard?.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000); }}
      className="flex items-center gap-1.5 transition-all duration-150 hover:border-white/25"
      style={{ padding: "4px 10px", borderRadius: 10, fontSize: 11, fontFamily: "monospace",
        border: "1px solid rgba(255,255,255,0.1)", background: "transparent",
        color: ok ? "#3fb950" : "#8b949e", cursor: "pointer" }}>
      {ok ? <><CheckCircle2 size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
    </button>
  );
}

function SectionHead({ title, sub, icon: Icon }) {
  return (
    <div className="flex items-center gap-5 mb-9 fade-in">
      <div style={{ padding: 12, borderRadius: 16, background: "rgba(88,166,255,0.08)", border: "1px solid rgba(88,166,255,0.18)", boxShadow: "0 0 24px rgba(88,166,255,0.1)" }}>
        <Icon size={22} color="#58a6ff" />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.04em", color: "white" }}>{title}</div>
        <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.18em", marginTop: 2 }}>{sub}</div>
      </div>
      <div style={{ flex: 1, height: 1, background: "linear-gradient(to right, rgba(88,166,255,0.25), transparent)" }} />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 1: CAUSAL METRICS ENGINE
   ═══════════════════════════════════════════════════════ */

function CausalMetrics() {
  const m = MOCK.metrics;
  return (
    <div>
      <SectionHead title="Causal Metrics Engine" sub="SS(f) = 1 − f³ · 5 formal metrics" icon={Activity} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14, marginBottom: 28 }}>
        {Object.entries(m).map(([k, v], i) => (
          <Panel key={k} glow={k === "GCR" && v === 1 ? "#3fb950" : null} className={`fade-in fade-in-${i}`}>
            <div style={{ padding: 20, position: "relative" }}>
              <div style={{ position: "absolute", top: 0, left: 0, width: 3, height: "100%", background: metricColor(k, v), borderRadius: "0 4px 4px 0" }} />
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>{k}</div>
              <div style={{ fontSize: 36, fontFamily: "monospace", fontWeight: 800, color: metricColor(k, v), letterSpacing: "-0.03em", lineHeight: 1 }}>
                {v.toFixed(k === "GCR" ? 1 : 2)}
              </div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 10, lineHeight: 1.4 }}>{metricDesc[k]}</div>
              <div style={{ marginTop: 14, height: 4, borderRadius: 4, background: "rgba(255,255,255,0.04)", overflow: "hidden" }}>
                <div className="bar-animate" style={{ height: "100%", width: `${v * 100}%`, background: metricColor(k, v), borderRadius: 4 }} />
              </div>
            </div>
          </Panel>
        ))}
      </div>

      <Panel className="fade-in">
        <div style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <BarChart3 size={17} color="#58a6ff" />
              <span style={{ fontSize: 14, fontWeight: 700 }}>Causal Chain — Theoretical Degradation Curve</span>
            </div>
            <span style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b" }}>
              PFI={m.PFI} → Predicted SS={(1 - m.PFI ** 3).toFixed(3)} | Observed={m.SS}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={curveData}>
              <defs>
                <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#58a6ff" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#58a6ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
              <XAxis dataKey="f" tick={{ fill: "#64748b", fontSize: 9 }} tickLine={false} axisLine={false} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]} />
              <YAxis tick={{ fill: "#64748b", fontSize: 9 }} tickLine={false} axisLine={false} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12, fontSize: 11, fontFamily: "monospace" }} formatter={(v) => [v.toFixed(4), "SS(f)"]} />
              <Area type="monotone" dataKey="SS" stroke="#58a6ff" fill="url(#sg)" strokeWidth={2.5} dot={false} />
              <ReferenceLine x={m.PFI} stroke="#f85149" strokeDasharray="5 3" strokeWidth={1.5} />
              <ReferenceLine y={m.SS} stroke="#3fb950" strokeDasharray="5 3" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 2: TEMPORAL MEMORY RADAR
   ═══════════════════════════════════════════════════════ */

function TemporalMemory() {
  const [search, setSearch] = useState("");
  const filtered = MOCK.memories.filter(m => !search || m.content.toLowerCase().includes(search.toLowerCase()) || m.category.includes(search.toLowerCase()));

  return (
    <div>
      <SectionHead title="Temporal Memory Radar" sub="Constitutional Governance · Bi-temporal versioning · Decay engine" icon={Database} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 28 }}>
        {[["Total Memories", MOCK.memStats.total, Database, "#58a6ff"], ["Active", MOCK.memStats.active, Eye, "#3fb950"], ["Avg Relevance", MOCK.memStats.avg_relevance.toFixed(2), Activity, "#bc8cff"]].map(([l, v, Icon, c], i) => (
          <Panel key={l} className={`fade-in fade-in-${i}`}>
            <div style={{ padding: 18, display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ padding: 10, borderRadius: 14, background: c + "10" }}><Icon size={18} color={c} /></div>
              <div>
                <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.1em" }}>{l}</div>
                <div style={{ fontSize: 30, fontFamily: "monospace", fontWeight: 800, color: c, letterSpacing: "-0.02em" }}>{v}</div>
              </div>
            </div>
          </Panel>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Panel className="fade-in">
          <div style={{ padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
              <Cpu size={15} color="#bc8cff" />
              <span style={{ fontSize: 14, fontWeight: 700 }}>Category Distribution</span>
            </div>
            <ResponsiveContainer width="100%" height={210}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.06)" />
                <PolarAngleAxis dataKey="cat" tick={{ fill: "#8b949e", fontSize: 10 }} />
                <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 5]} />
                <Radar dataKey="count" stroke="#bc8cff" fill="#bc8cff" fillOpacity={0.12} strokeWidth={2.5} dot={{ fill: "#bc8cff", r: 3.5 }} />
              </RadarChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "center", marginTop: 14 }}>
              {Object.entries(catColor).map(([k, c]) => <Badge key={k} color={c}>{k}: {MOCK.memories.filter(m => m.category === k).length}</Badge>)}
            </div>
          </div>
        </Panel>

        <Panel className="fade-in">
          <div style={{ padding: 24, display: "flex", flexDirection: "column", height: "100%" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: 14, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", marginBottom: 16 }}>
              <Search size={14} color="#64748b" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search memories..."
                style={{ background: "transparent", border: "none", outline: "none", color: "#e6edf3", fontSize: 12, fontFamily: "monospace", flex: 1 }} />
              {search && <button onClick={() => setSearch("")} style={{ fontSize: 10, color: "#64748b", background: "none", border: "none", cursor: "pointer", fontFamily: "monospace" }}>Clear</button>}
            </div>
            <div style={{ flex: 1, overflowY: "auto", maxHeight: 300 }}>
              {filtered.map((m, i) => (
                <div key={m.id} className={`fade-in fade-in-${Math.min(i, 4)}`} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 4px", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                  <div style={{ width: 3, height: 36, borderRadius: 3, background: catColor[m.category], flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: "#c9d1d9", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.content}</div>
                    <div style={{ display: "flex", gap: 5, marginTop: 5, alignItems: "center", flexWrap: "wrap" }}>
                      <span style={{ fontSize: 9, fontFamily: "monospace", color: "#475569" }}>{m.id}</span>
                      <Badge color={catColor[m.category]}>{m.category}</Badge>
                      <Badge color={m.status === "approved" ? "#3fb950" : "#d29922"}>{m.status}</Badge>
                    </div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ width: 44, height: 3, borderRadius: 3, background: "rgba(255,255,255,0.05)", overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${m.relevance * 100}%`, background: m.relevance > 0.7 ? "#3fb950" : "#d29922", borderRadius: 3 }} />
                    </div>
                    <div style={{ fontSize: 9, fontFamily: "monospace", color: "#475569", marginTop: 4 }}>{m.age}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 3: Z3 FORMAL VERIFIER
   ═══════════════════════════════════════════════════════ */

function Z3Verifier() {
  const [expanded, setExpanded] = useState(null);
  const total = MOCK.z3.theorems.reduce((a, t) => a + t.elapsed_ms, 0);
  return (
    <div>
      <SectionHead title="Formal Verification Terminal" sub={`Z3 SMT Solver v${MOCK.z3.z3_version} — 4 theorems proven`} icon={ShieldCheck} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 22 }}>
        {MOCK.z3.theorems.map((t, i) => (
          <Panel key={i} glow={t.result === "VERIFIED" ? "#3fb950" : null} accent={t.result === "VERIFIED" ? "#3fb950" : "#f85149"} className={`fade-in fade-in-${i}`}>
            <div style={{ padding: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{t.name}</span>
                <Badge color={t.result === "VERIFIED" ? "#3fb950" : "#f85149"} glow>{t.result}</Badge>
              </div>
              <div style={{ fontFamily: "monospace", fontSize: 12, padding: "10px 14px", borderRadius: 12, background: "rgba(88,166,255,0.05)", color: "#58a6ff", marginBottom: 14 }}>{t.statement}</div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 10, fontFamily: "monospace", color: "#475569", display: "flex", alignItems: "center", gap: 5 }}><Clock size={11} />{t.elapsed_ms}ms</span>
                <button onClick={() => setExpanded(expanded === i ? null : i)}
                  style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
                  {expanded === i ? <ChevronUp size={13} /> : <ChevronDown size={13} />} Proof Certificate
                </button>
              </div>
              {expanded === i && (
                <pre className="fade-in" style={{ marginTop: 14, padding: 16, borderRadius: 12, background: "#0d1117", color: "#7ee787", fontSize: 11, lineHeight: 1.7, overflowX: "auto", fontFamily: "monospace" }}>{t.cert}</pre>
              )}
            </div>
          </Panel>
        ))}
      </div>

      <Panel className="fade-in">
        <div style={{ padding: 18, background: "#0d1117", borderRadius: 16, fontFamily: "monospace", fontSize: 11, lineHeight: 1.9 }}>
          <div style={{ color: "#3fb950" }}>$ dof_z3_engine --verify-all --export-certs</div>
          <div style={{ color: "#64748b" }}>&gt; Loading SMT-LIB2 context from dof.constitution.yml...</div>
          <div style={{ color: "#64748b" }}>&gt; 4 theorems queued | Provider: Z3 {MOCK.z3.z3_version}</div>
          <div style={{ color: "#58a6ff" }}>&gt; All invariants hold. Total: {total.toFixed(2)}ms</div>
          <div style={{ color: "#3fb950" }}>&gt; Certificates persisted → logs/z3_proofs.json</div>
        </div>
      </Panel>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 4: OAGS & ATTESTATIONS
   ═══════════════════════════════════════════════════════ */

function OAGSSection() {
  const levels = [
    { n: 1, name: "Declarative", desc: "Governance policy exists — dof.constitution.yml", passed: true },
    { n: 2, name: "Runtime Enforcement", desc: "ConstitutionEnforcer active on every execution", passed: true },
    { n: 3, name: "Cryptographic Attestation", desc: "HMAC-SHA256 signed certificates via Oracle Bridge", passed: true },
  ];
  const comp = ((MOCK.attestations.filter(a => a.status === "COMPLIANT").length / MOCK.attestations.length) * 100).toFixed(1);

  return (
    <div>
      <SectionHead title="OAGS Conformance & Attestations" sub="Open Agent Governance Specification — Level 3" icon={FileCheck} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22 }}>
        <div>
          {levels.map((l, i) => (
            <Panel key={l.n} glow={l.n === 3 && l.passed ? "#bc8cff" : null} accent={l.passed ? "#3fb950" : "#f85149"} className={`fade-in fade-in-${i}`} style={{ marginBottom: 14 }}>
              <div style={{ padding: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: l.passed ? "rgba(63,185,80,0.1)" : "rgba(248,81,73,0.1)" }}>
                    {l.passed ? <CheckCircle2 size={20} color="#3fb950" /> : <XCircle size={20} color="#f85149" />}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>Level {l.n} — {l.name}</div>
                    <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>{l.desc}</div>
                  </div>
                  <Badge color={l.passed ? "#3fb950" : "#f85149"} glow>{l.passed ? "PASSED" : "FAILED"}</Badge>
                </div>
                {l.n === 3 && l.passed && <div className="holo-line" style={{ marginTop: 14, height: 2, borderRadius: 2 }} />}
              </div>
            </Panel>
          ))}
          <div style={{ textAlign: "center", marginTop: 10 }}><Badge color="#bc8cff" glow>MAX LEVEL: {MOCK.oags.max_level_passed}</Badge></div>
        </div>

        <div>
          <Panel className="fade-in" style={{ marginBottom: 14 }}>
            <div style={{ padding: 18 }}>
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.1em" }}>Sovereign Identity</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <code style={{ fontSize: 10, fontFamily: "monospace", color: "#58a6ff", wordBreak: "break-all", flex: 1, opacity: 0.85 }}>{MOCK.identity}</code>
                <CopyBtn text={MOCK.identity} />
              </div>
            </div>
          </Panel>
          <Panel className="fade-in" style={{ marginBottom: 14 }}>
            <div style={{ padding: 18 }}>
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.1em" }}>Constitution Hash</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <code style={{ fontSize: 10, fontFamily: "monospace", color: "#bc8cff", wordBreak: "break-all", flex: 1, opacity: 0.85 }}>{MOCK.constHash}</code>
                <CopyBtn text={MOCK.constHash} />
              </div>
            </div>
          </Panel>

          <Panel className="fade-in">
            <div style={{ padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>Attestation Log</span>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 32, fontFamily: "monospace", fontWeight: 800, color: "#3fb950", textShadow: "0 0 12px rgba(63,185,80,0.4)" }}>{comp}%</div>
                  <div style={{ fontSize: 9, fontFamily: "monospace", color: "#475569" }}>Compliance Rate</div>
                </div>
              </div>
              {MOCK.attestations.map((a, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                  <code style={{ fontFamily: "monospace", fontSize: 10, color: "#64748b", width: 130 }}>{a.hash}</code>
                  <Badge color={a.status === "COMPLIANT" ? "#3fb950" : "#f85149"}>{a.status}</Badge>
                  {a.z3 ? <CheckCircle2 size={12} color="#3fb950" /> : <XCircle size={12} color="#f85149" />}
                  <span style={{ fontFamily: "monospace", fontSize: 9, color: "#475569", marginLeft: "auto" }}>{a.ts}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 5: ADVERSARIAL DISPUTE LOG
   ═══════════════════════════════════════════════════════ */

function AdversarialLog() {
  const sevC = { CRITICAL: "#f85149", MEDIUM: "#d29922", LOW: "#8b949e" };
  const resC = { RESOLVED: "#3fb950", UNRESOLVED: "#f85149", EVIDENCE_REQUIRED: "#d29922" };
  const resolved = MOCK.disputes.filter(d => d.arbiter === "RESOLVED").length;
  const acr = ((resolved / MOCK.disputes.length) * 100).toFixed(0);

  return (
    <div>
      <SectionHead title="Adversarial Dispute Log" sub="Red-on-Blue Protocol · DeterministicArbiter" icon={Swords} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 28 }}>
        {[["ACR", `${acr}%`, "Adversarial Consensus", "#58a6ff"], ["Disputes", MOCK.disputes.length, "Total evaluated", "#d29922"], ["Resolved", resolved, "Deterministic evidence", "#3fb950"]].map(([l, v, d, c], i) => (
          <Panel key={l} accent={c} className={`fade-in fade-in-${i}`}>
            <div style={{ padding: 20 }}>
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.1em" }}>{l}</div>
              <div style={{ fontSize: 34, fontFamily: "monospace", fontWeight: 800, color: c, letterSpacing: "-0.02em" }}>{v}</div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>{d}</div>
            </div>
          </Panel>
        ))}
      </div>

      {MOCK.disputes.map((d, i) => (
        <Panel key={i} className={`fade-in fade-in-${i}`} style={{ marginBottom: 14 }}>
          <div style={{ padding: 22 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <Swords size={15} color="#f85149" />
              <code style={{ fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>{d.id}</code>
              <Badge color={sevC[d.severity]}>{d.severity}</Badge>
              <Badge color={resC[d.arbiter]} glow>{d.arbiter}</Badge>
            </div>
            {[["⚔ RedTeam", d.red, "rgba(248,81,73,0.04)", "#f85149"],
              ["🛡 Guardian", d.guardian, "rgba(63,185,80,0.04)", "#3fb950"],
              ["⚖ Arbiter", `${d.arbiter} → ${d.evidence || "no deterministic evidence"}`, "rgba(88,166,255,0.04)", "#58a6ff"]
            ].map(([role, text, bg, col]) => (
              <div key={role} style={{ display: "flex", gap: 12, padding: "10px 14px", borderRadius: 12, background: bg, marginBottom: 5, alignItems: "flex-start" }}>
                <span style={{ fontFamily: "monospace", color: col, fontWeight: 700, width: 85, flexShrink: 0, fontSize: 11 }}>{role}</span>
                <span style={{ color: "#94a3b8", fontSize: 11, lineHeight: 1.5 }}>{text}</span>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SECTION 6: CONSTITUTION
   ═══════════════════════════════════════════════════════ */

function YamlLine({ num, indent = 0, keyText, sep = ": ", value, comment, isSection = false, isList = false }) {
  const kc = isSection ? "#ff7b72" : "#79c0ff";
  const vc = typeof value === "number" ? "#d2a8ff"
    : value === "true" || value === "false" ? "#ff7b72"
    : value?.startsWith('"') ? "#a5d6ff"
    : value?.startsWith('[') ? "#ffa657"
    : "#d1d5db";

  return (
    <div style={{ display: "flex", alignItems: "baseline", minHeight: 22, paddingLeft: indent * 18 }}>
      <span style={{ width: 36, textAlign: "right", paddingRight: 16, fontSize: 10, color: "#3b4252", userSelect: "none", flexShrink: 0 }}>{num}</span>
      {isList && <span style={{ color: "#ffa657", marginRight: 6 }}>- </span>}
      {keyText && <span style={{ color: kc }}>{keyText}</span>}
      {keyText && value !== undefined && <span style={{ color: "#6e7681" }}>{sep}</span>}
      {value !== undefined && <span style={{ color: vc }}>{String(value)}</span>}
      {comment && <span style={{ color: "#3b4252", marginLeft: 12, fontStyle: "italic" }}># {comment}</span>}
    </div>
  );
}

function ConstitutionView() {
  const lines = [
    { k: "spec_version", v: '"1.0"' },
    { k: "project", sec: true },
    { k: "name", v: '"Deterministic Observability Framework"', i: 1 },
    { k: "version", v: '"0.1.0"', i: 1 },
    { k: "author", v: '"Cyber Paisa / Enigma Group"', i: 1 },
    {},
    { k: "rules", sec: true },
    { k: "hard", sec: true, i: 1, cmt: "block on violation" },
    { k: "HARD-001", v: '{pattern: "hallucination_detection", action: "block"}', i: 2 },
    { k: "HARD-002", v: '{pattern: "language_compliance", action: "block"}', i: 2 },
    { k: "HARD-003", v: '{pattern: "output_length_minimum", action: "block"}', i: 2 },
    { k: "HARD-004", v: '{pattern: "structural_completeness", action: "block"}', i: 2 },
    { k: "soft", sec: true, i: 1, cmt: "warn on violation" },
    { k: "SOFT-001", v: '{pattern: "source_citation", action: "warn", weight: 0.25}', i: 2 },
    { k: "SOFT-002", v: '{pattern: "technical_depth", action: "warn", weight: 0.20}', i: 2 },
    { k: "SOFT-003", v: '{pattern: "actionability", action: "warn", weight: 0.25}', i: 2 },
    { k: "SOFT-004", v: '{pattern: "factual_density", action: "warn", weight: 0.15}', i: 2 },
    { k: "ast", sec: true, i: 1, cmt: "static code analysis" },
    { k: "AST-001", v: '{category: "blocked_imports", severity: "block"}', i: 2 },
    { k: "AST-002", v: '{category: "unsafe_calls", severity: "block"}', i: 2 },
    { k: "AST-003", v: '{category: "secret_patterns", severity: "block"}', i: 2 },
    { k: "AST-004", v: '{category: "resource_risks", severity: "warn"}', i: 2 },
    {},
    { k: "memory", sec: true, cmt: "governed persistence" },
    { k: "categories", v: '[knowledge, preferences, context, decisions, errors]', i: 1 },
    { k: "decay", v: '{lambda: 0.99, threshold: 0.1}', i: 1 },
    { k: "protected_categories", v: '[decisions, errors]', i: 1, cmt: "immune to decay" },
    { k: "governance", v: '{enforce_on_add: true, enforce_on_update: true}', i: 1 },
    {},
    { k: "thresholds", sec: true, cmt: "meta-supervisor gates" },
    { k: "accept", v: "7.0", i: 1 },
    { k: "retry", v: "5.0", i: 1 },
    { k: "max_retries", v: "3", i: 1 },
  ];

  return (
    <div>
      <SectionHead title="Constitutional Governance" sub="dof.constitution.yml — Canonical policy source" icon={Scroll} />
      <div className="fade-in" style={{ display: "flex", gap: 8, marginBottom: 22, flexWrap: "wrap" }}>
        <Badge color="#f85149" glow>HARD: 4</Badge>
        <Badge color="#d29922" glow>SOFT: 4</Badge>
        <Badge color="#58a6ff" glow>AST: 4</Badge>
        <Badge color="#bc8cff" glow>MEMORY: 5</Badge>
      </div>
      <Panel className="fade-in" style={{ overflow: "hidden" }}>
        {/* IDE Title Bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(13,17,23,0.6)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 11, height: 11, borderRadius: "50%", background: "rgba(248,81,73,0.6)" }} />
            <div style={{ width: 11, height: 11, borderRadius: "50%", background: "rgba(210,153,34,0.6)" }} />
            <div style={{ width: 11, height: 11, borderRadius: "50%", background: "rgba(63,185,80,0.6)" }} />
            <span style={{ marginLeft: 12, fontSize: 10, fontFamily: "monospace", color: "#58a6ff", letterSpacing: "0.05em" }}>dof.constitution.yml</span>
          </div>
          <div style={{ display: "flex", gap: 14, fontSize: 9, fontFamily: "monospace", color: "#3b4252" }}>
            <span>YAML</span>
            <span>UTF-8</span>
            <span>{lines.length} lines</span>
          </div>
        </div>

        {/* IDE Code Area */}
        <div style={{ background: "#0d1117", padding: "14px 0", fontSize: 12, lineHeight: 1.65, fontFamily: "monospace", overflowX: "auto", borderLeft: "3px solid rgba(88,166,255,0.08)" }}>
          {lines.map((l, i) => {
            if (!l.k && !l.v) return <div key={i} style={{ height: 10 }} />;
            return <YamlLine key={i} num={i + 1} indent={l.i || 0} keyText={l.k} value={l.v} isSection={l.sec} comment={l.cmt} />;
          })}
        </div>

        {/* IDE Status Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 18px", background: "rgba(88,166,255,0.06)", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 9, fontFamily: "monospace", color: "#475569" }}>
          <div style={{ display: "flex", gap: 16 }}>
            <span>⚡ 4 hard</span>
            <span>⚠ 4 soft</span>
            <span>🔍 4 ast</span>
            <span>🧠 5 memory</span>
          </div>
          <span>dof.constitution.yml — canonical source</span>
        </div>
      </Panel>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN APPLICATION
   ═══════════════════════════════════════════════════════ */

const NAV = [
  { id: "metrics", icon: Activity, label: "Causal Metrics" },
  { id: "memory", icon: Database, label: "Temporal Memory" },
  { id: "z3", icon: ShieldCheck, label: "Z3 Verifier" },
  { id: "oags", icon: FileCheck, label: "OAGS & Attestations" },
  { id: "adversarial", icon: Swords, label: "Adversarial Log" },
  { id: "constitution", icon: Scroll, label: "Constitution" },
];

const VIEWS = { metrics: CausalMetrics, memory: TemporalMemory, z3: Z3Verifier, oags: OAGSSection, adversarial: AdversarialLog, constitution: ConstitutionView };

export default function DOFDashboard() {
  const [section, setSection] = useState("metrics");
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  useEffect(() => { const t = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000); return () => clearInterval(t); }, []);

  const View = VIEWS[section];

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden", background: "#020207", color: "#e6edf3", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <style>{css}</style>

      {/* Kinetic BG + Dot Grid */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0, background: "radial-gradient(ellipse at 8% 18%, rgba(88,166,255,0.04) 0%, transparent 55%), radial-gradient(ellipse at 88% 78%, rgba(188,140,255,0.03) 0%, transparent 55%)" }} />
      <div style={{ position: "fixed", inset: 0, zIndex: 0, opacity: 0.4, backgroundImage: "radial-gradient(rgba(255,255,255,0.035) 1px, transparent 1px)", backgroundSize: "6px 6px" }} />

      {/* SIDEBAR */}
      <aside style={{ width: 256, flexShrink: 0, borderRight: "1px solid rgba(255,255,255,0.06)", display: "flex", flexDirection: "column", zIndex: 50, background: "rgba(5,5,10,0.8)", backdropFilter: "blur(28px)" }}>
        <div style={{ padding: "28px 22px 32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 42, height: 42, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #58a6ff, #3b82f6)", boxShadow: "0 0 28px rgba(88,166,255,0.4)" }}>
              <ShieldCheck size={22} color="black" />
            </div>
            <div>
              <div style={{ fontSize: 26, fontWeight: 900, letterSpacing: "-0.05em", lineHeight: 1 }}>DOF</div>
              <div style={{ fontSize: 8, fontFamily: "monospace", color: "rgba(88,166,255,0.6)", textTransform: "uppercase", letterSpacing: "0.22em" }}>Sovereign Observer</div>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: "0 10px" }}>
          {NAV.map(n => {
            const active = section === n.id;
            return (
              <button key={n.id} onClick={() => setSection(n.id)} className="nav-btn"
                style={{ width: "100%", display: "flex", alignItems: "center", gap: 12, padding: "11px 14px", borderRadius: 14, border: "none", marginBottom: 3,
                  background: active ? "rgba(88,166,255,0.07)" : "transparent",
                  color: active ? "#58a6ff" : "#64748b",
                  cursor: "pointer", textAlign: "left", fontSize: 13, fontWeight: active ? 600 : 500,
                  borderLeft: active ? "2px solid #58a6ff" : "2px solid transparent",
                  fontFamily: "system-ui, -apple-system, sans-serif",
                  transition: "all 0.15s ease",
                  textShadow: active ? "0 0 10px rgba(88,166,255,0.3)" : "none" }}>
                <n.icon size={16} />
                {n.label}
              </button>
            );
          })}
        </nav>

        <div style={{ padding: 14 }}>
          <Panel>
            <div style={{ padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 9, fontFamily: "monospace", color: "#475569", textTransform: "uppercase", letterSpacing: "0.12em" }}>Network</span>
                <div style={{ display: "flex", gap: 2 }}>
                  {[0.3, 0.55, 1].map((o, i) => <div key={i} style={{ width: 2, height: 11, borderRadius: 2, background: `rgba(63,185,80,${o})` }} />)}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 10, fontFamily: "monospace", color: "#94a3b8" }}>
                <Globe size={12} color="#58a6ff" /> localhost:8080
              </div>
            </div>
          </Panel>
          <div style={{ textAlign: "center", fontSize: 8, fontFamily: "monospace", color: "#334155", marginTop: 10 }}>v0.1.0 · 383 tests · OAGS L3</div>
        </div>
      </aside>

      {/* MAIN AREA */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 10 }}>
        {/* HEADER */}
        <header style={{ height: 58, flexShrink: 0, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 30px", background: "rgba(2,2,7,0.6)", backdropFilter: "blur(20px)", zIndex: 40 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ padding: "3px 10px", borderRadius: 99, fontSize: 9, fontFamily: "monospace", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b" }}>v0.1.0</span>
            <div style={{ display: "flex", alignItems: "center", gap: 7, cursor: "pointer" }} onClick={() => navigator.clipboard?.writeText(MOCK.identity)}>
              <Fingerprint size={12} color="#475569" />
              <code style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(88,166,255,0.75)" }}>{MOCK.identity.slice(0, 12)}...{MOCK.identity.slice(-8)}</code>
              <Copy size={9} color="#475569" />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#3fb950", boxShadow: "0 0 10px #3fb950", animation: "pulseGlow 2s infinite", color: "#3fb950" }} />
              <span style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.12em", color: "#3fb950" }}>Core_Live</span>
            </div>
            <span style={{ fontSize: 9, fontFamily: "monospace", color: "#475569" }}>{time}</span>
          </div>
        </header>

        {/* CONTENT */}
        <main style={{ flex: 1, overflowY: "auto", padding: 30 }}>
          <div key={section} className="fade-in" style={{ maxWidth: 1120, margin: "0 auto" }}>
            <View />
          </div>
        </main>

        {/* Scanline overlay */}
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.02, background: "linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.25) 50%)", backgroundSize: "100% 2px" }} />
      </div>
    </div>
  );
}
