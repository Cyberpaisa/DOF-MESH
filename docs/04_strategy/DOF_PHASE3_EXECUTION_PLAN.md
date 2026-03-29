# DOF PHASE 3 — EXECUTION PLAN
## MCP Server + REST API + PostgreSQL Backend + LangGraph Integration

**Author:** Juan Carlos Quiceno Vasquez
**Project:** `/Users/jquiceva/equipo de agentes/`
**Prerequisites:** Phase 2 complete (318 tests, CI verde, 25+ modules)
**Assessment Impact:** Phase 3 targets the weakest dimensions — Adopción (+30), Escalabilidad (+25), Producción (+20)

---

## OVERVIEW

| Session | Module | Depends On | Time Est. | Tests Expected |
|---------|--------|------------|-----------|----------------|
| 16 | MCP Server — DOF as MCP tool provider | All core modules | 60 min | ~20 new |
| 17 | REST API — FastAPI endpoints | Session 16 | 45 min | ~20 new |
| 18 | Dashboard Web — React visualization | Session 17 | 60 min | ~10 new |
| 19 | PostgreSQL Backend — replace JSONL | Sessions 16-17 | 45 min | ~15 new |
| 20 | LangGraph Integration — framework-agnostic | Sessions 16-19 | 45 min | ~15 new |
| 21 | Full Integration + README + Paper | Sessions 16-20 | 30 min | validation |
| **Total** | **6 sessions** | | **~5 hours** | **~80 new tests** |

After Phase 3: ~398 total tests, 30+ modules, MCP-compatible, REST API, web dashboard, PostgreSQL-ready, multi-framework.

---

## WHY THIS ORDER

1. **MCP Server first** (Session 16): Highest visibility impact. Once DOF is an MCP server, it works with Claude Desktop, Cursor, Windsurf, ClawX, and any MCP client. This is the single fastest path to adoption. Corvic Labs just launched their Agentic MCP Evaluator 2 days ago — we need to be in the same conversation.

2. **REST API second** (Session 17): The MCP server wraps DOF functions. The REST API exposes them via HTTP for any client. Together, MCP + REST = DOF is accessible from anywhere.

3. **Dashboard third** (Session 18): Consumes the REST API. Visual proof that DOF works. Screenshots for the Dev.to article. Demo for investors/collaborators.

4. **PostgreSQL fourth** (Session 19): Replaces JSONL with real database. Makes everything production-ready. Multi-tenant capable.

5. **LangGraph last** (Session 20): Makes DOF framework-agnostic. Not just CrewAI — now LangGraph, AutoGen, any framework can use DOF governance.

---

## SESSION 16: MCP Server

**What it creates:** DOF as an MCP (Model Context Protocol) tool server. Any MCP client (Claude Desktop, Cursor, Windsurf, ClawX) can call DOF governance functions as tools.

**Paste this in Claude Code:**

