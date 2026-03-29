# DOF Mesh Phase 9: Autonomous Scaling Architecture

## 1. Vision: What Phase 9 Is and Why It Is Needed

The **Deterministic Observability Framework (DOF)** has evolved from a singular agent to a robust heterogeneous mesh capable of orchestrating 11 concurrent P2P nodes: from purely free local LLMs (`local-qwen`, `local-agi-m4max`) to specialized cloud cognitive powerhouses (`deepseek-coder`, `hermes-405b`, `cerebras-llama`, `sambanova-llama`, `nvidia-nim`, etc.). Up to Phase 8, this communication was grounded in an infallible asynchronous protocol through a *file system JSONL* (`logs/mesh/inbox/{node_id}/*.json`) managed by `api_node_runner.py` without concurrency vulnerabilities.

However, as the mesh dynamically scales against unpredictable task volumes, manually delegating responsibility to local and remote nodes becomes the bottleneck. This is where **Phase 9: Autonomous Scaling** comes in.

**Why is it needed?**
Phase 9 transforms DOF Mesh from a *passive* cluster to a *self-regulated* organism. We no longer depend on a human (nor a static Commander) to start, suspend, or reassign nodes. By infusing a layer of **autonomous scaling based on telemetric observability (cost, latency, and health)**, the Mesh can react to peak loads by spinning up fast nodes (Cerebras, Groq) and reducing costs by dispatching complex tasks without immediate SLA to local hardware (Ollama). In short, it guarantees massive throughput while minimizing the cloud bill to zero during idle cycles.

---

## 2. New Architectural Components

To achieve purely deterministic scaling without ghost agents, we introduce three key components that will operate as in-memory singletons.

### 2.1 MeshOrchestrator
It is the "central nervous system" of the auto-scaling layer. It perpetually listens to network queues (Inbox) and dispatches tasks based on the vector analysis proposed by the other components. Its mission is to ensure that no task suffers more delay than stipulated (SLA) nor gets sent to a "comatose" (dead_node) node.

### 2.2 AutoProvisioner
It is the "muscle engine". Capable of starting underlying processes, registering new `node_ids` in `logs/mesh/nodes.json` with specific metadata, or, in the worst case, hibernating/killing nodes that are not contributing value. It works by creating demand snapshots and spinning up the necessary adapter (`api_node_runner.py` or local LLM daemon) to cover that peak.

### 2.3 CostOptimizer
The "financial auditor". Contains the static price matrix (e.g. `$0.27/M TOKENS` for DeepSeek Coder, `$0.0` for Local Qwen). For each incoming task, the MeshOrchestrator consults this module for which node to use according to the budget limits and context window required by the task.

---

## 3. Automatic Scaling Algorithm (Autoscaling)

The Mesh control loop operates on a **Multivector Hysteresis Algorithm** to avoid "flapping" (starting and killing processes very rapidly).

1. **State Collection:** At each instant the queue depth ($Q_D$), average latency ($L_{avg}$), and spend ($C_{ac}$) are calculated.
2. **Weighted Demand Calculation:** The variable $D_{net} = w_1 \cdot Q_D + w_2 \cdot (L_{avg} / SLA)$ is calculated.
3. **Scale-Out Decision:** If $D_{net} > Threshold_{high}$, the *MeshOrchestrator* invokes the *CostOptimizer* to decide the ideal node, and orders the *AutoProvisioner* to wake new cloud nodes.
4. **Scale-In Decision:** If $D_{net} < Threshold_{low}$, expensive Cloud nodes without assigned tasks receive a signal and are suspended, delegating everything to local hardware.

---

## 4. Hybrid Multi-Model Integration (Providers)

Scaling is segmented by native hardware Tiers and Cloud:

- **Tier 0 (Free Sovereign Compute):** Nodes `local-qwen` and `local-agi-m4max`. Constant base.
- **Tier 1 (Ultra Fast Cerebras / Sambanova / Groq):** Deployed instantly during fast inference peaks.
- **Tier 2 (DeepSeek / Minimax / GLM-5):** Base nodes for programming and multilingual structured reasoning.
- **Tier 3 (Heavy Reasoning NVIDIA / Hermes 405B / Gemini):** Only provisioned when a request requires deep semantics with large context (128k+) or extreme analysis.

---

## 5. Decision Metrics (Mesh Vectorization)

- **Latency:** Time it takes a task from the *queued* state to *completed*.
- **Cost:** Actively tracked variable summing incoming and outgoing tokens.
- **Task Queue Depth:** Absolute number of pending files in P2P inboxes.
- **Health Score:** Observability metric. Penalized by errors, excessive latencies, or Timeouts.

---

## 6. Core Pseudocode (Python 3.13)

```python
import os
import json
import time
from dataclasses import dataclass
from pathlib import Path

MESH_INBOX = Path("logs/mesh/inbox")
NODES_CONF = Path("logs/mesh/nodes.json")

@dataclass
class CostOptimizer:
    def get_cheapest_node(self, cx: int) -> str:
        # Returns the id of the most cost-efficient node based on context
        return "local-qwen"

@dataclass
class AutoProvisioner:
    opt: CostOptimizer
    def spawn(self, provider: str, role: str) -> str:
        node_id = f"auto-{provider}-{int(time.time())}"
        # ... logic to insert to nodes.json ...
        os.system(f"python3 core/api_node_runner.py --node {node_id} &")
        return node_id
    def kill(self, node_id: str):
        pass # kill the process

@dataclass
class MeshOrchestrator:
    prov: AutoProvisioner
    def evaluate(self):
        q_depth = sum(1 for _ in MESH_INBOX.glob("**/*.json"))
        if q_depth > 50:
            target = self.prov.opt.get_cheapest_node(32000)
            self.prov.spawn(target, "worker")
        elif q_depth == 0:
            pass # Scale in

if __name__ == "__main__":
    opt = CostOptimizer()
    orc = MeshOrchestrator(AutoProvisioner(opt))
    while True:
        orc.evaluate()
        time.sleep(5)
```

---

## 7. Implementation Timeline (4 Weeks)

- **Week 1:** CostOptimizer and Financial Telemetry (price table and tokens).
- **Week 2:** MeshOrchestrator and Queue Depth parser from the OS.
- **Week 3:** AutoProvisioner, dynamic subprocess management, and Garbage Collection.
- **Week 4:** Massive A/B Testing under heavy load, verifying 0 regressions across the 2900 concurrent tests.
