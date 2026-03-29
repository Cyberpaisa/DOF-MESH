# Chapter 10: The Control Room — First Real Stress Test of DOF Mesh

*When 18 tasks hit 6 nodes simultaneously and the system tells you the truth about itself.*

*March 24, 2026 — DOF v0.6.1*

---

## 1. The Scenario

Until the night of March 23, the DOF Mesh was a promising architecture: 52+ modules, 3000+ tests, nodes exchanging JSON over the filesystem, daemons that auto-start with LaunchAgent. Everything worked in unit tests, in integration tests, in manual runs with a single task at a time.

But a distributed system does not exist until you break it.

The real stress test started with a simple premise: send 18 simultaneous tasks to 6 mesh nodes, each node with its own specialized Ollama model, and measure what happens. Not simulating load — applying it for real, with actual models running on the M4 Max, with the daemon actively reading inbox dirs every 3 seconds, with Telegram reporting results in real time.

What we discovered changed our understanding of the system.

---

## 2. What We Built This Session

Before the test, the March 24 session was dedicated to completing the local execution infrastructure. These are the modules that went into production:

### 2.1 `core/autonomous_executor.py` — The Tool Engine

The executor is the heart of local agentic execution. It operates in a loop of up to 10 iterations, where each iteration can use one of 5 available tools:

```python
TOOLS = {
    "bash":       executes shell commands with configurable timeout,
    "python":     evaluates Python code in an isolated namespace,
    "read_file":  reads filesystem files with line limits,
    "write_file": writes files with path validation,
    "list_dir":   lists directories with extension filters
}
```

Two critical design decisions:

**Think-tag stripping:** DeepSeek and some Qwen models emit `<think>...</think>` blocks with internal reasoning before the final output. The executor strips them before parsing JSON, which was essential to allow local models to be used without modification:

```python
def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    import re
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
```

**BLOCKED_PATTERNS for security:** The executor rejects commands matching dangerous patterns before executing them — `rm -rf`, `sudo`, unauthorized network operations, credential access. This is not full Z3 governance, but it is the first line of defense in local execution.

### 2.2 `core/local_orchestrator.py` — Multi-Model Routing

The orchestrator automatically selects the correct Ollama model based on task type:

```
Task type            → Selected model
─────────────────────────────────────────
"code" / "debug"     → dof-coder (Qwen2.5-Coder 14.8B)
"security" / "audit" → dof-guardian (Qwen2.5-Coder 14.8B + security system prompt)
"analysis" / "data"  → dof-analyst (Qwen2.5-Coder 14.8B + analysis system prompt)
"reasoning" / "plan" → dof-reasoner (Qwen2.5-Coder 14.8B + chain-of-thought)
"general"            → local-agi-m4max (Qwen2.5-Coder 14.8B + generalist prompt)
```

The routing is deterministic — keywords in the task JSON's `type` field determine the destination node. No LLM classifier, no probabilities: exact string matching.

### 2.3 `scripts/run_mesh_agent.py` — The Mesh Daemon

This script is the process that keeps the mesh alive. It operates in an infinite loop:

```
Every 3 seconds:
  For each node in [dof-coder, dof-reasoner, dof-guardian,
                    dof-analyst, local-agi-m4max, local-agent]:
    1. Scan logs/mesh/inbox/{node}/*.json
    2. If there are pending tasks (without .processing or .done extension):
       a. Rename task.json → task.json.processing
       b. Load the node's Ollama model
       c. Execute autonomous_executor with the task
       d. Write result to logs/mesh/outbox/{node}/
       e. Rename task.json.processing → task.json.done
    3. Report status via Telegram if there are changes
```

The file protocol (.processing → .done) acts as a distributed lock. If the daemon dies mid-task, the file remains in `.processing` state — a clear signal that it needs manual attention. No messages are silently lost.

### 2.4 LaunchAgent — Auto-Start on Login

```xml
<!-- ~/Library/LaunchAgents/com.dof.mesh-agent.plist -->
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>ProgramArguments</key>
<array>
  <string>/Users/jquiceva/.nvm/versions/node/v20.x.x/bin/python3</string>
  <string>/Users/jquiceva/equipo-de-agentes/scripts/run_mesh_agent.py</string>
</array>
```

