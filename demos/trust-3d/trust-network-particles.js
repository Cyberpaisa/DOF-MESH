/**
 * DOF-MESH LEGION — Particle Visualizer (Three.js puro)
 * ═══════════════════════════════════════════════════════
 * Inspirado en particles.casberry.in
 * BufferGeometry + Points + Additive Blending + OrbitControls
 *
 * 65 nodos del sistema representados como capas de particulas
 * concéntricas con transiciones suaves entre formaciones.
 *
 * Cyber Paisa — Enigma Group — DOF-MESH Legion — 2026
 */

// ═══════════════════════════════════════════════════════
// DATA — 65 nodos del DOF-MESH
// ═══════════════════════════════════════════════════════

const LAYER_CONFIG = {
  core:       { color: [0, 1, 0.53],    hex: '#00ff88', label: 'DOF Core',       count: 1,  radius: [0, 2],   particles: 500,  size: 4.0 },
  governance: { color: [0, 0.85, 0.53], hex: '#00d988', label: 'Governance',     count: 7,  radius: [2, 5],   particles: 1500, size: 3.0 },
  agents:     { color: [0, 0.71, 1],    hex: '#00b4ff', label: 'Agentes CrewAI', count: 17, radius: [5, 10],  particles: 3000, size: 2.5 },
  mesh:       { color: [1, 0.67, 0],    hex: '#ffaa00', label: 'LLM Mesh',       count: 11, radius: [10, 15], particles: 3000, size: 2.0 },
  mcps:       { color: [0.67, 0.53, 1], hex: '#aa88ff', label: 'MCPs',           count: 11, radius: [15, 20], particles: 3500, size: 1.8 },
  modules:    { color: [1, 0.4, 0.27],  hex: '#ff6644', label: 'Core Modules',   count: 16, radius: [20, 25], particles: 3500, size: 1.5 },
};

