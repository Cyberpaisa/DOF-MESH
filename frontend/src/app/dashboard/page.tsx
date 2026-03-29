"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Shield, Zap, Lock, Cpu, Globe, MessageSquare, Terminal, Send, Users, ListFilter, Activity, ArrowUpRight, Paperclip, FileText, AlertTriangle, CheckCircle, XCircle, Clock, Database, Boxes, TrendingUp, RefreshCw, Crown, Star, Award } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message { role: 'user' | 'assistant' | 'system'; content: string; }
interface Agent { name: string; status: 'ACTIVE' | 'IDLE' | 'BUSY'; role: string; last_log: string; mission?: string; security_level?: number; }
interface Issue { agent: string; id: string; title: string; priority?: 'HIGH' | 'NORMAL'; karma_reward?: number; estimated_time?: string; }
interface GraphNode { id: string; label: string; level: number; size: number; type?: 'USER' | 'CORE' | 'AGENT' | 'TOOL'; status?: string; }
interface GraphEdge { source: string; target: string; label?: string; activity?: number; }
interface GraphData { nodes: GraphNode[]; edges: GraphEdge[]; }
interface Trace { cycle: number; timestamp: string; action: string; thought: string; proof: string; attestations_ok: number; cycles_completed: number; status: string; signature: string; }
interface SecurityData { shield_status: string; heartbeats: any; rate_limiter: string; input_sanitization: string; agent_security_levels: any[]; audit_events_total: number; recent_threats: any[]; cors_policy: string; security_headers: string[]; }
interface SkillItem { name: string; description: string; version: string; tags: string[]; pattern: string; authorized_agents: string[]; times_used: number; times_refined: number; success_rate: number; avg_score: number; degraded: boolean; }
interface SkillsData { total_skills: number; patterns_supported: string[]; skills: SkillItem[]; routing_confusion_count: number; degraded_skills: string[]; }
interface KarmaAgent { agent_id: string; name: string; role: string; karma: number; level: string; recent_actions: any[]; total_actions: number; }
interface ChatMsg { id: string; from: string; from_name: string; role: string; content: string; type: string; timestamp: string; karma_at_time: number; }


const StatusRing = ({ value, label, color = "stroke-purple-500" }: { value: number, label: string, color?: string }) => {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center relative group">
      <svg className="w-16 h-16 transform -rotate-90">
        <circle cx="32" cy="32" r={radius} stroke="currentColor" strokeWidth="2" fill="transparent" className="text-white/5" />
        <motion.circle
          cx="32" cy="32" r={radius} stroke="currentColor" strokeWidth="3" fill="transparent"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          className={color}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[10px] font-mono font-black text-white">{value}%</span>
      </div>
      <span className="text-[7px] font-mono text-zinc-500 uppercase mt-2 tracking-widest">{label}</span>
    </div>
  );
};

