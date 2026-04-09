# Knowledge Base Schema: DOF-MESH Second Brain

## What This Is
A personal sovereign knowledge base (Second Brain) for CyberPaisa. This brain contains context about DeFi, Autonomous Agents (MoE), Sovereign Architecture, Startup Pitching, Negotiation Principles, and Conflux Integrations.

## How It's Organized
- `raw/`: Contains unprocessed source material (PDFs, Meeting Notes, Voice Transcripts, External Snippets). **HUMAN dumps context here. AI NEVER modifies these original files.**
- `wiki/`: Contains the highly organized, structured, and cross-linked knowledge. **AI maintains this entirely.**
- `outputs/`: Contains generated reports, pitch decks, market research, and analyses compiled by querying the Wiki.

## Wiki Rules
- Every topic gets its own `.md` file in `wiki/`.
- Every wiki file starts with a one-paragraph **executive summary** (TL;DR).
- Link related topics using `[[topic-name]]` format or Markdown relative links.
- Maintain an `INDEX.md` that acts as the Map of Content (MOC).
- When a human drops new raw sources in `raw/`, the AI (via the Second-Brain Skill) must ingest them, summarize them, and update the relevant wiki articles without duplicating.

## Core Directives for the AI
1. **Never Hallucinate Context:** If the answer is not in the `wiki/` or `raw/`, say it is not in the Second Brain.
2. **Prioritize Determinism:** The knowledge base is a tool for sovereign execution. Keep explanations dense, technical but accessible, and free of fluff.
3. **Monthly Health Check:** Analyze for contradictions across files and flag them in a report placed in `outputs/`.