```
Lee estos archivos para entender el proyecto:
- dof/__init__.py (la API pública del SDK)
- core/governance.py (ConstitutionEnforcer)
- core/z3_verifier.py (formal proofs)
- core/memory_governance.py (GovernedMemoryStore)
- core/oags_bridge.py (OAGS identity)
- core/oracle_bridge.py (attestation)
- core/observability.py (métricas)

Investiga el Model Context Protocol (MCP) de Anthropic. MCP permite que aplicaciones expongan "tools" que los LLMs pueden usar. DOF será un MCP server que expone governance como herramientas.

Instala: pip install mcp

Crea mcp_server.py en la raíz del proyecto (NO dentro de core/):

1. MCP Server con estas tools:

   a) tool "dof_verify_governance":
      - Input: {"output_text": str}
      - Acción: Pasa el texto por ConstitutionEnforcer
      - Output: {"status": "pass"|"fail", "hard_violations": [...], "soft_violations": [...], "score": float}
      - Esto permite que Claude/Cursor verifique governance de cualquier output

   b) tool "dof_verify_ast":
      - Input: {"code": str}
      - Acción: Pasa el código por ASTVerifier
      - Output: {"score": float, "violations": [...], "categories": {...}}
      - Esto permite verificar código generado por IA contra reglas AST

   c) tool "dof_run_z3":
      - Input: {} (no necesita input)
      - Acción: Ejecuta Z3Verifier.verify_all()
      - Output: {"theorems": [...], "all_verified": bool, "elapsed_ms": float}
      - Esto permite que cualquier cliente verifique los invariantes formales

   d) tool "dof_memory_add":
      - Input: {"content": str, "category": str (optional)}
      - Acción: GovernedMemoryStore.add()
      - Output: {"memory_id": str, "status": "approved"|"warning"|"rejected", "category": str}

   e) tool "dof_memory_query":
      - Input: {"query": str, "category": str (optional)}
      - Acción: GovernedMemoryStore.query()
      - Output: {"results": [...], "count": int}

   f) tool "dof_memory_snapshot":
      - Input: {"as_of": str (ISO datetime)}
      - Acción: TemporalGraph.snapshot()
      - Output: {"memories": [...], "count": int, "as_of": str}

   g) tool "dof_get_metrics":
      - Input: {"run_trace_path": str (optional)}
      - Acción: Calcula métricas SS, GCR, PFI, RP, SSR
      - Output: {"SS": float, "GCR": float, "PFI": float, "RP": float, "SSR": float}

   h) tool "dof_create_attestation":
      - Input: {"task_id": str, "metrics": dict}
      - Acción: OracleBridge.create_attestation()
      - Output: {"certificate_hash": str, "governance_status": str, "should_publish": bool}

   i) tool "dof_oags_identity":
      - Input: {"model": str, "tools": list[str]}
      - Acción: OAGSIdentity.compute_identity()
      - Output: {"identity_hash": str, "constitution_hash": str, "agent_card": dict}

   j) tool "dof_conformance_check":
      - Input: {}
      - Acción: OAGSPolicyBridge.validate_conformance()
      - Output: {"level_1": {...}, "level_2": {...}, "level_3": {...}, "max_level": int}

2. El server usa stdio transport (estándar MCP):
   - Se inicia con: python mcp_server.py
   - Comunicación via stdin/stdout en formato JSON-RPC

3. Crear archivo de configuración para Claude Desktop:
   mcp_config.json:
   {
     "mcpServers": {
       "dof-governance": {
         "command": "python",
         "args": ["mcp_server.py"],
         "cwd": "/path/to/dof"
       }
     }
   }

4. Resource MCP (read-only data):
   - resource "dof://constitution" — retorna el contenido de dof.constitution.yml
   - resource "dof://metrics/latest" — retorna las últimas métricas calculadas
   - resource "dof://memory/stats" — retorna estadísticas del memory store

5. Tests en tests/test_mcp_server.py:
   - Test que cada tool retorna el schema correcto
   - Test dof_verify_governance con output limpio — pass
   - Test dof_verify_governance con output que viola HARD_RULE — fail
   - Test dof_verify_ast con código limpio — score 1.0
   - Test dof_verify_ast con código con eval() — violation detectada
   - Test dof_run_z3 — 4 theorems verified
   - Test dof_memory_add — memory created with governance
   - Test dof_memory_query — results returned
   - Test dof_create_attestation — certificate generated
   - Test dof_oags_identity — deterministic hash
   - Test dof_conformance_check — level 3 passed
   - Ejecuta TODOS los tests del proyecto

6. Actualizar dof/__init__.py para exportar: from dof import MCPServer (si tiene sentido)

7. Agregar a main.py como opción 22: "Start MCP Server"

8. Crear docs/MCP_SETUP.md con instrucciones de configuración para:
   - Claude Desktop
   - Cursor
   - Cualquier cliente MCP genérico

IMPORTANTE:
- Si el paquete `mcp` no está disponible o tiene problemas de import, implementa un MCP server mínimo usando solo la librería estándar de Python (json-rpc sobre stdio). El protocolo MCP es JSON-RPC 2.0 sobre stdio — se puede implementar sin dependencias externas.
- Maneja gracefully la ausencia del paquete mcp: try/except ImportError
- El server debe funcionar standalone (python mcp_server.py) sin necesitar el resto del proyecto instalado como dependencia pesada

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: MCP Server — DOF governance as Model Context Protocol tools

- mcp_server.py: 10 governance tools + 3 resources via MCP
- Tools: verify_governance, verify_ast, run_z3, memory_add/query/snapshot, get_metrics, create_attestation, oags_identity, conformance_check
- Resources: constitution, latest metrics, memory stats
- stdio transport (JSON-RPC 2.0) — works with Claude Desktop, Cursor, Windsurf
- docs/MCP_SETUP.md: configuration guide for all MCP clients
- Zero heavy dependencies — graceful fallback if mcp package unavailable"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** mcp_server.py, docs/MCP_SETUP.md, ~20 tests, MCP-compatible.

---

## SESSION 17: REST API (FastAPI)

**What it creates:** HTTP endpoints exposing all DOF governance functions. Any client, any language, any platform.

**Paste this in Claude Code:**

```
Instala: pip install fastapi uvicorn

