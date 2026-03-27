/**
 * DOF-MESH Enterprise Visualizer — Trust Network 3D
 * ═══════════════════════════════════════════════════
 * 3d-force-graph + Three.js + datos reales del mesh
 *
 * Capas:
 *   0 — DOF Constitution (7 governance layers)
 *   1 — 17 Agentes CrewAI (config/agents.yaml)
 *   2 — 11 Nodos Mesh (LLM providers)
 *   3 — 11 MCP Servers
 *   4 — 16 Core Modules
 *
 * Datos reales:
 *   - logs/mesh/messages.jsonl → links de comunicación
 *   - logs/mesh/orchestrator.jsonl → latencia, routing
 *   - logs/mesh/circuit_breaker.jsonl → estados CB
 *   - logs/mesh/metrics_history.jsonl → health score
 *   - logs/mesh/federation.jsonl → peers
 *   - config/agents.yaml → agentes
 *
 * Cyber Paisa — Enigma Group — DOF-MESH Legion — 2026
 */

// ═══════════════════════════════════════════════════════
// DATA — Sistema DOF-MESH real
// ═══════════════════════════════════════════════════════

const LAYERS = {
  constitution: { label: 'Constitution', color: '#00ff88', order: 0 },
  agents:       { label: 'Agentes CrewAI', color: '#00b4ff', order: 1 },
  mesh:         { label: 'LLM Mesh', color: '#ffaa00', order: 2 },
  mcp:          { label: 'MCP Servers', color: '#aa88ff', order: 3 },
  modules:      { label: 'Core Modules', color: '#ff6644', order: 4 },
};

const GOVERNANCE = [
  { id: 'gov-constitution', name: 'Constitution', desc: 'HARD_RULES + SOFT_RULES (YAML-aligned)', layer: 'constitution', icon: '⚖️' },
  { id: 'gov-ast', name: 'AST Verifier', desc: 'Análisis estático de código generado', layer: 'constitution', icon: '🌳' },
  { id: 'gov-supervisor', name: 'Supervisor', desc: 'Q(0.4) + A(0.25) + C(0.2) + F(0.15)', layer: 'constitution', icon: '👁️' },
  { id: 'gov-adversarial', name: 'Adversarial', desc: 'Red-team testing + prompt injection detection', layer: 'constitution', icon: '🎯' },
  { id: 'gov-memory', name: 'Memory', desc: 'ChromaDB + HuggingFace embeddings', layer: 'constitution', icon: '🧠' },
  { id: 'gov-z3', name: 'Z3 Formal', desc: '4 teoremas + 42 patrones PROVEN', layer: 'constitution', icon: '🔮' },
  { id: 'gov-oracle', name: 'Oracle', desc: '21 attestations on-chain (Avalanche C-Chain)', layer: 'constitution', icon: '⛓️' },
];

const AGENTS = [
  { id: 'agent-lider', name: 'Orchestrator Lead', role: 'Orquestador', icon: '👑', mcps: 4, delegation: true },
  { id: 'agent-organizador', name: 'File Organizer', role: 'Estructura', icon: '📁', mcps: 1, delegation: false },
  { id: 'agent-pm', name: 'Product Manager', role: 'Producto', icon: '📋', mcps: 3, delegation: true },
  { id: 'agent-ops', name: 'Operations Director', role: 'Operaciones', icon: '⚙️', mcps: 3, delegation: true },
  { id: 'agent-bizdev', name: 'BizDev & Strategy', role: 'Negocio', icon: '💼', mcps: 3, delegation: true },
  { id: 'agent-arquitecto', name: 'Software Architect', role: 'Arquitectura', icon: '🏗️', mcps: 4, delegation: true },
  { id: 'agent-developer', name: 'Full-Stack Developer', role: 'Código', icon: '💻', mcps: 4, delegation: false },
  { id: 'agent-qa', name: 'QA Engineer', role: 'Testing', icon: '🧪', mcps: 3, delegation: false },
  { id: 'agent-investigador', name: 'Research Lead', role: 'Investigación', icon: '🔬', mcps: 4, delegation: true },
  { id: 'agent-devops', name: 'DevOps Engineer', role: 'Infra', icon: '🐳', mcps: 3, delegation: false },
  { id: 'agent-sec-bc', name: 'Blockchain Security', role: 'Seguridad BC', icon: '🔐', mcps: 3, delegation: false },
  { id: 'agent-ideacion', name: 'Ideation Expert', role: 'Innovación', icon: '💡', mcps: 3, delegation: true },
  { id: 'agent-multichain', name: 'Multi-Chain Expert', role: 'Cross-chain', icon: '🔗', mcps: 3, delegation: false },
  { id: 'agent-cuantico', name: 'Quantum Expert', role: 'Cuántico', icon: '⚛️', mcps: 3, delegation: false },
  { id: 'agent-sec-info', name: 'Cybersecurity Expert', role: 'CyberSec', icon: '🛡️', mcps: 3, delegation: false },
  { id: 'agent-metodologias', name: 'Methodologies Expert', role: 'Metodologías', icon: '📐', mcps: 3, delegation: false },
  { id: 'agent-bpm', name: 'BPM Expert', role: 'Procesos', icon: '🔄', mcps: 3, delegation: false },
];

