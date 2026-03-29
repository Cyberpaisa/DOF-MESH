# Cline.bot Design Reference

Referencia completa del sistema de diseno, contenido y estructura de cline.bot.
Extraido el 2026-03-26 para usarse como referencia en la landing page de DOF-MESH.

---

## Tabla de Contenidos

1. [Sistema de Diseno Global](#sistema-de-diseno-global)
2. [Pagina Principal (/)](#pagina-principal)
3. [Enterprise (/enterprise)](#enterprise)
4. [Pricing (/pricing)](#pricing)
5. [Kanban (/kanban)](#kanban)
6. [MCP Marketplace (/mcp-marketplace)](#mcp-marketplace)
7. [CLI (/cli)](#cli)

---

## Sistema de Diseno Global

### Paleta de Colores

| Rol | Valor | Uso |
|-----|-------|-----|
| Background principal (light) | `#ffffff` / `brand-white` | Fondo principal de todas las paginas |
| Background principal (dark) | `#0a0a0a` | Modo oscuro |
| Texto primario (light) | Negro / dark gray | Headings y body text |
| Texto primario (dark) | Blanco | Headings y body text en dark mode |
| Acento principal | `brand-purple` | Seleccion de texto, highlights, CTAs |
| Backgrounds secundarios | `bg-slate-100`, `bg-slate-200` | Secciones alternas, cards |
| Secciones oscuras | `bg-slate-900` | Bloques de contraste |
| Selection highlight | `brand-purple` bg + white text | `selection:bg-brand-purple selection:text-white` |
| Bordes y divisores | Grises neutros | Separadores, card borders |

### Tipografia

| Propiedad | Valor |
|-----------|-------|
| Font Family | `font-sans` (system sans-serif stack) |
| Headings | Bold weight, multiples niveles h1-h4 |
| Body text | Regular weight |
| Tamanos responsivos | Clases Tailwind (text-4xl, text-xl, etc.) |
| Selection styling | Purple background con white text |

### Efectos Visuales

- **Animaciones de carga**: `animate-pulse` para skeleton loading states
- **Hover states**: Transiciones suaves en links y botones
- **Fade-in on scroll**: Animaciones de entrada al hacer scroll
- **Skeleton loaders**: Gradiente shimmer effect en estados de carga
- **Gradientes**: Gradientes sutiles en secciones de fondo
- **Videos embebidos**: Tag `<video>` en secciones de demo
- **Dark mode toggle**: Soporte completo de modo oscuro
- **Overflow hidden**: En containers principales

### Navegacion Global

**Menu Principal:**
- Enterprise
- Pricing
- Kanban
- MCP (MCP Marketplace)
- CLI

**Botones de accion:**
- Sign In (secundario)
- Install Cline (primario)

**Menu de Recursos (dropdown):**
- Blog
- Learn
- Docs
- Prompts
- FAQ
- Careers
- Support
- Contact Sales
- GitHub

### Footer Global

**Tagline:** "Transform your engineering team with a fully collaborative AI partner. Open source, fully extensible, and built to amplify developer impact."

**Columnas de links:**

| Product | Community | Support | Company |
|---------|-----------|---------|---------|
| Docs | Discord | GitHub Issues | Careers |
| Blog | Reddit | Feature Requests | Brand |
| Enterprise | GitHub Discussions | Contact | Terms |
| MCP Marketplace | | | Privacy |
| CLI | | | |
| Changelog | | | |

**Iconos sociales:** Discord, X/Twitter, LinkedIn, Reddit, GitHub

**Copyright:** "(c) 2026 Cline Bot Inc. All rights reserved."

---

## Pagina Principal

**URL:** `https://cline.bot/`

### Estructura de Layout

```
[Nav Header]
[Hero Section]
  - Headline principal
  - Subheadline
  - Dual CTAs
[Product Distribution Grid] (3 columnas)
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

### Contenido por Seccion

#### Hero
- **Heading:** "The Open Coding Agent"
- **Subheading:** "Ship securely w/ Claude in VS Code"
- **CTAs:** "Sign Up Free" | "Contact Sales"

#### Product Distribution (3 columnas)
- **Visual Studio Code:** "The world's most popular code editor with Cline's full AI capabilities built right in"
- **Cline CLI:** "Command-line interface for terminal-first developers. Power and flexibility at your fingertips"
- **JetBrains:** "Professional IDE suite with Cline integration for IntelliJ IDEA, PyCharm, WebStorm, and more"

#### Subheading de transicion
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

#### CTA intermedio
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

### Estructura de Layout

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

### Contenido por Seccion

#### Hero
- **Heading:** "Secure by design."
- **Subheading:** "The coding agent for enterprises that use any provider in any IDE"
- **CTAs:** "Talk to Us" | "Contact Sales"

#### Feature Grid (3 columnas)

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
- **Interactivo:** "Click around to explore" con hover states

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

#### Press Coverage (5 cards con fechas)

1. Salesforce Agentforce Vibes (Oct 29, 2025)
2. Samsung Electronics adoption (Sep 12, 2025)
3. AMD Ryzen AI vibe-coding guide (Aug 29, 2025)
4. Forbes margin game exploration (Oct 29, 2025)
5. Latent.Space deep dive on Cline (Oct 29, 2025)

---

## Pricing

**URL:** `https://cline.bot/pricing`

### Estructura de Layout

```
[Nav Header]
[Hero Section]
  - Headline
  - Value proposition copy
[Pricing Cards] (3 columnas)
  - Open Source | Teams | Enterprise
[Trust Badges]
[FAQ Accordion]
[Footer]
```

### Contenido por Seccion

#### Hero
- **Heading:** "Simple, transparent pricing"
- **Copy:** "Cline is free for individual developers. Pay only for AI inference on a usage basis - no subscriptions, no vendor lock-in."

#### Pricing Tiers

**Open Source - Free**
- Subtitulo: "For individual developers"
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
- Todo lo de Open Source, mas:
  - JetBrains Extension
  - Centralized Billing
  - Simple Config Mgmt
  - Role Based Access Control
  - Limit Inference Providers
  - Team Management System & Dashboard
  - Priority Support

**Enterprise - Custom**
- Subtitulo: "SSO, SLA & Dedicated Support"
- CTA: "Contact Sales"
- Todo lo de Teams, mas:
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

### Estructura de Layout

```
[Nav Header]
[Hero Section]
  - Headline principal
  - Subtitulo
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

### Contenido por Seccion

#### Hero
- **Heading:** "Cline Kanban"
- **Subheading:** "Orchestrate Coding Agents With a Kanban Board"

#### Feature Sections

**"Built for human-agent coordination"**
"Break down a large project or your backlog with one prompt. Use the sidebar agent to add, edit, link, and start tasks for you. Connect to Linear MCP to do the same with your tickets."

**"Watch the board, not the terminals."**
"Observe your agents working next to a real time diff of changes. Leave comments like you're reviewing a PR and see as your agents execute."

**"Unblock agents quickly. No more issue hunting."**
(Monitoreo en tiempo real de agentes bloqueados)

**"Chain dependent tasks, manually or automatically."**
"Set up your workflow in the sequence you'd like it to run. Or let Cline do it. Break a project down with auto-commit and Cline will create and link with max parallelization."

**"Any Agent. One UI."**
Agentes soportados: Claude Code, Codex, Cline + "more agents coming soon"

#### Resources
- "Kanban Launch Announcement" - CTA: "Read the blog"
- "See it in action" - CTA: "Request a demo"
- "Get started" - CTA: "Read docs"

---

## MCP Marketplace

**URL:** `https://cline.bot/mcp-marketplace`

### Estructura de Layout

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

### Contenido por Seccion

#### Hero
- **Heading:** "Plugins for Cline"
- **Subheading:** "Unlock new AI capabilities with a single click"

#### Value Proposition
- "Supercharge Cline"
- "Each MCP server adds new capabilities to Cline"

#### Search/Filter UI
- Placeholder: "Search MCPs..."
- Tabs de filtro: "All" | "Popular" | categorias especificas
- CTA por servidor: "One-click install"

#### Categorias del Marketplace (27 categorias)

Developer-tools, Speech-processing, Security, Ecommerce-retail, Monitoring, Location-services, Finance, Communication, Cloud-platforms, File-systems, Search, Image-video-processing, Knowledge-memory, Browser-automation, Note-taking, Quality, Databases, Os-automation, Virtualization, Research-data, Version-control, License, Entertainment-media, Calendar-management, Cloud-storage, Marketing, Customer-support

#### Servidores Populares
Airtable, Google Calendar, Supabase, File System, Browser Tools, Sequential Thinking, Git Tools, Playwright + 200 mas

#### Submit Section
- CTA: "Submit to Marketplace"
- Link: "Server Development Guide"

---

## CLI

**URL:** `https://cline.bot/cli`

### Estructura de Layout

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

### Contenido por Seccion

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
# Instalacion
npm install -g cline

# Autenticacion
cline auth

# Version
cline --version

# Actualizar
npm update -g cline

# CI/CD - Review de diff
git diff origin/main | cline -y "Review this diff. Flag bugs, security issues, and style violations."

# Seguridad
cline -y "Check for known CVEs in package.json"

# Review de staged changes
git diff --cached | cline -y "Review staged changes"

# ACP Protocol
cline --acp
```

#### System Requirements
"Node.js 18+ and an API key from a supported provider. Works on macOS, Linux, and Windows"

#### FAQ - "Frequently Asked Questions"
(Accordion section, preguntas no detalladas en el fetch)

#### Resources
- CTA: "Read docs"
- CTA: "View on GitHub"
- CTA: "Read announcement"

---

## Patrones de Diseno Clave para Replicar

### 1. Layout General
- **Hero sections grandes** con headline bold + subheadline + dual CTAs
- **Grids de 3 columnas** para features principales
- **Secciones alternantes** (light/dark backgrounds)
- **Social proof prominente** (logos de empresas, stats)
- **Cards de contenido** para blog posts y recursos

### 2. Componentes Recurrentes
- **Trust badge strip**: Grid de logos de companias
- **Feature card**: Icono + heading + descripcion
- **CTA block**: Heading + copy + boton(es)
- **FAQ accordion**: Pregunta expandible con respuesta
- **Pricing card**: Nombre + precio + lista de features + CTA
- **Blog card**: Imagen + titulo + excerpt + link

### 3. Patrones de CTA
- **Primario**: Fondo solido (purple/brand color), texto blanco
- **Secundario**: Borde/outline, texto del color de acento
- **Texto link**: Sin borde, con flecha ">"
- Siempre en pares: accion principal + accion secundaria

### 4. Esquema de Pagina Tipo
```
[Sticky Nav]
[Hero: grande, centrado, con gradiente sutil]
[Social Proof: stats + logos]
[Features: grid o tabs]
[Deep Dive: secciones alternantes con demos/screenshots]
[CTA intermedio]
[Testimonials o Press]
[Footer multi-columna]
```

### 5. Tech Stack Detectado
- **Framework**: Next.js (Next.js image optimization detectado)
- **CSS**: Tailwind CSS (clases utilitarias en todo el markup)
- **Dark mode**: Toggle con clases Tailwind dark:
- **SEO**: Schema markup (SoftwareApplication, FAQPage, Organization)
- **Analytics**: Google Tag Manager, Google Ads, Facebook Pixel
- **Fonts**: System sans-serif stack (no custom fonts detectadas)

---

## Notas para Adaptacion a DOF-MESH

1. **Reemplazar brand-purple** con el color primario de DOF-MESH
2. **Mantener la estructura**: Hero > Social Proof > Features > Deep Dive > CTA > Footer
3. **Adaptar el social proof**: En lugar de logos enterprise, usar metricas de nodos, uptime, scores
4. **Feature showcase**: Tabs o cards para las capacidades principales de DOF-MESH
5. **Pricing**: Adaptar tiers al modelo de DOF-MESH si aplica
6. **Dark mode first**: Considerar dark mode como default (mas apropiado para crypto/blockchain)
7. **Codigo/terminal demos**: Mostrar comandos de DOF-MESH CLI similar al CLI page de Cline
8. **MCP Marketplace equivalent**: Marketplace de agentes o skills de DOF-MESH