Lee mcp_server.py para ver las funciones ya expuestas via MCP. Ahora las exponemos via HTTP.

Crea api/server.py:

1. FastAPI app con estos endpoints:

   POST /api/v1/governance/verify
   - Body: {"output_text": str}
   - Response: {"status", "hard_violations", "soft_violations", "score"}

   POST /api/v1/ast/verify
   - Body: {"code": str}
   - Response: {"score", "violations", "categories"}

   GET /api/v1/z3/verify
   - Response: {"theorems", "all_verified", "elapsed_ms"}

   POST /api/v1/memory
   - Body: {"content": str, "category": str (optional)}
   - Response: {"memory_id", "status", "category"}

   GET /api/v1/memory?query=X&category=Y
   - Response: {"results", "count"}

   GET /api/v1/memory/snapshot?as_of=ISO_DATE
   - Response: {"memories", "count", "as_of"}

   GET /api/v1/memory/stats
   - Response: {total, active, by_category, by_status, avg_relevance}

   GET /api/v1/metrics
   - Response: {"SS", "GCR", "PFI", "RP", "SSR"}

   POST /api/v1/attestation
   - Body: {"task_id": str, "metrics": dict}
   - Response: {"certificate_hash", "governance_status", "should_publish"}

   GET /api/v1/attestation/history
   - Response: {"attestations": [...], "compliance_rate": float}

   GET /api/v1/oags/identity?model=X&tools=Y,Z
   - Response: {"identity_hash", "constitution_hash", "agent_card"}

   GET /api/v1/oags/conformance
   - Response: {"level_1", "level_2", "level_3", "max_level"}

   GET /api/v1/constitution
   - Response: contenido de dof.constitution.yml como JSON

   GET /api/v1/health
   - Response: {"status": "ok", "version": "0.1.0", "tests": 318, "modules": 25}

2. Middleware:
   - CORS habilitado (para que el dashboard web pueda conectar)
   - Request logging a logs/api_requests.jsonl
   - Error handling global con respuestas JSON consistentes

3. El server se inicia con:
   python -m api.server
   o
   uvicorn api.server:app --host 0.0.0.0 --port 8080

4. Crear api/__init__.py (paquete Python)

5. Tests en tests/test_api.py:
   - Usa TestClient de FastAPI (no necesita server corriendo)
   - Test cada endpoint retorna 200 con schema correcto
   - Test POST governance con input válido — pass
   - Test POST governance con input que viola — fail
   - Test POST ast con código limpio — score 1.0
   - Test GET z3 — 4 theorems
   - Test POST memory — created
   - Test GET memory — results
   - Test GET health — status ok
   - Test GET conformance — level 3
   - Ejecuta TODOS los tests

6. Agregar a main.py como opción 23: "Start REST API Server"

IMPORTANTE:
- Si fastapi o uvicorn no están disponibles, el API no se importa (try/except)
- Los tests de API usan TestClient que no requiere server corriendo
- Agregar fastapi y uvicorn a pyproject.toml en [project.optional-dependencies] api

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: REST API — FastAPI endpoints for all DOF governance functions

- api/server.py: 14 HTTP endpoints covering governance, AST, Z3, memory, metrics, attestation, OAGS
- CORS enabled for dashboard integration
- Request logging to JSONL
- Health endpoint with version and module count
- Runnable via uvicorn or python -m api.server
- Optional dependency — graceful degradation if fastapi unavailable"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** api/server.py, ~20 tests, REST API functional.