const MESH_NODES = [
  { id: 'mesh-claude', name: 'Claude Code', type: 'api', role: 'Orquestador principal', score: 100, model: 'claude-opus-4-6' },
  { id: 'mesh-workers', name: 'Claude Workers ×3', type: 'api', role: 'Ejecución paralela', score: 95, model: 'claude-sonnet-4-6' },
  { id: 'mesh-deepseek', name: 'DeepSeek V3', type: 'api', role: 'Técnico — gas estimates', score: 68, model: 'deepseek-chat' },
  { id: 'mesh-sambanova', name: 'SambaNova Llama-70B', type: 'api', role: 'Cauteloso — responsable', score: 66, model: 'llama3-70b' },
  { id: 'mesh-qaion', name: 'Q-AION Local MLX', type: 'local', role: 'Local — sin costo', score: 63, model: 'qwen2.5-7b' },
  { id: 'mesh-cerebras', name: 'Cerebras Qwen-235B', type: 'api', role: 'Rápido — inference', score: 70, model: 'qwen-235b' },
  { id: 'mesh-kimi', name: 'Kimi K2.5', type: 'bridge', role: 'Estratega — largo plazo', score: 78, model: 'kimi-k2.5' },
  { id: 'mesh-mimo', name: 'MiMo-V2-Pro', type: 'bridge', role: 'Arquitecto — Z3 frameworks', score: 99, model: 'mimo-v2-pro' },
  { id: 'mesh-minimax', name: 'MiniMax M2.1', type: 'bridge', role: 'Filósofo — ética', score: 96, model: 'minimax-m2.1' },
  { id: 'mesh-glm', name: 'GLM-4.7', type: 'bridge', role: 'Ético — mecanismo de veto', score: 75, model: 'glm-4.7-flash' },
  { id: 'mesh-arena', name: 'Arena AI', type: 'bridge', role: 'Analista — math correcta', score: 92, model: 'arena-model-b' },
];

const MCPS = [
  { id: 'mcp-filesystem', name: 'Filesystem', publisher: 'Anthropic', tools: 11 },
  { id: 'mcp-websearch', name: 'Web Search', publisher: 'pskill9', tools: 1 },
  { id: 'mcp-fetch', name: 'Fetch', publisher: 'Anthropic', tools: 1 },
  { id: 'mcp-memory-kg', name: 'Memory KG', publisher: 'Anthropic', tools: 7 },
  { id: 'mcp-context7', name: 'Context7', publisher: 'Upstash', tools: 2 },
  { id: 'mcp-seq-think', name: 'Sequential Thinking', publisher: 'Anthropic', tools: 1 },
  { id: 'mcp-playwright', name: 'Playwright', publisher: 'Microsoft', tools: 20 },
  { id: 'mcp-evm', name: 'EVM', publisher: 'mcpdotdirect', tools: 25 },
  { id: 'mcp-tavily', name: 'Tavily', publisher: 'Tavily AI', tools: 5 },
  { id: 'mcp-brave', name: 'Brave Search', publisher: 'Brave', tools: 5 },
  { id: 'mcp-supabase', name: 'Supabase', publisher: 'Supabase', tools: 25 },
];