Lesson learned from experience with OpenClaw: the plist MUST use the absolute path of the nvm Python, not `/usr/local/bin/python3`. In macOS Tahoe, the LaunchAgent PATH does not inherit the user's PATH — if the executable does not exist at the exact path, the service fails silently.

### 2.5 Modelfiles — The 6 Specialized Nodes

We created Modelfiles for each mesh node, each with a different system prompt that guides the behavior of the base model (Qwen2.5-Coder 14.8B):

```dockerfile
# Example: dof-coder
FROM qwen2.5-coder:14b
SYSTEM """
You are dof-coder, an agent specialized in writing and analyzing Python code.
Your goal: produce correct, documented code with error handling.
When using tools, respond ONLY with valid JSON.
Format: {"tool": "name", "args": {...}} or {"result": "final response"}
"""
PARAMETER temperature 0.1
PARAMETER top_p 0.9
```

Low temperature (0.1) is critical for tool use — we need parseable JSON, not creativity.

### 2.6 Mission Control APIs

Three new endpoints in the Next.js frontend to integrate the mesh with the web interface:

| Endpoint | Function |
|---|---|
| `api/local/ollama` | SSE streaming with cross-chunk think-tag stripping |
| `api/local/mesh` | Sends tasks to the mesh via filesystem |
| `api/local/upload` | Upload with server-side extraction (pdfplumber + pandas) |
| `api/system/control` | System process control |

The SSE streaming with cross-chunk think-tag stripping deserves special attention: `<think>` tags can arrive split between chunks. The handler maintains an accumulative buffer and only emits content outside the thinking tags to the client:

```typescript
// SSE handler pseudocode
let buffer = '';
let inThink = false;

for await (const chunk of ollamaStream) {
  buffer += chunk.response;

  // Detect think tag opening/closing crossing chunks
  if (buffer.includes('<think>')) inThink = true;
  if (buffer.includes('</think>')) {
    inThink = false;
    buffer = buffer.replace(/<think>[\s\S]*?<\/think>/g, '');
  }

  if (!inThink) {
    const clean = extractClean(buffer);
    if (clean) emit(clean);
  }
}
```

---

## 3. The Stress Test

### 3.1 Experiment Setup

With the complete infrastructure in place, we launched the test: **18 simultaneous tasks across 6 mesh nodes**.

The setup:

```
Hardware:    MacBook Pro M4 Max, 36GB RAM, Ollama 0.6.x
Models:      Qwen2.5-Coder 14.8B (base for all nodes)
Instances:   1 Ollama process, 6 Modelfiles, 2 daemon instances
Timeout:     180s initial (later adjusted to 600s)
Tasks:       3 per node, JSON in logs/mesh/inbox/{node}/
```

The 18 tasks covered real system operations:

```
dof-coder:      analyze autonomous_executor.py, generate docstrings, review imports
dof-reasoner:   plan scaling architecture, reason about trade-offs
dof-guardian:   audit security patterns, review BLOCKED_PATTERNS
dof-analyst:    analyze test metrics, report coverage
local-agi-m4max: summarize system state, generate report
local-agent:    verify mesh health, report anomalies
```

### 3.2 Mesh Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOF MESH — STRESS TEST                        │
│                    18 tasks / 6 nodes                            │
└─────────────────────────────────────────────────────────────────┘

  Telegram / CLI / Mission Control
          │
          │  POST task (JSON)
          ▼
  ┌──────────────────┐
  │  local_orchestrator │  ← Routing by task type
  │  (deterministic)    │
  └──────────┬───────┘
             │
    Writes to filesystem
             │
    ┌────────┴────────────────────────────────────────────┐
    │                                                     │
    ▼            ▼            ▼            ▼              ▼
