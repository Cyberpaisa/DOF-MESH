/**
 * DOF-MESH — Sistema Completo en 3D
 * Visualización real del Deterministic Observability Framework
 *
 * 4 capas concéntricas:
 *   Capa 0 (centro): DOF Constitution + 7 capas governance
 *   Capa 1 (inner):  17 agentes CrewAI con roles reales
 *   Capa 2 (mid):    11 nodos del Mesh (LLM providers)
 *   Capa 3 (outer):  11 MCPs + 16 Tools
 *
 * Cyber Paisa — Enigma Group — DOF-MESH Legion — 2026
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

// ═══════════════════════════════════════════════════════
// DATA — Sistema DOF-MESH real
// ═══════════════════════════════════════════════════════

const GOVERNANCE_LAYERS = [
  { name: 'Constitution', color: 0x00ff88, desc: 'HARD_RULES + SOFT_RULES (YAML)' },
  { name: 'AST Verifier', color: 0x00ddff, desc: 'Análisis estático de código generado' },
  { name: 'Supervisor', color: 0x00aaff, desc: 'Q(0.4)+A(0.25)+C(0.2)+F(0.15)' },
  { name: 'Adversarial', color: 0xff6644, desc: 'Red-team testing' },
  { name: 'Memory', color: 0xaa88ff, desc: 'ChromaDB + HuggingFace embeddings' },
  { name: 'Z3 Formal', color: 0xffaa00, desc: '4 teoremas + 42 patrones PROVEN' },
  { name: 'Oracle', color: 0xff00aa, desc: '21 attestations on-chain Avalanche' },
];

const AGENTS = [
  { id: 'lider', name: 'Orchestrator Lead', role: 'Orquestador', icon: '👑', mcps: 4, color: 0x00ff88 },
  { id: 'organizador', name: 'File Organizer', role: 'Estructura', icon: '📁', mcps: 1, color: 0x00ddff },
  { id: 'pm', name: 'Product Manager', role: 'Producto', icon: '📋', mcps: 3, color: 0x00aaff },
  { id: 'ops', name: 'Operations Director', role: 'Operaciones', icon: '⚙️', mcps: 3, color: 0x0088ff },
  { id: 'bizdev', name: 'BizDev & Strategy', role: 'Negocio', icon: '💼', mcps: 3, color: 0x00ff88 },
  { id: 'arquitecto', name: 'Software Architect', role: 'Arquitectura', icon: '🏗️', mcps: 4, color: 0x00ddff },
  { id: 'developer', name: 'Full-Stack Developer', role: 'Código', icon: '💻', mcps: 4, color: 0x00aaff },
  { id: 'qa', name: 'QA Engineer', role: 'Testing', icon: '🧪', mcps: 3, color: 0x0088ff },
  { id: 'investigador', name: 'Research Lead', role: 'Investigación', icon: '🔬', mcps: 4, color: 0xaa88ff },
  { id: 'devops', name: 'DevOps Engineer', role: 'Infra', icon: '🐳', mcps: 3, color: 0x00ff88 },
  { id: 'sec_blockchain', name: 'Blockchain Security', role: 'Seguridad BC', icon: '🔐', mcps: 3, color: 0xff6644 },
  { id: 'ideacion', name: 'Ideation Expert', role: 'Innovación', icon: '💡', mcps: 3, color: 0xffaa00 },
  { id: 'multichain', name: 'Multi-Chain Expert', role: 'Cross-chain', icon: '🔗', mcps: 3, color: 0x00ddff },
  { id: 'cuantico', name: 'Quantum Expert', role: 'Cuántico', icon: '⚛️', mcps: 3, color: 0xaa88ff },
  { id: 'sec_info', name: 'Cybersecurity Expert', role: 'CyberSec', icon: '🛡️', mcps: 3, color: 0xff6644 },
  { id: 'metodologias', name: 'Methodologies Expert', role: 'Metodologías', icon: '📐', mcps: 3, color: 0x00aaff },
  { id: 'bpm', name: 'BPM Expert', role: 'Procesos', icon: '🔄', mcps: 3, color: 0x00ff88 },
];

const MESH_NODES = [
  { name: 'Claude Code', type: 'api', role: 'Orquestador', score: 100, color: 0xd4a574 },
  { name: 'Claude Workers ×3', type: 'api', role: 'Ejecución paralela', score: 95, color: 0xd4a574 },
  { name: 'DeepSeek V3', type: 'api', role: 'Técnico — gas estimates', score: 68, color: 0x4488ff },
  { name: 'SambaNova Llama-70B', type: 'api', role: 'Cauteloso — responsable', score: 66, color: 0x88aaff },
  { name: 'Q-AION Local MLX', type: 'local', role: 'Local — sin costo', score: 63, color: 0xff8844 },
  { name: 'Cerebras Qwen-235B', type: 'api', role: 'Rápido — inference', score: 70, color: 0x44ddaa },
  { name: 'Kimi K2.5', type: 'bridge', role: 'Estratega — largo plazo', score: 78, color: 0x66ccff },
  { name: 'MiMo-V2-Pro', type: 'bridge', role: 'Arquitecto — Z3 frameworks', score: 99, color: 0xff4488 },
  { name: 'MiniMax M2.1', type: 'bridge', role: 'Filósofo — ética', score: 96, color: 0xaa66ff },
  { name: 'GLM-4.7', type: 'bridge', role: 'Ético — mecanismo de veto', score: 75, color: 0x44ff88 },
  { name: 'Arena AI', type: 'bridge', role: 'Analista — math', score: 92, color: 0xffaa44 },
];

const MCPS = [
  { name: 'Filesystem', publisher: 'Anthropic' },
  { name: 'Web Search', publisher: 'pskill9' },
  { name: 'Fetch', publisher: 'Anthropic' },
  { name: 'Memory KG', publisher: 'Anthropic' },
  { name: 'Context7', publisher: 'Upstash' },
  { name: 'Seq. Thinking', publisher: 'Anthropic' },
  { name: 'Playwright', publisher: 'Microsoft' },
  { name: 'EVM', publisher: 'mcpdotdirect' },
  { name: 'Tavily', publisher: 'Tavily AI' },
  { name: 'Brave Search', publisher: 'Brave' },
  { name: 'Supabase', publisher: 'Supabase' },
];

const CORE_MODULES = [
  'governance.py', 'z3_verifier.py', 'z3_gate.py', 'supervisor.py',
  'observability.py', 'providers.py', 'crew_runner.py', 'memory_manager.py',
  'adversarial.py', 'entropy_detector.py', 'mesh_scheduler.py', 'node_mesh.py',
  'autonomous_daemon.py', 'claude_commander.py', 'security_hierarchy.py', 'a_mem.py',
];

// ═══════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════

function scoreToColor(score) {
  if (score >= 90) return new THREE.Color(0x00ff88);
  if (score >= 75) return new THREE.Color(0x00b4ff);
  if (score >= 60) return new THREE.Color(0xffaa00);
  return new THREE.Color(0xff4444);
}

function createLabel(text, color = '#aaa', borderColor = '0,255,136', fontSize = '10px') {
  const div = document.createElement('div');
  div.style.cssText = `
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: ${fontSize};
    color: ${color}; background: rgba(10,10,20,0.75); padding: 2px 6px;
    border-radius: 4px; border: 1px solid rgba(${borderColor},0.4);
    white-space: nowrap; pointer-events: none;
  `;
  div.textContent = text;
  return new CSS2DObject(div);
}

// ═══════════════════════════════════════════════════════
// SCENE SETUP
// ═══════════════════════════════════════════════════════

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x06060c);
scene.fog = new THREE.FogExp2(0x06060c, 0.035);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 6, 12);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
document.body.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 3;
controls.maxDistance = 30;
controls.target.set(0, 1, 0);

// Lights
scene.add(new THREE.AmbientLight(0x111122, 0.8));
const mainLight = new THREE.PointLight(0x00ff88, 3, 30);
mainLight.position.set(0, 5, 0);
scene.add(mainLight);
const blueLight = new THREE.PointLight(0x00b4ff, 2, 20);
blueLight.position.set(-5, 3, 5);
scene.add(blueLight);
const purpleLight = new THREE.PointLight(0xaa88ff, 1.5, 20);
purpleLight.position.set(5, 2, -5);
scene.add(purpleLight);

// ═══════════════════════════════════════════════════════
// LAYER 0 — DOF CONSTITUTION (centro)
// ═══════════════════════════════════════════════════════

// Núcleo central — icosaedro DOF
const coreGeo = new THREE.IcosahedronGeometry(0.4, 1);
const coreMat = new THREE.MeshPhysicalMaterial({
  color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 0.6,
  metalness: 1, roughness: 0, clearcoat: 1, transparent: true, opacity: 0.85,
});
const core = new THREE.Mesh(coreGeo, coreMat);
core.position.set(0, 1.5, 0);
scene.add(core);

const coreLabel = createLabel('DOF CONSTITUTION', '#00ff88', '0,255,136', '13px');
coreLabel.position.set(0, 0.7, 0);
core.add(coreLabel);

// 7 capas de governance orbitando el núcleo
const govMeshes = [];
GOVERNANCE_LAYERS.forEach((layer, i) => {
  const angle = (i / GOVERNANCE_LAYERS.length) * Math.PI * 2;
  const r = 1.2;
  const geo = new THREE.OctahedronGeometry(0.12, 0);
  const mat = new THREE.MeshPhysicalMaterial({
    color: layer.color, emissive: new THREE.Color(layer.color).multiplyScalar(0.4),
    metalness: 0.5, roughness: 0.3, transparent: true, opacity: 0.9,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(Math.cos(angle) * r, 1.5 + Math.sin(i * 0.5) * 0.3, Math.sin(angle) * r);
  scene.add(mesh);
  govMeshes.push(mesh);

  const label = createLabel(layer.name, '#ccc', `${(layer.color >> 16) & 255},${(layer.color >> 8) & 255},${layer.color & 255}`, '9px');
  label.position.set(0, 0.2, 0);
  mesh.add(label);

  // Línea al núcleo
  const lineGeo = new THREE.BufferGeometry().setFromPoints([
    mesh.position.clone(), core.position.clone()
  ]);
  const lineMat = new THREE.LineBasicMaterial({ color: layer.color, transparent: true, opacity: 0.15 });
  scene.add(new THREE.Line(lineGeo, lineMat));
});

// Anillo governance
const govRingGeo = new THREE.TorusGeometry(1.2, 0.008, 8, 64);
const govRingMat = new THREE.MeshBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.2 });
const govRing = new THREE.Mesh(govRingGeo, govRingMat);
govRing.position.y = 1.5;
govRing.rotation.x = Math.PI / 2;
scene.add(govRing);

// ═══════════════════════════════════════════════════════
// LAYER 1 — 17 AGENTES CREWAI (inner ring)
// ═══════════════════════════════════════════════════════

const agentMeshes = [];
const agentRadius = 3.5;

// Distribución ESFÉRICA (no plana) — hélice DNA ascendente
AGENTS.forEach((agent, i) => {
  const t_param = i / AGENTS.length;
  const angle = t_param * Math.PI * 4; // 2 vueltas de hélice
  const height = 0.3 + t_param * 2.8;  // sube en espiral
  const x = Math.cos(angle) * agentRadius;
  const z = Math.sin(angle) * agentRadius;
  const y = height;

  const size = 0.15 + agent.mcps * 0.025;
  const geo = new THREE.SphereGeometry(size, 32, 32);
  const mat = new THREE.MeshPhysicalMaterial({
    color: agent.color,
    emissive: new THREE.Color(agent.color).multiplyScalar(0.3),
    metalness: 0.3, roughness: 0.35, clearcoat: 1.0, clearcoatRoughness: 0.1,
    transparent: true, opacity: 0.9,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  mesh.userData = { type: 'agent', data: agent, baseAngle: angle, baseY: height };
  scene.add(mesh);
  agentMeshes.push(mesh);

  // Anillo orbital 1 (Sentinel style)
  const ringGeo = new THREE.TorusGeometry(size + 0.07, 0.01, 8, 32);
  const ringMat = new THREE.MeshBasicMaterial({ color: agent.color, transparent: true, opacity: 0.6 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2;
  mesh.add(ring);

  // Anillo orbital 2 (inclinado)
  const ring2Geo = new THREE.TorusGeometry(size + 0.13, 0.007, 8, 32);
  const ring2Mat = new THREE.MeshBasicMaterial({ color: agent.color, transparent: true, opacity: 0.25 });
  const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
  ring2.rotation.x = Math.PI / 3;
  ring2.rotation.y = Math.PI / 5;
  mesh.add(ring2);

  mesh.userData.ring = ring;
  mesh.userData.ring2 = ring2;

  // Glow esfera
  const glowGeo = new THREE.SphereGeometry(size * 1.4, 16, 16);
  const glowMat = new THREE.MeshBasicMaterial({ color: agent.color, transparent: true, opacity: 0.07 });
  mesh.add(new THREE.Mesh(glowGeo, glowMat));
  mesh.userData.glow = mesh.children[2];

  // Label
  const label = createLabel(`${agent.role}`, '#bbb', '0,200,255', '9px');
  label.position.set(0, size + 0.14, 0);
  mesh.add(label);

  // Línea de energía al core (curva con arco alto)
  const mid = new THREE.Vector3(x * 0.4, y + 0.8, z * 0.4);
  const curve = new THREE.QuadraticBezierCurve3(mesh.position.clone(), mid, core.position.clone());
  const lineGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(25));
  const lineMat = new THREE.LineBasicMaterial({ color: agent.color, transparent: true, opacity: 0.07 });
  scene.add(new THREE.Line(lineGeo, lineMat));
});

// Hélice DNA visual (tubo espiral conectando los agentes)
const helixPoints = [];
for (let h = 0; h <= 1; h += 0.01) {
  const angle = h * Math.PI * 4;
  helixPoints.push(new THREE.Vector3(
    Math.cos(angle) * agentRadius * 0.95,
    0.3 + h * 2.8,
    Math.sin(angle) * agentRadius * 0.95,
  ));
}
const helixCurve = new THREE.CatmullRomCurve3(helixPoints);
const helixGeo = new THREE.TubeGeometry(helixCurve, 100, 0.008, 6, false);
const helixMat = new THREE.MeshBasicMaterial({ color: 0x00b4ff, transparent: true, opacity: 0.12 });
scene.add(new THREE.Mesh(helixGeo, helixMat));

// Segunda hélice (DNA doble)
const helix2Points = [];
for (let h = 0; h <= 1; h += 0.01) {
  const angle = h * Math.PI * 4 + Math.PI; // offset 180°
  helix2Points.push(new THREE.Vector3(
    Math.cos(angle) * agentRadius * 0.95,
    0.3 + h * 2.8,
    Math.sin(angle) * agentRadius * 0.95,
  ));
}
const helix2Curve = new THREE.CatmullRomCurve3(helix2Points);
const helix2Geo = new THREE.TubeGeometry(helix2Curve, 100, 0.008, 6, false);
const helix2Mat = new THREE.MeshBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.08 });
scene.add(new THREE.Mesh(helix2Geo, helix2Mat));

// Agent ring
const agentRingGeo = new THREE.TorusGeometry(agentRadius, 0.01, 8, 64);
const agentRingMat = new THREE.MeshBasicMaterial({ color: 0x00b4ff, transparent: true, opacity: 0.1 });
const agentRing = new THREE.Mesh(agentRingGeo, agentRingMat);
agentRing.position.y = 1.2;
agentRing.rotation.x = Math.PI / 2;
scene.add(agentRing);

const agentRingLabel = createLabel('17 AGENTES CREWAI', '#00b4ff', '0,180,255', '10px');
agentRingLabel.position.set(agentRadius + 0.5, 1.2, 0);
scene.add(agentRingLabel);

// ═══════════════════════════════════════════════════════
// LAYER 2 — 11 NODOS MESH (LLM providers) (mid ring)
// ═══════════════════════════════════════════════════════

const meshNodeMeshes = [];
const meshRadius = 6.0;

MESH_NODES.forEach((node, i) => {
  const angle = (i / MESH_NODES.length) * Math.PI * 2;
  // Distribución esférica — no plana
  const phi = (i / MESH_NODES.length) * Math.PI * 0.6 + 0.4; // elevación variada
  const x = Math.cos(angle) * meshRadius * Math.sin(phi);
  const z = Math.sin(angle) * meshRadius * Math.sin(phi);
  const y = 0.5 + Math.cos(phi) * 2.5 + (node.score / 100) * 0.8;

  const size = 0.12 + (node.score / 100) * 0.12;
  const color = scoreToColor(node.score);

  // Esferas estilo planetas (como primera versión)
  const geo = new THREE.SphereGeometry(size, 32, 32);
  const mat = new THREE.MeshPhysicalMaterial({
    color: node.color,
    emissive: new THREE.Color(node.color).multiplyScalar(0.3),
    metalness: 0.3, roughness: 0.4, clearcoat: 1.0, clearcoatRoughness: 0.1,
    transparent: true, opacity: 0.9,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  mesh.userData = { type: 'mesh_node', data: node };
  scene.add(mesh);
  meshNodeMeshes.push(mesh);

  // Anillo orbital 1 (estilo planeta — como v1)
  const orbitGeo1 = new THREE.TorusGeometry(size + 0.08, 0.01, 8, 32);
  const orbitMat1 = new THREE.MeshBasicMaterial({
    color: node.score >= 80 ? 0x00ff88 : node.score >= 60 ? 0xffaa00 : 0xff4444,
    transparent: true, opacity: 0.6,
  });
  const orbit1 = new THREE.Mesh(orbitGeo1, orbitMat1);
  orbit1.rotation.x = Math.PI / 2;
  mesh.add(orbit1);
  mesh.userData.orbit1 = orbit1;

  // Anillo orbital 2 (inclinado)
  const orbitGeo2 = new THREE.TorusGeometry(size + 0.15, 0.008, 8, 32);
  const orbitMat2 = new THREE.MeshBasicMaterial({ color: node.color, transparent: true, opacity: 0.3 });
  const orbit2 = new THREE.Mesh(orbitGeo2, orbitMat2);
  orbit2.rotation.x = Math.PI / 3;
  orbit2.rotation.y = Math.PI / 6;
  mesh.add(orbit2);
  mesh.userData.orbit2 = orbit2;

  // Glow (como v1)
  const glowGeo = new THREE.SphereGeometry(size * 1.4, 16, 16);
  const glowMat = new THREE.MeshBasicMaterial({ color: node.color, transparent: true, opacity: 0.07 });
  mesh.add(new THREE.Mesh(glowGeo, glowMat));
  mesh.userData.glow = mesh.children[2];

  // Label con score
  const typeTag = node.type === 'api' ? 'API' : node.type === 'bridge' ? 'BRIDGE' : 'LOCAL';
  const label = createLabel(
    `${node.name} [${node.score}] ${typeTag}`,
    node.score >= 90 ? '#00ff88' : node.score >= 75 ? '#00b4ff' : '#ffaa00',
    `${(node.color >> 16) & 255},${(node.color >> 8) & 255},${node.color & 255}`,
    '9px'
  );
  label.position.set(0, size + 0.15, 0);
  mesh.add(label);

  // Conexión a agentes cercanos (cada LLM alimenta agentes)
  const nearestAgents = agentMeshes.filter((_, ai) => ai % MESH_NODES.length === i || (ai + 3) % MESH_NODES.length === i);
  nearestAgents.forEach(agentMesh => {
    const mid = mesh.position.clone().add(agentMesh.position).multiplyScalar(0.5);
    mid.y += 0.3;
    const curve = new THREE.QuadraticBezierCurve3(mesh.position.clone(), mid, agentMesh.position.clone());
    const lineGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(15));
    const lineMat = new THREE.LineBasicMaterial({ color: node.color, transparent: true, opacity: 0.04 });
    scene.add(new THREE.Line(lineGeo, lineMat));
  });
});

// Mesh ring
const meshRingGeo = new THREE.TorusGeometry(meshRadius, 0.012, 8, 64);
const meshRingMat = new THREE.MeshBasicMaterial({ color: 0xffaa00, transparent: true, opacity: 0.08 });
const meshRing = new THREE.Mesh(meshRingGeo, meshRingMat);
meshRing.position.y = 1.0;
meshRing.rotation.x = Math.PI / 2;
scene.add(meshRing);

const meshRingLabel = createLabel('11 NODOS MESH (LLM)', '#ffaa00', '255,170,0', '10px');
meshRingLabel.position.set(meshRadius + 0.5, 1.0, 0);
scene.add(meshRingLabel);

// ═══════════════════════════════════════════════════════
// LAYER 3 — 11 MCPs (outer ring)
// ═══════════════════════════════════════════════════════

const mcpRadius = 8.5;

const mcpMeshes = [];
MCPS.forEach((mcp, i) => {
  const angle = (i / MCPS.length) * Math.PI * 2;
  const elevation = Math.sin(i * 0.8) * 1.2;
  const x = Math.cos(angle) * mcpRadius;
  const z = Math.sin(angle) * mcpRadius;
  const y = 1.0 + elevation;

  // Diamantes brillantes para MCPs
  const geo = new THREE.OctahedronGeometry(0.08, 0);
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 0.3,
    metalness: 0.8, roughness: 0.1, clearcoat: 1.0, transparent: true, opacity: 0.8,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  mesh.userData = { baseAngle: angle, baseY: y };
  scene.add(mesh);
  mcpMeshes.push(mesh);

  // Mini glow
  const glowGeo = new THREE.SphereGeometry(0.15, 8, 8);
  const glowMat = new THREE.MeshBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.04 });
  mesh.add(new THREE.Mesh(glowGeo, glowMat));

  const label = createLabel(`${mcp.name}`, '#777', '0,255,136', '8px');
  label.position.set(0, 0.16, 0);
  mesh.add(label);
});

// MCP ring
const mcpRingGeo = new THREE.TorusGeometry(mcpRadius, 0.006, 8, 64);
const mcpRingMat = new THREE.MeshBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.05 });
const mcpRing = new THREE.Mesh(mcpRingGeo, mcpRingMat);
mcpRing.position.y = 0.5;
mcpRing.rotation.x = Math.PI / 2;
scene.add(mcpRing);

const mcpRingLabel = createLabel('11 MCP SERVERS', '#666', '0,255,136', '9px');
mcpRingLabel.position.set(mcpRadius + 0.5, 0.5, 0);
scene.add(mcpRingLabel);

// ═══════════════════════════════════════════════════════
// GRID + PARTICLES
// ═══════════════════════════════════════════════════════

// Anillos de suelo
for (let r = 2; r <= 10; r += 2) {
  const ringGeo = new THREE.RingGeometry(r - 0.01, r + 0.01, 64);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.03, side: THREE.DoubleSide });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = -0.3;
  scene.add(ring);
}

// Partículas
const pCount = 500;
const pGeo = new THREE.BufferGeometry();
const pPos = new Float32Array(pCount * 3);
const pColors = new Float32Array(pCount * 3);
for (let i = 0; i < pCount; i++) {
  pPos[i * 3] = (Math.random() - 0.5) * 25;
  pPos[i * 3 + 1] = Math.random() * 8 - 1;
  pPos[i * 3 + 2] = (Math.random() - 0.5) * 25;
  const c = new THREE.Color().setHSL(0.45 + Math.random() * 0.15, 0.8, 0.5);
  pColors[i * 3] = c.r;
  pColors[i * 3 + 1] = c.g;
  pColors[i * 3 + 2] = c.b;
}
pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
pGeo.setAttribute('color', new THREE.BufferAttribute(pColors, 3));
const pMat = new THREE.PointsMaterial({ size: 0.02, transparent: true, opacity: 0.35, vertexColors: true });
scene.add(new THREE.Points(pGeo, pMat));

// ═══════════════════════════════════════════════════════
// RAYCASTER — click to inspect
// ═══════════════════════════════════════════════════════

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const allClickable = [...agentMeshes, ...meshNodeMeshes];

renderer.domElement.addEventListener('mousemove', (e) => {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(allClickable);
  renderer.domElement.style.cursor = hits.length > 0 ? 'pointer' : 'default';
});

renderer.domElement.addEventListener('click', (e) => {
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(allClickable);
  if (hits.length > 0) {
    const data = hits[0].object.userData;
    const panel = document.getElementById('agent-info');
    panel.style.display = 'block';

    if (data.type === 'agent') {
      const a = data.data;
      document.getElementById('info-name').textContent = a.name;
      document.getElementById('info-id').textContent = a.id;
      document.getElementById('info-score').textContent = `${a.role} · ${a.mcps} MCPs`;
      document.getElementById('info-class').textContent = 'CrewAI Agent';
      document.getElementById('info-uptime').textContent = 'Activo';
      document.getElementById('info-scans').textContent = `${a.mcps} MCP servers asignados`;
      document.getElementById('info-tools').textContent = a.mcps;
      document.getElementById('info-caps').textContent = a.role;
      document.getElementById('info-bar').style.width = `${a.mcps / 5 * 100}%`;
      document.getElementById('info-bar').style.background = `#${new THREE.Color(a.color).getHexString()}`;
      document.getElementById('info-sentinel').innerHTML = '<span class="sentinel-badge sentinel-pass">CREWAI AGENT</span>';
    } else if (data.type === 'mesh_node') {
      const n = data.data;
      document.getElementById('info-name').textContent = n.name;
      document.getElementById('info-id').textContent = n.type.toUpperCase();
      document.getElementById('info-score').textContent = `Coliseum Score: ${n.score}/100`;
      document.getElementById('info-class').textContent = n.role;
      document.getElementById('info-uptime').textContent = n.type === 'api' ? 'API Directa' : n.type === 'bridge' ? 'Web Bridge (Playwright)' : 'Local MLX';
      document.getElementById('info-scans').textContent = n.role;
      document.getElementById('info-tools').textContent = '—';
      document.getElementById('info-caps').textContent = n.role;
      document.getElementById('info-bar').style.width = `${n.score}%`;
      document.getElementById('info-bar').style.background = `#${scoreToColor(n.score).getHexString()}`;
      document.getElementById('info-sentinel').innerHTML =
        `<span class="sentinel-badge ${n.score >= 80 ? 'sentinel-pass' : 'sentinel-fail'}">COLISEUM ${n.score}/100</span>`;
    }
  }
});

// ═══════════════════════════════════════════════════════
// HUD
// ═══════════════════════════════════════════════════════

document.getElementById('agent-count').textContent = `${AGENTS.length} agents · ${MESH_NODES.length} LLMs · ${MCPS.length} MCPs`;
document.getElementById('edge-count').textContent = `${GOVERNANCE_LAYERS.length} layers`;
document.getElementById('avg-score').textContent = Math.round(MESH_NODES.reduce((s, n) => s + n.score, 0) / MESH_NODES.length);
document.getElementById('sentinel-rate').textContent = '4/4 Z3 VERIFIED';

// ═══════════════════════════════════════════════════════
// ANIMATION
// ═══════════════════════════════════════════════════════

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  // ── Capa 0: Core — RÁPIDO (corazón del sistema)
  core.rotation.y = t * 0.5;
  core.rotation.x = Math.sin(t * 0.3) * 0.2;
  core.position.y = 1.5 + Math.sin(t * 0.8) * 0.05;

  // ── Capa 0: Governance orbits — RÁPIDO
  govMeshes.forEach((mesh, i) => {
    const angle = t * 0.5 + (i / GOVERNANCE_LAYERS.length) * Math.PI * 2;
    mesh.position.x = Math.cos(angle) * 1.2;
    mesh.position.z = Math.sin(angle) * 1.2;
    mesh.position.y = 1.5 + Math.sin(t * 0.6 + i) * 0.2;
    mesh.rotation.y = t * 2.5;
    mesh.rotation.x = t * 1.8;
  });

  // ── Capa 1: Agentes — ESPIRAL DNA ROTANDO
  agentMeshes.forEach((mesh, i) => {
    const d = mesh.userData;
    const orbitSpeed = t * 0.06;
    const spiralAngle = d.baseAngle + orbitSpeed;
    const bobY = Math.sin(t * 0.4 + i * 0.6) * 0.08;
    const breathRadius = agentRadius + Math.sin(t * 0.2 + i) * 0.15;
    mesh.position.x = Math.cos(spiralAngle) * breathRadius;
    mesh.position.z = Math.sin(spiralAngle) * breathRadius;
    mesh.position.y = d.baseY + bobY;
    if (d.ring) d.ring.rotation.z = t * 0.9 + i;
    if (d.ring2) {
      d.ring2.rotation.y = t * 0.5 + i;
      d.ring2.rotation.z = t * 0.3 + i * 0.4;
    }
    if (d.glow) d.glow.material.opacity = 0.05 + Math.sin(t * 1.5 + i) * 0.025;
  });

  // ── Capa 2: Mesh Nodes (LLMs) — LENTO + ESFÉRICO (sistema solar)
  meshNodeMeshes.forEach((mesh, i) => {
    const node = mesh.userData.data;
    const baseAngle = (i / MESH_NODES.length) * Math.PI * 2;
    const phi = (i / MESH_NODES.length) * Math.PI * 0.6 + 0.4;
    const orbitAngle = baseAngle + t * 0.025; // muy lento
    const breathR = meshRadius + Math.sin(t * 0.15 + i * 1.2) * 0.2;
    mesh.position.x = Math.cos(orbitAngle) * breathR * Math.sin(phi);
    mesh.position.z = Math.sin(orbitAngle) * breathR * Math.sin(phi);
    mesh.position.y = 0.5 + Math.cos(phi) * 2.5 + (node.score / 100) * 0.8 + Math.sin(t * 0.18 + i * 0.7) * 0.07;
    // Anillos orbitales del nodo
    if (mesh.userData.orbit1) {
      mesh.userData.orbit1.rotation.z = t * 0.5 + i;
    }
    if (mesh.userData.orbit2) {
      mesh.userData.orbit2.rotation.y = t * 0.3 + i;
      mesh.userData.orbit2.rotation.z = t * 0.2 + i * 0.5;
    }
    if (mesh.userData.glow) {
      mesh.userData.glow.material.opacity = 0.05 + Math.sin(t * 1.2 + i) * 0.025;
    }
  });

  // ── Capa 3: MCPs — MUY LENTO (diamantes orbitando)
  mcpMeshes.forEach((mesh, i) => {
    const d = mesh.userData;
    const orbitAngle = d.baseAngle + t * 0.012; // ultra lento
    mesh.position.x = Math.cos(orbitAngle) * mcpRadius;
    mesh.position.z = Math.sin(orbitAngle) * mcpRadius;
    mesh.position.y = d.baseY + Math.sin(t * 0.15 + i * 0.9) * 0.04;
    mesh.rotation.y = t * 1.5 + i; // diamante gira sobre sí mismo
    mesh.rotation.x = t * 0.8 + i * 0.5;
  });

  // ── Ring rotations — progresivamente más lentas hacia afuera
  govRing.rotation.z = t * 0.15;
  agentRing.rotation.z = -t * 0.06;
  meshRing.rotation.z = t * 0.025;
  mcpRing.rotation.z = -t * 0.008;

  // Lights pulse
  mainLight.intensity = 2.5 + Math.sin(t) * 0.5;

  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  labelRenderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