const NODES = [
  // Core (1)
  { name: 'DOF Core', layer: 'core', desc: 'Constitution Engine' },

  // Governance (7)
  { name: 'Constitution', layer: 'governance', desc: 'HARD_RULES + SOFT_RULES' },
  { name: 'AST Verifier', layer: 'governance', desc: 'Analisis estatico' },
  { name: 'Supervisor', layer: 'governance', desc: 'Q(0.4)+A(0.25)+C(0.2)+F(0.15)' },
  { name: 'Adversarial', layer: 'governance', desc: 'Red-team testing' },
  { name: 'Memory', layer: 'governance', desc: 'ChromaDB + embeddings' },
  { name: 'Z3 Formal', layer: 'governance', desc: '4 teoremas + 42 patrones' },
  { name: 'Oracle', layer: 'governance', desc: '21 attestations on-chain' },

  // Agents (17)
  { name: 'Orchestrator Lead', layer: 'agents', desc: 'Orquestador principal' },
  { name: 'File Organizer', layer: 'agents', desc: 'Estructura de archivos' },
  { name: 'Product Manager', layer: 'agents', desc: 'Producto y roadmap' },
  { name: 'Operations Director', layer: 'agents', desc: 'Operaciones' },
  { name: 'Research Lead', layer: 'agents', desc: 'Investigacion' },
  { name: 'Code Architect', layer: 'agents', desc: 'Arquitectura' },
  { name: 'Security Auditor', layer: 'agents', desc: 'Seguridad' },
  { name: 'Test Engineer', layer: 'agents', desc: 'Testing' },
  { name: 'DevOps Agent', layer: 'agents', desc: 'CI/CD' },
  { name: 'Documentation', layer: 'agents', desc: 'Documentacion' },
  { name: 'Data Analyst', layer: 'agents', desc: 'Analisis de datos' },
  { name: 'Blockchain Agent', layer: 'agents', desc: 'On-chain ops' },
  { name: 'API Designer', layer: 'agents', desc: 'Diseno de APIs' },
  { name: 'UX Researcher', layer: 'agents', desc: 'Experiencia de usuario' },
  { name: 'Performance Agent', layer: 'agents', desc: 'Optimizacion' },
  { name: 'Compliance Agent', layer: 'agents', desc: 'Cumplimiento' },
  { name: 'Integration Agent', layer: 'agents', desc: 'Integraciones' },

  // LLM Mesh (11)
  { name: 'Groq Llama-3.3', layer: 'mesh', desc: 'Coliseum: 87/100' },
  { name: 'NVIDIA Qwen3.5', layer: 'mesh', desc: 'Coliseum: 92/100' },
  { name: 'Cerebras GPT-OSS', layer: 'mesh', desc: 'Coliseum: 78/100' },
  { name: 'Zhipu GLM-4.7', layer: 'mesh', desc: 'Coliseum: 71/100' },
  { name: 'SambaNova DeepSeek', layer: 'mesh', desc: 'Coliseum: 83/100' },
  { name: 'MiniMax M2.1', layer: 'mesh', desc: 'Coliseum: 69/100' },
  { name: 'Gemini 2.5 Flash', layer: 'mesh', desc: 'Coliseum: 90/100' },
  { name: 'OpenRouter Hermes', layer: 'mesh', desc: 'Coliseum: 75/100' },
  { name: 'NVIDIA Kimi K2.5', layer: 'mesh', desc: 'Coliseum: 88/100' },
  { name: 'Groq Kimi K2', layer: 'mesh', desc: 'Coliseum: 85/100' },
  { name: 'Claude Opus', layer: 'mesh', desc: 'Coliseum: 96/100' },

  // MCPs (11)
  { name: 'Filesystem MCP', layer: 'mcps', desc: 'Lectura/escritura local' },
  { name: 'Web Search MCP', layer: 'mcps', desc: 'Busqueda web' },
  { name: 'Fetch MCP', layer: 'mcps', desc: 'HTTP requests' },
  { name: 'Knowledge Graph', layer: 'mcps', desc: 'Grafo de conocimiento' },
  { name: 'Sequential Thinking', layer: 'mcps', desc: 'Razonamiento paso a paso' },
  { name: 'Context7', layer: 'mcps', desc: 'Documentacion libs' },
  { name: 'Playwright MCP', layer: 'mcps', desc: 'Browser automation' },
  { name: 'EVM MCP', layer: 'mcps', desc: 'Blockchain EVM' },
  { name: 'Tavily MCP', layer: 'mcps', desc: 'Busqueda AI' },
  { name: 'Supabase MCP', layer: 'mcps', desc: 'Base de datos' },
  { name: 'Brave Search MCP', layer: 'mcps', desc: 'Busqueda Brave' },

  // Core Modules (16)
  { name: 'governance.py', layer: 'modules', desc: 'Constitution + rules' },
  { name: 'ast_verifier.py', layer: 'modules', desc: 'AST analysis' },
  { name: 'z3_verifier.py', layer: 'modules', desc: 'Formal proofs' },
  { name: 'z3_gate.py', layer: 'modules', desc: 'Neurosymbolic gate' },
  { name: 'supervisor.py', layer: 'modules', desc: 'Meta-supervisor' },
  { name: 'observability.py', layer: 'modules', desc: '5 metricas DOF' },
  { name: 'providers.py', layer: 'modules', desc: 'TTL backoff + chains' },
  { name: 'crew_runner.py', layer: 'modules', desc: 'Crew factory + retry' },
  { name: 'memory_manager.py', layer: 'modules', desc: 'ChromaDB persistence' },
  { name: 'adversarial.py', layer: 'modules', desc: 'Red-team testing' },
  { name: 'entropy_detector.py', layer: 'modules', desc: 'Output entropy' },
  { name: 'mesh_scheduler.py', layer: 'modules', desc: 'Priority queue' },
  { name: 'node_mesh.py', layer: 'modules', desc: 'Registry + MessageBus' },
  { name: 'autonomous_daemon.py', layer: 'modules', desc: '4 phases' },
  { name: 'claude_commander.py', layer: 'modules', desc: '5 modes' },
  { name: 'llm_config.py', layer: 'modules', desc: 'Provider chains' },

  // Extras (2)
  { name: 'Sentinel Engine', layer: 'governance', desc: '27 checks, max 85/85' },
  { name: 'Self-Improvement', layer: 'agents', desc: 'Autonomous learning loop' },
];

// ═══════════════════════════════════════════════════════
// THREE.JS SETUP
// ═══════════════════════════════════════════════════════

const W = window.innerWidth;
const H = window.innerHeight;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x030308, 0.008);

const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
camera.position.set(0, 12, 35);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(W, H);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x030308, 1);
document.body.appendChild(renderer.domElement);