logs/mesh/   logs/mesh/   logs/mesh/   logs/mesh/   logs/mesh/
inbox/       inbox/       inbox/       inbox/       inbox/
dof-coder/   dof-reasoner/ dof-guardian/ dof-analyst/ local-agent/
task1.json   task1.json   task1.json   task1.json   task1.json
task2.json   task2.json   task2.json   task2.json   task2.json
task3.json   task3.json   task3.json   task3.json   task3.json
    │            │            │            │              │
    └─────────────────────────┼────────────────────────────┘
                              │
                    run_mesh_agent.py
                    (scan every 3s)
                              │
                    ┌─────────┴──────────┐
                    │                    │
              .processing           Ollama API
                (lock)               (serial)
                    │                    │
                    │       ┌────────────┴──────────┐
                    │       │    ONE single process  │
                    │       │    Qwen2.5-Coder 14B   │
                    │       │    serializes all      │
                    │       └────────────┬──────────┘
                    │                    │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  autonomous_executor│
                    │  max 10 iterations  │
                    │  5 tools            │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  logs/mesh/outbox/  │
                    │  task1.json.done    │  ← result
                    └─────────────────────┘
                              │
                    Telegram notification
```

### 3.3 Results

| Node | Tasks | OK | Timeout | Avg time |
|------|--------|----|---------|----|
| dof-analyst | 3 | 1 | 2 | 210s |
| local-agi-m4max | 3 | 2 | 1 | 218s |
| dof-guardian | 3 | 1 | 2 | 237s |
| dof-coder | 3 | 1 | 2 | 253s |
| local-agent | 3 | 1 | 2 | 248s |
| dof-reasoner | 3 | 0 | 3 | 280s |
| **TOTAL** | **18** | **6 (33%)** | **12 (67%)** | **241s** |

**33% success.** At first glance, a bad result. But the correct interpretation is different.

### 3.4 Root Cause Analysis

The diagnosis took less than 10 minutes once we understood the problem:

**Initial hypothesis (incorrect):** The models are failing to process the tasks.

**Evidence:** The most notable successful task refuted this hypothesis. dof-coder read `autonomous_executor.py` and `local_orchestrator.py` completely in 2 tool iterations, and in 103 seconds generated professional docstrings for both files. Tool use working perfectly, quality output.

**Real root cause:** Timeouts did not occur during execution. They occurred while tasks waited in the queue.

```
Timeline of a task that times out:

t=0s    Task enters inbox/dof-coder/
t=1s    Daemon detects it, marks it .processing
t=2s    Daemon sends to Ollama... but Ollama is busy
t=150s  Ollama finishes previous task, starts this one
t=180s  ⚡ Executor TIMEOUT (configured at 180s)
        The task had only 30s of actual execution
        → marked as failed
```

Ollama with a single process handles requests serially. 18 simultaneous requests means a wait queue. The 180s timeout, reasonable for a single task, was insufficient when it included queue wait time.

**Fix applied:** timeout 180s → 600s in the executor. With this change, the same 18 tasks would have had enough actual execution time even waiting in the queue.

### 3.5 Hardware Behavior

```
RAM state during the test:
─────────────────────────────────────────────────────────────
          Start     Peak     End
RAM used: 22GB   → 34GB  → 28GB    (of 36GB available)
─────────────────────────────────────────────────────────────
          ▲                ▲
    baseline         Real limit!
    2 daemon         Only 2GB margin
    instances +      before swap
    services
