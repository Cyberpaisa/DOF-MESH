# Feedback Log — Style Corrections

## Correcciones de Estilo
| Fecha | Agente | Correccion |
|-------|--------|------------|
| -- | -- | -- |

*Registrar aqui cuando el operador corrige el output de un agente*
*Esto ayuda a calibrar el tono y formato de cada agente*

## Patrones Detectados
- (se llenara con uso)

## Reglas Aprendidas
- (se llenara con feedback del operador)

### 29. Security — Never Use git add -A
- Problem: `git add -A` committed keys/oracle_key.json (HMAC secret) to PUBLIC repo
- Solution: Removed from tracking, added keys/ to .gitignore, rotated key
- Rule: NEVER use `git add -A`. Always use explicit `git add file1 file2`. Review staged files with `git status` before commit
- Severity: CRITICAL — secrets in public repo history are permanent even after removal

### 30. Token Tracking for Cost Observability
- Problem: No visibility into how many tokens each LLM call consumed
- Solution: TokenTracker in observability.py logs per-call: provider, model, tokens, latency, cost
- Rule: Always track token consumption — it's the primary cost driver in LLM systems

### 31. Test Count Drift
- Problem: Test count changed from 624 → 617 between implementations because test methods were refactored
- Rule: After ANY test file change, run full suite and update ALL docs with actual count. Never assume test count — always verify

### 32. Self Protocol — Complementary Not Competitive
- Observation: Self Protocol = identity (WHO is the agent). DOF = behavior (WHAT did the agent do)
- Rule: Position DOF as complementary to identity solutions. Identity + Behavior = complete trust stack

---

## Session: March 7, 2026 — README, Identity, CI, E2E

### #33: README is a door, not a library
Paper-grade READMEs kill engagement. Best READMEs (4K+ stars): banner → badges → quickstart → problem → highlights. Move methodology, assumptions, threat model to docs/. README max 250 lines. Quickstart visible without scrolling.

### #34: Banner/mascot = project identity
OpenClaw has lobster, GitHub has Octocat, DOF has owl. Projects with visual identity get more engagement. The mascot should have PERSONALITY and ATTITUDE, not be flat corporate. Warm colors (brown/amber) > cold colors (blue/teal) for approachability. Generate with AI image tools, iterate 4-5 times.

### #35: Cover image ≠ README banner
Dev.to/X cover images are 1000x420 with stats, layers, scanner data. GitHub README banners are centered on white, logo + name + tagline only. Different formats for different platforms.

### #36: X does not support markdown
Bold (**text**) does not render on X/Twitter. Use Unicode bold characters (bold) for emphasis. These render correctly on any platform.

### #37: Storytelling post > technical spec
A post telling the real story (failures, 2AM debugging, leaked keys, Reddit bans) gets more engagement than a feature list. People share stories, not specs. The best posts are honest about what went wrong.

### #38: Always declare ALL dependencies in requirements.txt
z3-solver was installed locally but missing from requirements.txt. CI failed on GitHub servers because of this. Every import in your code must have a corresponding entry in requirements.txt. Test CI before assuming it works.

### #39: GitHub Actions = external validation
Local tests prove it works on YOUR machine. CI proves it works on ANY machine. The green badge "CI passing" is the industry standard for credibility. Without it, 685 tests are invisible to the world.

### #40: CI will fail on the first run — expect it
Missing dependencies, path differences, import order issues. Always monitor the first CI run and fix immediately. Common failures: missing packages, hardcoded local paths, environment variables not available.

### #41: DOF is independent — not integrated into Sentinel
After architecture review with the dev team: DOF publishes attestations on-chain. The scanner reads them passively if it wants. DOF is NOT a component of the scanner scoring system. This reduces coupling and makes DOF useful for anyone, not just Enigma.

### #42: Figma diagrams need visual differentiation
Flat uniform boxes with no colors = unreadable diagrams. Use: diamonds for decisions (Supervisor ACCEPT/RETRY, Z3 VERIFIED/FAIL), cylinders for databases, colored fills per layer, dotted lines for passive reads, solid lines for active flows.

### #43: GitHub Releases ≠ Git Tags
Tags (v1.1, v1.2) exist in git but are invisible to most users. GitHub Releases with release notes are what people see. Always create a Release with full changelog for each version, not just a tag.

