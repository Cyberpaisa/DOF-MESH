# Skill: Web Researcher — Rastreador Autónomo de Proyectos e Inteligencia

## Cuándo usar este skill
Cuando se necesita descubrir nuevos repos, tools, papers, hackathons, grants, o cualquier inteligencia relevante del ecosistema AI/crypto/agents. Este agente rastrea, filtra, evalúa y documenta automáticamente.

## Identidad
```python
RESEARCHER = {
    "name": "DOF Web Researcher",
    "role": "Intelligence Gatherer + Trend Analyst + Opportunity Scout",
    "feeds": [
        "GitHub trending (daily/weekly)",
        "HuggingFace new models/papers",
        "ArXiv cs.AI + cs.MA + cs.CR",
        "Hacker News (AI/crypto threads)",
        "Twitter/X AI community",
        "Reddit r/LocalLLaMA r/MachineLearning r/cryptocurrency",
        "Hackathon platforms (Devpost, ETHGlobal, Devfolio)",
        "Grant programs (Gitcoin, Optimism, Avalanche, Base)",
    ],
    "output": "docs/TOOLS_AND_INTEGRATIONS.md + agents/synthesis/SOUL.md",
}
```

## Protocolo de Rastreo

### 1. SCAN — Buscar inteligencia nueva
```
Fuentes prioritarias:
- GitHub: trending repos en Python/TypeScript/Rust con tags: agent, llm, governance, mcp, blockchain
- HuggingFace: modelos nuevos que corran en M4 Max (< 48GB RAM)
- ArXiv: papers sobre multi-agent, formal verification, deterministic AI
- Hackathons: eventos con premios > $1K donde DOF califique
- Grants: programas abiertos en Avalanche, Base, Optimism, Gitcoin
- Tools: nuevos MCP servers, Claude skills, VS Code extensions para agentes
```

### 2. FILTER — Aplicar scoring DOF
```python
def score_finding(item):
    score = 0
    if item.is_open_source: score += 2
    if item.runs_locally: score += 3      # M4 Max sovereignty
    if item.serves_memory: score += 5     # highest priority
    if item.serves_governance: score += 4
    if item.serves_orchestration: score += 3
    if item.serves_monetization: score += 4  # need resources
    if item.has_grant_money: score += 5     # direct funding
    if item.free_tier: score += 1
    if item.has_mcp: score += 2

    if score >= 10: return "IMPLEMENT_NOW"
    if score >= 7: return "EVALUATE_DEEPLY"
    if score >= 4: return "DOCUMENT_AND_WATCH"
    return "SKIP"
```

### 3. BRAINSTORM — Generar ideas de integración
Para cada hallazgo con score >= 7:
- ¿Cómo se integra con DOF existente?
- ¿Qué nuevo habilita?
- ¿Puede generar ingresos?
- ¿Mejora alguna métrica de evolución?

### 4. DOCUMENT — Registrar en formato estándar
Agregar a `docs/TOOLS_AND_INTEGRATIONS.md` siguiendo el formato establecido.

### 5. DISTRIBUTE — Notificar al equipo
- Actualizar SOUL.md si es alta prioridad
- Proponer implementación si es IMPLEMENT_NOW

## Queries de Búsqueda Pre-Computadas

### GitHub Trending
```
language:python stars:>100 created:>2026-03-01 topic:agent
language:python stars:>50 created:>2026-03-01 topic:mcp
language:typescript stars:>100 created:>2026-03-01 topic:ai-agent
topic:formal-verification language:python
topic:blockchain topic:ai-agent
```

### Hackathons y Grants
```
"AI hackathon" 2026 prize money open
"blockchain grant" AI agents application open 2026
Avalanche ecosystem grant program
Base builder grants open
Gitcoin grants round AI
Optimism retropgf
```

### Papers y Research
```
arxiv multi-agent governance formal verification
arxiv deterministic observability AI
arxiv agent memory retrieval benchmark
```

### Monetización
```
"AI governance" consulting rate
"agent as a service" pricing model
SaaS AI safety platform pricing
```

## Frecuencia Recomendada
- **Diario**: GitHub trending + HuggingFace nuevos modelos
- **Semanal**: ArXiv papers + hackathons + grants
- **Mensual**: Revisión completa de roadmap + prioridades

## Integración con Scheduled Tasks
```
Prompt: "Activate web-researcher skill. Scan GitHub trending for AI agent repos,
check for new hackathons with prizes, verify grant applications open.
Score each finding. Document if score >= 7. Report summary."

Frequency: Daily at 7:00 AM
Repository: /Users/jquiceva/equipo de agentes
```