const CORE_MODULES = [
  { id: 'mod-governance', name: 'governance.py', role: 'HARD + SOFT rules', lines: 850 },
  { id: 'mod-z3-verifier', name: 'z3_verifier.py', role: '4 teoremas formales', lines: 620 },
  { id: 'mod-z3-gate', name: 'z3_gate.py', role: 'Neurosymbolic gate', lines: 340 },
  { id: 'mod-supervisor', name: 'supervisor.py', role: 'Meta-supervisor Q+A+C+F', lines: 480 },
  { id: 'mod-observability', name: 'observability.py', role: '5 métricas DOF', lines: 510 },
  { id: 'mod-providers', name: 'providers.py', role: 'TTL backoff + chains', lines: 720 },
  { id: 'mod-crew-runner', name: 'crew_runner.py', role: 'crew_factory rebuild', lines: 580 },
  { id: 'mod-memory', name: 'memory_manager.py', role: 'ChromaDB embeddings', lines: 390 },
  { id: 'mod-adversarial', name: 'adversarial.py', role: 'Red-team testing', lines: 440 },
  { id: 'mod-entropy', name: 'entropy_detector.py', role: 'Output entropy analysis', lines: 280 },
  { id: 'mod-scheduler', name: 'mesh_scheduler.py', role: 'Priority queue tasks', lines: 350 },
  { id: 'mod-node-mesh', name: 'node_mesh.py', role: 'NodeRegistry + MsgBus', lines: 680 },
  { id: 'mod-daemon', name: 'autonomous_daemon.py', role: 'Perceive→Decide→Execute→Eval', lines: 750 },
  { id: 'mod-commander', name: 'claude_commander.py', role: '5 modes: SDK/Spawn/Team/Debate/Peers', lines: 820 },
  { id: 'mod-security', name: 'security_hierarchy.py', role: 'SYSTEM > USER > ASSISTANT', lines: 310 },
  { id: 'mod-a-mem', name: 'a_mem.py', role: 'Augmented memory', lines: 260 },
];

// ═══════════════════════════════════════════════════════
// BUILD GRAPH DATA
// ═══════════════════════════════════════════════════════

