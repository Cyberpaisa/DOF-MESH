"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Crown, Star, Award, ArrowLeft, ChevronUp, ChevronDown,
  Shield, Zap, Search, Filter, TrendingUp,
} from "lucide-react";

interface KarmaAgent {
  agent_id: string;
  name: string;
  role: string;
  karma: number;
  level: string;
  recent_actions: { action: string; points: number; timestamp: string }[];
  total_actions: number;
}

type SortKey = "karma" | "name" | "total_actions" | "level";
type SortDir = "asc" | "desc";

const LEVEL_ORDER: Record<string, number> = {
  SOVEREIGN: 7, ELITE: 6, VETERAN: 5, SPECIALIST: 4,
  OPERATIVE: 3, CADET: 2, RECRUIT: 1,
};

const LEVEL_COLORS: Record<string, { text: string; bg: string; border: string; glow: string }> = {
  SOVEREIGN: { text: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/30", glow: "shadow-purple-500/20" },
  ELITE:     { text: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/30", glow: "shadow-indigo-500/20" },
  VETERAN:   { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30", glow: "shadow-emerald-500/20" },
  SPECIALIST:{ text: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/30", glow: "shadow-amber-500/20" },
  OPERATIVE: { text: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/30", glow: "shadow-blue-500/20" },
  CADET:     { text: "text-zinc-400", bg: "bg-zinc-500/10", border: "border-zinc-500/30", glow: "shadow-zinc-500/20" },
  RECRUIT:   { text: "text-zinc-500", bg: "bg-zinc-700/10", border: "border-zinc-700/30", glow: "shadow-zinc-700/20" },
};

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) return <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/30"><Crown size={14} className="text-black" /></div>;
  if (rank === 2) return <div className="w-8 h-8 rounded-full bg-gradient-to-br from-zinc-300 to-zinc-500 flex items-center justify-center shadow-lg shadow-zinc-400/20"><span className="text-[11px] font-black text-black">2</span></div>;
  if (rank === 3) return <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-600 to-amber-800 flex items-center justify-center shadow-lg shadow-amber-700/20"><span className="text-[11px] font-black text-black">3</span></div>;
  return <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center"><span className="text-[10px] font-mono font-bold text-zinc-500">{rank}</span></div>;
}

export default function LeaderboardPage() {
  const [agents, setAgents] = useState<KarmaAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("karma");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLevel, setFilterLevel] = useState<string>("ALL");

  useEffect(() => {
    async function fetchKarma() {
      try {
        const res = await fetch("http://localhost:8000/api/karma");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setAgents(data.leaderboard || []);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to fetch");
      } finally {
        setLoading(false);
      }
    }
    fetchKarma();
    const interval = setInterval(fetchKarma, 30000);
    return () => clearInterval(interval);
  }, []);

  const sorted = useMemo(() => {
    let filtered = agents;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        a.name.toLowerCase().includes(q) || a.role.toLowerCase().includes(q) || a.agent_id.toLowerCase().includes(q)
      );
    }
    if (filterLevel !== "ALL") {
      filtered = filtered.filter(a => a.level === filterLevel);
    }
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "karma": cmp = a.karma - b.karma; break;
        case "name": cmp = a.name.localeCompare(b.name); break;
        case "total_actions": cmp = a.total_actions - b.total_actions; break;
        case "level": cmp = (LEVEL_ORDER[a.level] || 0) - (LEVEL_ORDER[b.level] || 0); break;
      }
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [agents, sortKey, sortDir, searchQuery, filterLevel]);

  const totalKarma = agents.reduce((s, a) => s + a.karma, 0);
  const topLevel = agents.length > 0
    ? agents.reduce((best, a) => (a.karma > best.karma ? a : best), agents[0])
    : null;

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  const SortIcon = ({ active }: { active: boolean }) =>
    active ? (sortDir === "desc" ? <ChevronDown size={12} /> : <ChevronUp size={12} />) : null;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="bg-zinc-950 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition">
              <ArrowLeft size={16} className="text-zinc-400" />
            </Link>
            <div>
              <h1 className="text-xl font-black tracking-tight flex items-center gap-2">
                <Crown size={20} className="text-purple-400" />
                DOF Leaderboard
              </h1>
              <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mt-1">
                Agent Karma Rankings &middot; Real-time
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-purple-600/10 border border-purple-500/20 px-4 py-2 rounded-xl">
              <span className="text-[9px] font-mono text-purple-500 uppercase tracking-widest">Total Karma</span>
              <div className="text-lg font-black text-purple-400">{totalKarma.toLocaleString()} CR</div>
            </div>
            <div className="bg-zinc-900 border border-white/5 px-4 py-2 rounded-xl">
              <span className="text-[9px] font-mono text-zinc-600 uppercase tracking-widest">Agents</span>
              <div className="text-lg font-black text-white">{agents.length}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Top 3 Podium */}
      {!loading && sorted.length >= 3 && (
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-3 gap-4 items-end">
            {[1, 0, 2].map(podiumIdx => {
              const agent = sorted[podiumIdx];
              if (!agent) return null;
              const rank = podiumIdx === 1 ? 2 : podiumIdx === 0 ? 1 : 3;
              const lc = LEVEL_COLORS[agent.level] || LEVEL_COLORS.RECRUIT;
              const heights = ["h-48", "h-36", "h-32"];
              return (
                <motion.div
                  key={agent.agent_id}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: podiumIdx * 0.1 }}
                  className={`${heights[podiumIdx]} bg-zinc-950 border border-white/10 rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden ${rank === 1 ? "shadow-lg shadow-purple-500/10 border-purple-500/30" : ""}`}
                >
                  {rank === 1 && <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500 to-transparent" />}
                  <div className="flex items-center justify-between">
                    <RankBadge rank={rank} />
                    <div className={`px-2 py-0.5 rounded-md border text-[7px] font-mono font-bold uppercase ${lc.text} ${lc.bg} ${lc.border}`}>
                      {agent.level}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-black tracking-tight">{agent.name}</div>
                    <div className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">{agent.role}</div>
                    <div className="flex items-center gap-1 mt-2">
                      <Star size={14} className="text-purple-400" />
                      <span className="text-xl font-black text-white">{agent.karma}</span>
                      <span className="text-[9px] text-purple-500 font-bold">CR</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="max-w-7xl mx-auto px-6 pb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search agents..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-900 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50"
            />
          </div>
          <div className="flex items-center gap-1">
            <Filter size={12} className="text-zinc-500" />
            {["ALL", "SOVEREIGN", "ELITE", "VETERAN", "SPECIALIST", "OPERATIVE"].map(level => (
              <button
                key={level}
                onClick={() => setFilterLevel(level)}
                className={`px-3 py-1.5 rounded-lg text-[9px] font-mono font-bold uppercase tracking-wider transition ${
                  filterLevel === level
                    ? "bg-purple-600/20 border border-purple-500/30 text-purple-400"
                    : "bg-zinc-900 border border-white/5 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="max-w-7xl mx-auto px-6 pb-12">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <Shield size={32} className="text-red-500 mx-auto mb-3" />
            <p className="text-sm text-zinc-400">Error: {error}</p>
            <p className="text-[10px] font-mono text-zinc-600 mt-1">Start A2A server: python3 a2a_server.py --port 8000</p>
          </div>
        ) : (
          <div className="bg-zinc-950 border border-white/10 rounded-2xl overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-[48px_1fr_1fr_120px_120px_100px] gap-4 px-5 py-3 border-b border-white/5 bg-zinc-900/50">
              <span className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest">#</span>
              <button onClick={() => toggleSort("name")} className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest text-left flex items-center gap-1 hover:text-zinc-400">
                Agent <SortIcon active={sortKey === "name"} />
              </button>
              <span className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest">Role</span>
              <button onClick={() => toggleSort("karma")} className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest text-right flex items-center gap-1 justify-end hover:text-zinc-400">
                Karma <SortIcon active={sortKey === "karma"} />
              </button>
              <button onClick={() => toggleSort("level")} className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest text-center flex items-center gap-1 justify-center hover:text-zinc-400">
                Level <SortIcon active={sortKey === "level"} />
              </button>
              <button onClick={() => toggleSort("total_actions")} className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest text-right flex items-center gap-1 justify-end hover:text-zinc-400">
                Actions <SortIcon active={sortKey === "total_actions"} />
              </button>
            </div>

            {/* Rows */}
            <AnimatePresence>
              {sorted.map((agent, idx) => {
                const rank = idx + 1;
                const lc = LEVEL_COLORS[agent.level] || LEVEL_COLORS.RECRUIT;
                return (
                  <motion.div
                    key={agent.agent_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: idx * 0.02 }}
                    className="grid grid-cols-[48px_1fr_1fr_120px_120px_100px] gap-4 px-5 py-3 border-b border-white/[0.03] hover:bg-white/[0.02] transition group"
                  >
                    <div className="flex items-center">
                      <RankBadge rank={rank} />
                    </div>
                    <div className="flex flex-col justify-center">
                      <span className="text-sm font-bold text-white tracking-tight">{agent.name}</span>
                      <span className="text-[9px] font-mono text-zinc-600">{agent.agent_id}</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">{agent.role}</span>
                    </div>
                    <div className="flex items-center justify-end gap-1">
                      <Star size={12} className="text-purple-400" />
                      <span className="text-sm font-mono font-black text-white">{agent.karma.toLocaleString()}</span>
                      <span className="text-[8px] text-purple-500 font-bold">CR</span>
                    </div>
                    <div className="flex items-center justify-center">
                      <span className={`px-2.5 py-1 rounded-lg border text-[8px] font-mono font-bold uppercase tracking-wider ${lc.text} ${lc.bg} ${lc.border}`}>
                        {agent.level}
                      </span>
                    </div>
                    <div className="flex items-center justify-end gap-1">
                      <Zap size={10} className="text-emerald-500" />
                      <span className="text-xs font-mono text-zinc-400">{agent.total_actions}</span>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {sorted.length === 0 && (
              <div className="text-center py-12 text-zinc-600 text-sm">
                No agents match your filters.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