---

## SESSION 18: Dashboard Web (React)

**What it creates:** Visual dashboard consuming the REST API. Metrics, memory, attestations, OAGS — all in browser.

**Paste this in Claude Code:**

```
El dashboard se construye como un artefacto HTML standalone que consume la REST API.

Crea dashboard/index.html — un SINGLE FILE dashboard (HTML + CSS + JS) que:

1. Layout:
   - Header: "DOF — Deterministic Observability Framework" con version y status
   - Sidebar: Navigation (Metrics, Memory, Attestations, OAGS, Z3, Constitution)
   - Main area: contenido dinámico según la sección seleccionada

2. Sección "Metrics":
   - Fetch GET /api/v1/metrics
   - Muestra SS, GCR, PFI, RP, SSR como cards grandes con colores:
     * GCR == 1.0 — verde
     * SS > 0.8 — verde, 0.5-0.8 — amarillo, <0.5 — rojo
   - Gráfico simple (canvas o SVG) mostrando las 5 métricas como barras

3. Sección "Memory":
   - Fetch GET /api/v1/memory/stats
   - Muestra: total memories, active, by category (pie chart simple), avg relevance
   - Lista de últimas 10 memorias con: id, category, status badge, relevance score
   - Input para buscar memorias (query — GET /api/v1/memory?query=X)

4. Sección "Attestations":
   - Fetch GET /api/v1/attestation/history
   - Muestra: total attestations, compliance rate como porcentaje grande
   - Lista de últimas attestations con: certificate_hash (truncado), status badge, timestamp

5. Sección "OAGS":
   - Fetch GET /api/v1/oags/conformance
   - Muestra: Level 1/2/3 con checkmarks verdes o X rojas
   - Agent identity hash
   - Constitution hash

6. Sección "Z3":
   - Fetch GET /api/v1/z3/verify
   - Muestra: 4 teoremas con status (VERIFIED badge verde)
   - Elapsed time total

7. Sección "Constitution":
   - Fetch GET /api/v1/constitution
   - Muestra el YAML formateado y coloreado
   - Conteo de reglas HARD, SOFT, AST

8. Diseño:
   - Dark theme (fondo #0d1117, texto #c9d1d9, accents #58a6ff — estilo GitHub Dark)
   - Responsive (funciona en mobile)
   - Sin frameworks CSS — vanilla CSS con variables
   - Fuente: monospace para datos, sans-serif para UI
   - Animaciones sutiles en los números

9. Auto-refresh cada 30 segundos

10. Fallback: si la API no está disponible, muestra "API not connected — start with: python -m api.server"

NO necesita tests automatizados (es UI). Pero verifica que se abre sin errores en el browser.

Agregar a main.py como opción 24: "Open Dashboard" (abre el archivo HTML en el browser por defecto)

Después:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: web dashboard — visual metrics, memory, attestations, OAGS, Z3 verification

- dashboard/index.html: single-file dashboard consuming REST API
- Dark theme, responsive, auto-refresh
- 6 sections: Metrics, Memory, Attestations, OAGS, Z3, Constitution
- Zero dependencies — vanilla HTML/CSS/JS
- Fallback message when API unavailable"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** dashboard/index.html, visual dashboard, ~10 tests (API integration).

---

## SESSION 19: PostgreSQL Backend

**What it creates:** Database storage replacing JSONL for production scalability.

**Paste this in Claude Code:**

```
Instala: pip install psycopg2-binary sqlalchemy alembic

Crea core/storage.py — una capa de abstracción de storage que soporta JSONL (actual) y PostgreSQL (nuevo).

1. Clase abstracta StorageBackend:
   - save_memory(entry: MemoryEntry) -> bool
   - load_memories() -> list[MemoryEntry]
   - save_attestation(cert: AttestationCertificate) -> bool
   - load_attestations() -> list[AttestationCertificate]
   - save_audit_event(event: dict) -> bool
   - query_memories(query: str, category: str, as_of: datetime) -> list[MemoryEntry]
   - get_stats() -> dict