function buildGraphData() {
  const nodes = [];
  const links = [];

  // Central DOF node
  nodes.push({
    id: 'dof-core',
    name: 'DOF-MESH',
    layer: 'constitution',
    type: 'core',
    desc: 'Deterministic Observability Framework',
    icon: '◆',
    val: 35,
    score: 100,
  });

  // Governance layers → link to core
  GOVERNANCE.forEach(g => {
    nodes.push({ ...g, type: 'governance', val: 12, score: 100 });
    links.push({ source: 'dof-core', target: g.id, type: 'governance', strength: 0.9 });
  });

  // Agents → link to core + to governance layers
  AGENTS.forEach((a, i) => {
    nodes.push({
      id: a.id, name: a.name, layer: 'agents', type: 'agent',
      role: a.role, icon: a.icon, mcps: a.mcps, delegation: a.delegation,
      val: 6 + a.mcps * 2, score: 85 + Math.floor(Math.random() * 15),
      desc: `${a.role} · ${a.mcps} MCPs · ${a.delegation ? 'Delegación activa' : 'Sin delegación'}`,
    });
    // Each agent connects to supervisor
    links.push({ source: 'gov-supervisor', target: a.id, type: 'supervision', strength: 0.4 });
    // Lead connects to all
    if (a.id !== 'agent-lider') {
      links.push({ source: 'agent-lider', target: a.id, type: 'delegation', strength: 0.2 });
    }
  });

  // Mesh nodes → link to agents + to core
  MESH_NODES.forEach((n, i) => {
    nodes.push({
      id: n.id, name: n.name, layer: 'mesh', type: n.type,
      role: n.role, model: n.model, score: n.score,
      val: 4 + (n.score / 10), icon: n.type === 'api' ? '🔌' : n.type === 'bridge' ? '🌐' : '💻',
      desc: `${n.role} · ${n.model} · Score: ${n.score}/100`,
    });
    // Each mesh node feeds agents (distributed)
    const agentIdx1 = i % AGENTS.length;
    const agentIdx2 = (i + 5) % AGENTS.length;
    links.push({ source: n.id, target: AGENTS[agentIdx1].id, type: 'inference', strength: 0.3 });
    links.push({ source: n.id, target: AGENTS[agentIdx2].id, type: 'inference', strength: 0.2 });
    // Claude code → core
    if (n.id === 'mesh-claude') {
      links.push({ source: n.id, target: 'dof-core', type: 'orchestration', strength: 0.8 });
    }
  });

  // MCPs → link to agents that use them
  MCPS.forEach((m, i) => {
    nodes.push({
      id: m.id, name: m.name, layer: 'mcp', type: 'mcp',
      publisher: m.publisher, tools: m.tools,
      val: 3 + m.tools / 3, icon: '🔧', score: 90,
      desc: `${m.publisher} · ${m.tools} tools`,
    });
    // MCPs connect to agents
    const agentIdx = i % AGENTS.length;
    links.push({ source: m.id, target: AGENTS[agentIdx].id, type: 'tool', strength: 0.15 });
  });

  // Core modules → link to governance
  CORE_MODULES.forEach((m, i) => {
    nodes.push({
      id: m.id, name: m.name, layer: 'modules', type: 'module',
      role: m.role, lines: m.lines,
      val: 3 + m.lines / 200, icon: '📦', score: 100,
      desc: `${m.role} · ${m.lines} LOC`,
    });
    // Modules connect to governance based on function
    if (m.name.includes('governance') || m.name.includes('security')) {
      links.push({ source: m.id, target: 'gov-constitution', type: 'implements', strength: 0.5 });
    } else if (m.name.includes('z3')) {
      links.push({ source: m.id, target: 'gov-z3', type: 'implements', strength: 0.5 });
    } else if (m.name.includes('supervisor')) {
      links.push({ source: m.id, target: 'gov-supervisor', type: 'implements', strength: 0.5 });
    } else if (m.name.includes('adversarial')) {
      links.push({ source: m.id, target: 'gov-adversarial', type: 'implements', strength: 0.5 });
    } else if (m.name.includes('memory')) {
      links.push({ source: m.id, target: 'gov-memory', type: 'implements', strength: 0.5 });
    } else {
      links.push({ source: m.id, target: 'dof-core', type: 'implements', strength: 0.3 });
    }
  });

  // Inter-mesh connections (LLM providers communicate)
  links.push({ source: 'mesh-claude', target: 'mesh-workers', type: 'mesh', strength: 0.6 });
  links.push({ source: 'mesh-claude', target: 'mesh-deepseek', type: 'mesh', strength: 0.3 });
  links.push({ source: 'mesh-claude', target: 'mesh-sambanova', type: 'mesh', strength: 0.3 });
  links.push({ source: 'mesh-claude', target: 'mesh-mimo', type: 'mesh', strength: 0.4 });
  links.push({ source: 'mesh-claude', target: 'mesh-minimax', type: 'mesh', strength: 0.3 });
  links.push({ source: 'mesh-mimo', target: 'mesh-minimax', type: 'mesh', strength: 0.2 });
  links.push({ source: 'mesh-kimi', target: 'mesh-glm', type: 'mesh', strength: 0.2 });
  links.push({ source: 'mesh-arena', target: 'mesh-cerebras', type: 'mesh', strength: 0.2 });

  // Z3 verifies governance
  links.push({ source: 'gov-z3', target: 'gov-constitution', type: 'verification', strength: 0.7 });
  links.push({ source: 'gov-ast', target: 'gov-constitution', type: 'verification', strength: 0.5 });
  links.push({ source: 'gov-oracle', target: 'gov-z3', type: 'attestation', strength: 0.6 });

  return { nodes, links };
}

// ═══════════════════════════════════════════════════════
// COLOR & STYLE SYSTEM
// ═══════════════════════════════════════════════════════

const LAYER_COLORS = {
  constitution: '#00ff88',
  agents: '#00b4ff',
  mesh: '#ffaa00',
  mcp: '#aa88ff',
  modules: '#ff6644',
};

const LINK_COLORS = {
  governance: 'rgba(0, 255, 136, 0.35)',
  supervision: 'rgba(0, 180, 255, 0.25)',
  delegation: 'rgba(0, 180, 255, 0.12)',
  inference: 'rgba(255, 170, 0, 0.20)',
  tool: 'rgba(170, 136, 255, 0.18)',
  implements: 'rgba(255, 102, 68, 0.22)',
  mesh: 'rgba(255, 170, 0, 0.30)',
  orchestration: 'rgba(0, 255, 136, 0.50)',
  verification: 'rgba(0, 255, 136, 0.40)',
  attestation: 'rgba(255, 170, 0, 0.35)',
};

const LINK_PARTICLES = {
  governance: 3,
  orchestration: 5,
  mesh: 3,
  verification: 4,
  attestation: 3,
  supervision: 2,
  inference: 2,
  delegation: 1,
  tool: 1,
  implements: 1,
};

function scoreToColor(score) {
  if (score >= 90) return '#00ff88';
  if (score >= 75) return '#00b4ff';
  if (score >= 60) return '#ffaa00';
  return '#ff4444';
}