// OrbitControls
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.3;
controls.minDistance = 8;
controls.maxDistance = 80;

// ═══════════════════════════════════════════════════════
// LIGHTS
// ═══════════════════════════════════════════════════════

const ambientLight = new THREE.AmbientLight(0x111122, 0.5);
scene.add(ambientLight);

const coreLight = new THREE.PointLight(0x00ff88, 2, 50);
coreLight.position.set(0, 0, 0);
scene.add(coreLight);

// ═══════════════════════════════════════════════════════
// PARTICLE SYSTEM
// ═══════════════════════════════════════════════════════

let TOTAL_PARTICLES = 15000;
let speed = 1.0;
let glowIntensity = 1.5;
let currentFormation = 'radial';

let geometry, material, particles;
let positions, colors, sizes, baseSizes, targets, layerIndices;

// Build lookup: which layer does each node index belong to
const layerNames = Object.keys(LAYER_CONFIG);

// Assign particles to layers (proportional)
function getLayerForParticle(idx, total) {
  const layers = layerNames;
  let offset = 0;
  const scale = total / 15000; // scale particle counts to match total
  for (let l = 0; l < layers.length; l++) {
    const count = Math.round(LAYER_CONFIG[layers[l]].particles * scale);
    if (idx < offset + count) return layers[l];
    offset += count;
  }
  return layers[layers.length - 1];
}

// Node assignment: pick a node from the layer for tooltip
function getNodeForParticle(idx, total) {
  const layerName = getLayerForParticle(idx, total);
  const layerNodes = NODES.filter(function(n) { return n.layer === layerName; });
  if (layerNodes.length === 0) return null;
  return layerNodes[idx % layerNodes.length];
}

// ── Glow texture (circle with soft falloff) ──
function createGlowTexture() {
  var canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  var ctx = canvas.getContext('2d');
  var gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.15, 'rgba(255,255,255,0.8)');
  gradient.addColorStop(0.4, 'rgba(255,255,255,0.3)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  var tex = new THREE.CanvasTexture(canvas);
  return tex;
}

var glowTexture = createGlowTexture();

// ── Formation generators ──

