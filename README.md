# DOF — Sovereign Agent Mesh
> **v0.5.0** · Phase 5 Autonomous Operations · Medellín, Colombia 🛡️

**DOF (Deterministic Observability Framework)** is a sovereign multi-LLM agent mesh. It routes tasks across 8+ AI providers, enforces deterministic governance (Z3 proofs), and executes financial strategies (SAM Engine) with zero cloud dependencies.

---

## ⚡ Quick Start: Zero to Sovereign in 2 Lines

Deployment is optimized for **Phase 5 (Autonomous Operations)**.

### 📥 1. Minimal Installation
```bash
git clone https://github.com/jquiceva/equipo-de-agentes.git && cd equipo-de-agentes
cp .env.example .env && docker-compose up -d --build
```
> [!TIP]
> **Citadel Mode:** Running via Docker ensures your code is **READ-ONLY**, preventing autonomous agents from self-modifying or persisting unauthorized changes.

### 🛡️ 2. The Power of One-Liner (Python SDK)
Integrate state-of-the-art AI security and governance into any app with a single line:

```python
from dof.quick import verify; print(verify("AI Output content here"))
```
*This line instantly triggers 7 layers of security checking against the Mesh Constitution.*

---

## 💎 Phase 5 Operational Modules

| Feature | Description | Status |
|---------|-------------|--------|
| **SAM Yield Engine** | Autonomous yield farming on Avalanche & Conflux | ✅ LIVE |
| **Effort Levels** | Dynamic reasoning depth (Low → Max/R1) | ✅ LIVE |
| **MeshGuardian** | Deterministic Z3 governance enforcer | ✅ PROVEN |
| **Sovereign Vault** | Zero-dependency, air-gapped memory | ✅ ACTIVE |

---

## 🛠️ Minimal Usage

### Run the Swarm (Multi-Model)
```bash
# Wake up the API providers (Cerebras, DeepSeek, SambaNova, etc.)
python3 core/api_node_runner.py --daemon

# Start the Autonomous Planner (scans repo, dispatches work)
python3 core/autonomous_planner.py --interval 60
```

### Integrated Dashboard
```bash
# Launch the Mission Control Panel (SAM Yield Engine + Health)
streamlit run interfaces/streamlit_dashboard.py
```

---

## 📖 Resource Index

*   **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Full module map, 7-layer security stack, and system design.
*   **[AGENTS.md](AGENTS.md)**: The Sovereign Team Constitution (Immutable Rules).
*   **[SECURITY.md](SECURITY.md)**: Hardening guides and threat models.
*   **[SAM_ENGINE.md](docs/SAM_ENGINE.md)**: Financial operations and yield strategies.

### Author
**Juan Carlos Quiceno Vasquez**
*Building the first deterministic multi-model AGI mesh. Legion never sleeps.*