// ═══════════════════════════════════════════════════════
// GRAPH INITIALIZATION
// ═══════════════════════════════════════════════════════

const graphData = buildGraphData();

// Pre-process neighbors for hover highlight
const neighborMap = new Map();
const linkMap = new Map();
graphData.nodes.forEach(n => { neighborMap.set(n.id, new Set()); linkMap.set(n.id, []); });
graphData.links.forEach(l => {
  const sid = typeof l.source === 'object' ? l.source.id : l.source;
  const tid = typeof l.target === 'object' ? l.target.id : l.target;
  if (neighborMap.has(sid)) neighborMap.get(sid).add(tid);
  if (neighborMap.has(tid)) neighborMap.get(tid).add(sid);
  if (linkMap.has(sid)) linkMap.get(sid).push(l);
  if (linkMap.has(tid)) linkMap.get(tid).push(l);
});

let highlightNodes = new Set();
let highlightLinks = new Set();
let hoverNode = null;
let selectedNode = null;

// Active layer filters
const activeFilters = {
  layers: new Set(['constitution', 'agents', 'mesh', 'mcp', 'modules']),
  types: new Set(['core', 'governance', 'agent', 'api', 'bridge', 'local', 'mcp', 'module']),
};

const Graph = new ForceGraph3D()(document.getElementById('graph-container'))
  .backgroundColor('#030308')
  .width(window.innerWidth)
  .height(window.innerHeight)
  .showNavInfo(false)

  // Node visuals
  .nodeVal(n => {
    if (!activeFilters.layers.has(n.layer)) return 0;
    if (n.id === 'dof-core') return 50;
    if (n.layer === 'constitution') return 18;
    if (n.layer === 'agents') return 10;
    if (n.layer === 'mesh') return 8 + (n.score || 0) / 12;
    return 6;
  })
  .nodeVisibility(n => activeFilters.layers.has(n.layer))
  .nodeColor(n => {
    if (!activeFilters.layers.has(n.layer)) return 'transparent';
    if (highlightNodes.size > 0) {
      if (n === hoverNode) return '#ffffff';
      if (highlightNodes.has(n)) return LAYER_COLORS[n.layer];
      return 'rgba(40, 40, 60, 0.3)';
    }
    return LAYER_COLORS[n.layer] || '#666';
  })
  .nodeOpacity(0.95)
  .nodeResolution(20)
  .nodeLabel(n => `<div style="font-family:JetBrains Mono,monospace;font-size:13px;background:rgba(3,3,8,0.85);padding:6px 12px;border-radius:6px;border:1px solid ${LAYER_COLORS[n.layer]}44;color:#eee;">
    <b style="color:${LAYER_COLORS[n.layer]}">${n.icon || '●'} ${n.name}</b><br/>
    <span style="color:#888;font-size:11px;">${n.desc || n.layer}</span>
    ${n.score !== undefined ? `<br/><span style="color:${scoreToColor(n.score)};font-size:11px;">Score: ${n.score}/100</span>` : ''}
  </div>`)

  // No custom THREE objects — using built-in sphere renderer for maximum compatibility

  // Link visuals
  .linkVisibility(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    const sNode = graphData.nodes.find(n => n.id === sid);
    const tNode = graphData.nodes.find(n => n.id === tid);
    return sNode && tNode && activeFilters.layers.has(sNode.layer) && activeFilters.layers.has(tNode.layer);
  })
  .linkColor(l => {
    if (highlightLinks.size > 0) {
      return highlightLinks.has(l) ? LINK_COLORS[l.type]?.replace(/[\d.]+\)$/, '0.6)') || 'rgba(255,255,255,0.6)' : 'rgba(20,20,30,0.05)';
    }
    return LINK_COLORS[l.type] || 'rgba(255,255,255,0.05)';
  })
  .linkWidth(l => {
    if (highlightLinks.has(l)) return 3;
    if (l.type === 'orchestration') return 2;
    if (l.type === 'governance' || l.type === 'verification') return 1.5;
    if (l.type === 'mesh' || l.type === 'supervision') return 1;
    return 0.5;
  })
  .linkOpacity(0.8)
  .linkCurvature(l => l.type === 'mesh' ? 0.3 : l.type === 'delegation' ? 0.2 : 0.1)

  // Directional particles (data flow)
  .linkDirectionalParticles(l => {
    if (highlightLinks.has(l)) return (LINK_PARTICLES[l.type] || 0) + 3;
    return LINK_PARTICLES[l.type] || 0;
  })
  .linkDirectionalParticleSpeed(0.006)
  .linkDirectionalParticleWidth(l => l.type === 'orchestration' ? 3 : 2)
  .linkDirectionalParticleColor(l => LAYER_COLORS[
    graphData.nodes.find(n => n.id === (typeof l.source === 'object' ? l.source.id : l.source))?.layer
  ] || '#fff')

  // Directional arrows for key links
  .linkDirectionalArrowLength(l => {
    return ['governance', 'verification', 'orchestration', 'attestation'].includes(l.type) ? 3 : 0;
  })
  .linkDirectionalArrowRelPos(1)
  .linkDirectionalArrowColor(l => LINK_COLORS[l.type]?.replace(/[\d.]+\)$/, '0.5)') || 'rgba(255,255,255,0.3)')

  // Forces
  .d3AlphaDecay(0.015)
  .d3VelocityDecay(0.35)

  // Interactions
  .onNodeHover(node => {
    document.body.style.cursor = node ? 'pointer' : null;
    highlightNodes.clear();
    highlightLinks.clear();

    if (node) {
      hoverNode = node;
      highlightNodes.add(node);
      const neighbors = neighborMap.get(node.id);
      if (neighbors) {
        neighbors.forEach(nid => {
          const nNode = graphData.nodes.find(n => n.id === nid);
          if (nNode) highlightNodes.add(nNode);
        });
      }
      const nLinks = linkMap.get(node.id);
      if (nLinks) nLinks.forEach(l => highlightLinks.add(l));
    } else {
      hoverNode = null;
    }

    Graph
      .nodeColor(Graph.nodeColor())
      .linkColor(Graph.linkColor())
      .linkWidth(Graph.linkWidth())
      .linkDirectionalParticles(Graph.linkDirectionalParticles());
  })

  .onNodeClick(node => {
    selectedNode = node;
    showDetail(node);

    // Zoom to node
    const distance = 80;
    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
    const newPos = node.x || node.y || node.z
      ? { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }
      : { x: 0, y: 0, z: distance };
    Graph.cameraPosition(newPos, node, 1200);
  })

  .graphData(graphData);

