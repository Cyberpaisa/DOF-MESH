# Adaline Advanced Features -- Ideas para DOF-MESH

> Investigacion: 27 marzo 2026
> Fuentes: 9 paginas de documentacion de adaline.ai/docs
> Objetivo: Extraer patrones aplicables al framework DOF-MESH

---

## 1. Tool Calling en Prompts

**URL:** https://www.adaline.ai/docs/iterate/use-tools-in-prompt

### Que hace Adaline
- Define tools con JSON Schema estandar (type, name, description, parameters, required)
- Cuatro modos de tool choice: `none`, `auto`, `required`, `any`
- Auto-ejecucion de tools via HTTP requests configurados directamente en el schema:
  ```json
  "request": {
    "type": "http",
    "method": "get",
    "url": "https://api.example.com/endpoint",
    "headers": {"Authorization": "Bearer <api-key>"},
    "retry": {"maxAttempts": 3, "initialDelay": 1000, "exponentialFactor": 2}
  }
  ```
- Compatible con OpenAI, Anthropic y Google
- Playground visual para testing iterativo de tools

### Como aplica en DOF
- DOF ya tiene MCP tools definidos por agente (Apex 18, AvaBuilder 21)
- **NO tenemos**: un sistema unificado de tool schemas con auto-ejecucion HTTP
- **NO tenemos**: modos de tool choice configurables por prompt/agente

### Idea concreta de mejora
Crear un `ToolRegistry` en DOF que defina tools con JSON Schema + request HTTP automatico. Cada agente del mesh registraria sus tools con retry configurable. El orchestrator podria cambiar el tool_choice mode dinamicamente segun la tarea (auto para exploracion, required para tareas criticas).

### Prioridad: **ALTA**

---

## 2. MCP Server en Prompts

**URL:** https://www.adaline.ai/docs/iterate/use-mcp-server-in-prompt

### Que hace Adaline
- Integra MCP servers directamente en la definicion del prompt
- Configuracion por JSON: type (url), url (HTTPS/SSE), name, tool_configuration (enabled, allowed_tools), authorization_token
- Soporta multiples MCP servers simultaneos en un solo prompt
- Whitelist de tools por servidor (allowed_tools)
- Transporte SSE sobre HTTPS con OAuth tokens

### Como aplica en DOF
- DOF ya tiene 11 MCPs configurados (Sequential Thinking, Context7, Playwright, EVM, Tavily, Supabase, Brave, etc.)
- `mcp_config.py` tiene MCP_REGISTRY(11) + ROLE_MCP_MAP(25) + ROLE_ALIASES(12)
- **Ya tenemos** un sistema robusto de MCP per-role

### Idea concreta de mejora
Agregar `tool_configuration.allowed_tools` por agente/rol en DOF. Hoy cada rol tiene acceso a TODOS los tools de sus MCPs asignados. Con whitelisting granular, un agente de seguridad solo veria `browser_snapshot` de Playwright pero no `browser_click`, reduciendo superficie de ataque. Implementar en `mcp_config.py` como `ROLE_TOOL_WHITELIST`.

### Prioridad: **MEDIA**

---

## 3. Datasets en Playground

**URL:** https://www.adaline.ai/docs/iterate/link-datasets-in-playground

### Que hace Adaline
- Conecta datasets estructurados a prompts via variables `{{variable}}`
- Mapeo columna-variable por nombre automatico
- Sincronizacion bidireccional: nuevas variables crean columnas y viceversa
- Columnas dinamicas que ejecutan APIs o prompts en runtime
- Seleccion de filas para poblar variables y ejecutar tests individuales

### Como aplica en DOF
- DOF usa JSONL logging en equipo-de-agentes
- Sentinel tiene 27 checks con datos estructurados
- **NO tenemos**: un sistema de datasets para testing de prompts
- **NO tenemos**: batch testing de prompts con datos variables

### Idea concreta de mejora
Crear un `PromptTestBench` en DOF: directorio `datasets/` con archivos JSONL donde cada linea es un caso de test (variables + expected output). Un script `dof test-prompts` iteraria sobre el dataset, ejecutaria cada caso contra el prompt, y compararia resultados. Ideal para validar que cambios en system prompts no rompen behavior existente.

### Prioridad: **ALTA**

---

## 4. Evaluacion Multi-Turn Chat

**URL:** https://www.adaline.ai/docs/evaluate/evaluate-multi-turn-chat