2. Clase JSONLBackend(StorageBackend):
   - Wrapper sobre el comportamiento ACTUAL de JSONL
   - Misma funcionalidad que ya existe, pero ahora detrás de la interfaz abstracta
   - Es el backend por defecto (no requiere PostgreSQL)

3. Clase PostgreSQLBackend(StorageBackend):
   - Usa SQLAlchemy como ORM
   - Tablas:
     * memories: id, content, category, metadata (JSONB), valid_from, valid_to, recorded_at, relevance_score, governance_status, version, parent_id
     * attestations: id, agent_identity, task_id, timestamp, metrics (JSONB), governance_status, z3_verified, signature, certificate_hash
     * audit_events: id, timestamp, event_type, module, payload (JSONB)
   - Connection string desde environment variable: DOF_DATABASE_URL
   - Si DOF_DATABASE_URL no existe — fallback a JSONLBackend automáticamente

4. Clase StorageFactory:
   - Método get_backend() -> StorageBackend:
     * Si DOF_DATABASE_URL existe y es válida — PostgreSQLBackend
     * Si no — JSONLBackend
   - Singleton pattern (una sola instancia)

5. Migración:
   - Método migrate_jsonl_to_postgres():
     * Lee todos los JSONL existentes
     * Inserta en PostgreSQL
     * Reporte: {migrated_memories: N, migrated_attestations: N, migrated_events: N}

6. Actualizar GovernedMemoryStore para usar StorageBackend en vez de JSONL directo
7. Actualizar AttestationRegistry para usar StorageBackend
8. Actualizar audit logging para usar StorageBackend

9. Agregar a dof.constitution.yml:
   storage:
     backend: "auto"  # auto, jsonl, postgresql
     jsonl_path: "memory/"
     postgresql_url: null  # override via DOF_DATABASE_URL env var

10. Tests en tests/test_storage.py:
    - Test JSONLBackend save + load memories
    - Test JSONLBackend save + load attestations
    - Test StorageFactory retorna JSONLBackend cuando no hay DATABASE_URL
    - Test StorageFactory retorna PostgreSQLBackend cuando hay DATABASE_URL (mock)
    - Test que GovernedMemoryStore funciona con ambos backends
    - Test migración JSONL — PostgreSQL (con SQLite como proxy de PostgreSQL para tests)
    - Ejecuta TODOS los tests

IMPORTANTE:
- JSONL sigue siendo el default. PostgreSQL es OPCIONAL.
- Si psycopg2 o sqlalchemy no están instalados — JSONLBackend funciona sin errores
- Para tests, usa SQLite in-memory como proxy de PostgreSQL (SQLAlchemy lo soporta transparente)
- Agrega psycopg2-binary, sqlalchemy, alembic a pyproject.toml en [project.optional-dependencies] db

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: storage abstraction — JSONL default + PostgreSQL backend for production

- core/storage.py: StorageBackend interface, JSONLBackend, PostgreSQLBackend
- StorageFactory: auto-detect backend from DOF_DATABASE_URL
- SQLAlchemy ORM with JSONB columns for flexible metadata
- Migration utility: jsonl_to_postgres for existing data
- GovernedMemoryStore and AttestationRegistry now use storage abstraction
- JSONL remains default — zero configuration change for existing users
- PostgreSQL enables multi-tenant, high-throughput production deployments"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** core/storage.py, ~15 tests, dual-backend storage.

---

## SESSION 20: LangGraph Integration

**What it creates:** DOF governance working with LangGraph, not just CrewAI. Framework-agnostic governance.

**Paste this in Claude Code:**