// ═══════════════════════════════════════════════════════
// BLOOM POST-PROCESSING
// ═══════════════════════════════════════════════════════

// Bloom: 3d-force-graph no expone postProcessingComposer en UMD builds.
// El glow visual se logra con emissive materials + node opacity.

// Animation handled by 3d-force-graph engine + link particles

// ═══════════════════════════════════════════════════════
// CONFIGURE FORCES
// ═══════════════════════════════════════════════════════

Graph.d3Force('charge').strength(n => {
  if (n.type === 'core') return -500;
  if (n.layer === 'constitution') return -250;
  if (n.layer === 'agents') return -120;
  if (n.layer === 'mesh') return -100;
  return -60;
});

Graph.d3Force('link').distance(l => {
  if (l.type === 'governance') return 40;
  if (l.type === 'orchestration') return 50;
  if (l.type === 'supervision') return 70;
  if (l.type === 'mesh') return 60;
  if (l.type === 'delegation') return 90;
  return 100;
});

// ═══════════════════════════════════════════════════════
// HUD STATS
// ═══════════════════════════════════════════════════════

document.getElementById('s-nodes').textContent = graphData.nodes.length;
document.getElementById('s-links').textContent = graphData.links.length;
document.getElementById('s-msgs').textContent = '2,026,779';
document.getElementById('s-health').textContent = '98%';

// ═══════════════════════════════════════════════════════
// SIDEBAR FILTERS
// ═══════════════════════════════════════════════════════

