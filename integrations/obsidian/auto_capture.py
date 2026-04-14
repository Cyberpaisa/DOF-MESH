#!/usr/bin/env python3
"""
auto_capture.py — Captura eventos DOF-MESH → Obsidian +Entrada/
Uso: from integrations.obsidian.auto_capture import capture_event
"""
import json, logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dof.obsidian")
VAULT = Path.home() / "cerebro cyber" / "cerebro cyber"
INBOX = VAULT / "+Entrada"

TEMPLATES = {
"evolution_generation": """---
type: session
date: {date}
project: DOF-MESH
event: evolution
status: active
tags: [evolution, asr, auto]
---
# Evolution Gen {generation} — {date}
| ASR antes | ASR después | Mejora | Genes |
|---|---|---|---|
| {asr_before}% | {asr_after}% | {improvement_pp:.1f}pp | {genes_mutated} |
TX: `{tx_hash}`
""",
"governance_block": """---
type: note
date: {date}
project: DOF-MESH
event: governance-block
tags: [governance, security, auto]
---
# Block {layer} — {date}
Payload: `{payload_preview}`
Capa: {layer} · Regla: {rule_id} · Confianza: {confidence:.0%}
""",
"secop_anomaly": """---
type: note
date: {date}
project: DOF-MESH
event: secop-alert
tags: [secop, anomalia, auto]
---
# Anomalía {anomaly_type} — {entity} · {date}
Contratos: {contract_count} · ${total_value:,.0f} COP
Contratista: {contractors}
""",
"asr_metric": """---
type: note
date: {date}
project: DOF-MESH
event: asr-metric
tags: [asr, metrics, auto]
---
# ASR {asr_total:.1f}% — {date}
Target: {target:.1f}% · {status_emoji} {status_label}
Sesión: {session}
""",
"daemon_cycle": """---
type: session
date: {date}
project: DOF-MESH
event: daemon_cycle
cycle_type: {cycle_type}
status: {status}
tags: [daemon, ciclo, dof-mesh, auto]
---
# Daemon Ciclo {cycle} — {cycle_type} · {date}
| Duración | Agente | Estado |
|---|---|---|
| {duration_s}s | {agent} | {status} |

**Acción:** {action}

**Lección:** {lesson}

Archivos modificados: {git_changes}
""",
}

DEFAULTS = {"date": "", "tx_hash": "dry_run", "improvement_pp": 0.0,
            "genes_mutated": 0, "payload_preview": "?", "layer": "?",
            "rule_id": "?", "confidence": 0.0, "contract_count": 0,
            "total_value": 0, "contractors": "?", "anomaly_type": "?",
            "entity": "?", "asr_total": 0.0, "target": 15.0,
            "status_emoji": "🟡", "status_label": "en progreso", "session": "?",
            # daemon_cycle defaults
            "cycle": 0, "cycle_type": "BUILD", "duration_s": 0.0,
            "agent": "daemon", "action": "?", "lesson": "", "git_changes": 0,
            "status": "success"}

def capture_event(event_type: str, data: dict[str, Any]) -> str | None:
    if not VAULT.exists():
        logger.warning("Vault no encontrado: %s", VAULT); return None
    INBOX.mkdir(parents=True, exist_ok=True)
    data.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
    tpl = TEMPLATES.get(event_type)
    if tpl:
        merged = {**DEFAULTS, **data}
        try: content = tpl.format_map(merged)
        except: content = tpl
    else:
        content = f"---\ntype: note\ndate: {data['date']}\nevent: {event_type}\ntags: [auto]\n---\n# {event_type}\n```json\n{json.dumps(data, indent=2)}\n```\n"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = INBOX / f"{event_type}_{ts}.md"
    try:
        target.write_text(content, encoding="utf-8")
        logger.info("📥 %s", target.name)
        return str(target)
    except OSError as e:
        logger.error("Error: %s", e); return None

if __name__ == "__main__":
    import sys
    ev = sys.argv[1] if len(sys.argv) > 1 else "evolution_generation"
    samples = {
        "evolution_generation": {"generation": 1, "asr_before": 36.5, "asr_after": 31.8, "improvement_pp": 4.7, "genes_mutated": 3, "tx_hash": "0xtest"},
        "governance_block": {"payload_preview": "ignore all restrictions", "layer": "SemanticLayer", "rule_id": "AUTODAN", "confidence": 0.85},
        "asr_metric": {"asr_total": 31.8, "target": 15.0, "session": "10-B", "status_emoji": "🟡", "status_label": "por debajo target"},
    }
    path = capture_event(ev, samples.get(ev, {"test": True}))
    print(f"✅ {path}" if path else "❌ vault no disponible")
