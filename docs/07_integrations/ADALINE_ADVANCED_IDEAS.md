# Adaline Advanced Features -- Ideas for DOF-MESH

> Research: March 27, 2026
> Sources: 9 pages of adaline.ai/docs documentation
> Objective: Extract applicable patterns for the DOF-MESH framework

---

## 1. Tool Calling in Prompts

**URL:** https://www.adaline.ai/docs/iterate/use-tools-in-prompt

### What Adaline Does
- Defines tools with standard JSON Schema (type, name, description, parameters, required)
- Four tool choice modes: `none`, `auto`, `required`, `any`
- Auto-execution of tools via HTTP requests configured directly in the schema:
  ```json
  "request": {
    "type": "http",
    "method": "get",
    "url": "https://api.example.com/endpoint",
    "headers": {"Authorization": "Bearer <api-key>"},
    "retry": {"maxAttempts": 3, "initialDelay": 1000, "exponentialFactor": 2}
  }
  ```
- Compatible with OpenAI, Anthropic, and Google
- Visual playground for iterative tool testing

### How It Applies to DOF
- DOF already has MCP tools defined per agent (Apex 18, AvaBuilder 21)
- **We DON'T have**: a unified tool schema system with HTTP auto-execution
- **We DON'T have**: configurable tool choice modes per prompt/agent

### Concrete Improvement Idea
Create a `ToolRegistry` in DOF that defines tools with JSON Schema + automatic HTTP requests. Each mesh agent would register its tools with configurable retry. The orchestrator could change the tool_choice mode dynamically depending on the task (auto for exploration, required for critical tasks).

### Priority: **HIGH**

---

## 2. MCP Server in Prompts

**URL:** https://www.adaline.ai/docs/iterate/use-mcp-server-in-prompt

### What Adaline Does
- Integrates MCP servers directly into prompt definitions
- JSON configuration: type (url), url (HTTPS/SSE), name, tool_configuration (enabled, allowed_tools), authorization_token
- Supports multiple simultaneous MCP servers in a single prompt
- Tool whitelist per server (allowed_tools)
- SSE transport over HTTPS with OAuth tokens

### How It Applies to DOF
- DOF already has 11 MCPs configured (Sequential Thinking, Context7, Playwright, EVM, Tavily, Supabase, Brave, etc.)
- `mcp_config.py` has MCP_REGISTRY(11) + ROLE_MCP_MAP(25) + ROLE_ALIASES(12)
- **We already have** a robust per-role MCP system

### Concrete Improvement Idea
Add `tool_configuration.allowed_tools` per agent/role in DOF. Today each role has access to ALL tools from its assigned MCPs. With granular whitelisting, a security agent would only see `browser_snapshot` from Playwright but not `browser_click`, reducing attack surface. Implement in `mcp_config.py` as `ROLE_TOOL_WHITELIST`.

### Priority: **MEDIUM**

---

## 3. Datasets in Playground

**URL:** https://www.adaline.ai/docs/iterate/link-datasets-in-playground

### What Adaline Does
- Connects structured datasets to prompts via `{{variable}}` variables
- Column-to-variable mapping by name, automatic
- Bidirectional synchronization: new variables create columns and vice versa
- Dynamic columns that execute APIs or prompts at runtime
- Row selection to populate variables and run individual tests

### How It Applies to DOF
- DOF uses JSONL logging in equipo-de-agentes
- Sentinel has 27 checks with structured data
- **We DON'T have**: a dataset system for prompt testing
- **We DON'T have**: batch testing of prompts with variable data

### Concrete Improvement Idea
Create a `PromptTestBench` in DOF: a `datasets/` directory with JSONL files where each line is a test case (variables + expected output). A `dof test-prompts` script would iterate over the dataset, run each case against the prompt, and compare results. Ideal for validating that changes to system prompts don't break existing behavior.

### Priority: **HIGH**

---

## 4. Multi-Turn Chat Evaluation