### Que hace Adaline
- (En desarrollo) Evaluara conversaciones multi-turno completas
- Metricas planificadas: retencion de contexto, coherencia, completar tareas
- Datasets con historiales de conversacion completos
- LLM-as-a-Judge con rubrics enfocadas en conversacion
- Monitoreo de como escalan costo y latencia con longitud de conversacion

### Como aplica en DOF
- Los agentes DOF (Apex, AvaBuilder) manejan interacciones multi-turno via A2A
- equipo-de-agentes tiene 15 opciones de CLI que implican conversaciones
- **NO tenemos**: evaluacion sistematica de calidad en conversaciones multi-turno
- **NO tenemos**: metricas de coherencia cross-turn

### Idea concreta de mejora
Implementar un `ConversationEvaluator` que tome logs de interacciones A2A entre agentes, los pase por un LLM-as-Judge con rubric de: (1) retencion de contexto, (2) coherencia de respuesta, (3) task completion rate, (4) escalado de tokens. Integrar con TRACER score como dimension adicional de calidad.

### Prioridad: **MEDIA**

---

## 5. Integracion CI/CD

**URL:** https://www.adaline.ai/docs/deploy/integrate-your-ci-cd

### Que hace Adaline
- Webhook desde Adaline a GitHub Actions/GitLab CI/Jenkins cuando se deploya un prompt
- Pipeline: trigger -> fetch prompt -> evaluar contra dataset -> gate por threshold -> release
- API REST completa:
  - `GET /v2/deployments` - obtener prompt deployado
  - `POST /v2/prompts/{id}/evaluations` - trigger evaluacion
  - `GET /v2/prompts/{id}/evaluations/{id}/results` - poll resultados
- Threshold gating: si helpfulness < 0.7, bloquear deploy
- Evaluadores: LLM-as-a-Judge, JavaScript validation, Text Matcher, Cost, Latency, Response Length
- Auto-commit de config tras aprobacion

### Como aplica en DOF
- DOF tiene CI con hooks de pre-commit (Husky + lint-staged)
- Enigma tiene `npm run build` (Prisma generate + Next build)
- **NO tenemos**: evaluacion automatica de prompts en CI
- **NO tenemos**: gate de calidad para cambios en prompts/system instructions

### Idea concreta de mejora
Crear un GitHub Action `dof-prompt-eval.yml` que en cada PR que modifique archivos de prompts (`*.prompt.md`, `system_instructions/`, etc.):
1. Ejecute el prompt contra un dataset de test
2. Evalua con LLM-as-Judge (helpfulness, factuality, safety)
3. Bloquea merge si score < threshold configurable
4. Publica resultados como comentario en el PR

### Prioridad: **ALTA**

---

## 6. Evaluaciones Continuas (Monitoreo en Produccion)

**URL:** https://www.adaline.ai/docs/monitor/setup-continuous-evaluations

### Que hace Adaline
- Sampling configurable de spans en produccion (0 a 1.0)
- Evaluadores automaticos sobre trafico real: LLM-as-Judge, JavaScript, Text Matcher, metricas operacionales
- Override por request: `runEvaluation: true` en SDK, header `adaline-span-run-evaluation: true` en proxy
- Resultados visibles en: span details, charts de tendencia, trace view
- Recomiendan empezar con sample rate 0.1-0.2 por costos

### Como aplica en DOF
- Enigma tiene cron jobs para scoring (3 crons funcionales)
- Sentinel corre 27 checks periodicamente
- **NO tenemos**: evaluacion continua de calidad de outputs de agentes en produccion
- **NO tenemos**: sampling configurable de interacciones para quality review

### Idea concreta de mejora
Implementar `ContinuousEval` en DOF: un sampler que tome N% de las interacciones de cada agente (configurable por agente), las evalue con LLM-as-Judge en background, y publique scores en un dashboard. Alertas cuando el score promedio cae X% respecto al baseline. Integrar con el TRACER score existente como senyal de degradacion.

### Prioridad: **ALTA**

---

## 7. SDK para Instrumentacion

**URL:** https://www.adaline.ai/docs/instrument/with-adaline-sdks