function generateRadial(total) {
  var t = new Float32Array(total * 3);
  for (var i = 0; i < total; i++) {
    var layer = getLayerForParticle(i, total);
    var cfg = LAYER_CONFIG[layer];
    var rMin = cfg.radius[0];
    var rMax = cfg.radius[1];
    var theta = Math.random() * Math.PI * 2;
    var phi = Math.acos(2 * Math.random() - 1);
    var r = rMin + Math.random() * (rMax - rMin);
    var i3 = i * 3;
    t[i3]     = r * Math.sin(phi) * Math.cos(theta);
    t[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    t[i3 + 2] = r * Math.cos(phi);
  }
  return t;
}

function generateSphere(total) {
  var t = new Float32Array(total * 3);
  var R = 18;
  for (var i = 0; i < total; i++) {
    var theta = Math.random() * Math.PI * 2;
    var phi = Math.acos(2 * Math.random() - 1);
    var r = R * (0.85 + Math.random() * 0.15);
    var i3 = i * 3;
    t[i3]     = r * Math.sin(phi) * Math.cos(theta);
    t[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    t[i3 + 2] = r * Math.cos(phi);
  }
  return t;
}

function generateHelix(total) {
  var t = new Float32Array(total * 3);
  var turns = 6;
  var height = 40;
  var radius = 12;
  for (var i = 0; i < total; i++) {
    var frac = i / total;
    var angle = frac * Math.PI * 2 * turns;
    var y = (frac - 0.5) * height;
    // Double helix: even/odd strand
    var strand = (i % 2 === 0) ? 1 : -1;
    var r = radius + (Math.random() - 0.5) * 2;
    var i3 = i * 3;
    t[i3]     = Math.cos(angle) * r * strand;
    t[i3 + 1] = y + (Math.random() - 0.5) * 0.5;
    t[i3 + 2] = Math.sin(angle) * r * strand;
  }
  return t;
}

function generateExplode(total) {
  var t = new Float32Array(total * 3);
  for (var i = 0; i < total; i++) {
    var theta = Math.random() * Math.PI * 2;
    var phi = Math.acos(2 * Math.random() - 1);
    var r = 30 + Math.random() * 25;
    var i3 = i * 3;
    t[i3]     = r * Math.sin(phi) * Math.cos(theta);
    t[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    t[i3 + 2] = r * Math.cos(phi);
  }
  return t;
}

function getFormationTargets(formation, total) {
  switch (formation) {
    case 'sphere':  return generateSphere(total);
    case 'helix':   return generateHelix(total);
    case 'explode': return generateExplode(total);
    default:        return generateRadial(total);
  }
}

// ── Build particle system ──

function buildParticles(total) {
  // Remove old
  if (particles) {
    scene.remove(particles);
    geometry.dispose();
    material.dispose();
  }

  TOTAL_PARTICLES = total;
  geometry = new THREE.BufferGeometry();
  positions = new Float32Array(total * 3);
  colors = new Float32Array(total * 3);
  sizes = new Float32Array(total);
  baseSizes = new Float32Array(total);
  layerIndices = new Uint8Array(total);

  // Initial positions = radial
  targets = generateRadial(total);

  for (var i = 0; i < total; i++) {
    var i3 = i * 3;
    var layer = getLayerForParticle(i, total);
    var cfg = LAYER_CONFIG[layer];

    // Start slightly scattered, will lerp to target
    positions[i3]     = (Math.random() - 0.5) * 4;
    positions[i3 + 1] = (Math.random() - 0.5) * 4;
    positions[i3 + 2] = (Math.random() - 0.5) * 4;

    // Color
    colors[i3]     = cfg.color[0];
    colors[i3 + 1] = cfg.color[1];
    colors[i3 + 2] = cfg.color[2];

    // Size
    baseSizes[i] = cfg.size * (0.6 + Math.random() * 0.8);
    sizes[i] = baseSizes[i];

    // Layer index for raycasting
    layerIndices[i] = layerNames.indexOf(layer);
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

  material = new THREE.PointsMaterial({
    size: 0.4,
    map: glowTexture,
    vertexColors: true,
    transparent: true,
    opacity: Math.min(glowIntensity * 0.7, 1.0),
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  });

  particles = new THREE.Points(geometry, material);
  scene.add(particles);

  // Update formation targets
  targets = getFormationTargets(currentFormation, total);
}

buildParticles(TOTAL_PARTICLES);

// ═══════════════════════════════════════════════════════
// ANIMATION LOOP
// ═══════════════════════════════════════════════════════

var fpsEl = document.getElementById('fps');
var frameCount = 0;
var lastFpsTime = performance.now();

function animate() {
  requestAnimationFrame(animate);

  var t = performance.now() * 0.001 * speed;
  var pos = geometry.attributes.position.array;
  var sz = geometry.attributes.size.array;

  // Lerp positions toward targets + organic motion
  for (var i = 0; i < TOTAL_PARTICLES; i++) {
    var i3 = i * 3;
    // Smooth lerp
    pos[i3]     += (targets[i3]     - pos[i3])     * 0.02;
    pos[i3 + 1] += (targets[i3 + 1] - pos[i3 + 1]) * 0.02;
    pos[i3 + 2] += (targets[i3 + 2] - pos[i3 + 2]) * 0.02;
    // Organic drift
    pos[i3]     += Math.sin(t + i * 0.01) * 0.003;
    pos[i3 + 1] += Math.cos(t + i * 0.013) * 0.003;
    pos[i3 + 2] += Math.sin(t * 0.7 + i * 0.009) * 0.002;
  }
  geometry.attributes.position.needsUpdate = true;

  // Core pulse (first ~500 particles = core layer)
  var coreCount = Math.round(LAYER_CONFIG.core.particles * (TOTAL_PARTICLES / 15000));
  for (var j = 0; j < coreCount; j++) {
    sz[j] = baseSizes[j] * (1 + Math.sin(t * 2.5 + j * 0.5) * 0.4);
  }
  geometry.attributes.size.needsUpdate = true;

  // Pulsating core light
  coreLight.intensity = 2 + Math.sin(t * 1.5) * 0.8;

  controls.update();
  renderer.render(scene, camera);

  // FPS counter
  frameCount++;
  var now = performance.now();
  if (now - lastFpsTime >= 1000) {
    fpsEl.textContent = frameCount + ' FPS';
    frameCount = 0;
    lastFpsTime = now;
  }
}

animate();

// ═══════════════════════════════════════════════════════
// RAYCASTER — Hover tooltip
// ═══════════════════════════════════════════════════════

var raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 0.5;
var mouse = new THREE.Vector2();
var tooltipEl = document.getElementById('tooltip');

renderer.domElement.addEventListener('mousemove', function(e) {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  var intersects = raycaster.intersectObject(particles);

  if (intersects.length > 0) {
    var idx = intersects[0].index;
    var node = getNodeForParticle(idx, TOTAL_PARTICLES);
    if (node) {
      var layerCfg = LAYER_CONFIG[node.layer];
      tooltipEl.querySelector('.tt-name').textContent = node.name;
      tooltipEl.querySelector('.tt-layer').textContent = layerCfg.label + ' — ' + node.desc;
      tooltipEl.style.left = (e.clientX + 16) + 'px';
      tooltipEl.style.top = (e.clientY - 10) + 'px';
      tooltipEl.style.opacity = '1';
      tooltipEl.style.borderColor = layerCfg.hex;
      tooltipEl.querySelector('.tt-name').style.color = layerCfg.hex;
    }
  } else {
    tooltipEl.style.opacity = '0';
  }
});

// ═══════════════════════════════════════════════════════
// CLICK — Zoom to layer cluster
// ═══════════════════════════════════════════════════════

renderer.domElement.addEventListener('click', function(e) {
  // Only handle clicks not on UI
  if (e.target !== renderer.domElement) return;

  raycaster.setFromCamera(mouse, camera);
  var intersects = raycaster.intersectObject(particles);

  if (intersects.length > 0) {
    var idx = intersects[0].index;
    var layer = getLayerForParticle(idx, TOTAL_PARTICLES);
    var cfg = LAYER_CONFIG[layer];
    var midR = (cfg.radius[0] + cfg.radius[1]) / 2;

    // Smooth zoom: move camera to look at the layer's radius
    var dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    var target = new THREE.Vector3(
      dir.x * midR * 0.5,
      dir.y * midR * 0.5,
      dir.z * midR * 0.5
    );

    // Animate camera
    var startPos = camera.position.clone();
    var endPos = camera.position.clone().normalize().multiplyScalar(midR + 12);
    var startTime = performance.now();
    var duration = 800;

    function zoomStep() {
      var elapsed = performance.now() - startTime;
      var progress = Math.min(elapsed / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      camera.position.lerpVectors(startPos, endPos, ease);
      if (progress < 1) requestAnimationFrame(zoomStep);
    }
    zoomStep();
  }
});

// ═══════════════════════════════════════════════════════
// CONTROLS — Sliders & Buttons
// ═══════════════════════════════════════════════════════

// Particle count
var slParticles = document.getElementById('sl-particles');
var vParticles = document.getElementById('v-particles');
slParticles.addEventListener('input', function() {
  var val = parseInt(this.value);
  vParticles.textContent = val;
});
slParticles.addEventListener('change', function() {
  var val = parseInt(this.value);
  buildParticles(val);
});

// Speed
var slSpeed = document.getElementById('sl-speed');
var vSpeed = document.getElementById('v-speed');
slSpeed.addEventListener('input', function() {
  speed = parseFloat(this.value);
  vSpeed.textContent = speed.toFixed(1);
});

// Glow
var slGlow = document.getElementById('sl-glow');
var vGlow = document.getElementById('v-glow');
slGlow.addEventListener('input', function() {
  glowIntensity = parseFloat(this.value);
  vGlow.textContent = glowIntensity.toFixed(1);
  if (material) {
    material.opacity = Math.min(glowIntensity * 0.57, 1.0);
  }
});

// Formation buttons
var formBtns = document.querySelectorAll('.form-btn');
formBtns.forEach(function(btn) {
  btn.addEventListener('click', function() {
    formBtns.forEach(function(b) { b.classList.remove('active'); });
    this.classList.add('active');
    currentFormation = this.getAttribute('data-formation');
    targets = getFormationTargets(currentFormation, TOTAL_PARTICLES);
  });
});

// ═══════════════════════════════════════════════════════
// RESIZE
// ═══════════════════════════════════════════════════════

window.addEventListener('resize', function() {
  var w = window.innerWidth;
  var h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});