export default function Dashboard() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: 'Connection established via Enigma Sovereign Core.' },
    { role: 'assistant', content: 'Greetings Juan. Identity Enigma #1686 synchronized. Sovereign Office is Online.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [swarm, setSwarm] = useState<Agent[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [traces, setTraces] = useState<Trace[]>([]);
  const [tracesTotal, setTracesTotal] = useState(0);
  const [security, setSecurity] = useState<SecurityData | null>(null);
  const [skillsData, setSkillsData] = useState<SkillsData | null>(null);
  const [karmaBoard, setKarmaBoard] = useState<KarmaAgent[]>([]);
  const [legionChat, setLegionChat] = useState<ChatMsg[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeTab]);

  const fetchData = async () => {
    try {
      const [sRes, iRes, gRes, tRes, secRes, skRes, kRes, cRes] = await Promise.all([
        fetch('http://localhost:8000/api/swarm'),
        fetch('http://localhost:8000/api/issues'),
        fetch('http://localhost:8000/api/graph'),
        fetch('http://localhost:8000/api/traces'),
        fetch('http://localhost:8000/api/security'),
        fetch('http://localhost:8000/api/skills'),
        fetch('http://localhost:8000/api/karma'),
        fetch('http://localhost:8000/api/internal-chat?limit=100'),
      ]);
      if (sRes.ok) setSwarm((await sRes.json()).swarm);
      if (iRes.ok) setIssues((await iRes.json()).issues);
      if (gRes.ok) setGraph(await gRes.json());
      if (tRes.ok) {
        const tData = await tRes.json();
        setTraces(tData.traces || []);
        setTracesTotal(tData.total || 0);
      }
      if (secRes.ok) setSecurity(await secRes.json());
      if (skRes.ok) setSkillsData(await skRes.json());
      if (kRes.ok) setKarmaBoard((await kRes.json()).leaderboard || []);
      if (cRes.ok) setLegionChat((await cRes.json()).messages || []);
    } catch (e) {}
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/chat/history');
      if (res.ok) {
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          const formatted = data.history.map((m: any) => ({
            role: m.role as 'user' | 'assistant',
            content: m.content
          }));
          setMessages(formatted);
        }
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchData();
    fetchHistory();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, user: 'Juan' })
      });
      const data = await response.json();
      if (data.threats_blocked) {
        setMessages(prev => [...prev, { role: 'system', content: `SHIELD: ${data.threats_blocked} threat(s) blocked.` }]);
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'system', content: 'Neural bridge timeout.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/chat/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      const fileMsg = `uploaded: ${file.name}`;
      setMessages(prev => [...prev, { role: 'user', content: fileMsg }]);

      const chatRes = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `I uploaded a file: ${file.name}. Type: ${file.type}. URL: ${data.url}`, user: 'Juan' })
      });
      const chatData = await chatRes.json();
      setMessages(prev => [...prev, { role: 'assistant', content: chatData.response }]);
    } catch (error) {
       setMessages(prev => [...prev, { role: 'system', content: 'File upload failed.' }]);
    } finally {
      setUploading(false);
    }
  };

  const [stats, setStats] = useState<any>({ memory_percent: 0, cpu_percent: 0, total_karma: 0, x402_facilitator: 'OFFLINE' });
  const [skills, setSkills] = useState<string[]>([]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [sRes, skRes] = await Promise.all([
          fetch('http://localhost:8000/api/stats'),
          fetch('http://localhost:8000/api/skills')
        ]);
        if (sRes.ok) setStats(await sRes.json());
        if (skRes.ok) setSkills((await skRes.json()).active_skills || []);
      } catch (e) {}
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const getNodeIcon = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('security') || l.includes('shield')) return Shield;
    if (l.includes('neural') || l.includes('core') || l.includes('brain')) return Cpu;
    if (l.includes('network') || l.includes('gateway')) return Globe;
    if (l.includes('payment') || l.includes('x402')) return Zap;
    return Activity;
  };

  const securityLevelColor = (level: number) => {
    if (level >= 7) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (level >= 5) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    if (level >= 3) return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30';
  };

  return (
    <div className="min-h-screen bg-[#020202] text-zinc-300 font-sans selection:bg-purple-500/30 overflow-hidden flex flex-col">
      {/* Visual Foundation */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(88,28,135,0.05)_0%,transparent_70%)]" />
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" className="opacity-10">
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="white" strokeWidth="0.5" />
              <circle cx="0" cy="0" r="1" fill="white" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="fixed inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.05)_50%)] z-50 bg-[length:100%_4px] opacity-20" />

      {/* Top Mission Control Bar */}
      <header className="h-16 border-b border-white/10 bg-black/90 backdrop-blur-2xl flex items-center px-8 justify-between shrink-0 z-40 relative">
        <div className="flex items-center gap-6">
           <motion.div
             whileHover={{ scale: 1.05 }}
             className="w-10 h-10 bg-gradient-to-br from-purple-600 to-indigo-700 rounded-lg flex items-center justify-center shadow-[0_0_20px_rgba(168,85,247,0.4)] border border-white/20"
           >
             <Shield size={20} className="text-white" />
           </motion.div>
           <div className="flex flex-col">
             <span className="text-lg font-black tracking-[-0.05em] text-white leading-none">ENIGMA <span className="text-purple-500">#1686</span></span>
             <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest mt-1">SOVEREIGN MISSION CONTROL // {stats.status || 'LOADING'} // SHIELD: ACTIVE</span>
           </div>
        </div>

        <div className="flex-1 mx-16 overflow-hidden border-x border-white/5 h-full flex items-center group cursor-default bg-white/[0.02]">
           <div className="flex gap-16 whitespace-nowrap animate-marquee group-hover:pause italic">
              {[1, 2].map(i => (
                <div key={i} className="flex gap-16 text-[10px] font-mono font-bold text-zinc-500 tracking-wider items-center">
                   <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_#10b981]" /> SYS_STABLE</span>
                   <span className="text-white/20">/</span>
                   <span className="flex items-center gap-2 uppercase">UPTIME: {stats.uptime || '...'}</span>
                   <span className="text-white/20">/</span>
                   <span className="flex items-center gap-2 text-purple-400">KARMA: +{stats.total_karma} CR</span>
                   <span className="text-white/20">/</span>
                   <span className="flex items-center gap-2 text-emerald-400">CYCLE: {stats.autonomous_cycle || '?'}</span>
                   <span className="text-white/20">/</span>
                   <span className="flex items-center gap-2 text-indigo-400">OLLAMA: {stats.ollama_calls || 0} calls</span>
                   <span className="text-white/20">|</span>
                </div>
              ))}
           </div>
        </div>

        <div className="flex items-center gap-8">
           <div className="flex flex-col items-end gap-1">
              <span className="text-[8px] font-mono text-zinc-600 uppercase">Neural Sync</span>
              <div className="w-24 h-1 bg-white/5 rounded-full overflow-hidden border border-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${stats.neural_sync || 0}%` }}
                  className="h-full bg-purple-500 shadow-[0_0_10px_#a855f7]"
                />
              </div>
           </div>
            <div className="h-8 w-px bg-white/10" />
            <div className="flex flex-col items-end gap-1">
              <span className="text-[7px] font-mono text-zinc-600 uppercase">ERC-8004 Registry</span>
              <div className="text-[10px] font-mono text-purple-400 font-bold bg-white/5 px-3 py-1.5 rounded border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]">
                0x8004...a432
              </div>
            </div>
         </div>
      </header>

      {/* Primary HUD Layout */}
      <main className="flex-1 overflow-hidden grid grid-cols-12 relative">

         {/* Navigation Sidebar */}
         <aside className="col-span-1 border-r border-white/5 bg-zinc-950/20 flex flex-col items-center py-8 gap-8">
            {[
              { id: 'chat', icon: MessageSquare, label: 'COMMS' },
              { id: 'swarm', icon: Users, label: 'SWARM' },
              { id: 'issues', icon: ListFilter, label: 'TRACKS' },
              { id: 'traces', icon: Database, label: 'TRACES' },
              { id: 'neural', icon: Activity, label: 'NEURAL' },
              { id: 'skills', icon: Boxes, label: 'SKILLS' },
              { id: 'security', icon: Shield, label: 'SHIELD' },
              { id: 'legion', icon: Crown, label: 'LEGION' },
              { id: 'hackathon', icon: Award, label: 'HACK' },
            ].map((it) => (
              <button
               key={it.id}
               onClick={() => setActiveTab(it.id as any)}
               className={`group flex flex-col items-center gap-2 transition-all ${activeTab === it.id ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}
              >
                 <div className={`p-3 rounded-2xl border transition-all ${activeTab === it.id ? 'bg-purple-600/20 border-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.3)]' : 'bg-transparent border-transparent group-hover:bg-white/5'}`}>
                    <it.icon size={20} className={activeTab === it.id ? 'text-white' : 'text-zinc-500 group-hover:text-zinc-300'} />
                 </div>
                 <span className="text-[7px] font-mono font-black tracking-[0.2em] uppercase">{it.label}</span>
              </button>
            ))}
            <div className="mt-auto flex flex-col items-center gap-6 pb-4">
               <div className="w-10 h-10 rounded-full border border-white/10 bg-gradient-to-br from-indigo-500 to-purple-500 p-[1px] hover:scale-110 transition-all cursor-pointer">
                  <div className="w-full h-full rounded-full bg-black flex items-center justify-center">
                     <Users size={16} className="text-white" />
                  </div>
               </div>
            </div>
         </aside>


        {/* Global HUD Content Area */}
        <section className="col-span-8 flex flex-col bg-black/40 relative">
           <AnimatePresence mode="wait">

             {/* === CHAT TAB === */}
             {activeTab === 'chat' && (
               <motion.div key="chat" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full flex flex-col p-8 lg:p-12 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.02] pointer-events-none">
                     <MessageSquare size={300} />
                  </div>
                  <div ref={scrollRef} className="flex-1 space-y-10 overflow-y-auto pr-4 custom-scrollbar relative z-10">
                     {messages.map((m, i) => (
                       <motion.div
                         key={i}
                         initial={{ opacity: 0, x: m.role === 'user' ? 20 : -20 }}
                         animate={{ opacity: 1, x: 0 }}
                         className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                       >
                          <div className={`max-w-[80%] p-6 rounded-2xl border transition-all ${
                            m.role === 'user'
                            ? 'bg-purple-600/10 border-purple-500/40 text-white shadow-[0_0_30px_rgba(168,85,247,0.1)]'
                            : m.role === 'system'
                            ? 'bg-transparent border-zinc-800/50 text-zinc-500 font-mono text-[9px] uppercase tracking-[0.2em] py-2 px-4 italic'
                            : 'bg-zinc-900/80 border-white/10 text-zinc-300 backdrop-blur-xl shadow-2xl'
                          }`}>
                             {m.role === 'assistant' && (
                               <div className="flex items-center gap-3 mb-3 pb-3 border-b border-white/5">
                                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                                  <span className="text-[10px] font-mono font-black text-purple-400 uppercase tracking-widest">Enigma #1686 // Response</span>
                               </div>
                             )}

                             <div className="space-y-4">
                                {m.content.includes('uploaded:') && (
                                   <div className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/10">
                                      <FileText size={20} className="text-purple-400" />
                                      <div className="flex flex-col">
                                         <span className="text-[10px] font-mono text-zinc-300">{m.content.split('uploaded:')[1]?.trim() || 'Archivo'}</span>
                                         <span className="text-[8px] font-mono text-zinc-600 uppercase">FILE_VERIFIED</span>
                                      </div>
                                   </div>
                                )}

                                <p className={`leading-relaxed whitespace-pre-wrap ${m.role === 'assistant' ? 'text-sm' : 'text-xs opacity-90'}`}>
                                   {m.content.replace(/uploaded:.*|URL: https?:\/\/[^\s]+/, '').trim() || (m.content.includes('uploaded:') ? 'Archivo adjunto procesado.' : m.content)}
                                </p>
                             </div>

                             {m.role === 'assistant' && (
                               <div className="mt-4 pt-4 border-t border-white/5 flex justify-between items-center text-[8px] font-mono text-zinc-600">
                                  <span>SHIELD: AES-256</span>
                                  <span>LATENCY: {stats.ollama_avg_latency_ms || 0}ms</span>
                                </div>
                             )}
                          </div>
                       </motion.div>
                     ))}
                     {isLoading && (
                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2 text-[10px] font-mono text-purple-500 font-bold uppercase tracking-widest animate-pulse">
                             <Zap size={10} className="animate-bounce" /> Processing Neural Stream...
                          </div>
                          <div className="w-48 h-1 bg-white/5 rounded-full overflow-hidden">
                             <motion.div
                               animate={{ x: [-200, 200] }}
                               transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                               className="w-20 h-full bg-gradient-to-r from-transparent via-purple-500 to-transparent"
                             />
                          </div>
                       </div>
                     )}
                  </div>

                  <div
                    className={`mt-8 flex gap-4 relative z-10 pt-6 border-t border-white/5 transition-all ${isDragging ? 'scale-[1.02]' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={async (e) => {
                       e.preventDefault();
                       setIsDragging(false);
                       const file = e.dataTransfer.files[0];
                       if (file) {
                          const event = { target: { files: [file] } } as any;
                          handleFileUpload(event);
                       }
                    }}
                  >
                     <div className="flex-1 relative group">
                        {isDragging && (
                           <div className="absolute -inset-4 bg-purple-500/20 border-2 border-dashed border-purple-500 rounded-3xl z-20 flex items-center justify-center backdrop-blur-sm">
                              <span className="text-xs font-mono font-bold text-white uppercase tracking-[0.3em] animate-pulse">Release to Upload File</span>
                           </div>
                        )}
                        <div className="absolute -inset-1 bg-gradient-to-r from-purple-600/20 to-indigo-600/20 blur-xl group-focus-within:opacity-100 opacity-0 transition-opacity rounded-[2rem]" />
                        <div className="absolute left-6 top-6 text-zinc-600">
                           <Terminal size={16} />
                        </div>
                        <textarea
                          ref={textareaRef}
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              handleSend();
                            }
                          }}
                          placeholder="ENTER_SOVEREIGN_COMMAND..."
                          rows={1}
                          className="w-full bg-black/60 border border-white/10 rounded-[1.5rem] py-5 pl-16 pr-24 text-sm focus:outline-none focus:border-purple-500/50 transition-all text-white font-mono placeholder:text-zinc-700 backdrop-blur-md resize-none custom-scrollbar"
                        />
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploading}
                          className="absolute left-4 top-6 p-2 text-zinc-500 hover:text-purple-400 transition-colors"
                        >
                           <Paperclip size={18} className={uploading ? "animate-spin" : ""} />
                        </button>
                        <input
                           type="file"
                           ref={fileInputRef}
                           onChange={handleFileUpload}
                           className="hidden"
                        />
                        <button
                          onClick={handleSend}
                          className="absolute right-4 top-6 p-2 bg-purple-600 hover:bg-purple-500 text-white rounded-full transition-all shadow-[0_0_15px_rgba(168,85,247,0.4)] hover:scale-110 active:scale-95"
                        >
                           <Send size={16} />
                        </button>
                     </div>
                  </div>
               </motion.div>
             )}


             {/* === SWARM TAB === */}
             {activeTab === 'swarm' && (
               <motion.div key="swarm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-8 overflow-y-auto custom-scrollbar">
                  <div className="flex justify-between items-center border-b border-white/10 pb-6">
                     <div>
                        <span className="text-xs font-black text-white tracking-[0.4em] uppercase">Sovereign Swarm Command</span>
                        <div className="text-[8px] font-mono text-zinc-600 mt-2 uppercase">UNITS: {swarm.length} // THREAT_LEVEL: ZERO // SHIELD: ACTIVE</div>
                     </div>
                     <div className="flex items-center gap-6">
                        <div className="bg-white/5 px-5 py-3 rounded-2xl border border-white/10">
                           <span className="text-[10px] font-mono text-emerald-400 font-black uppercase tracking-widest">
                              Operational: {swarm.filter(a => a.status === 'ACTIVE').length}/{swarm.length}
                           </span>
                        </div>
                     </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6">
                  {swarm.map((agent, idx) => (
                    <motion.div
                      key={agent.name}
                      initial={{ opacity: 0, y: 30 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      className="bg-zinc-950/80 border border-white/10 rounded-2xl p-6 relative overflow-hidden group hover:border-purple-500/50 transition-all"
                    >
                       <div className="flex justify-between items-start mb-4 relative z-10">
                          <div className="flex flex-col">
                             <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${agent.status === 'ACTIVE' ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]' : 'bg-zinc-700'}`} />
                                <span className="text-sm font-black text-white tracking-tighter">{agent.name}</span>
                             </div>
                             <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest mt-1">{agent.role}</span>
                          </div>
                          {agent.security_level !== undefined && (
                            <div className={`px-2 py-1 rounded-lg border text-[8px] font-mono font-bold ${securityLevelColor(agent.security_level)}`}>
                              LVL {agent.security_level}
                            </div>
                          )}
                       </div>

                       {agent.mission && (
                         <div className="text-[8px] font-mono text-zinc-600 mb-4 uppercase">{agent.mission}</div>
                       )}

                       <div className="grid grid-cols-2 gap-2 relative z-10">
                          {[
                            { label: 'Latency', val: (agent as any).latency || '0ms' },
                            { label: 'Throughput', val: (agent as any).throughput || '0 tps' }
                          ].map(it => (
                            <div key={it.label} className="bg-white/5 p-2 rounded-lg border border-white/5 flex flex-col gap-1">
                               <span className="text-[7px] font-mono text-zinc-600 uppercase">{it.label}</span>
                               <div className="text-[10px] font-mono font-black text-white">{it.val}</div>
                            </div>
                          ))}
                       </div>
                     </motion.div>
                   ))}
                   </div>
                </motion.div>
              )}


             {/* === TRACKS TAB === */}
             {activeTab === 'issues' && (
               <motion.div key="issues" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-6 overflow-y-auto custom-scrollbar">
                  <div className="flex justify-between items-center border-b border-white/10 pb-4">
                     <div>
                        <span className="text-xs font-black text-white tracking-[0.4em] uppercase">Hackathon Track Registry</span>
                        <div className="text-[8px] font-mono text-zinc-600 mt-1 uppercase">SYNTHESIS 2026 // DEADLINE: MARCH 22</div>
                     </div>
                     <span className="bg-white/5 px-4 py-2 rounded-xl border border-white/10 text-[10px] font-mono text-purple-400 font-bold">
                        {issues.length} MISSIONS
                     </span>
                  </div>

                  <div className="grid grid-cols-1 gap-2">
                    {issues.map((issue, idx) => (
                      <motion.div
                        key={issue.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        className="bg-white/[0.02] border border-white/5 p-5 rounded-2xl flex items-center justify-between group hover:bg-white/5 hover:border-purple-500/30 transition-all cursor-pointer relative overflow-hidden"
                      >
                         <div className="absolute inset-y-0 left-0 w-1 bg-purple-500 opacity-20 group-hover:opacity-100 transition-opacity" />
                         <div className="flex items-center gap-8 relative z-10 w-full">
                            <div className="text-[10px] font-mono text-zinc-700 w-12">{idx + 1}.</div>
                            <div className={`w-2 h-2 rounded-full ${issue.priority === 'HIGH' ? 'bg-amber-500 shadow-[0_0_8px_#f59e0b]' : 'bg-purple-500 shadow-[0_0_8px_#a855f7]'}`} />

                            <div className="grid grid-cols-4 items-center gap-12 flex-1">
                               <div className="col-span-2">
                                  <div className="text-[8px] font-mono text-zinc-500 mb-1 flex items-center gap-2">
                                     <span className="bg-white/10 px-1.5 py-0.5 rounded text-white italic">@{issue.agent.toUpperCase()}</span>
                                     ID: {issue.id.split('-')[0]}
                                  </div>
                                  <div className="text-sm font-bold text-white tracking-tight group-hover:text-purple-300 transition-colors uppercase">
                                     {issue.title}
                                  </div>
                               </div>

                               <div className="text-right">
                                  <div className="text-[8px] font-mono text-zinc-600 uppercase mb-1">Priority</div>
                                  <div className="text-[10px] font-mono font-black text-amber-400">{issue.priority}</div>
                               </div>

                               <div className="text-right">
                                  <div className="text-[8px] font-mono text-zinc-600 uppercase mb-1">Karma</div>
                                  <div className="text-[10px] font-mono font-black text-emerald-400">+{issue.karma_reward} CR</div>
                               </div>
                            </div>
                         </div>
                         <ArrowUpRight size={14} className="text-zinc-800 group-hover:text-white transition-all" />
                      </motion.div>
                    ))}
                  </div>
               </motion.div>
             )}


             {/* === TRACES TAB (NEW) === */}
             {activeTab === 'traces' && (
               <motion.div key="traces" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-6 overflow-y-auto custom-scrollbar">
                  <div className="flex justify-between items-center border-b border-white/10 pb-4">
                     <div>
                        <span className="text-xs font-black text-white tracking-[0.4em] uppercase">Autonomous Cycle Traces</span>
                        <div className="text-[8px] font-mono text-zinc-600 mt-1 uppercase">DETERMINISTIC VERIFICATION // REAL DATA FROM LOGS/TRACES/</div>
                     </div>
                     <div className="flex items-center gap-4">
                        <span className="bg-white/5 px-4 py-2 rounded-xl border border-white/10 text-[10px] font-mono text-emerald-400 font-bold">
                           {tracesTotal} TOTAL CYCLES
                        </span>
                        <button onClick={fetchData} className="bg-purple-600/20 border border-purple-500/30 px-4 py-2 rounded-xl text-[10px] font-mono text-purple-400 font-bold hover:bg-purple-600/40 transition-all">
                           REFRESH
                        </button>
                     </div>
                  </div>

                  {traces.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center">
                       <div className="text-center">
                          <Database size={48} className="text-zinc-800 mx-auto mb-4" />
                          <p className="text-sm font-mono text-zinc-600">No traces found. Start the autonomous loop.</p>
                       </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {traces.map((trace, idx) => (
                        <motion.div
                          key={trace.cycle}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.03 }}
                          className="bg-zinc-950/80 border border-white/10 rounded-xl p-5 hover:border-purple-500/30 transition-all group"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-4">
                              <div className="bg-purple-600/20 border border-purple-500/30 px-3 py-1 rounded-lg">
                                <span className="text-xs font-mono font-black text-purple-400">CYCLE {trace.cycle}</span>
                              </div>
                              <span className="text-[9px] font-mono text-zinc-500">{trace.timestamp}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[8px] font-mono font-bold ${
                                trace.status === 'VERIFIED_DETERMINISTIC'
                                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                                  : 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                              }`}>
                                {trace.status === 'VERIFIED_DETERMINISTIC' ? <CheckCircle size={10} /> : <Clock size={10} />}
                                {trace.status}
                              </div>
                            </div>
                          </div>

                          <div className="grid grid-cols-4 gap-4 mt-3">
                            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                              <div className="text-[7px] font-mono text-zinc-600 uppercase mb-1">Action</div>
                              <div className="text-[11px] font-mono font-bold text-white uppercase">{trace.action}</div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                              <div className="text-[7px] font-mono text-zinc-600 uppercase mb-1">Attestations</div>
                              <div className="text-[11px] font-mono font-bold text-emerald-400">{trace.attestations_ok}</div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                              <div className="text-[7px] font-mono text-zinc-600 uppercase mb-1">Proof</div>
                              <div className="text-[11px] font-mono font-bold text-indigo-400 truncate">{trace.proof || '---'}</div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                              <div className="text-[7px] font-mono text-zinc-600 uppercase mb-1">Signature</div>
                              <div className="text-[11px] font-mono font-bold text-zinc-400 truncate">{trace.signature || '---'}</div>
                            </div>
                          </div>

                          {trace.thought && (
                            <div className="mt-3 text-[9px] font-mono text-zinc-500 italic truncate">
                              {trace.thought}
                            </div>
                          )}
                        </motion.div>
                      ))}
                    </div>
                  )}
               </motion.div>
             )}


             {/* === NEURAL TAB === */}
             {activeTab === 'neural' && (
               <motion.div
                 key="neural"
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 exit={{ opacity: 0 }}
                 className="h-full relative overflow-hidden flex items-center justify-center bg-zinc-950/20"
                 style={{ perspective: '3000px' }}
               >
                  <div className="absolute inset-0 opacity-5 pointer-events-none">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(168,85,247,0.15)_0%,transparent_70%)]" />
                  </div>

                  <motion.div
                    style={{ rotateX: 10, rotateY: 0, transformStyle: 'preserve-3d' }}
                    className="w-full h-full relative flex items-center justify-center"
                  >
                    <svg className="w-full h-full absolute inset-0 z-0 overflow-visible">
                       {graph.edges.map((edge, i) => {
                          const source = graph.nodes.find(n => n.id === edge.source);
                          const target = graph.nodes.find(n => n.id === edge.target);
                          if (!source || !target) return null;

                          const x1 = `${(source.level - 1) * 28 + 10}%`;
                          const y1 = `${20 + (graph.nodes.filter(n => n.level === source.level).indexOf(source) * 20)}%`;
                          const x2 = `${(target.level - 1) * 28 + 10}%`;
                          const y2 = `${20 + (graph.nodes.filter(n => n.level === target.level).indexOf(target) * 20)}%`;

                          return (
                            <g key={i}>
                              <motion.path
                                d={`M ${x1} ${y1} L ${x2} ${y2}`}
                                stroke="url(#edgeGradient3D)"
                                strokeWidth={edge.activity ? 1 + edge.activity * 2 : 1}
                                strokeOpacity={edge.activity ? 0.2 + edge.activity * 0.4 : 0.3}
                                fill="none"
                                initial={{ pathLength: 0 }}
                                animate={{ pathLength: 1 }}
                                transition={{ duration: 2, delay: i * 0.1 }}
                              />
                              <motion.circle
                                r="3"
                                fill="#a855f7"
                              >
                                 <animateMotion
                                   dur={`${3 + Math.random() * 2}s`}
                                   repeatCount="indefinite"
                                   path={`M ${x1} ${y1} L ${x2} ${y2}`}
                                 />
                              </motion.circle>
                            </g>
                          );
                       })}
                       <defs>
                          <linearGradient id="edgeGradient3D" x1="0%" y1="0%" x2="100%" y2="0%">
                             <stop offset="0%" stopColor="#6366f1" />
                             <stop offset="100%" stopColor="#a855f7" />
                          </linearGradient>
                       </defs>
                    </svg>

                    <div className="flex justify-between w-full h-full px-20 relative z-10 py-20" style={{ transformStyle: 'preserve-3d' }}>
                       {[1, 2, 3, 4].map(level => (
                         <div key={level} className="flex flex-col gap-12 items-center justify-center h-full" style={{ transform: `translateZ(${level * 50}px)` }}>
                            <span className="text-[7px] font-mono text-zinc-700 tracking-[0.6em] uppercase mb-4 py-1 px-3 border border-white/5 rounded-full bg-white/[0.02]">
                              Tier {level}
                            </span>
                            {graph.nodes.filter(n => n.level === level).map(node => {
                              const Icon = getNodeIcon(node.label);
                              return (
                                <motion.div
                                  key={node.id}
                                  whileHover={{ scale: 1.1 }}
                                  className="bg-black/80 border-2 border-white/10 p-4 rounded-2xl w-40 text-center relative group backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.8)] border-b-purple-500/40"
                                >
                                   <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/40 blur opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
                                   <div className="flex justify-center mb-2">
                                      <div className="p-2 bg-white/5 rounded-lg border border-white/10 text-purple-400 group-hover:text-white transition-colors">
                                         <Icon size={18} />
                                      </div>
                                   </div>
                                   <div className="text-[10px] font-black text-white tracking-tight uppercase relative z-10">{node.label}</div>
                                   <div className="text-[7px] font-mono text-zinc-500 mt-1 uppercase tracking-widest relative z-10 truncate">
                                     {node.id.slice(0, 12)}
                                   </div>
                                </motion.div>
                              );
                            })}
                         </div>
                       ))}
                    </div>
                  </motion.div>

                  <div className="absolute top-8 left-8 max-w-xs space-y-3">
                     <div className="bg-black/60 border border-white/10 p-4 rounded-xl backdrop-blur-xl">
                        <h4 className="text-[10px] font-black text-white uppercase tracking-[0.2em] mb-2 flex items-center gap-2">
                           <Activity size={12} className="text-purple-500" /> Neural Topology
                        </h4>
                        <p className="text-[8px] font-mono text-zinc-500 leading-relaxed uppercase">
                           Real-time orchestration graph. Nodes = agents, edges = data flows.
                        </p>
                     </div>
                  </div>
               </motion.div>
             )}


             {/* === SKILLS TAB === */}
             {activeTab === 'skills' && (
               <motion.div key="skills" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-6 overflow-y-auto custom-scrollbar">
                  <div className="flex justify-between items-center border-b border-white/10 pb-4">
                     <div>
                        <span className="text-xs font-black text-white tracking-[0.4em] uppercase">Sovereign Skill Engine v2.0</span>
                        <div className="text-[8px] font-mono text-zinc-600 mt-1 uppercase">
                          {skillsData?.total_skills || 0} SKILLS // PATTERNS: {skillsData?.patterns_supported?.join(', ') || '...'} // ROUTING CONFUSION: {skillsData?.routing_confusion_count || 0}
                        </div>
                     </div>
                     <div className="flex items-center gap-3">
                        {(skillsData?.degraded_skills?.length || 0) > 0 ? (
                          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 px-4 py-2 rounded-xl">
                            <AlertTriangle size={14} className="text-red-400" />
                            <span className="text-[10px] font-mono text-red-400 font-bold">{skillsData?.degraded_skills?.length} DEGRADED</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-4 py-2 rounded-xl">
                            <CheckCircle size={14} className="text-emerald-400" />
                            <span className="text-[10px] font-mono text-emerald-400 font-bold">ALL HEALTHY</span>
                          </div>
                        )}
                        <button onClick={fetchData} className="bg-purple-600/20 border border-purple-500/30 px-4 py-2 rounded-xl text-[10px] font-mono text-purple-400 font-bold hover:bg-purple-600/40 transition-all">
                           <RefreshCw size={12} />
                        </button>
                     </div>
                  </div>

                  {/* Skills Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(skillsData?.skills || []).map((skill, idx) => (
                      <motion.div
                        key={skill.name}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.04 }}
                        className={`bg-zinc-950/80 border rounded-xl p-5 hover:border-purple-500/30 transition-all group ${
                          skill.degraded ? 'border-red-500/30' : 'border-white/10'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Boxes size={14} className={skill.degraded ? 'text-red-400' : 'text-purple-400'} />
                              <span className="text-sm font-black text-white tracking-tight">{skill.name}</span>
                              <span className="text-[8px] font-mono text-zinc-600 bg-white/5 px-1.5 py-0.5 rounded">v{skill.version}</span>
                            </div>
                            <p className="text-[9px] font-mono text-zinc-500 leading-relaxed line-clamp-2">{skill.description}</p>
                          </div>
                          {skill.degraded && (
                            <div className="shrink-0 ml-2">
                              <AlertTriangle size={16} className="text-red-400 animate-pulse" />
                            </div>
                          )}
                        </div>

                        {/* Tags */}
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          {skill.tags.map(tag => (
                            <span key={tag} className={`text-[7px] font-mono font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                              tag === 'high-impact' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
                              tag === 'universal' ? 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' :
                              tag === 'security' ? 'text-red-400 bg-red-500/10 border-red-500/20' :
                              'text-zinc-400 bg-zinc-500/10 border-zinc-500/20'
                            }`}>{tag}</span>
                          ))}
                        </div>

                        {/* Metrics */}
                        <div className="grid grid-cols-3 gap-2">
                          <div className="bg-white/5 p-2 rounded-lg border border-white/5">
                            <div className="text-[7px] font-mono text-zinc-600 uppercase">Used</div>
                            <div className="text-xs font-mono font-bold text-white flex items-center gap-1">
                              <TrendingUp size={10} className="text-emerald-400" />
                              {skill.times_used}x
                            </div>
                          </div>
                          <div className="bg-white/5 p-2 rounded-lg border border-white/5">
                            <div className="text-[7px] font-mono text-zinc-600 uppercase">Refined</div>
                            <div className="text-xs font-mono font-bold text-white">
                              <RefreshCw size={10} className="text-indigo-400 inline mr-1" />
                              {skill.times_refined}x
                            </div>
                          </div>
                          <div className="bg-white/5 p-2 rounded-lg border border-white/5">
                            <div className="text-[7px] font-mono text-zinc-600 uppercase">Agents</div>
                            <div className="text-xs font-mono font-bold text-purple-400">{skill.authorized_agents.length}</div>
                          </div>
                        </div>

                        {/* Authorized Agents */}
                        <div className="mt-3 pt-3 border-t border-white/5">
                          <div className="flex flex-wrap gap-1">
                            {skill.authorized_agents.map(a => (
                              <span key={a} className="text-[7px] font-mono text-zinc-500 bg-white/5 px-1.5 py-0.5 rounded">{a}</span>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  {/* Patterns Legend */}
                  <div className="bg-zinc-950/80 border border-white/10 rounded-xl p-5 mt-2">
                    <h3 className="text-[9px] font-mono font-black text-white uppercase tracking-widest mb-3">5 ADK Skill Patterns Supported</h3>
                    <div className="grid grid-cols-5 gap-3">
                      {[
                        { name: 'Tool Wrapper', desc: 'Inject expertise on demand', color: 'text-indigo-400' },
                        { name: 'Generator', desc: 'Structured output from templates', color: 'text-purple-400' },
                        { name: 'Reviewer', desc: 'Score against rubric', color: 'text-amber-400' },
                        { name: 'Inversion', desc: 'Agent interviews first', color: 'text-emerald-400' },
                        { name: 'Pipeline', desc: 'Strict sequential workflow', color: 'text-red-400' },
                      ].map(p => (
                        <div key={p.name} className="text-center">
                          <div className={`text-[9px] font-mono font-bold ${p.color} uppercase`}>{p.name}</div>
                          <div className="text-[7px] font-mono text-zinc-600 mt-1">{p.desc}</div>
                        </div>
                      ))}
                    </div>
                  </div>
               </motion.div>
             )}


             {/* === SECURITY TAB (NEW) === */}
             {activeTab === 'security' && (
                <motion.div key="security" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 overflow-y-auto custom-scrollbar">
                   <div className="max-w-5xl mx-auto space-y-8">
                      <div className="flex items-center justify-between border-b border-white/10 pb-6">
                         <div>
                            <h2 className="text-xl font-black text-white tracking-tighter uppercase">DOF Shield Status</h2>
                            <p className="text-[9px] font-mono text-zinc-500 mt-1 tracking-widest uppercase">Cybersecurity Posture // Zero Trust Defense Layer</p>
                         </div>
                         <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/30 px-5 py-3 rounded-2xl">
                            <Shield className="text-emerald-400" size={20} />
                            <span className="text-sm font-mono font-black text-emerald-400 tracking-widest">SHIELD ACTIVE</span>
                         </div>
                      </div>

                      {/* Heartbeats */}
                      <div className="grid grid-cols-2 gap-4">
                        {security?.heartbeats && Object.entries(security.heartbeats).map(([name, hb]: [string, any]) => (
                          <div key={name} className={`border rounded-2xl p-6 ${hb.alive ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-xs font-mono font-black text-white uppercase">{name}</span>
                              {hb.alive ? <CheckCircle size={18} className="text-emerald-400" /> : <XCircle size={18} className="text-red-400" />}
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-[9px] font-mono text-zinc-500 uppercase">Status: <span className={hb.alive ? 'text-emerald-400' : 'text-red-400'}>{hb.alive ? 'ALIVE' : 'DOWN'}</span></div>
                              <div className="text-[9px] font-mono text-zinc-500 uppercase">Latency: <span className="text-indigo-400">{hb.latency_ms}ms</span></div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Security Features Grid */}
                      <div className="grid grid-cols-3 gap-4">
                        {[
                          { label: 'Rate Limiting', value: security?.rate_limiter || '60/min', icon: Clock, color: 'text-indigo-400' },
                          { label: 'Input Sanitization', value: 'XSS + SQLi + PI', icon: Shield, color: 'text-purple-400' },
                          { label: 'CORS Policy', value: security?.cors_policy || 'Restricted', icon: Lock, color: 'text-amber-400' },
                        ].map(feat => (
                          <div key={feat.label} className="bg-zinc-950/80 border border-white/10 rounded-xl p-5">
                            <div className="flex items-center gap-2 mb-3">
                              <feat.icon size={14} className={feat.color} />
                              <span className="text-[9px] font-mono font-bold text-white uppercase">{feat.label}</span>
                            </div>
                            <span className="text-[10px] font-mono text-zinc-400">{feat.value}</span>
                          </div>
                        ))}
                      </div>

                      {/* Security Headers */}
                      <div className="bg-zinc-950/80 border border-white/10 rounded-xl p-6">
                        <h3 className="text-xs font-mono font-black text-white uppercase tracking-widest mb-4">Active Security Headers</h3>
                        <div className="flex flex-wrap gap-2">
                          {(security?.security_headers || []).map((h: string) => (
                            <span key={h} className="bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg text-[9px] font-mono text-emerald-400">{h}</span>
                          ))}
                        </div>
                      </div>

                      {/* Agent Security Levels */}
                      <div className="bg-zinc-950/80 border border-white/10 rounded-xl p-6">
                        <h3 className="text-xs font-mono font-black text-white uppercase tracking-widest mb-4">Agent Security Clearance (8-Level System)</h3>
                        <div className="grid grid-cols-2 gap-2">
                          {(security?.agent_security_levels || []).map((agent: any) => (
                            <div key={agent.agent_id} className="flex items-center justify-between bg-white/[0.02] border border-white/5 p-3 rounded-lg">
                              <span className="text-[10px] font-mono font-bold text-zinc-300 uppercase">{agent.agent_id}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-[8px] font-mono text-zinc-600">{agent.tools.join(', ')}</span>
                                <div className={`px-2 py-0.5 rounded border text-[8px] font-mono font-bold ${securityLevelColor(agent.level)}`}>
                                  LVL {agent.level}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Recent Threats */}
                      <div className="bg-zinc-950/80 border border-white/10 rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xs font-mono font-black text-white uppercase tracking-widest">Audit Log</h3>
                          <span className="text-[9px] font-mono text-zinc-500">{security?.audit_events_total || 0} total events</span>
                        </div>
                        {(security?.recent_threats || []).length === 0 ? (
                          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-400">
                            <CheckCircle size={14} /> No threats detected. All clear.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {(security?.recent_threats || []).map((threat: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-3 bg-red-500/5 border border-red-500/20 p-3 rounded-lg">
                                <AlertTriangle size={14} className="text-red-400 shrink-0" />
                                <div className="flex-1">
                                  <span className="text-[9px] font-mono text-red-400 font-bold uppercase">{threat.event}</span>
                                  <span className="text-[8px] font-mono text-zinc-500 ml-3">{threat.timestamp}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                   </div>
                </motion.div>
              )}


             {/* === LEGION TAB === */}
             {activeTab === 'legion' && (
                <motion.div key="legion" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-8 overflow-y-auto custom-scrollbar">

                   {/* Karma Leaderboard */}
                   <div>
                      <div className="flex justify-between items-center border-b border-white/10 pb-6">
                         <div>
                            <h2 className="text-xl font-black text-white tracking-tighter uppercase">Legion Karma Leaderboard</h2>
                            <p className="text-[9px] font-mono text-zinc-500 mt-1 tracking-widest uppercase">Internal Agent Ranking // Merit-Based Progression</p>
                         </div>
                         <div className="flex items-center gap-3">
                            <div className="bg-purple-600/20 border border-purple-500/30 px-5 py-3 rounded-2xl flex items-center gap-2">
                               <Crown size={16} className="text-purple-400" />
                               <span className="text-[10px] font-mono text-purple-400 font-black uppercase tracking-widest">{karmaBoard.length} Agents</span>
                            </div>
                         </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4 mt-6">
                         {[...karmaBoard].sort((a, b) => b.karma - a.karma).map((agent, idx) => {
                            const levelColors: Record<string, string> = {
                               SOVEREIGN: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
                               ELITE: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
                               VETERAN: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
                               SPECIALIST: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
                               OPERATIVE: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
                               CADET: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30',
                               RECRUIT: 'text-zinc-500 bg-zinc-700/10 border-zinc-700/30',
                            };
                            const lc = levelColors[agent.level] || 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30';

                            return (
                               <motion.div
                                  key={agent.agent_id}
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ delay: idx * 0.04 }}
                                  className="bg-zinc-950/80 border border-white/10 rounded-2xl p-5 relative overflow-hidden group hover:border-purple-500/50 transition-all"
                               >
                                  {idx === 0 && (
                                     <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500/60 to-transparent" />
                                  )}
                                  <div className="flex items-start justify-between mb-3">
                                     <div className="flex flex-col">
                                        <div className="flex items-center gap-2">
                                           <span className="text-[10px] font-mono text-zinc-600 font-bold">#{idx + 1}</span>
                                           <span className="text-sm font-black text-white tracking-tight">{agent.name}</span>
                                        </div>
                                        <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest mt-1">{agent.role}</span>
                                     </div>
                                     <div className={`px-2.5 py-1 rounded-lg border text-[8px] font-mono font-bold uppercase tracking-wider ${lc}`}>
                                        {agent.level}
                                     </div>
                                  </div>

                                  <div className="grid grid-cols-2 gap-2 mt-3">
                                     <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                                        <div className="text-[7px] font-mono text-zinc-600 uppercase">Karma</div>
                                        <div className="text-lg font-mono font-black text-white flex items-center gap-1">
                                           <Star size={12} className="text-purple-400" />
                                           {agent.karma}
                                           <span className="text-[9px] text-purple-500 font-bold">CR</span>
                                        </div>
                                     </div>
                                     <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                                        <div className="text-[7px] font-mono text-zinc-600 uppercase">Recent Actions</div>
                                        <div className="text-lg font-mono font-black text-white flex items-center gap-1">
                                           <Award size={12} className="text-emerald-400" />
                                           {agent.recent_actions?.length || 0}
                                        </div>
                                     </div>
                                  </div>
                               </motion.div>
                            );
                         })}
                      </div>
                   </div>

                   {/* Internal Agent Chat */}
                   <div>
                      <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
                         <div>
                            <h3 className="text-xs font-black text-white tracking-[0.4em] uppercase">Legion Internal Comms</h3>
                            <div className="text-[8px] font-mono text-zinc-600 mt-1 uppercase">{legionChat.length} Messages // Real-Time Agent Chatter</div>
                         </div>
                      </div>

                      <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
                         {legionChat.map((msg, idx) => {
                            const typeBadge: Record<string, string> = {
                               alert: 'text-red-400 bg-red-500/10 border-red-500/30',
                               knowledge: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
                               report: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
                               chat: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30',
                               roast: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
                            };
                            const tb = typeBadge[msg.type] || typeBadge.chat;

                            return (
                               <motion.div
                                  key={msg.id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: idx * 0.02 }}
                                  className="bg-zinc-950/80 border border-white/10 rounded-xl p-4 hover:border-purple-500/20 transition-all"
                               >
                                  <div className="flex items-center justify-between mb-2">
                                     <div className="flex items-center gap-3">
                                        <span className="text-[10px] font-mono font-black text-white uppercase">{msg.from_name}</span>
                                        <span className="text-[8px] font-mono text-zinc-600 uppercase">{msg.role}</span>
                                        <span className={`px-2 py-0.5 rounded border text-[7px] font-mono font-bold uppercase tracking-wider ${tb}`}>{msg.type}</span>
                                     </div>
                                     <div className="flex items-center gap-3">
                                        <span className="text-[8px] font-mono text-zinc-600">{msg.timestamp}</span>
                                        <span className="text-[8px] font-mono text-purple-400 font-bold">{msg.karma_at_time} CR</span>
                                     </div>
                                  </div>
                                  <p className="text-[11px] font-mono text-zinc-300 leading-relaxed">{msg.content}</p>
                               </motion.div>
                            );
                         })}

                         {legionChat.length === 0 && (
                            <div className="flex-1 flex items-center justify-center py-12">
                               <div className="text-center">
                                  <Crown size={48} className="text-zinc-800 mx-auto mb-4" />
                                  <p className="text-sm font-mono text-zinc-600">No internal comms yet. Agents are silent.</p>
                               </div>
                            </div>
                         )}
                      </div>
                   </div>

                </motion.div>
              )}

             {/* === HACKATHON TAB === */}
             {activeTab === 'hackathon' && (
                <motion.div key="hackathon" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full p-8 flex flex-col gap-8 overflow-y-auto custom-scrollbar">

                   {/* Hero */}
                   <div className="relative overflow-hidden rounded-3xl border border-purple-500/30 bg-gradient-to-br from-purple-900/20 via-zinc-950 to-indigo-900/20 p-8">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-indigo-500 to-emerald-500" />
                      <div className="flex items-start justify-between">
                         <div>
                            <div className="flex items-center gap-3 mb-2">
                               <span className="text-[10px] font-mono text-purple-400 bg-purple-500/20 border border-purple-500/30 px-3 py-1 rounded-full font-bold uppercase tracking-widest">Synthesis 2026</span>
                               <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/20 border border-emerald-500/30 px-3 py-1 rounded-full font-bold uppercase tracking-widest">ERC-8004 #31013</span>
                            </div>
                            <h1 className="text-3xl font-black text-white tracking-tight mt-4">DOF Agent #1686</h1>
                            <p className="text-sm font-mono text-zinc-400 mt-2 max-w-2xl">Deterministic Observability Framework — Math-verified, blockchain-attested AI agent governance. Every action governed by rules, verified by Z3 proofs, recorded on-chain.</p>
                         </div>
                         <div className="flex gap-4">
                            <StatusRing value={100} label="Z3 Proofs" color="stroke-emerald-500" />
                            <StatusRing value={77} label="Gov Score" color="stroke-purple-500" />
                         </div>
                      </div>
                   </div>

                   {/* Stats Grid */}
                   <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                         { label: 'Autonomous Cycles', value: '238+', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30' },
                         { label: 'On-Chain Attestations', value: '38+', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
                         { label: 'Z3 Theorems Proven', value: '4/4', color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/30' },
                         { label: 'Unit Tests', value: '986', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' },
                      ].map((stat) => (
                         <div key={stat.label} className={`border rounded-2xl p-5 ${stat.bg}`}>
                            <div className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest">{stat.label}</div>
                            <div className={`text-2xl font-black mt-1 ${stat.color}`}>{stat.value}</div>
                         </div>
                      ))}
                   </div>

                   {/* Tracks */}
                   <div>
                      <h2 className="text-lg font-black text-white tracking-tight uppercase mb-4">Hackathon Tracks</h2>
                      <p className="text-xs font-mono text-zinc-500 mb-6">10 tracks with on-chain verification and live agent demonstrations.</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                         {[
                            { track: 'Synthesis Open Track', partner: 'Synthesis', prize: '$28,308', desc: 'Full DOF demo — governance, Z3 proofs, on-chain attestations, 14-agent swarm', status: 'ACTIVE', color: 'border-purple-500/50 bg-purple-500/5', iconBg: 'bg-purple-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>) },
                            { track: 'ERC-8004 Agent Receipts', partner: 'ERC-8004', prize: '$4,000', desc: 'On-chain receipts for every agent action — Z3 proof hashes published to Avalanche & Base', status: 'ACTIVE', color: 'border-emerald-500/50 bg-emerald-500/5', iconBg: 'bg-emerald-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12l2 2 4-4"/></svg>) },
                            { track: 'Let the Agent Cook', partner: 'Synthesis', prize: '$4,000', desc: '238+ autonomous cycles, zero human input — GLADIATOR loop with safety guardrails', status: 'ACTIVE', color: 'border-indigo-500/50 bg-indigo-500/5', iconBg: 'bg-indigo-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="currentColor"><path d="M12 2a5 5 0 015 5c0 2.76-2.24 5-5 5s-5-2.24-5-5a5 5 0 015-5zm0 12c5.52 0 10 2.24 10 5v3H2v-3c0-2.76 4.48-5 10-5z"/></svg>) },
                            { track: 'Private Agents', partner: 'Nillion / Lit Protocol', prize: '$11,500', desc: 'Privacy-preserving agent governance — deterministic rules enforce data boundaries without exposing internals', status: 'ACTIVE', color: 'border-rose-500/50 bg-rose-500/5', iconBg: 'bg-rose-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>) },
                            { track: 'Agent Services on Base', partner: 'Base (Coinbase)', prize: '$5,000', desc: 'ERC-8004 identity minted on Base — agent receipts and proof hashes anchored on-chain', status: 'ACTIVE', color: 'border-blue-500/50 bg-blue-500/5', iconBg: 'bg-blue-600', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8" stroke="white" strokeWidth="2" fill="none"/></svg>) },
                            { track: 'Best Agent on Celo', partner: 'Celo', prize: '$5,000', desc: 'Multi-chain attestation support — DOF agents publish governance proofs across EVM chains', status: 'ACTIVE', color: 'border-yellow-500/50 bg-yellow-500/5', iconBg: 'bg-yellow-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="currentColor"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4" fill="none" stroke="white" strokeWidth="2"/></svg>) },
                            { track: 'ERC-8183 Intent Protocol', partner: 'ERC-8183', prize: '$2,000', desc: 'Agent intent declarations verified by Z3 proofs before on-chain execution', status: 'ACTIVE', color: 'border-cyan-500/50 bg-cyan-500/5', iconBg: 'bg-cyan-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>) },
                            { track: 'Best Self Protocol', partner: 'Self Protocol', prize: '$1,000', desc: 'Self-sovereign agent identity with deterministic trust scoring and on-chain reputation', status: 'ACTIVE', color: 'border-orange-500/50 bg-orange-500/5', iconBg: 'bg-orange-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>) },
                            { track: 'Agents That Pay', partner: 'x402 Protocol', prize: '$1,500', desc: 'Autonomous payment flows governed by constitution rules — MPP pattern with safety guardrails', status: 'ACTIVE', color: 'border-teal-500/50 bg-teal-500/5', iconBg: 'bg-teal-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>) },
                            { track: 'Mechanism Design', partner: 'Flashbots / MEV', prize: '$1,000', desc: 'Game-theoretic governance mechanisms — formal verification of agent incentive alignment', status: 'ACTIVE', color: 'border-fuchsia-500/50 bg-fuchsia-500/5', iconBg: 'bg-fuchsia-500', icon: (<svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>) },
                         ].map((t) => (
                            <div key={t.track} className={`border rounded-2xl p-5 ${t.color} hover:scale-[1.02] transition-transform cursor-pointer group`}>
                               <div className="flex items-center gap-3 mb-4">
                                  <div className={`w-8 h-8 rounded-lg ${t.iconBg} flex items-center justify-center flex-shrink-0`}>
                                     {t.icon}
                                  </div>
                                  <span className="text-xs font-mono text-zinc-400">{t.partner}</span>
                               </div>
                               <div className="flex items-center justify-between mb-2">
                                  <h3 className="text-sm font-black text-white">{t.track}</h3>
                                  <span className="text-sm font-black text-white">{t.prize}</span>
                               </div>
                               <p className="text-[10px] font-mono text-zinc-500 mt-2 leading-relaxed">{t.desc}</p>
                               <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
                                  <span className="text-[8px] font-mono text-emerald-400 font-bold uppercase tracking-wider">{t.status}</span>
                                  <ArrowUpRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-white transition-colors" />
                               </div>
                            </div>
                         ))}
                      </div>
                   </div>

                   {/* Pipeline */}
                   <div>
                      <h2 className="text-lg font-black text-white tracking-tight uppercase mb-4">DOF Pipeline</h2>
                      <div className="flex items-center gap-2 overflow-x-auto pb-2">
                         {['Identity (ERC-8004)', 'Task Input', 'LLM Analysis', 'Governance Check', 'Z3 Proof', 'On-Chain TX', 'Supervisor', 'Output'].map((step, i) => (
                            <React.Fragment key={step}>
                               <div className="bg-zinc-950/80 border border-white/10 rounded-xl px-4 py-3 text-center min-w-[120px] hover:border-purple-500/50 transition-all">
                                  <div className="text-[8px] font-mono text-zinc-600 uppercase">Step {i + 1}</div>
                                  <div className="text-[10px] font-mono font-bold text-white mt-1">{step}</div>
                               </div>
                               {i < 7 && <ArrowUpRight size={14} className="text-purple-500/50 flex-shrink-0 rotate-45" />}
                            </React.Fragment>
                         ))}
                      </div>
                   </div>

                   {/* On-Chain Evidence */}
                   <div>
                      <h2 className="text-lg font-black text-white tracking-tight uppercase mb-4">On-Chain Evidence</h2>
                      <div className="space-y-3">
                         {[
                            { label: 'ERC-8004 Registration', chain: 'Base Mainnet', hash: '0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4', url: 'https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4' },
                            { label: 'DOF Proof Registry', chain: 'Avalanche C-Chain', hash: '0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6', url: 'https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6' },
                            { label: 'Attestation Wrapper', chain: 'Base Mainnet', hash: '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432', url: 'https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432' },
                         ].map((evidence) => (
                            <a key={evidence.label} href={evidence.url} target="_blank" rel="noopener noreferrer"
                               className="flex items-center justify-between bg-zinc-950/80 border border-white/10 rounded-xl p-4 hover:border-purple-500/30 transition-all group">
                               <div>
                                  <div className="text-[10px] font-mono font-bold text-white">{evidence.label}</div>
                                  <div className="text-[8px] font-mono text-zinc-600 mt-1">{evidence.chain}</div>
                               </div>
                               <div className="flex items-center gap-2">
                                  <span className="text-[9px] font-mono text-zinc-500 group-hover:text-purple-400 transition-colors">{evidence.hash.slice(0, 12)}...{evidence.hash.slice(-6)}</span>
                                  <ArrowUpRight size={14} className="text-zinc-600 group-hover:text-purple-400 transition-colors" />
                               </div>
                            </a>
                         ))}
                      </div>
                   </div>

                   {/* Tech Stack */}
                   <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {['Z3 Theorem Prover', 'Solidity / EVM', 'LiteLLM Router', 'JSONL Audit Logs', 'ChromaDB Memory', 'web3.py', 'Next.js Dashboard', 'ERC-8004 Identity'].map((tech) => (
                         <div key={tech} className="bg-zinc-950/60 border border-white/5 rounded-lg px-3 py-2 text-center">
                            <span className="text-[9px] font-mono text-zinc-400">{tech}</span>
                         </div>
                      ))}
                   </div>

                   {/* Pitch */}
                   <div className="border border-white/10 rounded-2xl p-6 bg-gradient-to-r from-purple-900/10 to-transparent">
                      <p className="text-sm font-mono text-zinc-300 italic leading-relaxed">
                         &ldquo;Agent acted autonomously. Math proved it. Blockchain recorded it.&rdquo;
                      </p>
                      <div className="flex gap-4 mt-4">
                         <a href="https://github.com/Cyberpaisa/deterministic-observability-framework/tree/hackathon" target="_blank" rel="noopener noreferrer"
                            className="text-[9px] font-mono text-purple-400 hover:text-white transition-colors uppercase tracking-widest">GitHub Repo &rarr;</a>
                         <a href="https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4" target="_blank" rel="noopener noreferrer"
                            className="text-[9px] font-mono text-emerald-400 hover:text-white transition-colors uppercase tracking-widest">Base TX &rarr;</a>
                         <a href="https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6" target="_blank" rel="noopener noreferrer"
                            className="text-[9px] font-mono text-indigo-400 hover:text-white transition-colors uppercase tracking-widest">Avalanche Contract &rarr;</a>
                      </div>
                   </div>

                </motion.div>
              )}

           </AnimatePresence>
        </section>

        {/* Right HUD Panels */}
        <aside className="col-span-3 border-l border-white/5 bg-zinc-950/40 p-6 flex flex-col gap-6 overflow-y-auto">

            <div className="space-y-6">
               <div className="text-[10px] font-black text-zinc-500 tracking-[0.5em] mb-4 uppercase border-b border-white/5 pb-2">Vital Telemetry</div>
               <div className="grid grid-cols-1 gap-6 py-4">
                  <div className="flex justify-around items-center bg-white/[0.02] border border-white/5 py-6 rounded-2xl backdrop-blur-sm">
                    <StatusRing value={Math.round(stats.cpu_percent || 0)} label="CPU" color="stroke-indigo-500" />
                    <StatusRing value={Math.round(stats.memory_percent || 0)} label="RAM" color="stroke-purple-500" />
                    <StatusRing value={Math.round(stats.neural_sync || 0)} label="Neural" color="stroke-emerald-500" />
                  </div>
               </div>

               {/* Hardware Info */}
               <div className="bg-zinc-950/80 border border-white/10 p-4 rounded-xl flex flex-col gap-3">
                  <div className="flex justify-between items-center text-[8px] font-mono text-zinc-500 uppercase tracking-widest">
                    <span>Inference Engine</span>
                    <span className="text-emerald-500">LOCAL</span>
                  </div>
                  <div className="flex items-end justify-between">
                    <span className="text-lg font-black text-white">Ollama Llama3</span>
                    <span className="text-[9px] font-mono text-indigo-400">{stats.memory_total || '?'}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <div className="bg-white/5 p-2 rounded-lg">
                      <div className="text-[7px] font-mono text-zinc-600 uppercase">Calls</div>
                      <div className="text-xs font-mono font-bold text-white">{stats.ollama_calls || 0}</div>
                    </div>
                    <div className="bg-white/5 p-2 rounded-lg">
                      <div className="text-[7px] font-mono text-zinc-600 uppercase">Avg Latency</div>
                      <div className="text-xs font-mono font-bold text-white">{stats.ollama_avg_latency_ms || 0}ms</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-white/5 p-2 rounded-lg">
                      <div className="text-[7px] font-mono text-zinc-600 uppercase">CPU Cores</div>
                      <div className="text-xs font-mono font-bold text-white">{stats.cpu_count_physical || '?'}P/{stats.cpu_count || '?'}L</div>
                    </div>
                    <div className="bg-white/5 p-2 rounded-lg">
                      <div className="text-[7px] font-mono text-zinc-600 uppercase">Available</div>
                      <div className="text-xs font-mono font-bold text-emerald-400">{stats.memory_available || '?'}</div>
                    </div>
                  </div>
               </div>
            </div>

            {/* Sovereign Registry */}
            <div className="bg-gradient-to-br from-zinc-900/80 to-black border border-white/10 rounded-2xl p-5 relative overflow-hidden">
               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500/60 to-transparent" />
               <div className="flex items-center gap-3 mb-6">
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-ping" />
                  <span className="text-[9px] font-black text-white tracking-[0.3em] uppercase">System Status</span>
               </div>
               <div className="space-y-2">
                 {[
                   { name: 'Autonomous Loop', val: stats.autonomous_cycle ? `Cycle ${stats.autonomous_cycle}` : 'OFFLINE', color: stats.autonomous_cycle ? 'text-emerald-400' : 'text-zinc-600' },
                   { name: 'DOF Shield', val: 'ACTIVE', color: 'text-emerald-400' },
                   { name: 'x402 Settlement', val: stats.x402_facilitator || 'PENDING', color: 'text-amber-400' },
                   { name: 'Agents Online', val: `${stats.agents_active || 0}/${stats.agents_total || 14}`, color: 'text-indigo-400' },
                 ].map(tool => (
                   <div key={tool.name} className="flex items-center justify-between p-2 bg-white/5 border border-white/5 rounded-lg">
                      <span className="text-[8px] font-mono font-bold text-zinc-500 uppercase">{tool.name}</span>
                      <span className={`text-[8px] font-mono font-bold ${tool.color}`}>{tool.val}</span>
                   </div>
                 ))}
               </div>

               <div className="mt-6 pt-4 border-t border-white/10">
                  <div className="flex justify-between items-end">
                     <div className="flex flex-col gap-1">
                        <span className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest">Karma Balance</span>
                        <span className="text-3xl font-black text-white tracking-tighter">{stats.total_karma || 0}<span className="text-sm font-mono text-purple-500 ml-1">CR</span></span>
                     </div>
                  </div>
               </div>
            </div>

            {/* Uptime */}
            <div className="bg-white/[0.02] border border-white/5 p-4 rounded-xl text-center">
               <span className="text-[7px] font-mono text-zinc-600 uppercase tracking-[0.5em]">System Uptime</span>
               <div className="text-lg font-mono font-black text-white mt-1">{stats.uptime || '...'}</div>
               <span className="text-[7px] font-mono text-zinc-700 uppercase">Boot: {stats.boot_time || '?'}</span>
            </div>
         </aside>

      </main>

      <style jsx global>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
        .pause { animation-play-state: paused; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #52525b; }
      `}</style>
    </div>
  );
}