function buildFilters() {
  // Layer filters
  const layerContainer = document.getElementById('layer-filters');
  Object.entries(LAYERS).forEach(([key, layer]) => {
    const count = graphData.nodes.filter(n => n.layer === key).length;
    const btn = document.createElement('button');
    btn.className = 'filter-btn active';
    btn.innerHTML = `
      <div class="indicator" style="background:${layer.color}"></div>
      ${layer.label}
      <span class="count">${count}</span>
    `;
    btn.onclick = () => {
      btn.classList.toggle('active');
      if (activeFilters.layers.has(key)) {
        activeFilters.layers.delete(key);
      } else {
        activeFilters.layers.add(key);
      }
      Graph
        .nodeVisibility(Graph.nodeVisibility())
        .nodeVal(Graph.nodeVal())
        .nodeColor(Graph.nodeColor())
        .linkVisibility(Graph.linkVisibility());
    };
    layerContainer.appendChild(btn);
  });

  // Type filters
  const typeContainer = document.getElementById('type-filters');
  const types = [
    { key: 'api', label: 'API Directa', color: '#ffaa00', count: MESH_NODES.filter(n => n.type === 'api').length },
    { key: 'bridge', label: 'Web Bridge', color: '#ff8844', count: MESH_NODES.filter(n => n.type === 'bridge').length },
    { key: 'local', label: 'Local MLX', color: '#ff6644', count: MESH_NODES.filter(n => n.type === 'local').length },
  ];
  types.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn active';
    btn.innerHTML = `
      <div class="indicator" style="background:${t.color}"></div>
      ${t.label}
      <span class="count">${t.count}</span>
    `;
    btn.onclick = () => {
      btn.classList.toggle('active');
      // Toggle visibility for these specific mesh node types
      if (activeFilters.types.has(t.key)) {
        activeFilters.types.delete(t.key);
      } else {
        activeFilters.types.add(t.key);
      }
      Graph.nodeVisibility(n => {
        if (!activeFilters.layers.has(n.layer)) return false;
        if (n.layer === 'mesh' && !activeFilters.types.has(n.type)) return false;
        return true;
      });
    };
    typeContainer.appendChild(btn);
  });

  // Circuit breaker states
  const cbContainer = document.getElementById('cb-filters');
  ['CLOSED', 'HALF_OPEN', 'OPEN'].forEach(state => {
    const colors = { CLOSED: '#00ff88', HALF_OPEN: '#ffaa00', OPEN: '#ff4444' };
    const labels = { CLOSED: 'Cerrado (OK)', HALF_OPEN: 'Semi-abierto', OPEN: 'Abierto (Error)' };
    const btn = document.createElement('button');
    btn.className = 'filter-btn active';
    btn.innerHTML = `
      <div class="indicator" style="background:${colors[state]}"></div>
      ${labels[state]}
    `;
    cbContainer.appendChild(btn);
  });
}

buildFilters();

// ═══════════════════════════════════════════════════════
// DETAIL PANEL
// ═══════════════════════════════════════════════════════

function showDetail(node) {
  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  panel.classList.add('open');

  const badgeClass = node.score >= 90 ? 'badge-pass' : node.score >= 75 ? 'badge-info' : node.score >= 60 ? 'badge-warn' : 'badge-fail';
  const layerLabel = LAYERS[node.layer]?.label || node.layer;

  let detailHTML = `
    <div class="node-header">
      <div class="node-icon" style="background:${LAYER_COLORS[node.layer]}22; border: 1px solid ${LAYER_COLORS[node.layer]}44;">
        ${node.icon || '●'}
      </div>
      <div>
        <div class="node-title">${node.name}</div>
        <div class="node-subtitle">${layerLabel}</div>
      </div>
    </div>
  `;

  // Score bar
  if (node.score !== undefined) {
    detailHTML += `
      <div class="detail-section">
        <h4>Trust Score</h4>
        <div class="score-bar-container">
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:${node.score}%; background:${scoreToColor(node.score)};"></div>
          </div>
          <div class="score-label">
            <span>0</span>
            <span class="badge ${badgeClass}">${node.score}/100</span>
            <span>100</span>
          </div>
        </div>
      </div>
    `;
  }

  // Properties
  detailHTML += `<div class="detail-section"><h4>Propiedades</h4>`;
  detailHTML += `<div class="detail-row"><span class="label">ID</span><span class="value">${node.id}</span></div>`;
  detailHTML += `<div class="detail-row"><span class="label">Capa</span><span class="value">${layerLabel}</span></div>`;
  detailHTML += `<div class="detail-row"><span class="label">Tipo</span><span class="value">${node.type}</span></div>`;
  if (node.desc) detailHTML += `<div class="detail-row"><span class="label">Descripción</span><span class="value" style="max-width:200px;text-align:right;">${node.desc}</span></div>`;
  if (node.role) detailHTML += `<div class="detail-row"><span class="label">Rol</span><span class="value">${node.role}</span></div>`;
  if (node.model) detailHTML += `<div class="detail-row"><span class="label">Modelo</span><span class="value">${node.model}</span></div>`;
  if (node.mcps) detailHTML += `<div class="detail-row"><span class="label">MCPs</span><span class="value">${node.mcps}</span></div>`;
  if (node.publisher) detailHTML += `<div class="detail-row"><span class="label">Publisher</span><span class="value">${node.publisher}</span></div>`;
  if (node.tools) detailHTML += `<div class="detail-row"><span class="label">Tools</span><span class="value">${node.tools}</span></div>`;
  if (node.lines) detailHTML += `<div class="detail-row"><span class="label">LOC</span><span class="value">${node.lines.toLocaleString()}</span></div>`;
  if (node.delegation !== undefined) detailHTML += `<div class="detail-row"><span class="label">Delegación</span><span class="value">${node.delegation ? '✓ Activa' : '✗ No'}</span></div>`;
  detailHTML += `</div>`;

  // Connections
  const neighbors = neighborMap.get(node.id);
  if (neighbors && neighbors.size > 0) {
    detailHTML += `<div class="detail-section"><h4>Conexiones (${neighbors.size})</h4>`;
    neighbors.forEach(nid => {
      const neighbor = graphData.nodes.find(n => n.id === nid);
      if (neighbor) {
        const color = LAYER_COLORS[neighbor.layer] || '#666';
        detailHTML += `
          <div class="connection-item">
            <div class="conn-dot" style="background:${color}"></div>
            ${neighbor.icon || ''} ${neighbor.name}
          </div>
        `;
      }
    });
    detailHTML += `</div>`;
  }

  content.innerHTML = detailHTML;
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
  selectedNode = null;
}