### Que hace Adaline
- SDKs en TypeScript (`@adaline/client`) y Python (`adaline-client`)
- Modelo de Traces (flujo completo) y Spans (operaciones individuales)
- 8 tipos de content para spans:
  | Tipo | Proposito |
  |------|-----------|
  | Model | LLM chat completions sincronos |
  | ModelStream | Respuestas streaming |
  | Tool | Ejecucion de funciones/tools |
  | Retrieval | RAG y busqueda vectorial |
  | Embeddings | Generacion de vectores |
  | Function | Logica de negocio custom |
  | Guardrail | Safety checks, PII |
  | Other | Catch-all |
- Buffering en memoria con flush por timer o capacidad
- Retry con backoff exponencial (1s inicial, 10s max)
- Health monitoring: sentCount, droppedCount, buffer length
- Deployment Controller con auto-refresh de config cada 60s

### Como aplica en DOF
- equipo-de-agentes tiene logging JSONL
- Los agentes tienen `/api/health` y `/api/interactions`
- **NO tenemos**: tracing estructurado con spans tipados
- **NO tenemos**: instrumentacion que capture tokens, costos, latencia por operacion

### Idea concreta de mejora
Crear `dof-tracer` -- un modulo de instrumentacion inspirado en Adaline pero adaptado a DOF:
- Traces por request completo (user -> orchestrator -> agent -> tool -> response)
- Spans tipados: `model`, `tool`, `guardrail`, `governance` (tipo custom para Z3 verification)
- Buffer con flush a JSONL local + opcional push a Supabase
- Metricas automaticas: tokens, costo, latencia, resultado de governance checks
- Dashboard en Enigma frontend mostrando traces del mesh

### Prioridad: **ALTA**

---

## 8. Proxy para Interceptar LLM Calls

**URL:** https://www.adaline.ai/docs/instrument/with-adaline-proxy

### Que hace Adaline
- Gateway transparente: cambia solo `baseUrl` del SDK del provider
- Soporta 10 providers: OpenAI, Anthropic, Google, Azure, Bedrock, Groq, OpenRouter, Together, xAI, Vertex
- Headers requeridos: `adaline-api-key`, `adaline-project-id`, `adaline-prompt-id`
- Headers opcionales de trace: `adaline-trace-name`, `adaline-trace-reference-id`, `adaline-trace-session-id`, `adaline-span-variables`, `adaline-span-run-evaluation`
- Captura automatica: request/response, tokens, costos, latencia, errores
- Zero modificacion de respuesta -- proxy transparente

### Como aplica en DOF
- DOF usa LiteLLM en equipo-de-agentes (ya es un proxy de providers)
- Agentes usan Anthropic SDK directo
- **NO tenemos**: logging centralizado de TODAS las llamadas LLM del ecosistema
- **NO tenemos**: headers de traza para correlacionar llamadas

### Idea concreta de mejora
Usar LiteLLM como proxy DOF con middleware custom que:
1. Intercepte todas las llamadas LLM de todos los agentes
2. Agregue headers de trace (mesh_node_id, task_id, governance_hash)
3. Logee a un store centralizado (Supabase o JSONL)
4. Calcule costos totales del mesh en tiempo real
5. Expose dashboard de costos por agente/modelo/tarea

### Prioridad: **MEDIA**

---

## 9. Custom AI Providers

**URL:** https://www.adaline.ai/docs/admin/configure-ai-provider/custom

### Que hace Adaline
- Registro de providers custom con: nombre, API key, base URL, modelos
- Los modelos custom aparecen en dropdowns de la plataforma igual que OpenAI/Anthropic
- Interfaz simple: nombre + URL + key + lista de modelos
- Activacion inmediata tras crear

### Como aplica en DOF
- DOF ya soporta multiples providers via LiteLLM (FREE_PROVIDERS_GUIDE.md documenta opciones gratuitas)
- equipo-de-agentes tiene ROLE_MCP_MAP con 25 roles
- **Ya tenemos** soporte multi-provider

### Idea concreta de mejora
Crear un `ProviderRegistry` en DOF que formalice el registro de providers custom (Ollama local, vLLM self-hosted, fine-tuned models) con health checks automaticos. Si un provider custom falla, el mesh rutea automaticamente al fallback. Integrar con el circuit breaker existente (`mesh_circuit_breaker`).

### Prioridad: **BAJA**

---

## TOP 10 IDEAS ACCIONABLES

Ideas ordenadas por impacto para DOF-MESH, basadas en el analisis de Adaline:

### 1. dof-tracer: Instrumentacion Estructurada (de SDK, seccion 7)
**Impacto: CRITICO** | Esfuerzo: Medio
- Traces + Spans tipados para todo el mesh
- Captura automatica de tokens, costos, latencia, governance
- Sin esto, estamos ciegos sobre que pasa dentro del mesh
- **Accion:** Crear modulo `src/dof_tracer/` con clases Trace y Span

### 2. PromptTestBench: Datasets para Testing (de Datasets, seccion 3)
**Impacto: ALTO** | Esfuerzo: Bajo
- Directorio `datasets/` con JSONL de casos de test
- Script `dof test-prompts` para batch testing
- Detecta regresiones antes de deploy
- **Accion:** Crear 3 datasets iniciales (governance, scoring, routing)

### 3. GitHub Action de Prompt Eval (de CI/CD, seccion 5)
**Impacto: ALTO** | Esfuerzo: Bajo
- Gate automatico en PRs que tocan prompts
- LLM-as-Judge evalua calidad
- Bloquea merge si score < threshold
- **Accion:** Crear `.github/workflows/prompt-eval.yml`

### 4. ContinuousEval en Produccion (de Continuous Evals, seccion 6)
**Impacto: ALTO** | Esfuerzo: Medio
- Sampling de interacciones reales para evaluar calidad
- Alertas de degradacion automaticas
- Integra con TRACER score como baseline
- **Accion:** Crear servicio `continuous_eval.py` con configurable sample rate

### 5. ToolRegistry Unificado (de Tool Calling, seccion 1)
**Impacto: ALTO** | Esfuerzo: Medio
- JSON Schema + auto-ejecucion HTTP para todos los tools del mesh
- Tool choice modes dinamicos por tarea
- Retry configurable por tool
- **Accion:** Crear `src/tool_registry/` con schema validation

### 6. ConversationEvaluator A2A (de Multi-Turn, seccion 4)
**Impacto: MEDIO-ALTO** | Esfuerzo: Medio
- Evalua calidad de interacciones entre agentes
- Metricas: coherencia, retencion de contexto, task completion
- Alimenta TRACER score
- **Accion:** Crear evaluador que procese logs de `/api/interactions`

### 7. LiteLLM Proxy con Tracing (de Proxy, seccion 8)
**Impacto: MEDIO** | Esfuerzo: Bajo
- Middleware en LiteLLM que logee TODAS las llamadas LLM
- Headers de correlacion (mesh_node_id, task_id)
- Dashboard de costos por agente
- **Accion:** Agregar middleware a `litellm_config.yaml`

### 8. Tool Whitelisting por Rol (de MCP, seccion 2)
**Impacto: MEDIO** | Esfuerzo: Bajo
- Restringir tools visibles por agente/rol
- Reduce superficie de ataque
- Principio de minimo privilegio para agentes
- **Accion:** Agregar `ROLE_TOOL_WHITELIST` a `mcp_config.py`

### 9. Span tipo Governance (extension de SDK, seccion 7)
**Impacto: MEDIO** | Esfuerzo: Bajo
- Tipo de span custom `governance` para Z3 verification checks
- Registra: proposicion, resultado Z3, hash, tiempo
- Trazabilidad completa de decisiones deterministas
- **Accion:** Agregar a dof-tracer como ContentType.Governance

### 10. ProviderRegistry con Failover (de Custom Providers, seccion 9)
**Impacto: BAJO-MEDIO** | Esfuerzo: Bajo
- Registro formal de providers con health checks
- Failover automatico cuando un provider cae
- Integra con circuit breaker existente
- **Accion:** Extender `mesh_circuit_breaker` con provider health

---

## Resumen Ejecutivo

| Categoria | Features de Adaline | Ya tenemos en DOF | Gap principal |
|-----------|--------------------|--------------------|---------------|
| Iteracion | Tools + MCP + Datasets | MCP config robusto | Datasets y tool registry |
| Evaluacion | Multi-turn + CI/CD | Sentinel 27 checks | Eval de prompts en CI |
| Monitoreo | Continuous evals | Cron scoring | Sampling de produccion |
| Instrumentacion | SDK + Proxy | JSONL logging | Tracing estructurado |
| Admin | Custom providers | LiteLLM multi-provider | Failover formal |

**Conclusion:** El gap mas grande de DOF vs Adaline esta en **observabilidad y testing sistematico**. Tenemos buena infraestructura de MCPs y scoring, pero nos falta tracing estructurado, testing de prompts con datasets, y evaluacion continua en produccion. Las ideas 1-4 cubririan el 80% del gap.