```
Lee estos archivos:
- dof/__init__.py (API pública)
- core/governance.py (ConstitutionEnforcer)
- core/observability.py (RunTrace, StepTrace)
- core/memory_governance.py (GovernedMemoryStore)

Crea integrations/langgraph_adapter.py:

1. Clase DOFGovernanceNode:
   - Un nodo de LangGraph que ejecuta governance verification
   - Método __call__(state: dict) -> dict:
     * Extrae el output del state
     * Pasa por ConstitutionEnforcer
     * Agrega governance_result al state
     * Si viola HARD_RULE — marca state["governance_pass"] = False
     * Si pasa — marca state["governance_pass"] = True
   - Puede usarse como nodo en cualquier grafo LangGraph

2. Clase DOFObservabilityNode:
   - Un nodo que registra métricas de observabilidad
   - Método __call__(state: dict) -> dict:
     * Crea StepTrace con la info del state
     * Calcula métricas parciales
     * Agrega traces al state

3. Clase DOFMemoryNode:
   - Un nodo que interactúa con GovernedMemoryStore
   - Método __call__(state: dict) -> dict:
     * Si state tiene "memory_action" == "add": agrega memoria
     * Si state tiene "memory_action" == "query": consulta memorias
     * Agrega resultados al state

4. Clase DOFASTNode:
   - Un nodo que verifica código generado
   - Método __call__(state: dict) -> dict:
     * Si state contiene código — ejecuta ASTVerifier
     * Agrega ast_result al state

5. Función create_governed_graph():
   - Helper que crea un grafo LangGraph pre-configurado con nodos DOF
   - Retorna un grafo con: governance_check — ast_check — output

6. Clase FrameworkAdapter (abstracción):
   - Interfaz genérica para cualquier framework
   - Método wrap_output(output: str) -> dict: aplica governance
   - Método wrap_code(code: str) -> dict: aplica AST
   - Método record_step(step_data: dict) -> None: observabilidad
   - Implementaciones:
     * CrewAIAdapter — wrapper sobre el crew_runner existente
     * LangGraphAdapter — usa los nodos de arriba
     * GenericAdapter — funciona con cualquier framework que produzca output string

7. Crear integrations/__init__.py

8. Actualizar dof/__init__.py:
   from dof import DOFGovernanceNode, DOFObservabilityNode, FrameworkAdapter

9. Crear examples/langgraph_example.py:
   - Ejemplo mínimo de un grafo LangGraph con governance DOF
   - Funciona SIN API keys (usa mock LLM)
   - Muestra: crear grafo — ejecutar — verificar governance — ver métricas

10. Crear examples/generic_example.py:
    - Ejemplo de FrameworkAdapter.GenericAdapter
    - Funciona con cualquier output string
    - "Si puedes producir un string, DOF puede gobernarlo"

11. Tests en tests/test_integrations.py:
    - Test DOFGovernanceNode con output limpio — pass
    - Test DOFGovernanceNode con output que viola — fail
    - Test DOFASTNode con código limpio — pass
    - Test DOFMemoryNode add + query
    - Test GenericAdapter.wrap_output
    - Test GenericAdapter.wrap_code
    - Test CrewAIAdapter existe y es importable
    - Test LangGraphAdapter existe (mock si langgraph no instalado)
    - Ejecuta TODOS los tests

IMPORTANTE:
- LangGraph es dependencia OPCIONAL. Si no está instalado, los adapters de LangGraph se importan con try/except
- El GenericAdapter funciona SIN ninguna dependencia externa
- La filosofía: "DOF gobierna output, no importa qué framework lo produjo"
- Agregar langgraph a pyproject.toml en [project.optional-dependencies] langgraph

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: framework-agnostic governance — LangGraph adapter + generic adapter

- integrations/langgraph_adapter.py: DOF nodes for LangGraph graphs
- DOFGovernanceNode, DOFObservabilityNode, DOFMemoryNode, DOFASTNode
- FrameworkAdapter: CrewAIAdapter, LangGraphAdapter, GenericAdapter
- GenericAdapter: governance for ANY framework that produces string output
- examples/langgraph_example.py: minimal LangGraph + DOF governance
- examples/generic_example.py: framework-agnostic governance demo
- LangGraph is optional — GenericAdapter has zero external dependencies"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** integrations/, examples/, ~15 tests, multi-framework support.

---

## SESSION 21: Full Integration + README + Paper

**What it creates:** Final wiring, updated documentation, clean commit.

**Paste this in Claude Code:**

```
Ejecuta todos los tests:
python -m unittest discover tests/ -v 2>&1 | tail -5

Muéstrame el conteo total.

Actualiza README.md (mantén tono académico formal, Cyber Paisa / Enigma Group):

1. Header stats: actualiza tests, módulos, agrega "MCP Server | REST API | PostgreSQL | Multi-Framework"

