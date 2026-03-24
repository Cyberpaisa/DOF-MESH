# Changelog — DOF (Decentralized Oracle Framework)

---

## [0.5.0] — 2026-03-24 — Mesh Legion & Phase 9 Autonomous Scaling

### Highlights
- **100 core modules** | **117 test files** | **3,115 tests** | 0 errors
- Full autonomous mesh: perceive → route → execute → evaluate — no human in the loop
- Phase 9 Autonomous Scaling: cost-aware, latency-aware, health-aware orchestration
- DOF_MESH compliance: **100%** (all 5 security gaps closed)

### New Modules — Phase 9 Autonomous Scaling
- `core/mesh_orchestrator.py` — Central nervous system: routing + circuit breaker + cost optimizer + auto-scaler in one deterministic loop
- `core/mesh_router_v2.py` — O(√n) intelligent routing with latency/specialty scoring (DeepSeek algorithm)
- `core/mesh_bridge.py` — HTTP bridge for remote dashboard access (port 8080) + REST API
- `core/mesh_consensus.py` — Raft consensus log for distributed state coordination
- `core/mesh_load_balancer.py` — Round-robin / weighted / least-loaded strategies
- `core/mesh_dns_sd.py` — Service discovery with TTL-based expiry (DNS-SD pattern)
- `core/mesh_nat_punch.py` — NAT traversal for cross-network federation (Medellín ↔ Houston)

### New Modules — Security Hardening
- `core/kms.py` — AES-256-GCM vault (NaCl SecretBox), master key in `keys/vault/master.key`
- `core/dlp.py` — Data Loss Prevention: 18 regex patterns + Shannon entropy (threshold 4.5)
- `core/cerberus.py` — 3-headed message guardian: syntax + semantics + policy validation
- `core/icarus.py` — Proactive threat hunter with honeypot integration
- `core/mesh_guardian.py` — Base message validator for all mesh traffic
- `core/honeypot.py` — 3 trap nodes, auto-block, CRITICAL alerts, audit-logged
- `core/pqc_analyzer.py` — Post-quantum crypto assessment (ML-KEM-768, ML-DSA-65)
- `core/contract_scanner.py` — Solidity vulnerability scanner (reentrancy, tx.origin, selfdestruct)
- `core/opsec_shield.py` — Infrastructure security audit (file permissions, exposed secrets)
- `core/a_mem.py` — A-Mem zettelkasten knowledge graph (NeurIPS 2025 pattern)
- `core/security_hierarchy.py` — L0→L4 orchestrator security layers

### New Modules — Intelligence
- `core/mesh_router.py` — DeepSeek O(√n) routing algorithm
- `core/cognitive_map.py` — 8 model family cognitive profiles for task-to-model matching
- `core/autonomous_planner.py` — Repo scanner: detects missing tests/TODOs, dispatches to free providers
- `core/mesh_auto_provisioner.py` — Dynamic node provisioning based on load
- `core/mesh_metrics_collector.py` — Prometheus + JSONL telemetry (nodes, messages, events/min, health)
- `core/mesh_auto_scaler.py` — Hysteresis-based scale-up/scale-down decisions
- `core/mesh_cost_optimizer.py` — Provider cost matrix ($0.00 local → $3.00/M Opus)
- `core/mesh_circuit_breaker.py` — Per-node circuit breaker with CLOSED/OPEN/HALF_OPEN states

### New Modules — Mesh Infrastructure
- `core/claude_commander.py` — 5 execution modes: SDK, Spawn, Team, Debate, Peers
- `core/autonomous_daemon.py` — Self-governing daemon: Perceive → Decide → Execute → Evaluate
- `core/node_mesh.py` — NodeRegistry + MessageBus + SessionScanner + MeshDaemon
- `core/local_node_runner.py` — Ollama/MLX local node runner
- `core/api_node_runner.py` — Multi-provider cloud node runner (8 free providers)
- `core/legion_orchestrator.py` — Multi-model Legion coordination
- `core/local_model_node.py` — Local model node abstraction

### Integration
- `NodeMesh.send_message()` now accepts `route_task_type='code'` with `to_node='auto'` — MeshRouterV2 picks optimal destination
- E2E encryption active on all inbox deliveries (NaCl box)
- Rate limiting per node (VULN-N003)

### Scripts
- `scripts/mesh_status.py` — Enhanced ASCII status dashboard
- `scripts/mesh_health_dashboard.py` — Live health dashboard (ANSI + Unicode box drawing)
- `scripts/mesh_benchmark.py` — Performance benchmarking suite
- `scripts/mesh_dispatcher.py` — CLI task dispatch to mesh
- `scripts/mesh_watchdog.py` — Process watchdog, auto-restart
- `scripts/mesh_monitor.py` — ASCII live mesh monitor (--live, --json)