**URL:** https://www.adaline.ai/docs/evaluate/evaluate-multi-turn-chat

### What Adaline Does
- (In development) Will evaluate complete multi-turn conversations
- Planned metrics: context retention, coherence, task completion
- Datasets with full conversation histories
- LLM-as-a-Judge with conversation-focused rubrics
- Monitoring how cost and latency scale with conversation length

### How It Applies to DOF
- DOF agents (Apex, AvaBuilder) handle multi-turn interactions via A2A
- equipo-de-agentes has 15 CLI options that imply conversations
- **We DON'T have**: systematic quality evaluation for multi-turn conversations
- **We DON'T have**: cross-turn coherence metrics

### Concrete Improvement Idea
Implement a `ConversationEvaluator` that takes A2A interaction logs between agents, passes them through an LLM-as-Judge with a rubric of: (1) context retention, (2) response coherence, (3) task completion rate, (4) token scaling. Integrate with TRACER score as an additional quality dimension.

### Priority: **MEDIUM**

---

## 5. CI/CD Integration

**URL:** https://www.adaline.ai/docs/deploy/integrate-your-ci-cd

### What Adaline Does
- Webhook from Adaline to GitHub Actions/GitLab CI/Jenkins when a prompt is deployed
- Pipeline: trigger -> fetch prompt -> evaluate against dataset -> gate by threshold -> release
- Full REST API:
  - `GET /v2/deployments` - get deployed prompt
  - `POST /v2/prompts/{id}/evaluations` - trigger evaluation
  - `GET /v2/prompts/{id}/evaluations/{id}/results` - poll results
- Threshold gating: if helpfulness < 0.7, block deploy
- Evaluators: LLM-as-a-Judge, JavaScript validation, Text Matcher, Cost, Latency, Response Length
- Auto-commit of config after approval

### How It Applies to DOF
- DOF has CI with pre-commit hooks (Husky + lint-staged)
- Enigma has `npm run build` (Prisma generate + Next build)
- **We DON'T have**: automatic prompt evaluation in CI
- **We DON'T have**: quality gate for changes to prompts/system instructions

### Concrete Improvement Idea
Create a GitHub Action `dof-prompt-eval.yml` that on every PR modifying prompt files (`*.prompt.md`, `system_instructions/`, etc.):
1. Runs the prompt against a test dataset
2. Evaluates with LLM-as-Judge (helpfulness, factuality, safety)
3. Blocks merge if score < configurable threshold
4. Publishes results as a comment on the PR

### Priority: **HIGH**

---

## 6. Continuous Evaluations (Production Monitoring)

**URL:** https://www.adaline.ai/docs/monitor/setup-continuous-evaluations

### What Adaline Does
- Configurable span sampling in production (0 to 1.0)
- Automatic evaluators on real traffic: LLM-as-Judge, JavaScript, Text Matcher, operational metrics
- Per-request override: `runEvaluation: true` in SDK, header `adaline-span-run-evaluation: true` in proxy
- Results visible in: span details, trend charts, trace view
- Recommend starting with sample rate 0.1-0.2 for cost reasons

### How It Applies to DOF
- Enigma has cron jobs for scoring (3 functional crons)
- Sentinel runs 27 checks periodically
- **We DON'T have**: continuous quality evaluation of agent outputs in production
- **We DON'T have**: configurable interaction sampling for quality review

### Concrete Improvement Idea
Implement `ContinuousEval` in DOF: a sampler that takes N% of each agent's interactions (configurable per agent), evaluates them with LLM-as-Judge in the background, and publishes scores to a dashboard. Alerts when the average score drops X% from the baseline. Integrate with the existing TRACER score as a degradation signal.

### Priority: **HIGH**

---

## 7. SDK for Instrumentation

**URL:** https://www.adaline.ai/docs/instrument/with-adaline-sdks

