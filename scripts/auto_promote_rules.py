#!/usr/bin/env python3
"""
DOF-MESH Auto-Promote Rules
─────────────────────────────────────────────────────────────────────────────
Sistema inmune autónomo: lee corrections.jsonl, detecta patrones repetidos,
promueve automáticamente a learned-rules.md.

Umbral: corrección vista 2+ veces → PROMOVER
Máximo: 50 líneas en learned-rules.md (per SKILL.md)

Uso:
    python3 scripts/auto_promote_rules.py [--dry-run]
    python3 scripts/auto_promote_rules.py --status   # ver estado sin cambios
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

CORRECTIONS_PATH  = Path(".claude/memory/corrections.jsonl")
LEARNED_RULES_PATH = Path(".claude/memory/learned-rules.md")
EVOLUTION_LOG_PATH = Path(".claude/memory/evolution-log.md")
MAX_RULES_LINES   = 50
PROMOTE_THRESHOLD = 2   # correcciones iguales para auto-promover


def load_corrections() -> list[dict]:
    if not CORRECTIONS_PATH.exists():
        return []
    entries = []
    for line in CORRECTIONS_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def load_learned_rules() -> str:
    if not LEARNED_RULES_PATH.exists():
        return "# Learned Rules — DOF-MESH\n\nMax 50 líneas.\n\n---\n\n"
    return LEARNED_RULES_PATH.read_text()


def count_rules_lines(content: str) -> int:
    return len(content.splitlines())


def rule_already_present(content: str, correction_text: str) -> bool:
    """True si ya existe una regla con texto similar."""
    # Normalizar para comparación fuzzy básica
    correction_words = set(correction_text.lower().split())
    for line in content.splitlines():
        if line.startswith("- "):
            line_words = set(line.lower().split())
            # Si comparten >50% de palabras, es duplicado
            if len(correction_words & line_words) / max(len(correction_words), 1) > 0.5:
                return True
    return False


def build_rule_entry(correction: str, verify: str, source_count: int, category: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"- {correction}"]
    if verify:
        lines.append(f"  verify: {verify}")
    lines.append(f"  [source: auto-promovido de {source_count} correcciones, {today}, cat:{category}]")
    lines.append("")
    return "\n".join(lines)


def group_corrections(corrections: list[dict]) -> dict[str, list[dict]]:
    """Agrupa correcciones por texto normalizado."""
    groups = defaultdict(list)
    for c in corrections:
        key = re.sub(r'\s+', ' ', c.get("correction", "").lower().strip())
        if key:
            groups[key].append(c)
    return groups


def append_to_evolution_log(promoted: list[dict]) -> None:
    if not promoted:
        return
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n## Auto-Promote {today}\n"]
    for p in promoted:
        lines.append(f"- PROMOVIDO: {p['correction']}")
        lines.append(f"  Fuente: {p['count']} correcciones, categoría {p['category']}")
        if p.get('verify'):
            lines.append(f"  Verify: {p['verify']}")
    lines.append("")
    with open(EVOLUTION_LOG_PATH, "a") as f:
        f.write("\n".join(lines))


def run(dry_run: bool = False, status_only: bool = False) -> None:
    corrections = load_corrections()
    learned = load_learned_rules()
    groups = group_corrections(corrections)

    candidates = []
    for key, entries in groups.items():
        if len(entries) >= PROMOTE_THRESHOLD:
            # Tomar el verify más reciente si existe
            verify = next((e.get("verify", "") for e in reversed(entries) if e.get("verify")), "")
            category = entries[-1].get("category", "general")
            # Usar la corrección más reciente (mejor redactada)
            correction = entries[-1].get("correction", key)
            candidates.append({
                "correction": correction,
                "verify": verify,
                "count": len(entries),
                "category": category,
                "key": key,
            })

    if status_only:
        print(f"\n📊 Estado Auto-Promote Rules")
        print(f"   Correcciones totales:   {len(corrections)}")
        print(f"   Grupos únicos:          {len(groups)}")
        print(f"   Candidatos (≥{PROMOTE_THRESHOLD}x):       {len(candidates)}")
        print(f"   Líneas learned-rules:   {count_rules_lines(learned)}/{MAX_RULES_LINES}")
        if candidates:
            print(f"\n   Candidatos a promover:")
            for c in candidates:
                already = rule_already_present(learned, c['correction'])
                status = "✓ ya existe" if already else "🆕 nuevo"
                print(f"   [{status}] ({c['count']}x) {c['correction'][:70]}")
        else:
            print(f"\n   ✓ Sin candidatos nuevos. Sistema limpio.")
        return

    promoted = []
    skipped_duplicate = 0
    skipped_capacity = 0

    for c in candidates:
        if rule_already_present(learned, c['correction']):
            skipped_duplicate += 1
            continue

        current_lines = count_rules_lines(learned)
        if current_lines >= MAX_RULES_LINES:
            skipped_capacity += 1
            print(f"⚠️  learned-rules.md lleno ({current_lines} líneas). Ejecuta /evolve para limpiar.")
            break

        rule_text = build_rule_entry(c['correction'], c['verify'], c['count'], c['category'])
        # Insertar antes del comentario final
        if "<!-- Máximo" in learned:
            learned = learned.replace("<!-- Máximo", rule_text + "<!-- Máximo")
        else:
            learned += "\n" + rule_text

        promoted.append(c)
        print(f"  ✅ PROMOVIDO ({c['count']}x): {c['correction'][:70]}")

    if not dry_run and promoted:
        LEARNED_RULES_PATH.write_text(learned)
        append_to_evolution_log(promoted)
        print(f"\n  {len(promoted)} regla(s) promovida(s) a learned-rules.md")
    elif dry_run and promoted:
        print(f"\n  [DRY RUN] {len(promoted)} regla(s) serían promovidas")
    elif not promoted:
        print(f"  ✓ Sin reglas nuevas que promover")

    if skipped_duplicate:
        print(f"  (omitidos {skipped_duplicate} duplicados)")
    if skipped_capacity:
        print(f"  ⚠️  omitidos {skipped_capacity} por capacidad — ejecuta /evolve")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOF-MESH Auto-Promote Rules")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir cambios")
    parser.add_argument("--status", action="store_true", help="Muestra estado sin cambios")
    args = parser.parse_args()
    run(dry_run=args.dry_run, status_only=args.status)