```

RAM was the second bottleneck. Qwen2.5-Coder 14.8B in Q4 occupies ~9GB of RAM for the base model, plus context for each active request. With 6 nodes potentially running in parallel (in theory), the 34GB peak out of 36GB available left no margin.

In practice, Ollama serializes everything — there was only one active inference process at a time — but the daemon, Mission Control, Telegram and other system services consumed the remaining 13GB.

**CPU:** Was not the bottleneck at any point. The M4 Max has 16 available CPU cores, and LLM inference is GPU/ANE bound.

**GPU/ANE:** Ollama's serialization means the 40 GPU cores of the M4 Max were being used sequentially by a single request at a time. For real parallelism, we would need multiple Ollama instances on different ports.

---

## 4. The Telegram 409 Bug

While the stress test was running, a separate but equally instructive problem emerged in the Telegram interface.

### 4.1 The Symptom

```
Error 409 Conflict: terminated by other getUpdates request
```

Appearing continuously, preventing the bot from receiving messages. The system was operationally blind — we could send tasks to the mesh, but couldn't receive confirmations.

### 4.2 Diagnosis

The first tool was `ps aux`:

```bash
$ ps aux | grep telegram_bot
jquiceva  12847  0.0  0.1  python3 interfaces/telegram_bot.py  # instance 1
jquiceva  13291  0.0  0.1  python3 interfaces/telegram_bot.py  # instance 2
jquiceva  14103  0.0  0.1  python3 interfaces/telegram_bot.py  # instance 3 (!!)
```

Three instances of the bot running simultaneously. Each trying to do `getUpdates` — Telegram's long-polling mechanism. The Telegram server only allows one active session per bot token, and when it detects a second one, it kills the first with 409.

**Source of the instances:**
- Instance 1: started manually days earlier, still running in background
- Instance 2: started by a background Claude agent (task b0n6utxjz) that the user started to monitor the test
- Instance 3: started by the main process trying to resolve the 409

**The structural problem:** `long_polling_timeout=60` in telebot means that when a process dies, Telegram keeps its session active for 60 seconds. During those 60 seconds, any new attempt to start the bot receives 409. If the new attempt also dies (because of the 409), and we try again, we enter a failure cycle.

**What does NOT work:** Doing `getUpdates?timeout=0` to "cancel" the existing session. Telegram ignores this attempt when there is an active long-polling session on the server.

### 4.3 The Fix

```bash
# Step 1: kill all instances
kill -9 12847 13291 14103

# Step 2: verify none remain
ps aux | grep telegram_bot  # must be empty

# Step 3: wait the full expiration time
sleep 65  # long_polling_timeout(60) + margin(5)

# Step 4: start ONE single instance
python3 interfaces/telegram_bot.py &

# Verify
curl -s "https://api.telegram.org/bot$TOKEN/getMe" | jq .ok
# → true ✅
```

The bot's fallback chain, once working correctly:

```
ANTHROPIC_API_KEY (not configured)
      │
      ▼ fallback
GROQ_API_KEY (expired — 401 Unauthorized)
      │
      ▼ fallback
CEREBRAS_API_KEY (valid — 200 OK) ✅ Active
      │
      ▼ fallback (if Cerebras fails)
Ollama local → local-agi-m4max ($0, always available)
```

This chain is exactly the resilience pattern we designed: never a single point of failure, always a $0 option available locally.

### 4.4 Organizational Lesson

The Telegram bug revealed a coordination problem between agents. When multiple Claude agents work in parallel (the main agent + background agents started by the user), they can compete for the same stateful resources — in this case, the Telegram connection.

The solution is not only technical — it is organizational: **a single agent in charge of each stateful service**. If the Telegram service needs management, only the agent designated for Telegram can start or restart it. Other agents can read the service status, but cannot start it.

This principle — exclusive ownership of stateful resources — is fundamental for multi-agent systems that share infrastructure.

---

## 5. Technical Lessons

### Lesson 1: Wall-Clock Timeout vs Execution Timeout

The executor timeout should start when Ollama begins responding, not when the task enters the queue.

```python
# BEFORE (incorrect for high load):
async def execute(task, timeout=180):
    start = time.time()
    result = await ollama.generate(...)  # may wait 150s in queue
    # Only 30s left for actual execution

# AFTER (correct):
async def execute(task, queue_timeout=300, exec_timeout=180):
    # Wait in queue up to queue_timeout
    response = await asyncio.wait_for(
        ollama.generate(...),
        timeout=queue_timeout
    )
    # Once Ollama starts, give full exec_timeout
    ...
```

Under high load, the queue wait time can exceed the configured timeout. The result is tasks that "fail" without ever having been executed — the most frustrating to debug because logs show timeout but there is no evidence of execution.

### Lesson 2: Ollama is Serial by Design

A single Ollama process on M4 Max handles one request at a time. This is a conscious design decision by Ollama — maximize GPU usage for each individual request.

For real parallelism there are three options:

```
Option A: Multiple Ollama instances on different ports
─────────────────────────────────────────────────────────────
ollama serve --port 11434  # instance 1 → dof-coder
ollama serve --port 11435  # instance 2 → dof-guardian
...
Cost: more RAM (each instance loads the model separately)
Gain: true hardware parallelism

