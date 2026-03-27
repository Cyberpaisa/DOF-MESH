// ═══════════════════════════════════════════════════════════════════════════
// DOF-MESH Legion — Enterprise Trust Network Visualizer v2.0
// Radial Concentric Layout — Deterministic Governance Visualization
//
// 119 core modules | 3,595 tests | 114,717 LOC | 7 governance layers
// 17 CrewAI agents | 11 LLM mesh nodes | 11 MCPs
//
// Cyber Paisa — Enigma Group — DOF-MESH Legion — 2026
// ═══════════════════════════════════════════════════════════════════════════

(function () {
  'use strict';

  // ── Layer Configuration ──────────────────────────────────────────────────
  const LAYERS = {
    constitution: { color: '#00ff88', label: 'Constitution', radius: 0,   baseVal: 80, order: 0 },
    governance:   { color: '#00ff88', label: 'Governance',   radius: 140, baseVal: 25, order: 1 },
    agents:       { color: '#00b4ff', label: 'Agentes',      radius: 300, baseVal: 12, order: 2 },
    mesh:         { color: '#ffaa00', label: 'LLM Mesh',     radius: 460, baseVal: 8,  order: 3 },
    mcp:          { color: '#aa88ff', label: 'MCPs',          radius: 580, baseVal: 5,  order: 4 },
    modules:      { color: '#ff6644', label: 'Modules',       radius: 700, baseVal: 3,  order: 5 }
  };

  const LINK_COLORS = {
    governance:    'rgba(0, 255, 136, 0.25)',
    orchestration: 'rgba(0, 180, 255, 0.30)',
    delegation:    'rgba(0, 180, 255, 0.15)',
    mesh_sync:     'rgba(255, 170, 0, 0.20)',
    mcp_bind:      'rgba(170, 136, 255, 0.18)',
    module_dep:    'rgba(255, 102, 68, 0.12)',
    verification:  'rgba(0, 255, 136, 0.35)',
    inter_mesh:    'rgba(255, 200, 0, 0.22)'
  };

  const LINK_WIDTH = {
    governance: 2.0,
    orchestration: 3.0,
    delegation: 0.5,
    mesh_sync: 1.0,
    mcp_bind: 0.8,
    module_dep: 0.4,
    verification: 2.5,
    inter_mesh: 1.2
  };

  const LINK_SPEED = {
    governance: 0.008,
    orchestration: 0.012,
    delegation: 0.003,
    mesh_sync: 0.006,
    mcp_bind: 0.005,
    module_dep: 0.002,
    verification: 0.010,
    inter_mesh: 0.007
  };

  // ── Node Definitions ─────────────────────────────────────────────────────

  var constitutionNodes = [
    { id: 'dof-core', name: 'DOF Core', layer: 'constitution', desc: 'Deterministic Observability Framework — 119 modules, 3,595 tests, 114,717 LOC', score: 100, icon: '\u2B22' }
  ];

  var governanceNodes = [
    { id: 'gov-constitution', name: 'Constitution',    layer: 'governance', desc: 'HARD/SOFT rules enforcement (YAML-aligned)',  score: 100, icon: '\uD83D\uDCDC' },
    { id: 'gov-ast',          name: 'AST Verifier',    layer: 'governance', desc: 'Static analysis of generated code',          score: 98,  icon: '\uD83C\uDF33' },
    { id: 'gov-supervisor',   name: 'Supervisor',      layer: 'governance', desc: 'Meta-supervisor Q(0.4)+A(0.25)+C(0.2)+F(0.15)', score: 97, icon: '\uD83D\uDC41\uFE0F' },
    { id: 'gov-adversarial',  name: 'Adversarial',     layer: 'governance', desc: 'Red-team testing + prompt injection detection', score: 95, icon: '\u2694\uFE0F' },
    { id: 'gov-memory',       name: 'Memory',          layer: 'governance', desc: 'ChromaDB + HuggingFace embeddings',          score: 93,  icon: '\uD83E\uDDE0' },
    { id: 'gov-z3',           name: 'Z3 Formal',       layer: 'governance', desc: '4 theorems + 42 hierarchy proofs PROVEN',    score: 100, icon: '\uD83D\uDD10' },
    { id: 'gov-oracle',       name: 'Oracle',          layer: 'governance', desc: '21 attestations on-chain (Avalanche C-Chain)', score: 91, icon: '\uD83D\uDD2E' }
  ];

  var agentNodes = [
    { id: 'ag-orchestrator',  name: 'Orchestrator Lead',    layer: 'agents', desc: 'Multi-agent orchestration lead',    score: 99, icon: '\uD83C\uDFAF' },
    { id: 'ag-file-org',      name: 'File Organizer',       layer: 'agents', desc: 'File system organization',          score: 88, icon: '\uD83D\uDCC1' },
    { id: 'ag-product',       name: 'Product Manager',      layer: 'agents', desc: 'Product strategy & roadmap',        score: 90, icon: '\uD83D\uDCCA' },
    { id: 'ag-ops',           name: 'Operations Director',  layer: 'agents', desc: 'Operations & process management',   score: 87, icon: '\u2699\uFE0F' },
    { id: 'ag-bizdev',        name: 'BizDev',               layer: 'agents', desc: 'Business development & growth',     score: 85, icon: '\uD83D\uDCB0' },
    { id: 'ag-architect',     name: 'Software Architect',   layer: 'agents', desc: 'System design & architecture',      score: 96, icon: '\uD83C\uDFD7\uFE0F' },
    { id: 'ag-fullstack',     name: 'Full-Stack Dev',       layer: 'agents', desc: 'Full-stack implementation',         score: 94, icon: '\uD83D\uDCBB' },
    { id: 'ag-qa',            name: 'QA Engineer',          layer: 'agents', desc: 'Quality assurance & testing',       score: 92, icon: '\uD83E\uDDEA' },
    { id: 'ag-research',      name: 'Research Lead',        layer: 'agents', desc: 'Research & analysis',               score: 91, icon: '\uD83D\uDD2C' },
    { id: 'ag-devops',        name: 'DevOps Engineer',      layer: 'agents', desc: 'CI/CD & infrastructure',            score: 89, icon: '\uD83D\uDE80' },
    { id: 'ag-blockchain',    name: 'Blockchain Security',  layer: 'agents', desc: 'Smart contract security audit',     score: 93, icon: '\uD83D\uDD17' },
    { id: 'ag-ideation',      name: 'Ideation Expert',      layer: 'agents', desc: 'Creative ideation & brainstorming', score: 86, icon: '\uD83D\uDCA1' },
    { id: 'ag-multichain',    name: 'Multi-Chain Expert',   layer: 'agents', desc: 'Cross-chain interoperability',      score: 88, icon: '\uD83C\uDF10' },
    { id: 'ag-quantum',       name: 'Quantum Expert',       layer: 'agents', desc: 'Quantum computing research',        score: 82, icon: '\u269B\uFE0F' },
    { id: 'ag-cybersec',      name: 'Cybersecurity Expert', layer: 'agents', desc: 'Security analysis & hardening',     score: 94, icon: '\uD83D\uDEE1\uFE0F' },
    { id: 'ag-methods',       name: 'Methodologies Expert', layer: 'agents', desc: 'Engineering methodologies',         score: 87, icon: '\uD83D\uDCD0' },
    { id: 'ag-bpm',           name: 'BPM Expert',           layer: 'agents', desc: 'Business process management',       score: 84, icon: '\uD83D\uDCC8' }
  ];

  var meshNodes = [
    { id: 'mesh-claude',     name: 'Claude Code',      layer: 'mesh', desc: 'Primary sovereign LLM (Opus 4)',  score: 100, icon: '\uD83E\uDDE0' },
    { id: 'mesh-worker1',    name: 'Claude Worker 1',  layer: 'mesh', desc: 'Parallel worker instance',        score: 95,  icon: '\u26A1' },
    { id: 'mesh-worker2',    name: 'Claude Worker 2',  layer: 'mesh', desc: 'Parallel worker instance',        score: 95,  icon: '\u26A1' },
    { id: 'mesh-worker3',    name: 'Claude Worker 3',  layer: 'mesh', desc: 'Parallel worker instance',        score: 95,  icon: '\u26A1' },
    { id: 'mesh-deepseek',   name: 'DeepSeek V3',      layer: 'mesh', desc: 'Deep reasoning model',            score: 68,  icon: '\uD83D\uDCA0' },
    { id: 'mesh-sambanova',  name: 'SambaNova',         layer: 'mesh', desc: 'High-throughput inference',       score: 66,  icon: '\u26A1' },
    { id: 'mesh-qaion',      name: 'Q-AION Local',     layer: 'mesh', desc: 'Local MoE model',                 score: 63,  icon: '\uD83C\uDFE0' },
    { id: 'mesh-cerebras',   name: 'Cerebras',          layer: 'mesh', desc: 'Wafer-scale inference',           score: 70,  icon: '\uD83D\uDFE2' },
    { id: 'mesh-kimi',       name: 'Kimi K2.5',        layer: 'mesh', desc: 'Long-context reasoning',          score: 78,  icon: '\uD83C\uDF19' },
    { id: 'mesh-mimo',       name: 'MiMo-V2-Pro',      layer: 'mesh', desc: 'Multimodal expert',               score: 99,  icon: '\uD83D\uDC41\uFE0F' },
    { id: 'mesh-minimax',    name: 'MiniMax M2.7',     layer: 'mesh', desc: 'Efficient large model',           score: 96,  icon: '\uD83D\uDD37' },
    { id: 'mesh-glm',        name: 'GLM-4.7',          layer: 'mesh', desc: 'Zhipu bilingual model',           score: 75,  icon: '\uD83C\uDDE8\uD83C\uDDF3' },
    { id: 'mesh-arena',      name: 'Arena AI',          layer: 'mesh', desc: 'Multi-model arena router',       score: 92,  icon: '\uD83C\uDFC6' }
  ];

  var mcpNodes = [
    { id: 'mcp-filesystem',  name: 'Filesystem',          layer: 'mcp', desc: 'File read/write/search',          score: null, icon: '\uD83D\uDCC2' },
    { id: 'mcp-websearch',   name: 'Web Search',          layer: 'mcp', desc: 'Brave/Tavily web search',         score: null, icon: '\uD83D\uDD0D' },
    { id: 'mcp-fetch',       name: 'Fetch',               layer: 'mcp', desc: 'HTTP fetch & scraping',           score: null, icon: '\uD83C\uDF10' },
    { id: 'mcp-memorykg',    name: 'Memory KG',           layer: 'mcp', desc: 'Knowledge graph memory',          score: null, icon: '\uD83E\uDDE0' },
    { id: 'mcp-context7',    name: 'Context7',            layer: 'mcp', desc: 'Library documentation lookup',    score: null, icon: '\uD83D\uDCDA' },
    { id: 'mcp-sequential',  name: 'Sequential Thinking', layer: 'mcp', desc: 'Step-by-step reasoning',          score: null, icon: '\uD83E\uDDE9' },
    { id: 'mcp-playwright',  name: 'Playwright',          layer: 'mcp', desc: 'Browser automation & testing',    score: null, icon: '\uD83C\uDFAD' },
    { id: 'mcp-evm',         name: 'EVM',                 layer: 'mcp', desc: 'Blockchain interaction',          score: null, icon: '\u26D3\uFE0F' },
    { id: 'mcp-tavily',      name: 'Tavily',              layer: 'mcp', desc: 'AI search & extraction',          score: null, icon: '\uD83D\uDCA1' },
    { id: 'mcp-brave',       name: 'Brave Search',        layer: 'mcp', desc: 'Privacy-first web search',        score: null, icon: '\uD83E\uDD81' },
    { id: 'mcp-supabase',    name: 'Supabase',            layer: 'mcp', desc: 'Database & auth platform',        score: null, icon: '\uD83D\uDFE2' }
  ];

  var moduleNodes = [
    { id: 'mod-governance',       name: 'governance.py',             layer: 'modules', desc: 'Constitution enforcement engine',      score: null, icon: '\uD83D\uDCDC' },
    { id: 'mod-z3-verifier',      name: 'z3_verifier.py',           layer: 'modules', desc: 'Z3 formal proof verification',         score: null, icon: '\uD83D\uDD10' },
    { id: 'mod-z3-gate',          name: 'z3_gate.py',               layer: 'modules', desc: 'Neurosymbolic gate APPROVED/REJECTED', score: null, icon: '\uD83D\uDEAA' },
    { id: 'mod-supervisor',       name: 'supervisor.py',            layer: 'modules', desc: 'Meta-supervisor scoring engine',        score: null, icon: '\uD83D\uDC41\uFE0F' },
    { id: 'mod-observability',    name: 'observability.py',         layer: 'modules', desc: '5 metrics: SS, PFI, RP, GCR, SSR',     score: null, icon: '\uD83D\uDCCA' },
    { id: 'mod-providers',        name: 'providers.py',             layer: 'modules', desc: 'TTL backoff, provider chains, 7+ LLMs', score: null, icon: '\uD83D\uDD04' },
    { id: 'mod-crew-runner',      name: 'crew_runner.py',           layer: 'modules', desc: 'Crew factory rebuild + retry x3',       score: null, icon: '\uD83C\uDFAF' },
    { id: 'mod-sentinel',         name: 'sentinel_lite.py',         layer: 'modules', desc: 'Lightweight sentinel validation',       score: null, icon: '\uD83D\uDEE1\uFE0F' },
    { id: 'mod-zk-governance',    name: 'zk_governance_proof.py',   layer: 'modules', desc: 'ZK proofs for governance decisions',    score: null, icon: '\uD83D\uDD12' },
    { id: 'mod-cross-chain',      name: 'cross_chain_identity.py',  layer: 'modules', desc: 'Cross-chain identity resolution',      score: null, icon: '\uD83C\uDF10' },
    { id: 'mod-threshold',        name: 'threshold_consensus.py',   layer: 'modules', desc: 'Threshold-based consensus protocol',   score: null, icon: '\uD83E\uDD1D' },
    { id: 'mod-self-improve',     name: 'self_improvement.py',      layer: 'modules', desc: 'Self-improvement feedback loop',       score: null, icon: '\uD83D\uDCC8' },
    { id: 'mod-daemon',           name: 'autonomous_daemon.py',     layer: 'modules', desc: '4 phases: Perceive-Decide-Exec-Eval',  score: null, icon: '\uD83D\uDC7E' },
    { id: 'mod-commander',        name: 'claude_commander.py',      layer: 'modules', desc: '5 modes: SDK, Spawn, Team, Debate',    score: null, icon: '\u2328\uFE0F' },
    { id: 'mod-security',         name: 'security_hierarchy.py',    layer: 'modules', desc: 'SYSTEM > USER > ASSISTANT hierarchy',  score: null, icon: '\uD83D\uDD12' },
    { id: 'mod-mesh-orch',        name: 'mesh_orchestrator.py',     layer: 'modules', desc: 'Mesh node orchestration layer',        score: null, icon: '\uD83C\uDF0A' }
  ];

  // ── Combine all nodes ────────────────────────────────────────────────────
  var allNodes = [].concat(
    constitutionNodes,
    governanceNodes,
    agentNodes,
    meshNodes,
    mcpNodes,
    moduleNodes
  );

  // ── Link Definitions ─────────────────────────────────────────────────────
  var links = [];

  function addLink(source, target, type) {
    links.push({ source: source, target: target, type: type });
  }

  // Constitution -> Governance (verification)
  addLink('dof-core', 'gov-constitution', 'verification');
  addLink('dof-core', 'gov-ast',          'verification');
  addLink('dof-core', 'gov-supervisor',   'verification');
  addLink('dof-core', 'gov-adversarial',  'verification');
  addLink('dof-core', 'gov-memory',       'verification');
  addLink('dof-core', 'gov-z3',           'verification');
  addLink('dof-core', 'gov-oracle',       'verification');

  // Governance internal
  addLink('gov-z3',     'gov-constitution', 'verification');
  addLink('gov-ast',    'gov-constitution', 'verification');
  addLink('gov-oracle', 'gov-z3',           'verification');

  // All agents -> Supervisor
  agentNodes.forEach(function (a) {
    addLink(a.id, 'gov-supervisor', 'governance');
  });

  // Lead -> all other agents (delegation)
  agentNodes.forEach(function (a) {
    if (a.id !== 'ag-orchestrator') {
      addLink('ag-orchestrator', a.id, 'delegation');
    }
  });

  // Mesh -> agents (distributed)
  var meshAgentPairs = [
    ['mesh-claude',    'ag-orchestrator'],
    ['mesh-claude',    'ag-architect'],
    ['mesh-claude',    'ag-fullstack'],
    ['mesh-worker1',   'ag-qa'],
    ['mesh-worker1',   'ag-devops'],
    ['mesh-worker2',   'ag-research'],
    ['mesh-worker2',   'ag-blockchain'],
    ['mesh-worker3',   'ag-cybersec'],
    ['mesh-worker3',   'ag-product'],
    ['mesh-deepseek',  'ag-research'],
    ['mesh-deepseek',  'ag-quantum'],
    ['mesh-cerebras',  'ag-fullstack'],
    ['mesh-kimi',      'ag-architect'],
    ['mesh-mimo',      'ag-ideation'],
    ['mesh-minimax',   'ag-methods'],
    ['mesh-glm',       'ag-multichain'],
    ['mesh-arena',     'ag-ops'],
    ['mesh-sambanova', 'ag-bpm'],
    ['mesh-qaion',     'ag-file-org']
  ];
  meshAgentPairs.forEach(function (pair) { addLink(pair[0], pair[1], 'orchestration'); });

  // Inter-mesh links
  var interMeshPairs = [
    ['mesh-claude', 'mesh-worker1'],
    ['mesh-claude', 'mesh-worker2'],
    ['mesh-claude', 'mesh-worker3'],
    ['mesh-claude', 'mesh-deepseek'],
    ['mesh-claude', 'mesh-cerebras'],
    ['mesh-claude', 'mesh-kimi'],
    ['mesh-claude', 'mesh-mimo'],
    ['mesh-worker1', 'mesh-minimax'],
    ['mesh-worker2', 'mesh-glm'],
    ['mesh-worker3', 'mesh-arena'],
    ['mesh-deepseek', 'mesh-sambanova'],
    ['mesh-qaion', 'mesh-cerebras']
  ];
  interMeshPairs.forEach(function (pair) { addLink(pair[0], pair[1], 'inter_mesh'); });

  // MCPs -> agents
  var mcpAgentPairs = [
    ['mcp-filesystem',  'ag-file-org'],
    ['mcp-filesystem',  'ag-fullstack'],
    ['mcp-websearch',   'ag-research'],
    ['mcp-websearch',   'ag-bizdev'],
    ['mcp-fetch',       'ag-devops'],
    ['mcp-fetch',       'ag-multichain'],
    ['mcp-memorykg',    'ag-orchestrator'],
    ['mcp-context7',    'ag-architect'],
    ['mcp-context7',    'ag-fullstack'],
    ['mcp-sequential',  'ag-research'],
    ['mcp-sequential',  'ag-methods'],
    ['mcp-playwright',  'ag-qa'],
    ['mcp-playwright',  'ag-cybersec'],
    ['mcp-evm',         'ag-blockchain'],
    ['mcp-evm',         'ag-multichain'],
    ['mcp-tavily',      'ag-research'],
    ['mcp-brave',       'ag-bizdev'],
    ['mcp-supabase',    'ag-fullstack'],
    ['mcp-supabase',    'ag-devops']
  ];
  mcpAgentPairs.forEach(function (pair) { addLink(pair[0], pair[1], 'mcp_bind'); });

  // Modules -> governance
  var moduleGovLinks = [
    ['mod-governance',    'gov-constitution'],
    ['mod-z3-verifier',   'gov-z3'],
    ['mod-z3-gate',       'gov-z3'],
    ['mod-supervisor',    'gov-supervisor'],
    ['mod-observability', 'gov-supervisor'],
    ['mod-security',      'gov-constitution'],
    ['mod-sentinel',      'gov-adversarial'],
    ['mod-zk-governance', 'gov-z3'],
    ['mod-cross-chain',   'gov-oracle'],
    ['mod-threshold',     'gov-supervisor'],
    ['mod-self-improve',  'gov-memory'],
    ['mod-daemon',        'gov-supervisor'],
    ['mod-commander',     'gov-supervisor'],
    ['mod-providers',     'gov-oracle'],
    ['mod-crew-runner',   'gov-supervisor'],
    ['mod-mesh-orch',     'gov-supervisor']
  ];
  moduleGovLinks.forEach(function (pair) { addLink(pair[0], pair[1], 'module_dep'); });

  // ── Compute node val ─────────────────────────────────────────────────────
  function computeVal(n) {
    switch (n.layer) {
      case 'constitution': return 80;
      case 'governance':   return 25;
      case 'agents':       return 12;
      case 'mesh':         return 8 + (n.score || 0) / 15;
      case 'mcp':          return 5;
      case 'modules':      return 3;
      default:             return 4;
    }
  }

  // ── Build Graph Data ─────────────────────────────────────────────────────
  var graphData = {
    nodes: allNodes.map(function (n) {
      return {
        id: n.id,
        name: n.name,
        layer: n.layer,
        desc: n.desc,
        score: n.score,
        icon: n.icon,
        val: computeVal(n),
        color: LAYERS[n.layer].color
      };
    }),
    links: links.map(function (l) {
      return {
        source: l.source,
        target: l.target,
        type: l.type,
        color: LINK_COLORS[l.type] || 'rgba(255,255,255,0.08)',
        width: LINK_WIDTH[l.type] || 0.5
      };
    })
  };

  // ── Radial Position Calculator ───────────────────────────────────────────
  function assignRadialPositions(nodes) {
    var layerGroups = {};
    nodes.forEach(function (n) {
      if (!layerGroups[n.layer]) layerGroups[n.layer] = [];
      layerGroups[n.layer].push(n);
    });

    Object.keys(layerGroups).forEach(function (layer) {
      var group = layerGroups[layer];
      var r = LAYERS[layer].radius;

      group.forEach(function (n, idx) {
        if (r === 0) {
          n.fx = 0;
          n.fy = 0;
          n.fz = 0;
        } else {
          var angle = (idx / group.length) * Math.PI * 2 - Math.PI / 2;
          var jitterY = (Math.random() - 0.5) * 25;
          n.fx = Math.cos(angle) * r;
          n.fz = Math.sin(angle) * r;
          n.fy = jitterY;
        }
      });
    });
  }

  // Assign fixed positions before graph init
  assignRadialPositions(graphData.nodes);

  // ── Layer Visibility State ───────────────────────────────────────────────
  var layerVisibility = {};
  Object.keys(LAYERS).forEach(function (l) { layerVisibility[l] = true; });

  // ── Initialize 3D Force Graph ────────────────────────────────────────────
  var container = document.getElementById('graph-container');

  var Graph = ForceGraph3D()(container)
    .graphData(graphData)
    .backgroundColor('#030308')
    .showNavInfo(false)

    // Node appearance
    .nodeVal(function (n) { return layerVisibility[n.layer] ? n.val : 0; })
    .nodeColor(function (n) { return layerVisibility[n.layer] ? n.color : 'transparent'; })
    .nodeOpacity(0.92)
    .nodeResolution(20)

    // Node tooltip
    .nodeLabel(function (n) {
      if (!layerVisibility[n.layer]) return '';
      var layerLabel = LAYERS[n.layer] ? LAYERS[n.layer].label : n.layer;
      var scoreBar = n.score != null
        ? '<div style="margin-top:6px;background:rgba(255,255,255,0.08);border-radius:3px;height:4px;overflow:hidden">'
          + '<div style="width:' + n.score + '%;height:100%;background:' + n.color + ';border-radius:3px"></div>'
          + '</div>'
          + '<div style="font-size:10px;color:#888;margin-top:3px">Score: ' + n.score + '/100</div>'
        : '';
      return '<div style="'
        + 'background:rgba(3,3,8,0.95);'
        + 'border:1px solid ' + n.color + '33;'
        + 'border-radius:10px;'
        + 'padding:10px 14px;'
        + 'font-family:Inter,sans-serif;'
        + 'min-width:180px;'
        + 'backdrop-filter:blur(12px);'
        + 'box-shadow:0 8px 32px rgba(0,0,0,0.5);'
        + '">'
        + '<div style="font-size:15px;margin-bottom:4px">' + n.icon + ' <b style="color:#fff">' + n.name + '</b></div>'
        + '<div style="font-size:11px;color:#888;margin-bottom:4px">' + n.desc + '</div>'
        + '<div style="display:inline-block;padding:2px 7px;border-radius:4px;font-size:9px;'
        + 'font-family:JetBrains Mono,monospace;font-weight:600;letter-spacing:0.5px;'
        + 'background:' + n.color + '18;color:' + n.color + ';border:1px solid ' + n.color + '33">'
        + layerLabel.toUpperCase() + '</div>'
        + scoreBar
        + '</div>';
    })

    // Links
    .linkWidth(function (l) { return l.width; })
    .linkColor(function (l) { return l.color; })
    .linkOpacity(0.7)
    .linkCurvature(0.2)
    .linkDirectionalParticles(2)
    .linkDirectionalParticleWidth(function (l) { return Math.max(l.width * 0.6, 0.4); })
    .linkDirectionalParticleSpeed(function (l) { return LINK_SPEED[l.type] || 0.004; })
    .linkDirectionalParticleColor(function (l) {
      var base = LINK_COLORS[l.type] || 'rgba(255,255,255,0.15)';
      return base.replace(/[\d.]+\)$/, '0.6)');
    })

    // Click handler
    .onNodeClick(function (node) {
      if (!layerVisibility[node.layer]) return;
      var distance = 200;
      var hyp = Math.hypot(node.fx || 0, node.fy || 0, node.fz || 0) || 1;
      var distRatio = 1 + distance / hyp;
      Graph.cameraPosition(
        { x: (node.fx || 0) * distRatio, y: (node.fy || 0) * distRatio, z: (node.fz || 0) * distRatio },
        { x: node.fx || 0, y: node.fy || 0, z: node.fz || 0 },
        1200
      );
      openDetail(node);
    })

    // Hover
    .onNodeHover(function (node) {
      container.style.cursor = node ? 'pointer' : 'default';
      highlightNode(node);
    })

    // Disable default forces (fixed positions)
    .d3AlphaDecay(0.05)
    .d3VelocityDecay(0.5)
    .warmupTicks(0)
    .cooldownTicks(0);

  // Kill default forces
  Graph.d3Force('link', null);
  Graph.d3Force('charge', null);
  Graph.d3Force('center', null);

  // ── Initial Camera ───────────────────────────────────────────────────────
  setTimeout(function () {
    Graph.cameraPosition({ x: 0, y: 400, z: 900 }, { x: 0, y: 0, z: 0 }, 0);
  }, 100);

  // ── Auto Orbit ───────────────────────────────────────────────────────────
  var orbitActive = true;
  var orbitAngle = 0;
  var ORBIT_SPEED = 0.0008;
  var ORBIT_RADIUS = 950;
  var ORBIT_HEIGHT = 350;

  function animateOrbit() {
    if (!orbitActive) return;
    orbitAngle += ORBIT_SPEED;
    Graph.cameraPosition({
      x: Math.cos(orbitAngle) * ORBIT_RADIUS,
      y: ORBIT_HEIGHT,
      z: Math.sin(orbitAngle) * ORBIT_RADIUS
    }, { x: 0, y: 0, z: 0 });
    requestAnimationFrame(animateOrbit);
  }

  setTimeout(function () { animateOrbit(); }, 1500);

  // ── Highlight Logic ──────────────────────────────────────────────────────
  function highlightNode(node) {
    var connectedIds = {};

    if (node) {
      graphData.links.forEach(function (l) {
        var sid = typeof l.source === 'object' ? l.source.id : l.source;
        var tid = typeof l.target === 'object' ? l.target.id : l.target;
        if (sid === node.id) connectedIds[tid] = true;
        if (tid === node.id) connectedIds[sid] = true;
      });
      connectedIds[node.id] = true;
    }

    Graph
      .nodeOpacity(function (n) {
        if (!node) return 0.92;
        return connectedIds[n.id] ? 1.0 : 0.12;
      })
      .linkOpacity(function (l) {
        if (!node) return 0.7;
        var sid = typeof l.source === 'object' ? l.source.id : l.source;
        var tid = typeof l.target === 'object' ? l.target.id : l.target;
        return (sid === node.id || tid === node.id) ? 1.0 : 0.04;
      });
  }

  // ── Detail Panel ─────────────────────────────────────────────────────────
  function openDetail(node) {
    var panel = document.getElementById('detail-panel');
    var content = document.getElementById('detail-content');
    var layerCfg = LAYERS[node.layer];

    var connections = [];
    graphData.links.forEach(function (l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (sid === node.id || tid === node.id) {
        var otherId = sid === node.id ? tid : sid;
        var other = graphData.nodes.find(function (n) { return n.id === otherId; });
        if (other) connections.push({ node: other, type: l.type });
      }
    });

    var scoreSection = '';
    if (node.score != null) {
      scoreSection = '<div class="detail-section">'
        + '<h4>Trust Score</h4>'
        + '<div class="score-bar-container">'
        + '<div class="score-bar-bg">'
        + '<div class="score-bar-fill" style="width:' + node.score + '%;background:' + node.color + '"></div>'
        + '</div>'
        + '<div class="score-label">'
        + '<span>0</span>'
        + '<span style="color:' + node.color + ';font-weight:600">' + node.score + '/100</span>'
        + '</div></div></div>';
    }

    var connectionsHTML = '';
    var showCount = Math.min(connections.length, 12);
    for (var i = 0; i < showCount; i++) {
      var c = connections[i];
      var dotColor = LAYERS[c.node.layer] ? LAYERS[c.node.layer].color : '#666';
      connectionsHTML += '<div class="connection-item">'
        + '<div class="conn-dot" style="background:' + dotColor + '"></div>'
        + '<span style="color:#ccc">' + c.node.icon + ' ' + c.node.name + '</span>'
        + '<span style="margin-left:auto;font-size:9px;color:#555;font-family:JetBrains Mono,monospace">' + c.type + '</span>'
        + '</div>';
    }
    if (connections.length > 12) {
      connectionsHTML += '<div style="text-align:center;color:#444;font-size:10px;margin-top:6px">+' + (connections.length - 12) + ' more</div>';
    }

    var badgeClass = 'badge-info';
    var badgeText = 'N/A';
    if (node.score != null) {
      badgeClass = node.score >= 90 ? 'badge-pass' : node.score >= 70 ? 'badge-info' : node.score >= 50 ? 'badge-warn' : 'badge-fail';
      badgeText = node.score >= 90 ? 'EXCELLENT' : node.score >= 70 ? 'GOOD' : node.score >= 50 ? 'ACCEPTABLE' : 'LOW';
    }

    var statusRow = node.score != null
      ? '<div class="detail-row"><span class="label">Estado</span><span class="badge ' + badgeClass + '">' + badgeText + '</span></div>'
      : '';

    content.innerHTML = '<div class="node-header">'
      + '<div class="node-icon" style="background:' + node.color + '15;border:1px solid ' + node.color + '33">'
      + '<span style="font-size:24px">' + node.icon + '</span>'
      + '</div>'
      + '<div>'
      + '<div class="node-title">' + node.name + '</div>'
      + '<div class="node-subtitle">' + node.desc + '</div>'
      + '</div></div>'
      + '<div class="detail-section">'
      + '<h4>Propiedades</h4>'
      + '<div class="detail-row"><span class="label">Capa</span><span class="value" style="color:' + node.color + '">' + layerCfg.label + '</span></div>'
      + '<div class="detail-row"><span class="label">ID</span><span class="value">' + node.id + '</span></div>'
      + '<div class="detail-row"><span class="label">Conexiones</span><span class="value">' + connections.length + '</span></div>'
      + statusRow
      + '</div>'
      + scoreSection
      + '<div class="detail-section">'
      + '<h4>Conexiones (' + connections.length + ')</h4>'
      + connectionsHTML
      + '</div>';

    panel.classList.add('open');
  }

  window.closeDetail = function () {
    document.getElementById('detail-panel').classList.remove('open');
  };

  // ── Sidebar Filters ──────────────────────────────────────────────────────
  function buildFilters() {
    var layerContainer = document.getElementById('layer-filters');
    if (!layerContainer) return;

    Object.keys(LAYERS).forEach(function (layerKey) {
      var cfg = LAYERS[layerKey];
      var count = graphData.nodes.filter(function (n) { return n.layer === layerKey; }).length;

      var btn = document.createElement('button');
      btn.className = 'filter-btn active';
      btn.dataset.layer = layerKey;
      btn.innerHTML = '<div class="indicator" style="background:' + cfg.color + '"></div>'
        + cfg.label
        + '<span class="count">' + count + '</span>';
      btn.addEventListener('click', function () {
        layerVisibility[layerKey] = !layerVisibility[layerKey];
        btn.classList.toggle('active', layerVisibility[layerKey]);
        updateVisibility();
      });
      layerContainer.appendChild(btn);
    });
  }

  function updateVisibility() {
    graphData.nodes.forEach(function (n) {
      n.val = layerVisibility[n.layer] ? computeVal(n) : 0;
    });
    Graph.graphData(graphData);
    assignRadialPositions(graphData.nodes);
    updateStats();
  }

  // ── Stats Bar ────────────────────────────────────────────────────────────
  function updateStats() {
    var visibleNodes = graphData.nodes.filter(function (n) { return layerVisibility[n.layer]; });
    var visibleLinks = graphData.links.filter(function (l) {
      var sn = typeof l.source === 'object' ? l.source : graphData.nodes.find(function (n) { return n.id === l.source; });
      var tn = typeof l.target === 'object' ? l.target : graphData.nodes.find(function (n) { return n.id === l.target; });
      return sn && tn && layerVisibility[sn.layer] && layerVisibility[tn.layer];
    });

    var setEl = function (id, val) {
      var e = document.getElementById(id);
      if (e) e.textContent = val;
    };
    setEl('s-nodes', visibleNodes.length);
    setEl('s-links', visibleLinks.length);
    setEl('s-msgs',  '2,026,779');
    setEl('s-health', '98%');
  }

  // ── View Controls ────────────────────────────────────────────────────────
  window.setView = function (mode) {
    var btns = document.querySelectorAll('#view-controls .view-btn');
    for (var b = 0; b < btns.length; b++) btns[b].classList.remove('active');

    if (mode === 'force') {
      btns[0].classList.add('active');
      graphData.nodes.forEach(function (n) { delete n.fx; delete n.fy; delete n.fz; });
      Graph
        .d3AlphaDecay(0.02)
        .d3VelocityDecay(0.3)
        .warmupTicks(100)
        .cooldownTicks(200);
      Graph.d3Force('link', null);
      Graph.d3Force('charge', null);
      Graph.d3Force('center', null);
      Graph.graphData(graphData);

    } else if (mode === 'radial') {
      btns[1].classList.add('active');
      assignRadialPositions(graphData.nodes);
      Graph
        .d3AlphaDecay(0.05)
        .d3VelocityDecay(0.5)
        .warmupTicks(0)
        .cooldownTicks(0);
      Graph.d3Force('link', null);
      Graph.d3Force('charge', null);
      Graph.d3Force('center', null);
      Graph.graphData(graphData);

    } else if (mode === 'tree') {
      btns[2].classList.add('active');
      var layerY = {
        constitution: 0,
        governance: -120,
        agents: -260,
        mesh: -400,
        mcp: -520,
        modules: -640
      };
      var layerGroups = {};
      graphData.nodes.forEach(function (n) {
        if (!layerGroups[n.layer]) layerGroups[n.layer] = [];
        layerGroups[n.layer].push(n);
      });
      Object.keys(layerGroups).forEach(function (layer) {
        var group = layerGroups[layer];
        var spread = Math.max(group.length * 40, 100);
        group.forEach(function (n, idx) {
          n.fx = (idx - (group.length - 1) / 2) * (spread / group.length);
          n.fy = layerY[layer] || 0;
          n.fz = (Math.random() - 0.5) * 40;
        });
      });
      Graph
        .d3AlphaDecay(0.05)
        .d3VelocityDecay(0.5)
        .warmupTicks(0)
        .cooldownTicks(0);
      Graph.d3Force('link', null);
      Graph.d3Force('charge', null);
      Graph.d3Force('center', null);
      Graph.graphData(graphData);
    }
  };

  window.toggleOrbit = function (btn) {
    orbitActive = !orbitActive;
    btn.classList.toggle('active', orbitActive);
    if (orbitActive) animateOrbit();
  };

  window.resetCamera = function () {
    Graph.cameraPosition({ x: 0, y: 400, z: 900 }, { x: 0, y: 0, z: 0 }, 1200);
  };

  // ── Keyboard Shortcuts ───────────────────────────────────────────────────
  var layerKeys = Object.keys(LAYERS);

  document.addEventListener('keydown', function (e) {
    // Ignore if typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    var num = parseInt(e.key);
    if (num >= 1 && num <= layerKeys.length) {
      var layerKey = layerKeys[num - 1];
      layerVisibility[layerKey] = !layerVisibility[layerKey];
      var btn = document.querySelector('.filter-btn[data-layer="' + layerKey + '"]');
      if (btn) btn.classList.toggle('active', layerVisibility[layerKey]);
      updateVisibility();
    }
    if (e.key === 'r' || e.key === 'R') {
      window.resetCamera();
    }
    if (e.key === 'o' || e.key === 'O') {
      orbitActive = !orbitActive;
      var orbitBtn = document.querySelectorAll('#view-controls .view-btn')[3];
      if (orbitBtn) orbitBtn.classList.toggle('active', orbitActive);
      if (orbitActive) animateOrbit();
    }
    if (e.key === 'Escape') {
      window.closeDetail();
    }
  });

  // ── Toggle Sidebar (mobile) ──────────────────────────────────────────────
  var toggleBtn = document.getElementById('toggle-sidebar');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      document.getElementById('sidebar').classList.toggle('open-mobile');
    });
  }

  // ── Initialize ───────────────────────────────────────────────────────────
  buildFilters();
  updateStats();

  // Set radial as default active view
  setTimeout(function () {
    var btns = document.querySelectorAll('#view-controls .view-btn');
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
    if (btns[1]) btns[1].classList.add('active');
  }, 200);

})();
