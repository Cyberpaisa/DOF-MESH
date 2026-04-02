# _index — Estado del Sistema DOF-MESH
*Auto-actualizado por Kernel Boot + Sovereign Hardening Phase 4 | 2026-04-01*

## ⚡ Phase 4: Sovereign Hardening — ACTIVADO (2026-04-01)

### Cambios Arquitectónicos Críticos
| Componente | Cambio | Archivo |
|---|---|---|
| **Ollama Runtime** | Añadido como Priority-0 en auto-detección de runtime | `core/local_model_node.py` |
| **OllamaEngine** | Nueva clase de inferencia OpenAI-compatible (localhost:11434) | `core/local_model_node.py` |
| **Global Evaluator** | Reescrito Agent-First CLI: `--json`, `--env`, exit codes 0/1/2/3, Hints | `scripts/execute_global_evaluator.py` |
| **Hardening Index** | Reescrito con stack soberano completo + veto OpenClaude/Glassworm | `docs/06_security/HARDENING_INDEX.md` |
| **AGENTS.md §6** | Estándar Agent-First CLI + Ollama como fallback soberano oficial | `AGENTS.md` |

### Stack Soberano Phase 4.6
```
[Agente / Claude Code / Humano]
          ↓  --json ó NO_COLOR=1 ó TTY-detection
[DOF-MESH scripts/ — Agent-First CLI]
          ↓  requests.post()
[Ollama localhost:11434/api]  ← Priority-0 runtime (Apple/GPU)
          ↓
[Llama 3.2 3B / Qwen 2.5 Coder]
```

### Reglas Agent-First CLI (obligatorias en todos los scripts nuevos)
- `--json` → NDJSON puro para agentes/pipes
- `NO_COLOR=1` auto-detectado → sin colores ANSI
- Exit codes: `0`=ok · `1`=error · `2`=bad flags · `3`=auth failure
- `Hint:` en cada excepción para auto-corrección de agentes
- Payloads ocultos por defecto; `--verbose` = opt-in explícito

### Cómo usar Ollama con el MESH
```bash
# 1. Inicia Ollama Server
# 2. El MESH lo detecta automáticamente como Priority-0

# Verificar detección
python3 core/local_model_node.py --detect --json

# Correr evaluador contra Ollama
python3 scripts/execute_global_evaluator.py --env local --json
```

### VETADO (Supply Chain / Glassworm)
- **OpenClaude** y cualquier herramienta basada en source leaks via npm no-pinned
- Ver: `docs/06_security/HARDENING_INDEX.md` § Invariantes de No-Ruptura

---

## DOF Status (2026-03-06 → actualizado 2026-04-01)
- **Tests:** 719/719 passing (3.9s)
- **LOC:** 51,000+ across 138 módulos
- **Z3:** 4/4 theorems verified
- **Governance:** 7 capas activas (Constitution, AST, Supervisor, Adversarial, Memory, Z3, Oracle)
- **Runtimes locales:** Ollama (P0) > MLX (P1) > llama.cpp (P2)

## On-Chain Status
- **Attestations:** 21 on Avalanche C-Chain mainnet
- **Contract:** DOFValidationRegistry at 0x88f6...C052
- **Agents:** #1687 (Apex, 0.85 trust), #1686 (AvaBuilder, 0.85 trust)

## Enigma Status
- **dof_trust_scores:** 24 rows
- **combined_trust_view:** both agents COMPLIANT

## Últimas Ejecuciones
- `2026-04-02T05:20` | phase5-moe | success | Implementación Mixture of Agents (dof-coder, dof-reasoner, dof-guardian)
- `2026-04-01T23:00` | phase4.6-hardening | success | Ollama+AgentFirstCLI integrated (Purged oMLX)
- `2026-03-02T12:54` | research | success | 48.6s

## Documentación de Referencia
- Arquitectura: `docs/01_architecture/`
- Seguridad: `docs/06_security/HARDENING_INDEX.md`
- Constitución: `AGENTS.md`
- Evaluador: `scripts/execute_global_evaluator.py --help`