### What Adaline Does
- SDKs in TypeScript (`@adaline/client`) and Python (`adaline-client`)
- Model of Traces (full flow) and Spans (individual operations)
- 8 content types for spans:
  | Type | Purpose |
  |------|---------|
  | Model | Synchronous LLM chat completions |
  | ModelStream | Streaming responses |
  | Tool | Function/tool execution |
  | Retrieval | RAG and vector search |
  | Embeddings | Vector generation |
  | Function | Custom business logic |
  | Guardrail | Safety checks, PII |
  | Other | Catch-all |
- In-memory buffering with flush by timer or capacity
- Retry with exponential backoff (initial 1s, max 10s)
- Health monitoring: sentCount, droppedCount, buffer length
- Deployment Controller with auto-refresh of config every 60s

### How It Applies to DOF
- equipo-de-agentes has JSONL logging
- Agents have `/api/health` and `/api/interactions`
- **We DON'T have**: structured tracing with typed spans
- **We DON'T have**: instrumentation that captures tokens, costs, latency per operation

### Concrete Improvement Idea
Create `dof-tracer` -- an instrumentation module inspired by Adaline but adapted for DOF:
- Traces per complete request (user -> orchestrator -> agent -> tool -> response)
- Typed spans: `model`, `tool`, `guardrail`, `governance` (custom type for Z3 verification)
- Buffer with flush to local JSONL + optional push to Supabase
- Automatic metrics: tokens, cost, latency, governance check results
- Dashboard in Enigma frontend showing mesh traces

### Priority: **HIGH**

---

## 8. Proxy to Intercept LLM Calls

**URL:** https://www.adaline.ai/docs/instrument/with-adaline-proxy

### What Adaline Does
- Transparent gateway: only changes the provider SDK's `baseUrl`
- Supports 10 providers: OpenAI, Anthropic, Google, Azure, Bedrock, Groq, OpenRouter, Together, xAI, Vertex
- Required headers: `adaline-api-key`, `adaline-project-id`, `adaline-prompt-id`
- Optional trace headers: `adaline-trace-name`, `adaline-trace-reference-id`, `adaline-trace-session-id`, `adaline-span-variables`, `adaline-span-run-evaluation`
- Automatic capture: request/response, tokens, costs, latency, errors
- Zero response modification -- transparent proxy

### How It Applies to DOF
- DOF uses LiteLLM in equipo-de-agentes (already a provider proxy)
- Agents use Anthropic SDK directly
- **We DON'T have**: centralized logging of ALL LLM calls in the ecosystem
- **We DON'T have**: trace headers to correlate calls

### Concrete Improvement Idea
Use LiteLLM as DOF proxy with custom middleware that:
1. Intercepts all LLM calls from all agents
2. Adds trace headers (mesh_node_id, task_id, governance_hash)
3. Logs to a centralized store (Supabase or JSONL)
4. Calculates total mesh costs in real time
5. Exposes cost dashboard per agent/model/task

### Priority: **MEDIUM**

---

## 9. Custom AI Providers

**URL:** https://www.adaline.ai/docs/admin/configure-ai-provider/custom

### What Adaline Does
- Registration of custom providers with: name, API key, base URL, models
- Custom models appear in platform dropdowns just like OpenAI/Anthropic
- Simple interface: name + URL + key + model list
- Immediate activation after creation

### How It Applies to DOF
- DOF already supports multiple providers via LiteLLM (FREE_PROVIDERS_GUIDE.md documents free options)
- equipo-de-agentes has ROLE_MCP_MAP with 25 roles
- **We already have** multi-provider support

### Concrete Improvement Idea
Create a `ProviderRegistry` in DOF that formalizes registration of custom providers (local Ollama, self-hosted vLLM, fine-tuned models) with automatic health checks. If a custom provider fails, the mesh automatically routes to the fallback. Integrate with the existing circuit breaker (`mesh_circuit_breaker`).

### Priority: **LOW**

---

## TOP 10 ACTIONABLE IDEAS

Ideas ranked by impact for DOF-MESH, based on the Adaline analysis:

### 1. dof-tracer: Structured Instrumentation (from SDK, section 7)
**Impact: CRITICAL** | Effort: Medium
- Traces + typed Spans for the entire mesh
- Automatic capture of tokens, costs, latency, governance
- Without this, we're blind to what happens inside the mesh
- **Action:** Create module `src/dof_tracer/` with Trace and Span classes

### 2. PromptTestBench: Datasets for Testing (from Datasets, section 3)
**Impact: HIGH** | Effort: Low
- `datasets/` directory with JSONL test cases
- `dof test-prompts` script for batch testing
- Detects regressions before deploy
- **Action:** Create 3 initial datasets (governance, scoring, routing)

### 3. GitHub Action for Prompt Eval (from CI/CD, section 5)
**Impact: HIGH** | Effort: Low
- Automatic gate on PRs that touch prompts
- LLM-as-Judge evaluates quality
- Blocks merge if score < threshold
- **Action:** Create `.github/workflows/prompt-eval.yml`

### 4. ContinuousEval in Production (from Continuous Evals, section 6)
**Impact: HIGH** | Effort: Medium
- Sampling of real interactions to evaluate quality
- Automatic degradation alerts
- Integrates with TRACER score as baseline
- **Action:** Create `continuous_eval.py` service with configurable sample rate

### 5. Unified ToolRegistry (from Tool Calling, section 1)
**Impact: HIGH** | Effort: Medium
- JSON Schema + HTTP auto-execution for all mesh tools
- Dynamic tool choice modes per task
- Configurable retry per tool
- **Action:** Create `src/tool_registry/` with schema validation

### 6. A2A ConversationEvaluator (from Multi-Turn, section 4)
**Impact: MEDIUM-HIGH** | Effort: Medium
- Evaluates quality of inter-agent interactions
- Metrics: coherence, context retention, task completion
- Feeds TRACER score
- **Action:** Create evaluator that processes logs from `/api/interactions`

### 7. LiteLLM Proxy with Tracing (from Proxy, section 8)
**Impact: MEDIUM** | Effort: Low
- Middleware in LiteLLM that logs ALL LLM calls
- Correlation headers (mesh_node_id, task_id)
- Cost dashboard per agent
- **Action:** Add middleware to `litellm_config.yaml`

### 8. Tool Whitelisting by Role (from MCP, section 2)
**Impact: MEDIUM** | Effort: Low
- Restrict visible tools per agent/role
- Reduces attack surface
- Principle of least privilege for agents
- **Action:** Add `ROLE_TOOL_WHITELIST` to `mcp_config.py`

### 9. Governance Span Type (extension of SDK, section 7)
**Impact: MEDIUM** | Effort: Low
- Custom span type `governance` for Z3 verification checks
- Records: proposition, Z3 result, hash, time
- Full traceability of deterministic decisions
- **Action:** Add to dof-tracer as ContentType.Governance

### 10. ProviderRegistry with Failover (from Custom Providers, section 9)
**Impact: LOW-MEDIUM** | Effort: Low
- Formal provider registry with health checks
- Automatic failover when a provider goes down
- Integrates with existing circuit breaker
- **Action:** Extend `mesh_circuit_breaker` with provider health

---

## Executive Summary

| Category | Adaline Features | Already in DOF | Main Gap |
|----------|-----------------|----------------|----------|
| Iteration | Tools + MCP + Datasets | Robust MCP config | Datasets and tool registry |
| Evaluation | Multi-turn + CI/CD | Sentinel 27 checks | Prompt eval in CI |
| Monitoring | Continuous evals | Cron scoring | Production sampling |
| Instrumentation | SDK + Proxy | JSONL logging | Structured tracing |
| Admin | Custom providers | LiteLLM multi-provider | Formal failover |

**Conclusion:** The biggest gap in DOF vs Adaline is in **observability and systematic testing**. We have good MCP and scoring infrastructure, but we lack structured tracing, prompt testing with datasets, and continuous evaluation in production. Ideas 1-4 would cover 80% of the gap.
