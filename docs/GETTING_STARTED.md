# Getting Started with DOF

## 30-Second Start (no API keys needed)

```bash
pip install -e .
python -c "from dof import GenericAdapter; print(GenericAdapter().wrap_output('Hello world'))"
```

## 5-Minute Start

### Install

```bash
git clone https://github.com/Cyberpaisa/deterministic-observability-framework.git
cd deterministic-observability-framework
pip install -e .
```

### Verify governance on any text

```python
from dof import GenericAdapter

adapter = GenericAdapter()

# Check any LLM output
result = adapter.wrap_output("Your agent's output here")
print(result)  # {status: "pass", score: 8.2, violations: []}

# Check generated code
result = adapter.wrap_code("print('hello')")
print(result)  # {score: 1.0, violations: []}
```

### Run Z3 formal proofs

```python
from dof import verify
results = verify()
print(results)  # 4 theorems VERIFIED
```

### Run full quickstart

```bash
python examples/quickstart.py       # Governance + Z3 + metrics
python examples/generic_example.py  # Framework-agnostic adapter
```

## Optional: Add LLM Providers

```bash
cp .env.example .env
# Edit .env — minimum: GROQ_API_KEY (free at console.groq.com)
python main.py  # Full interactive menu with 25 options
```

## Optional: MCP Server (Claude Desktop / Cursor)

```bash
python mcp_server.py
# Add to Claude Desktop config — see docs/MCP_SETUP.md
```

## Optional: REST API

```bash
pip install -e ".[api]"
python -m api.server
# API at http://localhost:8080, docs at http://localhost:8080/docs
```

## Optional: PostgreSQL (production)

```bash
pip install -e ".[db]"
# Add to .env: DOF_DATABASE_URL=postgresql://...
# Supports Supabase, Neon, or any PostgreSQL
```

## What DOF Does

DOF is a governance verification system for AI agents. It proves mathematically (Z3 SMT solver) that governance compliance is an architectural invariant. See README.md for the full technical paper.

No API keys needed for governance verification, Z3 proofs, AST analysis, and memory operations.
