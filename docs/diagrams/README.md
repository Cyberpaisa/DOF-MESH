# DOF Architecture Diagrams

> v1.2 — Execution DAG + Loop Guard + 7 Governance Layers

## Diagrams

| File | Description |
|------|-------------|
| 01_dof_v12_architecture.mmd | Complete system architecture with all components |
| 02_dof_v12_pipeline.mmd | Internal governance pipeline with decision gates |
| 03_10_round_sequence.mmd | 10-round agent cross-transaction sequence |
| 04_attestation_lifecycle.mmd | Attestation lifecycle state machine |
| 05_single_round_deep_dive.mmd | Single round detailed breakdown (6 phases) |
| 06_execution_timeline.mmd | Gantt chart of 10-round execution timing |

## Rendering

Open `render.html` in any browser to view all diagrams rendered with dark theme.

Or use Mermaid CLI:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i 01_dof_v12_architecture.mmd -o architecture.svg
```

## Color Legend

| Color | Hex | Meaning |
|-------|-----|---------|
| Blue | #2196F3 | Agents, transfers |
| Green | #4CAF50 | Governance, verification |
| Orange | #FF9800 | Supervisor, Loop Guard |
| Cyan | #00BCD4 | Z3 proofs, Centinela |
| Red | #EF5350 | Blockchain, adversarial |
| Purple | #7E57C2 | Memory, Merkle |
| Deep Orange | #FF5722 | Execution DAG |
