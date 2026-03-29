#!/usr/bin/env python3
"""
save_evidence.py — Captura obligatoria de aprendizajes, experimentos y pruebas.

Uso:
    python3 scripts/save_evidence.py experiment "Winston v5" --delta "+26.1%" --models 10
    python3 scripts/save_evidence.py test "test_z3_gate" --result PASS --count 42
    python3 scripts/save_evidence.py learning "TurboQuant" --note "6x KV cache con q4_0"
    python3 scripts/save_evidence.py session --auto   # captura estado del repo automáticamente

Genera docs/EVIDENCE_<fecha>_<tipo>.md y actualiza docs/EVIDENCE_INDEX.md.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
EVIDENCE_DIR = ROOT / "docs" / "evidence"
INDEX_FILE = ROOT / "docs" / "EVIDENCE_INDEX.md"


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            f"git -C {ROOT} {cmd}", shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""


def slug(text: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text.lower())[:40]


def write_evidence(kind: str, title: str, body: str, metadata: dict) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{kind}_{slug(title)}.md"
    path = EVIDENCE_DIR / filename

    commit = git("rev-parse --short HEAD")
    author = git("config user.name")

    content = f"""---
type: {kind}
title: {title}
date: {date}
commit: {commit}
author: {author}
---

# {title}

{body}

## Metadata

```json
{json.dumps(metadata, indent=2, ensure_ascii=False)}
```

## Contexto del repositorio

- Commit: `{commit}`
- Rama: `{git("symbolic-ref --short HEAD")}`
- Tests: `{git("ls-files tests/ | wc -l").strip()} archivos`
- Fecha: {datetime.now().isoformat()}
"""
    path.write_text(content)
    return path


def update_index(path: Path, kind: str, title: str):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(ROOT)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{title}]({rel}) — {kind} · {date}\n"

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("# Evidence Index\n\nRegistro de aprendizajes, experimentos y pruebas.\n\n")

    content = INDEX_FILE.read_text()
    # Insert after the header
    lines = content.split("\n")
    insert_at = 4
    lines.insert(insert_at, entry.rstrip())
    INDEX_FILE.write_text("\n".join(lines))


def cmd_experiment(args):
    metadata = {
        "delta": args.delta,
        "models": args.models,
        "scorer": args.scorer or "deterministic",
        "dataset": args.dataset or "unknown",
    }
    body = f"""## Resultados

| Métrica | Valor |
|---------|-------|
| Delta promedio | {args.delta or "N/A"} |
| Modelos evaluados | {args.models or "N/A"} |
| Scorer | {args.scorer or "deterministic (0 LLMs)"} |
| Dataset | {args.dataset or "N/A"} |

## Descripción

{args.note or "(sin descripción — agrega con --note)"}

## Cómo reproducir

```bash
# Agrega los comandos para reproducir este experimento
```

## Conclusiones

- (documenta los aprendizajes clave)
"""
    path = write_evidence("experiment", args.title, body, metadata)
    update_index(path, "experiment", args.title)
    print(f"✓ Experimento guardado: {path.relative_to(ROOT)}")


def cmd_test(args):
    metadata = {
        "result": args.result,
        "count": args.count,
        "module": args.module or "unknown",
    }
    body = f"""## Resultado de prueba

| Campo | Valor |
|-------|-------|
| Resultado | **{args.result or "N/A"}** |
| Tests ejecutados | {args.count or "N/A"} |
| Módulo | {args.module or "N/A"} |

## Evidencia

{args.note or "(sin evidencia adicional — agrega con --note)"}

## Comando

```bash
python3 -m unittest {args.module or "discover -s tests"}
```
"""
    path = write_evidence("test", args.title, body, metadata)
    update_index(path, "test", args.title)
    print(f"✓ Evidencia de test guardada: {path.relative_to(ROOT)}")


def cmd_learning(args):
    metadata = {"tags": args.tags or []}
    body = f"""## Aprendizaje

{args.note or "(sin descripción)"}

## Por qué importa

{args.why or "(documenta por qué esto es relevante para el proyecto)"}

## Cómo aplicar

{args.how or "(documenta cómo aplicar este aprendizaje en el futuro)"}
"""
    path = write_evidence("learning", args.title, body, metadata)
    update_index(path, "learning", args.title)
    print(f"✓ Aprendizaje guardado: {path.relative_to(ROOT)}")


def cmd_session(args):
    """Captura automática del estado del repo como evidencia de sesión."""
    now = datetime.now()
    title = f"Session {now.strftime('%Y-%m-%d %H:%M')}"

    # Auto-recolectar stats del repo
    core_count = len(list((ROOT / "core").glob("*.py"))) if (ROOT / "core").exists() else 0
    test_count = len(list((ROOT / "tests").glob("test_*.py"))) if (ROOT / "tests").exists() else 0
    recent_commits = git("log --oneline -10")
    modified = git("status --short")

    metadata = {
        "core_modules": core_count,
        "test_files": test_count,
        "commit": git("rev-parse --short HEAD"),
    }
    body = f"""## Estado del repositorio

| Métrica | Valor |
|---------|-------|
| Core modules | {core_count} |
| Test files | {test_count} |
| Commit | `{git("rev-parse --short HEAD")}` |
| Rama | `{git("symbolic-ref --short HEAD")}` |

## Últimos 10 commits

```
{recent_commits}
```

## Archivos modificados (sin commitear)

```
{modified or "(ninguno — todo commiteado)"}
```

## Notas de sesión

{args.note or "(sin notas — agrega con --note)"}
"""
    path = write_evidence("session", title, body, metadata)
    update_index(path, "session", title)
    print(f"✓ Estado de sesión guardado: {path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Captura evidencia de aprendizajes y experimentos")
    sub = parser.add_subparsers(dest="cmd")

    # experiment
    p_exp = sub.add_parser("experiment", help="Documenta un experimento")
    p_exp.add_argument("title")
    p_exp.add_argument("--delta", help="Mejora medida (ej: +26.1%%)")
    p_exp.add_argument("--models", type=int, help="Número de modelos evaluados")
    p_exp.add_argument("--scorer", help="Tipo de scorer usado")
    p_exp.add_argument("--dataset", help="Dataset usado")
    p_exp.add_argument("--note", help="Descripción libre")

    # test
    p_test = sub.add_parser("test", help="Documenta evidencia de tests")
    p_test.add_argument("title")
    p_test.add_argument("--result", help="PASS / FAIL / PARTIAL")
    p_test.add_argument("--count", type=int, help="Número de tests ejecutados")
    p_test.add_argument("--module", help="Módulo testeado")
    p_test.add_argument("--note", help="Evidencia adicional")

    # learning
    p_learn = sub.add_parser("learning", help="Documenta un aprendizaje")
    p_learn.add_argument("title")
    p_learn.add_argument("--note", help="Descripción del aprendizaje")
    p_learn.add_argument("--why", help="Por qué importa")
    p_learn.add_argument("--how", help="Cómo aplicar")
    p_learn.add_argument("--tags", nargs="*", help="Tags")

    # session
    p_sess = sub.add_parser("session", help="Captura estado de la sesión actual")
    p_sess.add_argument("--auto", action="store_true", help="Captura automática")
    p_sess.add_argument("--note", help="Notas de la sesión")

    args = parser.parse_args()

    if args.cmd == "experiment":
        cmd_experiment(args)
    elif args.cmd == "test":
        cmd_test(args)
    elif args.cmd == "learning":
        cmd_learning(args)
    elif args.cmd == "session":
        cmd_session(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