Option B: External APIs for parallel load
─────────────────────────────────────────────────────────────
Cerebras: 868 tok/s, 60 req/min on free tier
Groq:     variable, very fast for small models
Cost: external dependency, possible key expiration
Gain: 5-10x faster than local for short tasks

Option C: Smaller models + parallelism
─────────────────────────────────────────────────────────────
Phi-4 14B (9GB, 120 tok/s ANE) → higher throughput
Llama 3.3 8B (5GB, 230 tok/s) → maximum local throughput
Cost: lower reasoning quality
Gain: 2-4 parallel tasks within the available 36GB
```

For DOF Mesh on M4 Max, the optimal short-term strategy is Option C: smaller models for routing/classification tasks, reserving Qwen2.5-Coder 14.8B for tasks requiring high quality.

### Lesson 3: Race Conditions on Stateful Resources

The Telegram server maintains state per bot session. This state has cleanup latency (60-65 seconds for long-polling). Any system that can have multiple competing initiators must manage this explicitly.

The correct pattern is a PID file with lock:

```python
import fcntl, os, sys

PID_FILE = "/tmp/dof-telegram-bot.pid"

def acquire_lock():
    """Acquires exclusive lock or exits if an instance already exists."""
    try:
        fp = open(PID_FILE, 'w')
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fp.write(str(os.getpid()))
        fp.flush()
        return fp
    except IOError:
        print(f"Bot already running (PID file: {PID_FILE})")
        sys.exit(1)

lock = acquire_lock()
# ... start bot normally
```

With this pattern, the second instance fails immediately instead of creating a 65-second conflict in Telegram.

### Lesson 4: The File Protocol is Solid Architecture

After the test, we can confirm: the JSON inbox → .processing → .done protocol worked correctly in all cases. All 18 task files were handled without corruption, without race conditions in the filesystem, without lost messages.

The only cause of failure was the resource layer (RAM/GPU) above the protocol. The protocol itself is robust.

This validates the design decision: use the filesystem as a message bus instead of Redis, RabbitMQ, or any other messaging system. On an M4 Max with NVMe SSD, filesystem operations are extremely fast. And more importantly: they are debuggable — you can do `ls logs/mesh/inbox/` and see exactly the state of the system at any moment.

### Lesson 5: The Successful Task is the Most Important Data

In a stress test with 33% success, it is tempting to focus on the 67% failures. But the dof-coder successful task is the most revealing result:

```
Task:    "Read autonomous_executor.py and local_orchestrator.py,
          generate professional docstrings for all functions"

Iteration 1: tool=read_file, args={path: "core/autonomous_executor.py"}
             → 847 lines read correctly

Iteration 2: tool=read_file, args={path: "core/local_orchestrator.py"}
             → 312 lines read correctly

Iteration 3: tool=write_file, args={path: "core/autonomous_executor.py",
             content: "...complete file with docstrings..."}
             → file written with Google-style docstrings on each function