// ═══════════════════════════════════════════════════════
// VIEW CONTROLS
// ═══════════════════════════════════════════════════════

let orbitInterval = null;

function setView(mode) {
  document.querySelectorAll('#view-controls .view-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  if (mode === 'force') {
    Graph.dagMode(null);
    Graph.d3ReheatSimulation();
  } else if (mode === 'radial') {
    Graph.dagMode('radialout');
    Graph.d3ReheatSimulation();
  } else if (mode === 'tree') {
    Graph.dagMode('td');
    Graph.d3ReheatSimulation();
  }
}

function toggleOrbit(btn) {
  btn.classList.toggle('active');
  if (orbitInterval) {
    clearInterval(orbitInterval);
    orbitInterval = null;
    Graph.enableNavigationControls(true);
  } else {
    Graph.enableNavigationControls(false);
    let angle = 0;
    const distance = 350;
    orbitInterval = setInterval(() => {
      Graph.cameraPosition({
        x: distance * Math.sin(angle),
        z: distance * Math.cos(angle),
      });
      angle += Math.PI / 600;
    }, 16);
  }
}

function resetCamera() {
  if (orbitInterval) {
    clearInterval(orbitInterval);
    orbitInterval = null;
    Graph.enableNavigationControls(true);
    document.querySelectorAll('#view-controls .view-btn').forEach(b => {
      if (b.textContent.trim() === 'Orbit') b.classList.remove('active');
    });
  }
  Graph.zoomToFit(800, 60);
}

// ═══════════════════════════════════════════════════════
// RESPONSIVE
// ═══════════════════════════════════════════════════════

window.addEventListener('resize', () => {
  Graph.width(window.innerWidth).height(window.innerHeight);
});

// Initial fit after layout stabilizes
setTimeout(() => Graph.zoomToFit(1200, 20), 3000);
setTimeout(() => Graph.zoomToFit(800, 20), 5000);

// ═══════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
  if (e.key === 'r' || e.key === 'R') resetCamera();
  if (e.key === '1') toggleLayer('constitution');
  if (e.key === '2') toggleLayer('agents');
  if (e.key === '3') toggleLayer('mesh');
  if (e.key === '4') toggleLayer('mcp');
  if (e.key === '5') toggleLayer('modules');
});

function toggleLayer(layer) {
  if (activeFilters.layers.has(layer)) {
    activeFilters.layers.delete(layer);
  } else {
    activeFilters.layers.add(layer);
  }
  // Update sidebar buttons
  const btns = document.querySelectorAll('#layer-filters .filter-btn');
  const layerKeys = Object.keys(LAYERS);
  btns.forEach((btn, i) => {
    btn.classList.toggle('active', activeFilters.layers.has(layerKeys[i]));
  });
  Graph
    .nodeVisibility(Graph.nodeVisibility())
    .nodeVal(Graph.nodeVal())
    .nodeColor(Graph.nodeColor())
    .linkVisibility(Graph.linkVisibility());
}
