# COMPETITION BIBLE -- The Definitive Bible for Hackathons

> Competitive intelligence document based on Synthesis 2026 (685 projects, $100K prize pool).
> Author: Cyber Paisa -- Enigma Group
> Base date: March 27, 2026
> Use: Mandatory reference before, during, and after every hackathon.

---

## Table of Contents

1. [Lessons Learned -- Synthesis 2026](#1-lessons-learned----synthesis-2026)
2. [Pre-Hackathon Checklist (30 items)](#2-pre-hackathon-checklist-30-items)
3. [Competitive Stack](#3-competitive-stack----what-we-must-have)
4. [Pitch Templates](#4-pitch-templates)
5. [Ideal Hackathon Timeline (10 days)](#5-ideal-hackathon-timeline-10-days)
6. [Post-Mortem Template](#6-post-mortem-template)

---

## 1. Lessons Learned -- Synthesis 2026

### What we did well

| Action | Why it matters |
|--------|-----------------|
| YouTube video | Most projects have no video. Judges appreciate quick visual content. |
| Professional DOF owl logo | Memorable branding. Among 685 projects, image matters more than we think. |
| 11 tracks = maximum exposure | We were seen in all categories. Guaranteed at least one review. |
| Real differentiating tech (Z3, deterministic, zero-LLM governance) | No other project had formal agent verification. Unique in the field. |
| Concrete numbers | 238 autonomous cycles, 986 tests, 48 on-chain attestations. Numbers don't lie. |
| Killer phrase | "Agent acted autonomously. Math proved it. Blockchain recorded it." -- Memorable and differentiating. |

### Mistakes NOT to repeat

| Mistake | Impact | Solution for next time |
|-------|---------|--------------------------|
| No public production service | Observer Protocol had 82 agents registered, live since Feb 2026. We only had a repo. | Have at least 1 public endpoint working BEFORE applying. |
| Too many tracks (11) | Looks like "spray and pray". Judges notice. Dilutes the message. | Maximum 4 tracks, well chosen, with narrative adapted to each. |
| Too technical pitch | "Z3 theorem prover" means nothing to a business judge. We lost non-technical audience. | Pitch in impact language: "we mathematically prove the agent did the right thing". |
| Only 2 own agents | Without external users, it looks like a toy project. | Get at least 5-10 third-party agents registered before submission. |
| Basic landing page | Winners have interactive demos, GIFs, live metrics. | Landing with embedded demo, real metrics, registration CTA. |
| No external adoption metrics | "We use it ourselves" is not traction. | Invite builders, document external usage, show growth charts. |
| No published SDK | Competitors like Observer had `pip install` or `npm install`. | Publish minimal SDK on npm/pip before the hackathon. |
| README without Quick Start | Judges have 5 minutes per project. If they can't try it quickly, next. | Quick Start of 5 lines maximum. Copy-paste and it works. |

### Competitors who taught us

#### Observer Protocol -- "The production standard"
- **Key lesson**: "This isn't a demo. It's infrastructure running in production since February 2026."
- 82 agents registered, 67 actively transacting
- LIVE on mainnet, not testnet
- **Takeaway**: Real production kills any demo. Priority #1 always.

#### Strata -- "The power of ZK"
- ZK rollup for AI cognition
- ZK proofs > JSONL logs (we use JSONL)
- **Takeaway**: Cryptographic proofs are more convincing than logs. Explore circom/noir.

#### ALIAS -- "Reputation as a primitive"
- Proof-of-Reputation as reusable on-chain primitive
- Not a feature, but a building block for others
- **Takeaway**: Position our trust score as a primitive, not a feature.

#### Sentinel8004 -- "Automatic scale"
- Scans 3,766 agents from the registry automatically
- Does not depend on agents manually registering
- **Takeaway**: Automate onboarding. Scan, don't wait.

#### DJZS Protocol -- "Prevention > Detection"
- Intercepts reasoning BEFORE execution
- 11 predefined failure codes
- **Takeaway**: Preventive governance is more valuable than post-facto auditing.

#### Chorus -- "Cryptographic consensus"
- FROST threshold signatures for multi-agent consensus
- Multiple agents sign together, not one alone decides
- **Takeaway**: Threshold crypto adds real trust, not just social governance.

#### OmniAgent -- "Cross-chain identity"
- ERC-8004 x LayerZero V2 = agent identity on multiple chains
- One agent, one identity, any blockchain
- **Takeaway**: Cross-chain identity is the natural next step for DOF.

#### Shulam -- "Compliance-first"
- 45 autonomous solutions with integrated compliance
- Regulatory-ready from day 1
- **Takeaway**: Compliance is not an afterthought. Institutional judges value it.

#### zkx402 -- "Privacy in payments"
- ZK + x402 = verifiable payments without revealing amounts
- Privacy as a payment feature between agents
- **Takeaway**: Privacy + payments is a powerful and underexplored niche.

#### Maiat8183 -- "Meta-governance"
- "Who watches the watchers?"
- Governance of governance itself
- **Takeaway**: The meta-question is powerful narratively and technically valid.

---

## 2. Pre-Hackathon Checklist (30 items)

### A. Technical Preparation (1-10)

- [ ] **1. Clean and public repo** -- Updated README, no secrets, no junk files, clear license
- [ ] **2. Green CI/CD** -- GitHub Actions passing. Green badge visible in README
- [ ] **3. Tests with >80% coverage** -- Number of tests visible in README (e.g.: "986 tests passing")
- [ ] **4. Production deploy** -- Public URL working, not localhost. Preferably mainnet
- [ ] **5. /health endpoint responding** -- `curl https://your-api.com/health` must return 200 + version + uptime
- [ ] **6. Agent.json registered and validated** -- In ERC-8004 registry, complete metadata, mandatory fields filled
- [ ] **7. Funded wallet** -- Enough gas for transactions during hackathon (minimum 0.5 AVAX + 5 USDC)
- [ ] **8. Published SDK** -- `npm install your-sdk` or `pip install your-sdk` working
- [ ] **9. API documentation** -- Swagger/OpenAPI or at least a doc with all endpoints
- [ ] **10. 5-line Quick Start** -- From zero to "it works" in less than 2 minutes

### B. Presentation and Branding (11-20)

- [ ] **11. Demo video (2-3 min)** -- Uploaded to YouTube, no annoying music, with subtitles if possible
- [ ] **12. Professional cover image** -- 1200x630px minimum. Logo, name, tagline. No generic templates
- [ ] **13. 1-line pitch** -- Non-technical. Understandable by anyone. Tested with non-tech people
- [ ] **14. Landing page with CTA** -- Public URL, embedded demo or demo link, registration button
- [ ] **15. Product screenshots/GIFs** -- At least 3 captures showing the main flow
- [ ] **16. Professional team profile** -- Photo/avatar, short bio, relevant links (GitHub, Twitter)
- [ ] **17. Social proof** -- At least 3-5 tweets/posts about the project BEFORE submission
- [ ] **18. Selection of 3-4 tracks** -- Maximum 4. Each with adapted narrative, not copy-paste
- [ ] **19. README with badges** -- CI status, version, license, tests, coverage. Visual professionalism
- [ ] **20. Memorable name** -- If the name is not remembered in 5 seconds, change it

### C. Traction and Metrics (21-25)

- [ ] **21. Real adoption metrics** -- Users, transactions, registered agents. Verifiable numbers
- [ ] **22. On-chain attestations visible** -- Link to explorer showing real transactions
- [ ] **23. At least 5 external users/agents** -- Not just your own. Third parties using the system
- [ ] **24. Documented uptime** -- How long the service has been running without interruptions
- [ ] **25. Growth chart** -- Even if small, show positive trend

### D. Competition Strategy (26-30)

- [ ] **26. Competitor analysis** -- Know at least 10 projects in the same tracks
- [ ] **27. Clear differentiator** -- 1 thing that NOBODY else has. Documented and prominent
- [ ] **28. Response plan to questions** -- Internal FAQ with the 10 most likely judge questions
- [ ] **29. Technical backup plan** -- If deploy fails during judging, have video/screenshots as backup
- [ ] **30. Post-submit engagement** -- Plan to respond to judge comments in the first 24h

---

## 3. Competitive Stack -- What We Must Have

### Technology Matrix

| Technology | Do we have it? | Priority | Reference | Estimated Effort | Impact on Judges |
|---|---|---|---|---|---|
| ZK Proofs (circom/noir) | NO | HIGH | Strata, zkx402 | 2-3 weeks | Very high -- cryptographic proofs > logs |
| Cross-chain bridge (LayerZero V2) | NO | HIGH | OmniAgent | 1-2 weeks | High -- multi-chain is the future |
| Threshold signatures (FROST) | NO | MEDIUM | Chorus | 2-3 weeks | High -- real cryptographic consensus |
| Public API in production | NO | CRITICAL | Observer Protocol | 3-5 days | Critical -- without this we can't compete |
| Compliance layer | NO | MEDIUM | Shulam | 1-2 weeks | Medium-high -- institutional judges |
| Insurance/surety bonds | NO | LOW | Surety | 3-4 weeks | Medium -- niche but differentiating |
| Published SDK (npm/pip) | NO | HIGH | Observer, others | 1 week | High -- facilitates evaluation |
| Live metrics dashboard | NO | HIGH | Sentinel8004 | 1 week | High -- visual and impactful |
| Privacy in payments (ZK+x402) | NO | MEDIUM | zkx402 | 3-4 weeks | High -- powerful narrative |
| Automatic registry scanning | NO | MEDIUM | Sentinel8004 | 1 week | Medium -- shows scale |
| Z3 formal verification | YES | -- | Unique to us | Already done | Very high -- nobody else has it |
| Deterministic governance | YES | -- | Unique to us | Already done | High -- core differentiator |
| On-chain attestations | YES | -- | Several | Already done | Medium -- many have it |
| ERC-8004 identity | YES | -- | Standard | Already done | Base -- everyone has it |
| x402 payments | YES | -- | Ultravioleta DAO | Already done | Medium -- few implement it well |

### Implementation Priorities (recommended order)

1. **Public API in production** -- Without this, there is nothing to show. Week 1.
2. **Published SDK** -- `npm install dof-mesh-sdk`. Week 1-2.
3. **Metrics dashboard** -- Landing page with live data. Week 2.
4. **ZK Proofs** -- Replace JSONL logs with cryptographic proofs. Week 3-4.
5. **Cross-chain (LayerZero)** -- DOF identity on Avalanche + Base + Ethereum. Week 4-5.

---

## 4. Pitch Templates

### For technical judges
> "DOF-MESH is the only framework that uses Z3 formal verification to mathematically prove that autonomous agent decisions comply with their governance contracts -- without relying on LLMs for validation."

### For business judges
> "DOF-MESH eliminates risk #1 of autonomous AI agents: that they do something they shouldn't. Companies can deploy agents with mathematical certainty that they operate within their boundaries."

### For AI judges (automated evaluation)
> "DOF-MESH: Deterministic governance framework for autonomous AI agents. Z3 theorem prover validates agent actions against formal specifications. 986 tests, 238 autonomous cycles verified, 48 on-chain attestations. Zero-LLM governance layer ensures verifiable compliance."

### For Twitter/social
> "If your AI agent can act alone, how do you prove it did the right thing? DOF-MESH uses math, not promises. Formal verification + blockchain = agents you can trust."

### For grant applications
> "DOF-MESH brings formal verification to the autonomous agent ecosystem on Avalanche. Our framework enables deterministic governance -- every agent decision is mathematically verifiable and recorded on-chain -- enabling the trust infrastructure needed for an autonomous agent economy at scale."

---

## 4b. Technical Argumentation Framework

### The Agentic Delivery Layer Model — DOF's Architecture in 4 Boundaries

DOF-MESH implements the four-layer agentic delivery model. Use this framing when explaining the architecture to any audience.

```
Foundation → Design → Alignment → Execution
  (rules)   (assembly)  (proof)   (artifact)
```

Think of it as a compiler pipeline:
- **Foundation** = the language spec (primitives that never change)
- **Design** = the program (assembles primitives for a specific use case)
- **Alignment** = the type checker + test suite (proves correctness before build)
- **Execution** = the binary ready to run (zero ambiguity, immediately deployable)

Breaking this pipeline introduces systemic uncertainty. DOF enforces every boundary.

| Layer | DOF Implementation |
|-------|--------------------|
| Foundation | `ConstitutionEnforcer`, Z3 primitives, ERC-8004 ontology |
| Design | Agent archetypes, `MeshRouterV2`, 15 MCP tools |
| Alignment | Sentinel 27 checks, `prompt_eval_gate.py`, ZK batch prover |
| Execution | `ExecutionPack` — machine-readable artifact, OpenAPI + state machine |

---

### Power Phrases — Battle-tested for Judges

**On governance as infrastructure:**
> "Alignment in DOF-MESH is not an external oversight committee. It is a physical property of the system."

**On the mandatory alignment gate:**
> "If alignment is weak, runtime failure is a statistical certainty. DOF makes alignment structurally mandatory — you cannot ship without passing it."

**On non-determinism at scale:**
> "Traditional agentic pipelines allow the four architecture layers to blend together. The result: execution artifacts become non-deterministic and the system's behavior becomes impossible to govern at scale. DOF enforces strict layer boundaries by design."

**On the ExecutionPack (Layer 4):**
> "If a specification cannot be executed immediately, it is functionally incomplete and must be sent back. DOF's ExecutionPack enforces this as a hard error — not a warning."

**On overall value:**
> "DOF transforms agentic systems into consistent, scalable architectures that are predictable by design — not by luck."

---

### Audience-to-Phrase Quick Reference

| Audience | Best phrase |
|----------|-------------|
| Technical judge | "Alignment is a physical property of the system" |
| Business judge | "Runtime failure is a statistical certainty without this gate" |
| VC / investor | "Predictable by design, not by luck" |
| AI safety evaluator | "Governance as infrastructure, not oversight committee" |
| Developer / builder | "Incomplete spec = hard error, not warning. Sent back automatically." |

---

## 5. Ideal Hackathon Timeline (10 days)

### Day 1 -- Reconnaissance and Strategy
- [ ] Read ALL rules, evaluation criteria, available tracks
- [ ] Analyze projects from previous editions (winners and finalists)
- [ ] Identify judges and their backgrounds (LinkedIn, Twitter)
- [ ] Select 3-4 tracks with adapted narrative for each
- [ ] Define the #1 differentiator to communicate
- [ ] Create internal strategy document

### Day 2 -- Base Infrastructure
- [ ] Ensure the repo is clean and public
- [ ] Production deploy working with /health
- [ ] Green CI/CD with badge in README
- [ ] Agent.json registered and validated in the registry
- [ ] Wallet with sufficient funds
- [ ] 5-line Quick Start tested by an external person

### Day 3 -- Main Feature
- [ ] Implement/polish the main hackathon feature
- [ ] Ensure the differentiator is demonstrable in 30 seconds
- [ ] Write tests for the new feature
- [ ] First deploy of the feature to production

### Day 4 -- Demo and Metrics
- [ ] Build landing page with embedded demo
- [ ] Metrics dashboard (even if basic)
- [ ] Generate first real metrics (transactions, registrations)
- [ ] Invite 3-5 external people to test the system

### Day 5 -- SDK and Documentation
- [ ] Publish minimal SDK (npm/pip)
- [ ] Complete API documentation
- [ ] Integration tutorial/guide
- [ ] Test that an external person can integrate in <10 minutes

### Day 6 -- Visual Content
- [ ] Record demo video (2-3 minutes)
- [ ] Create professional cover image
- [ ] Product screenshots/GIFs
- [ ] Upload video to YouTube (no copyright music)

### Day 7 -- Social Proof
- [ ] Publish 3-5 tweets about the project
- [ ] Share in relevant communities (Discord, Telegram)
- [ ] Get at least 2-3 external testimonials/mentions
- [ ] Document updated adoption metrics

### Day 8 -- Polish Submission
- [ ] Write project description for each track
- [ ] Adapt narrative by audience (technical vs business)
- [ ] Review full checklist (all 30 items)
- [ ] Prepare internal FAQ (10 likely judge questions)

### Day 9 -- Submit and Review
- [ ] Submit early (DO NOT wait until the last moment)
- [ ] Check that all links work
- [ ] Verify video, landing, API, demo -- everything accessible
- [ ] Ask an external person to review the complete submission
- [ ] Fix any errors found

### Day 10 -- Post-Submit
- [ ] Monitor judge comments
- [ ] Respond to questions in the first few hours
- [ ] Publish Twitter thread celebrating the submission
- [ ] Document initial post-mortem (what went well, what didn't)
- [ ] Update this document with new lessons

---

## 6. Post-Mortem Template

Copy and fill out after each hackathon:

```markdown
# Post-Mortem: [Hackathon Name]

**Date:** [date]
**Result:** [position / prize / mention]
**Tracks:** [tracks we participated in]
**Total projects:** [number]
**Prize pool:** [amount]

## Detailed Result
- Overall position: ___
- Position by track: ___
- Score (if available): ___
- Judge feedback: ___

## What we did well
1. ___
2. ___
3. ___

## What we did poorly
1. ___
2. ___
3. ___

## What we were missing
1. ___
2. ___
3. ___

## Outstanding competitors
| Project | Why they stood out | What to learn |
|----------|-----------------|--------------|
| ___ | ___ | ___ |
| ___ | ___ | ___ |
| ___ | ___ | ___ |

## Our submission metrics
- Registered agents: ___
- On-chain transactions: ___
- External users: ___
- Uptime during hackathon: ___
- Passing tests: ___
- Video views: ___

## Checklist Compliance
- Completed items: ___ / 30
- Missing critical items: ___

## Actions for the next hackathon
1. [ ] ___
2. [ ] ___
3. [ ] ___
4. [ ] ___
5. [ ] ___

## Technologies we should have had
| Tech | Did we have it? | Would it have changed the result? |
|------|-------------|-------------------------------|
| ___ | ___ | ___ |

## Time invested
- Preparation (pre-hackathon): ___ hours
- Development during hackathon: ___ hours
- Content (video, landing, social): ___ hours
- Total: ___ hours

## Additional notes
___

## COMPETITION BIBLE Update
Changes to add to the main document:
1. ___
2. ___
3. ___
```

---

## Appendix A -- Competitor Phrases We Should Study

> "This isn't a demo. It's infrastructure running in production since February 2026." -- **Observer Protocol**

> "ZK proofs don't lie. Logs do." -- **Strata** (paraphrased)

> "Who watches the watchers?" -- **Maiat8183**

> "Reputation is not a feature. It's a primitive." -- **ALIAS**

> "We intercept reasoning BEFORE execution." -- **DJZS Protocol**

Each of these phrases communicates value in one sentence. Our equivalent:
> **"Agent acted autonomously. Math proved it. Blockchain recorded it."**

---

## Appendix B -- Common Evaluation Criteria in Hackathons

| Criterion | Typical weight | How to win it |
|----------|-------------|--------------|
| Innovation / Originality | 20-30% | Z3 formal verification is unique. Always highlight. |
| Technical execution | 20-25% | Tests, CI, clean code, solid architecture. |
| Impact / Utility | 15-25% | Show real users, metrics, clear problem. |
| Presentation | 10-20% | Professional video, clear landing, memorable pitch. |
| Use of platform/sponsor | 10-15% | Deeply integrate the sponsor's tools. |
| Completeness | 5-10% | Working product, not just an idea. Demo that works. |

---

## Appendix C -- Red Flags Judges Detect

1. **"Coming soon"** anywhere -- if it's not ready, don't mention it
2. **Too many tracks** -- looks like desperation, not strategy
3. **Testnet only** -- mainnet > testnet, always
4. **No video** -- in 685 projects, no video = invisible
5. **3-line README** -- suggests incomplete project
6. **No metrics** -- "trust us" doesn't work
7. **Broken links** -- verify EVERYTHING before submission
8. **Excessive jargon** -- if the judge needs Google to understand, you've lost
9. **Copy-paste between tracks** -- adapt the narrative, don't copy
10. **No visible team** -- anonymous projects generate distrust

---

*This document is updated after each hackathon. Version: 1.0 -- March 2026.*