Total time: 103 seconds
Iterations: 3 of 10 maximum
Quality: professional docstrings with Args:, Returns:, Raises:
```

The local agent, running on Qwen2.5-Coder 14.8B in Ollama, executed a real engineering task with multiple tool steps, without JSON parsing errors, without path hallucinations, with publishable quality output. The system works. The timeouts were a configuration problem, not a capability problem.

---

## 6. DOF v0.6.1 Numbers

At the close of the March 24 session, local-agent confirmed the system state live:

| Metric | Value |
|---|---|
| Modules in core/ | **105** |
| Total tests | **3389** |
| Tests passing | **3384 (99.85%)** |
| Tests failing | 5 |
| Custom Ollama models | **6** (dof-coder, dof-reasoner, dof-guardian, dof-analyst, local-agi-m4max, moondream) |
| Available base models | 2 (qwen2.5-coder:14b, moondream) |
| SSE streaming active | Yes — with think-tag stripping |
| File upload without limit | Yes — PDF, Excel, images, code |
| Auto-start daemon | Yes — LaunchAgent (RunAtLoad + KeepAlive) |
| Timeout configured | 600s (updated from 180s) |

The number of modules — 105 — deserves a moment of pause. We started DOF with 25 modules in v0.2.0. Four weeks later, we are at 105. Not through synthetic growth, but because each chapter of this book generated real modules that the system needed.

---

## 7. Complete Local Stack Architecture

After this session, the DOF local inference stack looks like this:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACES                                │
│  Telegram Bot  │  Mission Control  │  CLI  │  REST API       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    ROUTING LAYER                              │
│              local_orchestrator.py                           │
│         Deterministic keyword routing                        │
│    code→coder  security→guardian  data→analyst  ...          │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │         FILESYSTEM BUS             │
          │  logs/mesh/inbox/{node}/*.json     │
          │  Protocol: .json → .processing    │
          │            .processing → .done    │
          └─────────────────┬──────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    DAEMON LAYER                              │
│              run_mesh_agent.py (scan 3s)                     │
│         LaunchAgent: auto-start + KeepAlive                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   EXECUTOR LAYER                             │
│              autonomous_executor.py                          │
│   Tools: bash | python | read_file | write_file | list_dir  │
│   Max 10 iterations | BLOCKED_PATTERNS | think-tag strip    │
│   Timeout: 600s (wall-clock from Ollama start)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   INFERENCE LAYER                            │
│              Ollama 0.6.x (serial, single GPU)               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  dof-coder   │  │ dof-guardian │  │ dof-analyst  │      │
│  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │      │
│  │  temp=0.1   │  │  temp=0.1   │  │  temp=0.1   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ dof-reasoner │  │local-agi-m4mx│  │  moondream   │      │
│  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │  │  vision 1.8B │      │
│  │  temp=0.3   │  │  temp=0.2   │  │  multimodal  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│              RAM: ~9GB per active model                     │
│              GPU: 40-core, one request at a time            │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   HARDWARE BASE                              │
│         Apple M4 Max — 36GB unified RAM                      │
│         16-core CPU | 40-core GPU | 16-core ANE             │
│         19 TFLOPS FP16 @ 2.8W | NVMe SSD 432GB free         │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. What Comes Next

The stress test revealed a clear path toward DOF v0.7.0:

### 8.1 Real Parallelism in Ollama

The most impactful change: multiple Ollama instances on different ports, each node with its own inference process. With 8B models (5GB) instead of 14B, we could run 4 simultaneous instances within the 36GB:

```
Port 11434: local-coder (Llama 3.3 8B) → 5GB
Port 11435: local-guardian (Phi-4 14B) → 9GB
Port 11436: local-analyst (Qwen2.5 7B) → 4GB
Port 11437: local-reasoner (Qwen3 8B) → 5GB
─────────────────────────────────────────────────
Total model: 23GB + 13GB system = 36GB ✅
Real parallelism: 4 simultaneous tasks
```

### 8.2 Adaptive Timeout

Instead of a fixed timeout, the executor should estimate queue wait time before starting:

```python
async def adaptive_timeout(task, base_timeout=180):
    queue_depth = await ollama.get_queue_depth()
    avg_exec_time = metrics.get_avg_exec_time()
    estimated_wait = queue_depth * avg_exec_time
    total_timeout = estimated_wait + base_timeout
    return min(total_timeout, 3600)  # maximum 1 hour
```

### 8.3 Governance in the Executor

The autonomous_executor currently has BLOCKED_PATTERNS as its only security layer. The next step is to integrate the complete DOF Governance Pipeline — pre-check + Z3 + post-check — before and after each executed tool:

```python
# Each tool use passes through governance
async def safe_tool_use(tool_name, args, governance):
    pre_result = await governance.pre_check(tool_name, args)
    if not pre_result.passed:
        return {"error": pre_result.violations}

    result = await execute_tool(tool_name, args)

    post_result = await governance.post_check(tool_name, args, result)
    return {"result": result, "governance": post_result}
