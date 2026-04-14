#!/usr/bin/env python3
"""
DOF-MESH — Auditoría SECOP con persistencia local + Obsidian.

Busca contratos SECOP II, corre auditoría Z3, detecta anomalías,
y guarda resultados en:
  - logs/secop/audit_YYYYMMDD_HHMMSS.jsonl  (local, auditable)
  - Obsidian vault via second_brain.py       (segundo cerebro)

Uso:
  python3 scripts/secop_audit.py                          # Medellín default
  python3 scripts/secop_audit.py --municipio BOGOTA       # otra ciudad
  python3 scripts/secop_audit.py --entity "GOBERNACION DE ANTIOQUIA"
  python3 scripts/secop_audit.py --limit 50 --year 2025
"""
import sys
import os
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "integrations" / "datos-colombia"))

LOGS_DIR = BASE_DIR / "logs" / "secop"


def _ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _save_jsonl(records: list[dict], filepath: Path):
    with open(filepath, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def _save_to_obsidian(title: str, content: str, tags: str = "secop,auditoria,dof"):
    """Guarda nota en el segundo cerebro via second_brain.py."""
    script = BASE_DIR / "scripts" / "second_brain.py"
    if not script.exists():
        print("  ⚠️  second_brain.py no encontrado — skip Obsidian")
        return False
    try:
        result = subprocess.run(
            ["python3", str(script), "add", title,
             "--content", content, "--tags", tags],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            print("  ✅ Guardado en Obsidian")
            return True
        else:
            print(f"  ⚠️  Obsidian error: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"  ⚠️  Obsidian error: {e}")
        return False


def run_audit(municipio: str = "MEDELLIN", entity: str = None,
              year: int = None, limit: int = 20):
    from tools.secop import fetch_contracts, audit_contract, detect_anomalies

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _ensure_dirs()

    print("=" * 65)
    print(f"  DOF-MESH — Auditoría SECOP II")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} COT")
    print("=" * 65)

    # 1. Buscar contratos
    print(f"\n[1/3] BUSCAR CONTRATOS — {entity or municipio}")
    kwargs = {"limit": limit}
    if entity:
        kwargs["entity"] = entity
    else:
        kwargs["municipio"] = municipio
    if year:
        kwargs["year"] = year

    contratos = fetch_contracts(**kwargs)
    print(f"  Encontrados: {len(contratos)}")

    if not contratos:
        print("  ⚠️ Sin resultados — verifica la entidad o municipio")
        return

    total_cop = sum(float(c.get("valor_del_contrato", 0) or 0) for c in contratos)
    print(f"  Valor total: ${total_cop:,.0f} COP")

    # 2. Auditoría Z3 por contrato
    print(f"\n[2/3] AUDITORÍA Z3 — Ley 80/1993")
    audit_results = []
    aprobados = 0
    for c in contratos:
        r = audit_contract(c)
        entry = {
            "ts": ts,
            "id_contrato": c.get("id_contrato", "?"),
            "entidad": c.get("nombre_entidad", "?"),
            "objeto": (c.get("objeto_del_contrato") or c.get("descripcion_del_proceso") or "?")[:120],
            "valor": c.get("valor_del_contrato", 0),
            "proveedor": c.get("proveedor_adjudicado") or c.get("nombre_representante_legal") or "?",
            "z3_passed": r.passed,
            "z3_score": getattr(r, "score", None),
            "z3_violations": getattr(r, "violations", []),
            "proof_hash": r.proof_hash[:32] if hasattr(r, "proof_hash") else None,
        }
        audit_results.append(entry)
        if r.passed:
            aprobados += 1

    print(f"  Aprobados Z3: {aprobados}/{len(contratos)}")
    rechazados = [a for a in audit_results if not a["z3_passed"]]
    if rechazados:
        print(f"  ⚠️ Rechazados:")
        for r in rechazados[:5]:
            print(f"    • {r['id_contrato']} — {r['z3_violations']}")

    # 3. Detección de anomalías
    print(f"\n[3/3] ANOMALÍAS — Fraccionamiento Ley 80 Art. 24")
    target = entity or municipio
    anomalias = detect_anomalies(contratos, entity=target, threshold_fraccionamiento=2)
    n_frac = len(anomalias.fraccionamiento) if anomalias else 0
    n_conc = len(anomalias.concentracion) if anomalias and hasattr(anomalias, "concentracion") else 0
    print(f"  Fraccionamiento: {n_frac} alertas")
    print(f"  Concentración:   {n_conc} alertas")

    if anomalias and anomalias.fraccionamiento:
        for a in anomalias.fraccionamiento[:3]:
            print(f"    ⚠️ {a}")

    # === GUARDAR LOCAL ===
    logfile = LOGS_DIR / f"audit_{ts}.jsonl"
    _save_jsonl(audit_results, logfile)
    print(f"\n📁 Local: {logfile}")

    # Guardar resumen
    summary = {
        "ts": ts,
        "query": {"municipio": municipio, "entity": entity, "year": year, "limit": limit},
        "total_contratos": len(contratos),
        "valor_total_cop": total_cop,
        "z3_aprobados": aprobados,
        "z3_rechazados": len(contratos) - aprobados,
        "anomalias_fraccionamiento": n_frac,
        "anomalias_concentracion": n_conc,
    }
    summary_file = LOGS_DIR / f"summary_{ts}.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"📁 Resumen: {summary_file}")

    # === GUARDAR OBSIDIAN ===
    obs_title = f"Auditoría SECOP — {target} — {datetime.now().strftime('%Y-%m-%d')}"
    obs_lines = [
        f"# {obs_title}",
        f"",
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')} COT",
        f"**Fuente:** datos.gov.co (SECOP II en vivo)",
        f"**Motor:** DOF-MESH Z3 + Ley 80/1993",
        f"",
        f"## Resultados",
        f"- Contratos analizados: **{len(contratos)}**",
        f"- Valor total: **${total_cop:,.0f} COP**",
        f"- Z3 aprobados: **{aprobados}/{len(contratos)}**",
        f"- Anomalías fraccionamiento: **{n_frac}**",
        f"- Anomalías concentración: **{n_conc}**",
        f"",
    ]

    if rechazados:
        obs_lines.append("## Contratos rechazados por Z3")
        for r in rechazados[:10]:
            obs_lines.append(f"- `{r['id_contrato']}` — {r['objeto'][:60]} — violaciones: {r['z3_violations']}")
        obs_lines.append("")

    if anomalias and anomalias.fraccionamiento:
        obs_lines.append("## Alertas de fraccionamiento")
        for a in anomalias.fraccionamiento[:10]:
            obs_lines.append(f"- ⚠️ {a}")
        obs_lines.append("")

    obs_lines.append(f"## Archivos")
    obs_lines.append(f"- Local: `{logfile}`")
    obs_lines.append(f"- Resumen: `{summary_file}`")

    obs_content = "\n".join(obs_lines)
    _save_to_obsidian(obs_title, obs_content, "secop,auditoria,dof,ley80,z3")

    print("\n" + "=" * 65)
    print("  Auditoría completa")
    print("=" * 65)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOF-MESH — Auditoría SECOP II")
    parser.add_argument("--municipio", default="MEDELLIN", help="Municipio a buscar")
    parser.add_argument("--entity", default=None, help="Entidad específica")
    parser.add_argument("--year", type=int, default=None, help="Año de firma")
    parser.add_argument("--limit", type=int, default=20, help="Máximo contratos")
    args = parser.parse_args()

    run_audit(
        municipio=args.municipio,
        entity=args.entity,
        year=args.year,
        limit=args.limit,
    )