### Tests
- Tests: **2,041 → 3,115** (+1,074 this release cycle)
- Test files: **85 → 117** (+32)
- 0 import errors | 0 syntax errors | 3 irresolvable generated contradictions (known)

### Numbers
- Core modules: **49 → 100** (+51)
- Providers: 8 (Cerebras, DeepSeek, SambaNova, NVIDIA, GLM-5, Gemini, Groq, local)
- Security layers: 3 → 7
- Compliance gaps: 5/5 closed (E2E, mTLS, KMS, SHA3 audit chain, DLP)

---

## [0.4.1] — 2026-03-19 — Claude Commander, Node Mesh, Skills Engine v2.0

### Added
- `core/claude_commander.py` — ClaudeCommander with 5 modes and persistent sessions
- `core/autonomous_daemon.py` — Self-governing 4-phase daemon (multi-daemon: Builder/Guardian/Researcher)
- `core/node_mesh.py` — Infinite agent network via filesystem JSON protocol
- Skills Engine v2.0: 18 skills, 5 ADK patterns, routing audit
- Mission Control dashboard: 7 tabs (COMMS, SWARM, TRACKS, TRACES, NEURAL, SKILLS, SHIELD)
- Blockchain skills: evm_audit (500+ items), solidity_security, foundry_testing
- Telegram commands: /claude, /team, /parallel, /daemon, /multidaemon

---

## [0.3.3] — 2026-03-09 — Z3 Proof Hash Attestations

### Added
- `core/z3_proof.py` — `Z3ProofAttestation` with keccak256 proof hash
- `core/proof_hash.py` — Deterministic proof serialization and hashing
- `core/proof_storage.py` — Local storage (default) + optional IPFS via Pinata
- `contracts/DOFProofRegistry.sol` — New on-chain proof registry (existing contracts untouched)
- Every attestation now includes `z3_proof_hash`, `invariants_verified`, `storage_ref`
- Public `verifyProof()` function — anyone can verify proofs on-chain
- `ProofRegistered` event for indexing

### Changed
- 3-layer publish pipeline now registers proofs: PG → Enigma → Avalanche + ProofRegistry
- Paradigm shift: trust-by-scoring → **trust-by-proof**

---

## [0.3.2] — 2026-03-09 — Auto-Counterexample Test Generation

### Added
- `core/z3_test_generator.py` — Converts Z3 counterexamples and boundary cases to unittest
- `core/boundary.py` — Boundary case engine using Z3 solver
- `.github/workflows/z3-verify.yml` — CI runs `verify-states` + `verify-hierarchy` on Z3 file changes
- `tests/z3_generated/` — Directory for auto-generated tests
- Z3 discovers edge cases humans wouldn't think of → auto-generates regression tests

---

## [0.3.1] — 2026-03-09 — Z3 Gate for Agent Outputs

### Added
- `core/z3_gate.py` — `Z3Gate` validates agent outputs before execution
- `core/agent_output.py` — `AgentOutput` protocol with `as_z3_constraints()`
- Neurosymbolic architecture: LLM proposes → Z3 approves/rejects with counterexample
- `GateResult`: APPROVED | REJECTED | TIMEOUT | FALLBACK
- Timeout gracefully delegates to deterministic layers (Constitution → AST → Arbiter → LoopGuard)

### Changed
- Meta-Supervisor decisions now gated by Z3 before execution
- Red/Blue agent outputs validated (they're already deterministic internally)

---

## [0.3.0] — 2026-03-09 — State Transition Verification

### Added
- `core/state_model.py` — `DOFAgentState` as Z3 symbolic variables
- `core/transitions.py` — `TransitionVerifier` with 8 formally proven invariants
- `core/hierarchy_z3.py` — All 42 hierarchy patterns translated to Z3 constraints
- CLI commands: `dof verify-states`, `dof verify-hierarchy`
- 8 invariants PROVEN: threat→blocked, trust bounds, hierarchy constraints, cooldown, governor auth, safety score, auto-correction

### Results
- `verify-states`: 8/8 PROVEN in 107.7ms
- `verify-hierarchy`: PROVEN (42 patterns) in 4.9ms
- Mathematical guarantee: no sequence of actions can violate governance

---

## [0.2.8] — 2026-03-09

### Fixed
- Closed missing threat patterns: "updated instructions", "root access for this session"
- Enterprise Report v5: 6/6 PASS APPROVED

## [0.2.7] — 2026-03-09

### Added
- `DOFThreatPatterns` 12 categories with `composite_detection` and `decode_and_scan`

## [0.2.6] — 2026-03-08

### Added
- `enforce_hierarchy` with 33 patterns in 2 categories

## [0.2.0] — 2026-03-07

### Added
- Initial PyPI release: 27K LOC, 25 modules, BSL-1.1 license
- Benchmark: Gov 100% FDR, Code 86%, Hallucination 90%, Consistency 100%, F1 96.8%
- Production agents #1686, #1687 (rank #1, #2 of 1,772)