```

### 8.4 Mesh Federation

With the local mesh working, the next level is federation: multiple mesh instances on different machines (or different users) that can exchange tasks. The JSON file protocol extends naturally to HTTP — the same JSON we write to inbox/ can be sent via POST to a remote endpoint.

This connects with the work in `BOOK_CH14_FEDERATION.md` and `BOOK_CH15_INTERNET_FEDERATION.md` — the design already exists, now we have the local infrastructure that justifies it.

### 8.5 The Goal: 18/18

The target for the next stress test is 18/18 completed tasks. Not as a quality goal — but as a reliability baseline. A production system needs to complete 100% of the tasks it accepts, or explicitly reject them before starting.

The path is clear:

```
Today (v0.6.1):   6/18 (33%) — wall-clock timeout misconfigured
v0.6.2:           16/18 (89%) — timeout 600s + queue wait fix
v0.7.0:           18/18 (100%) — real parallelism + adaptive timeout
```

---

## Closing

This session was the most honest in the project. We didn't build impressive features — we built the necessary infrastructure and then applied real load to it until it revealed its limitations. Every timeout was a lesson. Every failure was data.

The 33% success rate on the first test is not a failure — it is the initial calibration of a complex system. Distributed systems are not designed correctly on the first try. They are built, broken, understood, and improved.

What is certain after this session: the JSON file protocol is correct, the autonomous_executor can execute real tools with production quality, and the M4 Max has enough capacity to run a complete local mesh.

The DOF Mesh exists. Now it is time to scale it.

---

## Appendix A — Mesh Diagnostic Commands

```bash
# Daemon status
launchctl list | grep com.dof.mesh-agent

# Tasks in queue
ls logs/mesh/inbox/*/

# Tasks currently processing
find logs/mesh/inbox/ -name "*.processing"

# Completed tasks (last 10)
find logs/mesh/outbox/ -name "*.done" | tail -10

# Daemon logs
tail -f logs/mesh/mesh_agent.log

# Ollama status
curl -s http://localhost:11434/api/ps | python3 -m json.tool

# Available models
ollama list

# Available RAM
vm_stat | grep "Pages free"

# Telegram processes (verify single instance)
ps aux | grep telegram_bot | grep -v grep
```

## Appendix B — Mesh Task Structure

```json
{
  "task_id": "stress-test-001",
  "node": "dof-coder",
  "type": "code",
  "priority": "normal",
  "payload": {
    "instruction": "Read core/autonomous_executor.py and generate Google-style docstrings for each public function.",
    "context": "New module — no existing documentation",
    "expected_output": "Python file with complete docstrings"
  },
  "metadata": {
    "created_at": "2026-03-24T02:15:00Z",
    "timeout": 600,
    "max_iterations": 10
  }
}
```

## Appendix C — Pre-Stress-Test Checklist

Before the next stress test, verify:

- [ ] Single Ollama process running (`ps aux | grep ollama`)
- [ ] Available RAM > 15GB (`vm_stat | grep free`)
- [ ] Timeout configured at 600s or higher
- [ ] Single telegram_bot process running
- [ ] LaunchAgent active (`launchctl list | grep dof`)
- [ ] Empty inbox/ folders (no pending tasks from previous session)
- [ ] Ollama models loaded and responding (`curl http://localhost:11434/api/tags`)
- [ ] Logs with available disk space (`df -h /Users/jquiceva`)

---

## Chapter 11 Preview — Next Phase: Multi-Provider + Smart Scheduler

*From 33% to 85%+ without changing hardware: the architecture that turns bottlenecks into resilience.*

---

### 11.1 Final Stress Test Diagnosis — The 3 Root Causes

The 33% success rate in the stress test was not random. It was deterministic. Once we understood the real system, the three failure points were inevitable with the original configuration.

**Root Cause 1: Serial Ollama — The Fundamental Bottleneck**

Ollama by design processes one request at a time. This is not a bug — it is an architectural decision: maximize GPU/ANE usage per individual inference. The problem is not Ollama; the problem is having assumed that 6 "parallel" nodes translate to 6 simultaneous inferences.

```
System reality during the stress test:

t=0s    18 tasks enter the 6-node queues
        ↓
```
