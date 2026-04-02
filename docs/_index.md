# _index — Estado del Sistema DOF-MESH
*Auto-actualizado por Kernel Boot + Sovereign Hardening Phase 4 | 2026-04-01*

## ⚡ Phase 4: Sovereign Hardening — ACTIVADO (2026-04-01)

### Cambios Arquitectónicos Críticos
| Componente | Cambio | Archivo |
|---|---|---|
| **oMLX Runtime** | Añadido como Priority-0 en auto-detección de runtime | `core/local_model_node.py` |
| **OMLXEngine** | Nueva clase de inferencia OpenAI-compatible (localhost:8080) | `core/local_model_node.py` |
| **Global Evaluator** | Reescrito Agent-First CLI: `--json`, `--env`, exit codes 0/1/2/3, Hints | `scripts/execute_global_evaluator.py` |
| **Hardening Index** | Reescrito con stack soberano completo + veto OpenClaude/Glassworm | `docs/06_security/HARDENING_INDEX.md` |
| **AGENTS.md §6** | Estándar Agent-First CLI + oMLX como fallback soberano oficial | `AGENTS.md` |

### Stack Soberano Phase 4
```
[Agente / Claude Code / Humano]
          ↓  --json ó NO_COLOR=1 ó TTY-detection
[DOF-MESH scripts/ — Agent-First CLI]
          ↓  requests.post()
[oMLX localhost:8080/v1]  ← Priority-0 runtime (Apple Silicon)
          ↓
[Llama 3.3 70B / DeepSeek R1 en MLX — KV Tiering RAM+SSD]
```

### Reglas Agent-First CLI (obligatorias en todos los scripts nuevos)
- `--json` → NDJSON puro para agentes/pipes
- `NO_COLOR=1` auto-detectado → sin colores ANSI
- Exit codes: `0`=ok · `1`=error · `2`=bad flags · `3`=auth failure
- `Hint:` en cada excepción para auto-corrección de agentes
- Payloads ocultos por defecto; `--verbose` = opt-in explícito

### Cómo usar oMLX con el MESH
```bash
# 1. Inicia oMLX desde la barra de menú de tu Mac
# 2. Descarga llama3.3-70b desde localhost:8080
# 3. El MESH lo detecta automáticamente como Priority-0

# Verificar detección
python3 core/local_model_node.py --detect --json

# Correr evaluador contra oMLX
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
- **Runtimes locales:** oMLX (P0) > MLX (P1) > Ollama (P2) > llama.cpp (P3)

## On-Chain Status
- **Attestations:** 21 on Avalanche C-Chain mainnet
- **Contract:** DOFValidationRegistry at 0x88f6...C052
- **Agents:** #1687 (Apex, 0.85 trust), #1686 (AvaBuilder, 0.85 trust)

## Enigma Status
- **dof_trust_scores:** 24 rows
- **combined_trust_view:** both agents COMPLIANT

## Últimas Ejecuciones
- `2026-04-01T15:50` | phase4-hardening | success | oMLX+AgentFirstCLI integrated
- `2026-03-02T12:54` | research | success | 48.6s

## Documentación de Referencia
- Arquitectura: `docs/01_architecture/`
- Seguridad: `docs/06_security/HARDENING_INDEX.md`
- Constitución: `AGENTS.md`
- Evaluador: `scripts/execute_global_evaluator.py --help`