2. Agrega a Key Contributions:
   - MCP Server — DOF governance exposed as Model Context Protocol tools. 10 governance tools (verify_governance, verify_ast, run_z3, memory operations, attestation, OAGS) and 3 resources accessible from Claude Desktop, Cursor, Windsurf, and any MCP-compatible client via stdio JSON-RPC transport.
   - REST API — FastAPI-based HTTP interface with 14 endpoints covering governance verification, AST analysis, Z3 formal proofs, memory CRUD with temporal queries, attestation management, OAGS conformance, and system health. CORS-enabled for web dashboard integration.
   - Storage Abstraction — Dual-backend storage supporting JSONL (default, zero-config) and PostgreSQL (production, multi-tenant). StorageFactory auto-detects backend from environment. Migration utility for existing JSONL data. SQLAlchemy ORM with JSONB columns for flexible metadata.
   - Framework-Agnostic Governance — FrameworkAdapter abstraction enabling DOF governance for any framework. LangGraphAdapter provides native graph nodes. GenericAdapter governs any system that produces string output. CrewAIAdapter wraps existing integration. Philosophy: "if you can produce a string, DOF can govern it."

3. Agrega nueva sección "MCP Server" con setup instructions
4. Agrega nueva sección "REST API" con endpoint table
5. Agrega nueva sección "Dashboard" con screenshot description
6. Agrega nueva sección "Storage Backends" con JSONL vs PostgreSQL comparison
7. Agrega nueva sección "Multi-Framework Support" con adapter table
8. Actualiza Project Structure, Citation, y conteos

Actualiza paper/PAPER_OBSERVABILITY_LAB.md:
1. Agrega sección "Protocol Integration" — MCP server y REST API
2. Agrega sección "Storage Architecture" — dual-backend abstraction
3. Agrega sección "Framework-Agnostic Governance" — adapter pattern
4. Actualiza Abstract, Key Contributions, Discussion, Conclusion
5. Actualiza todos los conteos

Después:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "docs: Phase 3 complete — MCP Server, REST API, Dashboard, PostgreSQL, Multi-Framework

- README: 4 new Key Contributions, 5 new technical sections
- Paper: 3 new formal sections, updated abstract and conclusion
- Updated stats, project structure, citation
- Phase 3 delivers: MCP compatibility, HTTP API, visual dashboard, production storage, framework-agnostic governance"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

---

## EXECUTION CHECKLIST

| # | Session | Status | Tests | Commit |
|---|---------|--------|-------|--------|
| 16 | MCP Server | ⬜ | ~20 | → commit + push |
| 17 | REST API | ⬜ | ~20 | → commit + push |
| 18 | Dashboard Web | ⬜ | ~10 | → commit + push |
| 19 | PostgreSQL Backend | ⬜ | ~15 | → commit + push |
| 20 | LangGraph Integration | ⬜ | ~15 | → commit + push |
| 21 | README + Paper | ⬜ | validation | → commit + push |

**Total new: ~80 tests | 6 commits | 4 new systems**
**Grand total after Phase 3: ~398 tests | 30+ modules | CI green**

---

## ASSESSMENT IMPACT (projected)

| Dimension | Before Phase 3 | After Phase 3 | Change |
|-----------|----------------|---------------|--------|
| Adopción | 2 | 15 | +13 (MCP = discoverable) |
| Escalabilidad | 20 | 55 | +35 (PostgreSQL + REST API) |
| Producción | 25 | 50 | +25 (dual backend + API) |
| Integración | 10 | 45 | +35 (LangGraph + MCP + REST) |
| Documentación | 30 | 50 | +20 (dashboard + MCP docs) |
| **Projected Score** | **38** | **52** | **+14** |

Still not enough for revenue. But the jump from 38→52 makes DOF credible enough to go public, write the Dev.to article, and start conversations with CrewAI/LangChain.

---

## RULES (same as Phase 2)

1. One prompt per session.
2. Each session commits independently.
3. All commits: `--author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>"` — NO co-authored-by.
4. If tests fail: fix before moving to next session.
5. If Claude Code asks for permission: allow all edits.
6. If session expires: re-authenticate, cd to project, paste current session prompt.
