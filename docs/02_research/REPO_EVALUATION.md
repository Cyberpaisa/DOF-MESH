# Evaluacion de Repositorios Externos para DOF-MESH

> Fecha: 2026-03-26
> Evaluador: Cyber Paisa (Enigma Group)
> Contexto: DOF-MESH es un framework de gobernanza deterministica para agentes AI con pruebas Z3, 127 modulos, orquestacion mesh, y gobernanza de memoria (GovernedMemoryStore + ChromaDB + grafo temporal).

---

## Tabla de Evaluacion

| # | Repo | Stars | Que hace | Valor para DOF-MESH | Veredicto |
|---|------|-------|----------|----------------------|-----------|
| 1 | [memstack](https://github.com/cwinvestments/memstack) | 74 | Framework de skills para Claude Code con memoria persistente SQLite, busqueda semantica vectorial (LanceDB), hooks deterministicos, gobernanza de portfolio (3 tiers), y compresion de contexto. 77 skills especializados. | **MEDIO.** Su sistema de gobernanza de portfolio (Prototype/MVP/Production) es un patron interesante para DOF. Sin embargo, DOF ya tiene GovernedMemoryStore + ChromaDB + grafo temporal que es muy superior a SQLite + LanceDB. Los hooks deterministicos y el sistema de verificacion pre-commit podrian adaptarse como skill patterns. | **REFERENCE** |
| 2 | [claude-mem](https://github.com/thedotmack/claude-mem) | 41,209 | Sistema de memoria persistente comprimida para Claude Code. Captura automaticamente observaciones de herramientas, genera resumenes semanticos, e inyecta contexto relevante en sesiones futuras. Plugin marketplace. v6.5.0. | **BAJO.** DOF ya tiene un sistema de memoria gobernada mucho mas sofisticado (GovernedMemoryStore con ChromaDB, grafo temporal, Z3 proofs). Claude-mem es util para usuarios individuales de Claude Code pero no aporta nada que DOF no tenga ya a nivel superior. | **SKIP** |
| 3 | [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 52,020 | Skill de AI para inteligencia de diseno UI/UX. 161 reglas de razonamiento por industria, 67 estilos UI, generador de design systems, seleccion de paletas, tipografia, patrones anti-diseno. | **BAJO.** DOF-MESH es un framework de gobernanza de agentes, no una herramienta de frontend. Si necesitamos dashboard UI en el futuro, este skill podria ser util como referencia puntual, pero no complementa la arquitectura core. | **SKIP** |
| 4 | [n8n-mcp](https://github.com/czlonkowski/n8n-mcp) | 16,541 | Servidor MCP que da acceso a 1,396 nodos de n8n (812 core + 584 community). Permite a AI asistentes construir workflows de automatizacion. Template library con 2,709 workflows. | **ALTO.** DOF-MESH podria usar n8n como capa de orquestacion de workflows externos. Un nodo DOF en n8n permitiria integrar la gobernanza deterministica en pipelines de automatizacion empresarial. El patron MCP server es directamente replicable para exponer DOF como MCP tool. | **INTEGRATE** |
| 5 | [obsidian-skills](https://github.com/kepano/obsidian-skills) | 17,366 | Skills de agente para Obsidian: Markdown flavored, Bases (DB views), JSON Canvas, CLI. Sigue la especificacion Agent Skills (agentskills.io). | **MEDIO.** El formato de Agent Skills Specification es un estandar emergente que DOF deberia seguir para exponer sus capacidades. El skill de JSON Canvas podria ser util para visualizar grafos de gobernanza. El patron de skills composables es un buen modelo. | **REFERENCE** |
| 6 | [LightRAG](https://github.com/hkuds/lightrag) | 30,677 | RAG basado en knowledge graphs con extraccion de entidades/relaciones, busqueda dual (local + global), reranker, WebUI. Soporta Neo4j, PostgreSQL, MongoDB, OpenSearch. Paper EMNLP 2025. | **ALTO.** El grafo de conocimiento de LightRAG complementa directamente el grafo temporal de DOF-MESH. La busqueda dual (entidades locales + relaciones globales) es exactamente lo que necesita el GovernedMemoryStore para queries complejas. La integracion con Neo4j/PostgreSQL alinea con nuestra stack. Candidato serio para reemplazar o complementar ChromaDB. | **INTEGRATE** |
| 7 | [everything-claude-code](https://github.com/affaan-m/everything-claude-code) | 110,677 | Sistema completo de optimizacion de performance para harnesses de agentes AI. Skills, instintos, memoria, seguridad (AgentShield), aprendizaje continuo, hooks, reglas multi-lenguaje. Ganador de hackathon Anthropic. 997+ tests. | **ALTO.** El sistema de instintos con confidence scoring es un patron valioso para DOF. AgentShield (1282 tests, 102 reglas de seguridad) podria integrarse con nuestro sistema de verificacion Z3. Los hooks de memoria persistente y el observer con throttling son patrones maduros que podemos aprender. El modelo de "harness performance" valida nuestra arquitectura de mesh. | **INTEGRATE** |
| 8 | [superpowers](https://github.com/obra/superpowers) | 116,311 | Framework de desarrollo de software basado en skills composables. Workflow completo: brainstorming → spec → plan → subagent-driven-development → TDD → code review → merge. Skills que se activan automaticamente por contexto. | **ALTO.** El paradigma de subagent-driven-development con two-stage review (spec compliance + code quality) es directamente aplicable a DOF-MESH para la orquestacion de tareas entre nodos del mesh. El sistema de skills auto-activables por contexto es un patron que deberiamos adoptar. La filosofia de "mandatory workflows, not suggestions" alinea con nuestra gobernanza deterministica. | **INTEGRATE** |
| 9 | [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 32,900 | Lista curada de skills, hooks, slash-commands, orquestadores de agentes, aplicaciones y plugins para Claude Code. Catalogo de referencia del ecosistema. | **MEDIO.** Excelente como directorio de referencia para descubrir nuevas herramientas y patrones. No tiene codigo integrable directamente pero es valioso para mantenerse al dia con el ecosistema. Menciona repos como Ruflo (multi-agent swarms) que merecen evaluacion separada. | **REFERENCE** |
| 10 | [get-shit-done](https://github.com/gsd-build/get-shit-done) | 42,753 | Sistema de meta-prompting, context engineering y spec-driven development. Resuelve "context rot" (degradacion de calidad cuando se llena la ventana de contexto). Soporta 8+ runtimes (Claude Code, Codex, Gemini, Cursor, etc.). | **MEDIO.** El concepto de "context rot" y las tecnicas de context engineering son relevantes para DOF-MESH cuando los nodos del mesh tienen sesiones largas. El patron de orquestacion de sub-agentes con state management podria complementar nuestro mesh_orchestrator. Sin embargo, es mas un tool de productividad individual que un framework de gobernanza. | **REFERENCE** |
| 11 | [claude-howto](https://github.com/luongnv89/claude-howto) | 2,108 | Guia visual con tutoriales y templates copy-paste para Claude Code. 10 modulos desde comandos basicos hasta agentes avanzados. Diagramas Mermaid, quizzes de auto-evaluacion. | **BAJO.** Material educativo util pero no aporta codigo ni patrones nuevos para DOF-MESH. Bueno para onboarding de nuevos contribuidores pero no para integracion tecnica. | **SKIP** |
| 12 | [Cline](https://cline.bot/) / [GitHub](https://github.com/cline/cline) | 59,445 | Agente de codificacion autonomo en IDE (VS Code). Crea/edita archivos, ejecuta comandos, usa browser. Kanban multiagent orchestration. Permisos granulares por paso. | **MEDIO.** El modelo de Kanban multiagent orchestration es un patron interesante para visualizar y gestionar tareas en DOF-MESH. Su sistema de permisos granulares por paso podria informar nuestro sistema de gobernanza. Sin embargo, es un IDE tool, no un framework de mesh. | **REFERENCE** |

---

## Resumen de Veredictos

### INTEGRATE (4 repos) — Valor directo, integrar o adoptar patrones
1. **n8n-mcp** — Exponer DOF como MCP server + usar n8n para workflows externos
2. **LightRAG** — Knowledge graph para complementar/mejorar GovernedMemoryStore
3. **everything-claude-code** — AgentShield seguridad + instintos + observer patterns
4. **superpowers** — Subagent-driven-development + skills auto-activables + mandatory workflows

### REFERENCE (4 repos) — Estudiar patrones, no integrar directamente
5. **memstack** — Patron de gobernanza de portfolio (3 tiers)
6. **obsidian-skills** — Agent Skills Specification + JSON Canvas para grafos
7. **awesome-claude-code** — Directorio de referencia del ecosistema
8. **get-shit-done** — Context engineering + anti context-rot
9. **Cline** — Kanban multiagent + permisos granulares

### SKIP (3 repos) — No relevantes para DOF-MESH
10. **claude-mem** — DOF ya tiene memoria gobernada superior
11. **ui-ux-pro-max-skill** — Skill de diseno UI, no aplica a gobernanza de agentes
12. **claude-howto** — Material educativo, sin codigo integrable

---

## Plan de Integracion Priorizado

| Prioridad | Repo | Accion Concreta | Impacto |
|-----------|------|-----------------|---------|
| P0 | LightRAG | Evaluar como backend de knowledge graph para GovernedMemoryStore. Test con Neo4j para grafos de gobernanza. Busqueda dual (local entities + global relations) para queries de estado del mesh. | Mejora critica de memoria |
| P1 | superpowers | Adoptar patron de subagent-driven-development para mesh_orchestrator. Implementar skills auto-activables por contexto en los nodos DOF. Two-stage review para tareas del mesh. | Mejora de orquestacion |
| P2 | everything-claude-code | Integrar AgentShield como capa de seguridad complementaria a Z3. Adoptar patron de instintos con confidence scoring. Observer throttling para mesh_monitor. | Seguridad + observabilidad |
| P3 | n8n-mcp | Crear DOF MCP server siguiendo el patron de n8n-mcp. Publicar nodos DOF en n8n marketplace para adopcion empresarial. | Adopcion + ecosistema |

---

## Link Library

### Memoria y Contexto
- [memstack](https://github.com/cwinvestments/memstack) — Skill framework con memoria SQLite + busqueda semantica
- [claude-mem](https://github.com/thedotmack/claude-mem) — Memoria comprimida persistente para Claude Code
- [LightRAG](https://github.com/hkuds/lightrag) — RAG con knowledge graphs (EMNLP 2025)
- [LightRAG Paper](https://arxiv.org/abs/2410.05779) — Paper academico de LightRAG

### Frameworks de Desarrollo con Agentes
- [superpowers](https://github.com/obra/superpowers) — Skills composables + subagent-driven-development
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — Harness performance optimization system
- [get-shit-done](https://github.com/gsd-build/get-shit-done) — Meta-prompting + context engineering + spec-driven dev
- [Cline](https://github.com/cline/cline) — Agente autonomo de codificacion en IDE
- [Cline Website](https://cline.bot/) — Portal principal de Cline

### MCP e Integraciones
- [n8n-mcp](https://github.com/czlonkowski/n8n-mcp) — MCP server para n8n (1,396 nodos)
- [n8n-mcp Dashboard](https://dashboard.n8n-mcp.com) — Servicio hosted de n8n-mcp
- [obsidian-skills](https://github.com/kepano/obsidian-skills) — Skills de agente para Obsidian
- [Agent Skills Specification](https://agentskills.io/specification) — Estandar de skills para agentes

### UI/UX y Diseno
- [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — Skill de inteligencia de diseno UI/UX
- [UI UX Pro Max Website](https://uupm.cc) — Portal del skill

### Guias y Directorios
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — Lista curada del ecosistema Claude Code
- [claude-howto](https://github.com/luongnv89/claude-howto) — Guia visual de Claude Code
- [ECC Shorthand Guide](https://x.com/affaanmustafa/status/2012378465664745795) — Guia corta de Everything Claude Code
- [ECC Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) — Guia larga de Everything Claude Code
- [ECC Security Guide](https://x.com/affaanmustafa/status/2033263813387223421) — Guia de seguridad agentica

### Seguridad
- [AgentShield (via ECC)](https://github.com/affaan-m/everything-claude-code) — 1,282 tests, 102 reglas de seguridad
- [ECC GitHub App](https://github.com/marketplace/ecc-tools) — Marketplace de herramientas ECC

### Repos Mencionados en Awesome List (para evaluacion futura)
- [Ruflo](https://github.com/ruvnet/ruflo) — Plataforma de orquestacion multi-agent swarms
- [Headroom](https://github.com/chopratejas/headroom) — Compresor de output de herramientas (~34% reduccion)
- [RAG-Anything](https://github.com/HKUDS/RAG-Anything) — RAG multimodal (texto, imagenes, tablas, ecuaciones)
- [MiniRAG](https://github.com/HKUDS/MiniRAG) — RAG simplificado para modelos pequenos
- [VideoRAG](https://github.com/HKUDS/VideoRAG) — RAG para videos de contexto largo

### Comunidades
- [LightRAG Discord](https://discord.gg/yF2MmDJyGJ)
- [GSD Discord](https://discord.gg/gsd)
- [Superpowers Sponsor](https://github.com/sponsors/obra)
