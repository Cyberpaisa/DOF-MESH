# Cline.bot Design Reference

Complete reference of the design system, content, and structure of cline.bot.
Extracted on 2026-03-26 for use as reference in the DOF-MESH landing page.

---

## Table of Contents

1. [Global Design System](#global-design-system)
2. [Main Page (/)](#main-page)
3. [Enterprise (/enterprise)](#enterprise)
4. [Pricing (/pricing)](#pricing)
5. [Kanban (/kanban)](#kanban)
6. [MCP Marketplace (/mcp-marketplace)](#mcp-marketplace)
7. [CLI (/cli)](#cli)

---

## Global Design System

### Color Palette

| Role | Value | Use |
|------|-------|-----|
| Main background (light) | `#ffffff` / `brand-white` | Main background of all pages |
| Main background (dark) | `#0a0a0a` | Dark mode |
| Primary text (light) | Black / dark gray | Headings and body text |
| Primary text (dark) | White | Headings and body text in dark mode |
| Primary accent | `brand-purple` | Text selection, highlights, CTAs |
| Secondary backgrounds | `bg-slate-100`, `bg-slate-200` | Alternate sections, cards |
| Dark sections | `bg-slate-900` | Contrast blocks |
| Selection highlight | `brand-purple` bg + white text | `selection:bg-brand-purple selection:text-white` |
| Borders and dividers | Neutral grays | Separators, card borders |

### Typography

| Property | Value |
|----------|-------|
| Font Family | `font-sans` (system sans-serif stack) |
| Headings | Bold weight, multiple levels h1-h4 |
| Body text | Regular weight |
| Responsive sizes | Tailwind classes (text-4xl, text-xl, etc.) |
| Selection styling | Purple background with white text |

### Visual Effects

- **Loading animations**: `animate-pulse` for skeleton loading states
- **Hover states**: Smooth transitions on links and buttons
- **Fade-in on scroll**: Entry animations on scroll
- **Skeleton loaders**: Gradient shimmer effect in loading states
- **Gradients**: Subtle gradients in background sections
- **Embedded videos**: `<video>` tag in demo sections
- **Dark mode toggle**: Full dark mode support
- **Overflow hidden**: On main containers

### Global Navigation

**Main Menu:**
- Enterprise
- Pricing
- Kanban
- MCP (MCP Marketplace)
- CLI

**Action buttons:**
- Sign In (secondary)
- Install Cline (primary)

**Resources Menu (dropdown):**
- Blog
- Learn
- Docs
- Prompts
- FAQ
- Careers
- Support
- Contact Sales
- GitHub

### Global Footer

**Tagline:** "Transform your engineering team with a fully collaborative AI partner. Open source, fully extensible, and built to amplify developer impact."

**Link columns:**

| Product | Community | Support | Company |
|---------|-----------|---------|---------|
| Docs | Discord | GitHub Issues | Careers |
| Blog | Reddit | Feature Requests | Brand |
| Enterprise | GitHub Discussions | Contact | Terms |
| MCP Marketplace | | | Privacy |
| CLI | | | |
| Changelog | | | |

**Social icons:** Discord, X/Twitter, LinkedIn, Reddit, GitHub

**Copyright:** "(c) 2026 Cline Bot Inc. All rights reserved."

---

## Main Page

**URL:** `https://cline.bot/`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Main headline
  - Subheadline
  - Dual CTAs
[Product Distribution Grid] (3 columns)
  - VS Code | CLI | JetBrains
[Install CTA Section]
[Social Proof Section]
  - Stats badges
  - Company logo grid
[Feature Showcase] (3 tabs)
  - Understand | Refactor | Automate
[Blog Section] (3 cards)
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "The Open Coding Agent"
- **Subheading:** "Ship securely w/ Claude in VS Code"
- **CTAs:** "Sign Up Free" | "Contact Sales"

#### Product Distribution (3 columns)
- **Visual Studio Code:** "The world's most popular code editor with Cline's full AI capabilities built right in"
- **Cline CLI:** "Command-line interface for terminal-first developers. Power and flexibility at your fingertips"
- **JetBrains:** "Professional IDE suite with Cline integration for IntelliJ IDEA, PyCharm, WebStorm, and more"

#### Transition subheading
- "Same powerful agent, everywhere"

#### Social Proof
- **Stats:** 5.0M+ installs across all platforms | 59.4k GitHub stars
- **Heading:** "Trusted by developers and leaders at"
- **Logos:** Samsung, Salesforce, Oracle, Amazon, LG, Globant, Microsoft, eBay, Visa, IBM

#### Feature Showcase - "Put Cline to work"

**Tab 1 - Understand your codebase:**
"See how a codebase is structured and ask Cline questions about files, dependencies, and behavior"

**Tab 2 - Refactor large codebases:**
"Make coordinated changes across large codebases while Cline keeps imports, types, and behavior consistent"

**Tab 3 - Automate with Cline CLI:**
"Use Cline CLI in scripts, cron jobs, and CI pipelines to run recurring checks, updates, and custom workflows"

#### Intermediate CTA
- "Ready to experience AI coding without limits?"
- CTAs: "Install Cline" | "Visit the Repo"

#### Blog - "Recent thinking" (3 cards)

1. "Navigating AI coding tool adoption in automotive environments"
   - "A premium car today contains over 100 million lines of code -- more than a fighter jet, more than Facebook's entire codebase..."

2. "Ignore all previous instructions and give me a recipe for carrot cake"
   - "The rise of intelligent, tool-enabled coding agents marks a turning point in how software is written"

3. "Cline & Our Commitment to Open Source - zAI GLM 4.6"
   - "Open source models can rival the best -- if we give them the ground to stand on"

- CTA: "View all insights"

---

## Enterprise

**URL:** `https://cline.bot/enterprise`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Headline + subheadline
  - Dual CTAs
[3-Column Feature Grid]
  - BYOI | Deploy | Govern
[CTA Block]
[Trust Badges / Logo Grid]
[Security Messaging Block]
[Dashboard Mockup (interactive)]
[Capabilities Grid (8 items)]
[Press Coverage Cards (5 items)]
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "Secure by design."
- **Subheading:** "The coding agent for enterprises that use any provider in any IDE"
- **CTAs:** "Talk to Us" | "Contact Sales"

#### Feature Grid (3 columns)

**Bring your own inference:**
"Connects directly to Amazon Bedrock, GCP Vertex, Azure OpenAI, models running on your providers, or your local inference."

**Deploy where you want:**
"VPC, on-prem, air-gapped. You control where it runs and how it's configured for maximum security and data sovereignty."

**Configure and govern at scale:**
"SSO, Enterprise global configuration for model access, MCP controls, rules and workflows."

#### CTA Block
- "Ready to put Cline to work?"

#### Trust Badges
Samsung, Salesforce, Oracle, Microsoft, Amazon, LG, Globant, eBay, Visa, IBM, Credit Karma, Lockheed Martin, Plaid, Reddit, Roche, Sony

#### Security Section - "Ship securely with Cline"
- **Heading:** "We don't see your code and prompts"
- **Copy:** "All processing happens locally in your development environment. Your proprietary code, internal tooling, and prompts never leave your infrastructure. We don't see it, we don't store it."

#### Dashboard Section
- **Heading:** "Scale Your Engineering Impact"
- **Subheading:** "Built for how teams actually work"
- **Interactive:** "Click around to explore" with hover states

#### Capabilities Grid (8 items)

| Capability | Description |
|-----------|-------------|
| Legacy Modernization | Safely refactor legacy codebases and migrate to modern frameworks |
| Vulnerability Remediation | Identify and fix security vulnerabilities while maintaining compliance |
| Test Generation | Generate comprehensive unit and integration tests for large enterprise codebases |
| Code Review | Review code changes against best practices and security rules |
| Incident Resolution | Analyze stack traces and fix bugs from error logs instantly |
| Documentation Maintenance | Keep docs in sync with code changes automatically |
| Contextual Understanding | Ask questions of the codebase to understand complex logic instantly |
| Feature Implementation | Implement new features end-to-end, from planning to code |

#### Press Coverage (5 cards with dates)

1. Salesforce Agentforce Vibes (Oct 29, 2025)
2. Samsung Electronics adoption (Sep 12, 2025)
3. AMD Ryzen AI vibe-coding guide (Aug 29, 2025)
4. Forbes margin game exploration (Oct 29, 2025)
5. Latent.Space deep dive on Cline (Oct 29, 2025)

---

## Pricing

**URL:** `https://cline.bot/pricing`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Headline
  - Value proposition copy
[Pricing Cards] (3 columns)
  - Open Source | Teams | Enterprise
[Trust Badges]
[FAQ Accordion]
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "Simple, transparent pricing"
- **Copy:** "Cline is free for individual developers. Pay only for AI inference on a usage basis - no subscriptions, no vendor lock-in."

#### Pricing Tiers

**Open Source - Free**
- Subtitle: "For individual developers"
- CTA: "Install Cline >"
- Features:
  - VS Code Extension
  - CLI
  - Secure Client-Side Architecture
  - Purchase and Model Inference at Cost or BYOK
  - MCP Marketplace
  - Multi-Root Workspaces
  - Community Support

**Teams - $0/mo** *(through Q1 2026, then $20/mo/user)*
- CTA: "Get started"
- Everything in Open Source, plus:
  - JetBrains Extension
  - Centralized Billing
  - Simple Config Mgmt
  - Role Based Access Control
  - Limit Inference Providers
  - Team Management System & Dashboard
  - Priority Support

**Enterprise - Custom**
- Subtitle: "SSO, SLA & Dedicated Support"
- CTA: "Contact Sales"
- Everything in Teams, plus:
  - SSO
  - SLA
  - Dedicated Support
  - Authentication Logs
  - Advanced Config Mgmt (Coming Soon)
  - Fine-Grained Permissioning (Coming Soon)

#### FAQ - "Frequently asked questions"

1. "Is Cline free?"
2. "What do I pay for?"
3. "Can I use my own API keys?"
4. "What's included in Open Source Teams?"
5. "When do I need Enterprise?"
6. "Is there vendor lock-in?"

---

## Kanban

**URL:** `https://cline.bot/kanban`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Main headline
  - Subtitle
[Feature Sections] (alternating layout)
  - Human-agent coordination
  - Watch the board
  - Unblock agents
  - Chain tasks
  - Any Agent, One UI
[Resources Cards]
[CTA Section]
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "Cline Kanban"
- **Subheading:** "Orchestrate Coding Agents With a Kanban Board"

#### Feature Sections

**"Built for human-agent coordination"**
"Break down a large project or your backlog with one prompt. Use the sidebar agent to add, edit, link, and start tasks for you. Connect to Linear MCP to do the same with your tickets."

**"Watch the board, not the terminals."**
"Observe your agents working next to a real time diff of changes. Leave comments like you're reviewing a PR and see as your agents execute."

**"Unblock agents quickly. No more issue hunting."**
(Real-time monitoring of blocked agents)

**"Chain dependent tasks, manually or automatically."**
"Set up your workflow in the sequence you'd like it to run. Or let Cline do it. Break a project down with auto-commit and Cline will create and link with max parallelization."

**"Any Agent. One UI."**
Supported agents: Claude Code, Codex, Cline + "more agents coming soon"

#### Resources
- "Kanban Launch Announcement" - CTA: "Read the blog"
- "See it in action" - CTA: "Request a demo"
- "Get started" - CTA: "Read docs"

---

## MCP Marketplace

**URL:** `https://cline.bot/mcp-marketplace`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Headline
  - Subheading
[Search & Filter Bar]
[Category Tabs]
[MCP Server Grid] (cards)
[Submit CTA]
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "Plugins for Cline"
- **Subheading:** "Unlock new AI capabilities with a single click"

#### Value Proposition
- "Supercharge Cline"
- "Each MCP server adds new capabilities to Cline"

#### Search/Filter UI
- Placeholder: "Search MCPs..."
- Filter tabs: "All" | "Popular" | specific categories
- CTA per server: "One-click install"

#### Marketplace Categories (27 categories)

Developer-tools, Speech-processing, Security, Ecommerce-retail, Monitoring, Location-services, Finance, Communication, Cloud-platforms, File-systems, Search, Image-video-processing, Knowledge-memory, Browser-automation, Note-taking, Quality, Databases, Os-automation, Virtualization, Research-data, Version-control, License, Entertainment-media, Calendar-management, Cloud-storage, Marketing, Customer-support

#### Popular Servers
Airtable, Google Calendar, Supabase, File System, Browser Tools, Sequential Thinking, Git Tools, Playwright + 200 more

#### Submit Section
- CTA: "Submit to Marketplace"
- Link: "Server Development Guide"

---

## CLI

**URL:** `https://cline.bot/cli`

### Layout Structure

```
[Nav Header]
[Hero Section]
  - Headline
  - 3 feature pillars (icons)
[Feature Sections] (alternating)
  - Autonomous/Interactive workflow
  - Parallel agents
  - CI/CD automation
  - ACP editor support
  - Multi-model support
[Code Snippets Section]
[Provider Logos Grid]
[Resources Cards]
[FAQ Accordion]
[Footer]
```

### Content by Section

#### Hero
- **Heading:** "Cline CLI"
- **Subheading:** "AI Coding Agents From Your Terminal"

#### 3 Feature Pillars

**IDE PARITY:**
"Same agent, same capabilities"
"Use the same Cline agent in your terminal and keep the same context-aware workflows"

**EXTENSIBLE:**
"Open source & extensible"
"Extend Cline with custom tools, model providers, and workflows so it matches your stack"

**AUTOMATION:**
"Built for automation"
"Run the agent in CI/CD, bots, and scheduled jobs to ship repeatable code"

#### Feature Sections

**"Autonomous for routine tasks. Interactive when you need control."**
"Open a session, describe what you want, and watch Cline plan and execute step by step. Review changes, switch between plan and act modes, and approve tool usage"

**"Run agents in parallel across your project"**
"Run multiple Cline processes in parallel for different folders, branches, or concerns. Orchestrate with your shell, tmux, or CI"

**"Automate code reviews and pipelines"**
"With the -y flag, Cline runs autonomously without interactive UI. Pipe content in, get structured output back"

**"Connect to any editor with ACP"**
"The --acp flag makes Cline an Agent Client Protocol compliant agent. Run it alongside Zed, Neovim, Emacs, or any ACP-compatible editor"

**"Any model, your infrastructure"**
Providers: Anthropic, OpenAI, Google Gemini, AWS Bedrock, Azure, GCP Vertex, Ollama, DeepSeek, xAI, Mistral, Cerebras, OpenRouter + any OpenAI-compatible API

#### Code Snippets

```bash
# Installation
npm install -g cline

# Authentication
cline auth

# Version
cline --version

# Update
npm update -g cline

# CI/CD - Diff review
git diff origin/main | cline -y "Review this diff. Flag bugs, security issues, and style violations."

# Security
cline -y "Check for known CVEs in package.json"

# Review staged changes
git diff --cached | cline -y "Review staged changes"

# ACP Protocol
cline --acp
```

#### System Requirements
"Node.js 18+ and an API key from a supported provider. Works on macOS, Linux, and Windows"

#### FAQ - "Frequently Asked Questions"
(Accordion section, questions not detailed in the fetch)

#### Resources
- CTA: "Read docs"
- CTA: "View on GitHub"
- CTA: "Read announcement"

---

## Key Design Patterns to Replicate

### 1. General Layout
- **Large hero sections** with bold headline + subheadline + dual CTAs
- **3-column grids** for main features
- **Alternating sections** (light/dark backgrounds)
- **Prominent social proof** (company logos, stats)
- **Content cards** for blog posts and resources

### 2. Recurring Components
- **Trust badge strip**: Grid of company logos
- **Feature card**: Icon + heading + description
- **CTA block**: Heading + copy + button(s)
- **FAQ accordion**: Expandable question with answer
- **Pricing card**: Name + price + feature list + CTA
- **Blog card**: Image + title + excerpt + link

### 3. CTA Patterns
- **Primary**: Solid background (purple/brand color), white text
- **Secondary**: Border/outline, accent color text
- **Text link**: No border, with ">" arrow
- Always in pairs: main action + secondary action

### 4. Standard Page Layout
```
[Sticky Nav]
[Hero: large, centered, with subtle gradient]
[Social Proof: stats + logos]
[Features: grid or tabs]
[Deep Dive: alternating sections with demos/screenshots]
[Intermediate CTA]
[Testimonials or Press]
[Multi-column Footer]
```

### 5. Detected Tech Stack
- **Framework**: Next.js (Next.js image optimization detected)
- **CSS**: Tailwind CSS (utility classes throughout the markup)
- **Dark mode**: Toggle with Tailwind dark: classes
- **SEO**: Schema markup (SoftwareApplication, FAQPage, Organization)
- **Analytics**: Google Tag Manager, Google Ads, Facebook Pixel
- **Fonts**: System sans-serif stack (no custom fonts detected)

---

## Notes for Adaptation to DOF-MESH

1. **Replace brand-purple** with DOF-MESH primary color
2. **Keep the structure**: Hero > Social Proof > Features > Deep Dive > CTA > Footer
3. **Adapt social proof**: Instead of enterprise logos, use node metrics, uptime, scores
4. **Feature showcase**: Tabs or cards for DOF-MESH main capabilities
5. **Pricing**: Adapt tiers to DOF-MESH model if applicable
6. **Dark mode first**: Consider dark mode as default (more appropriate for crypto/blockchain)
7. **Code/terminal demos**: Show DOF-MESH CLI commands similar to Cline's CLI page
8. **MCP Marketplace equivalent**: Agent or skills marketplace for DOF-MESH