### #44: Separate docs from README
docs/METRICS.md: statistical methodology, assumptions, threat model (154 lines)
docs/GETTING_STARTED.md: onboarding guide
paper/PAPER_OBSERVABILITY_LAB.md: full research paper
README: door (222 lines). Docs: library.

### #45: E2E tests validate the full system offline
54 tests across 15 modules with zero external dependencies. Proves DOF works end-to-end without Avalanche, Supabase, or any API. Uses SQLite in-memory and mocks. This is the strongest validation after CI.

### #46: Files with spaces in names break shell commands
ChatGPT image downloads have names like "ChatGPT Image 7 mar 2026, 11_05_03 a.m..jpeg". Always rename to remove spaces before using in shell: mv 'long name.jpeg' /tmp/simple.jpeg

### #47: Always check the LATEST CI run
GitHub Actions page shows all runs. Old failed runs stay visible. Always navigate to page 1 or filter by the latest commit hash to see current status. Don't panic over old red badges.

### #48: Badge order matters for README
Optimal order: CI status (dynamic) → tests (static) → Z3 → attestations → PyPI → license → LOC → network. CI badge first because it's the only dynamic one — green = credibility.

### #49: Community forums ban new accounts that self-promote
CrewAI Forum silenced our account after community reports. Pattern: new account + multiple posts with links to own project = flagged as spam. The 90/10 rule: 90% value without links (answer questions, help others), 10% your project. Build reputation BEFORE sharing links. This applies to Reddit, CrewAI Forum, Discord communities, and any moderated forum. Dev.to, X, and PyPI don't have this filter.

### #50: SDK usability > SDK completeness
v0.1.0 exported 1 thing (GenericAdapter). v0.2.0 exports 20+ components + quick functions + CLI. The difference: someone can use DOF in 3 seconds now. quick.verify() does in 1 line what used to take 15 lines of imports and setup. Always build the "easy door" first.

### #51: Semantic hallucination detection needs multiple strategies
One regex strategy = 0% FDR. Six strategies (pattern + cross-reference + consistency + entity extraction + numerical plausibility + self-consistency) = 96.8% F1. No single strategy catches everything. Stack them.

### #52: Privacy benchmarks validate trust claims
AgentLeak-inspired 200-test benchmark proved DOF catches 71% of privacy leaks across 7 channels. PII detection (92%) is strong, memory leaks (60%) need work. Publishing honest numbers builds more credibility than claiming 100%.

### #53: OpenTelemetry integration must be zero-overhead
No-op pattern: if OTel not installed, every operation is a pass-through. Zero import cost, zero runtime cost. Optional dependencies in pyproject.toml: pip install dof-sdk[otel]. Never force infrastructure on users.

### #54: Event streaming starts in-memory
EventBus with InMemoryBackend (deque 10K) is the right Phase 8 prep. Abstract EventBackend interface means swapping to Redis/Kafka later is one class. Don't install infrastructure before you need it (1000+ exec/day threshold).

---

## Session: March 8, 2026 — Enterprise Colab Test (dof-sdk 0.2.1)

### #55: Runtime deps MUST be in required, not [dev]
**Fecha:** 2026-03-08 | **Source:** Prueba externa Colab (dof-sdk 0.2.1)
Issue: z3-solver y blake3 no estaban en deps PyPI. Fix: Movidos a required en pyproject.toml v0.2.1. Regla: Todas las deps de runtime van en `required`, no en `[dev]`.

### #56: Public APIs must be tolerant to input format
**Fecha:** 2026-03-08 | **Source:** Prueba externa Colab (dof-sdk 0.2.1)
Issue: MerkleBatcher.add() lanzaba ValueError con texto plano. Fix: Auto-hash SHA256 interno en v0.2.2. Regla: APIs publicas deben ser tolerantes al input del usuario.

### #57: Error classifier must cover ALL framework domains
**Fecha:** 2026-03-08 | **Source:** Prueba externa Colab (dof-sdk 0.2.1)
Issue: ErrorClass.UNKNOWN para patrones LLM/Provider/Memory/Hash/Z3. Fix: 9 categorias en v0.2.2 (era 4). Regla: El clasificador debe cubrir todos los dominios del sistema. UNKNOWN solo para errores genuinamente no clasificables.
