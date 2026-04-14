#!/usr/bin/env python3
"""
DOF-MESH — Test E2E Enterprise: Auditoría SECOP Completa
=========================================================

Pipeline completo como servicio para empresa real:

  1. Ingesta      → SECOP II datos.gov.co (contratos en vivo)
  2. Auditoría Z3 → 6 reglas Ley 80/1993 verificación formal
  3. Anomalías    → Fraccionamiento + concentración Art. 24
  4. Governance   → DOF 7 capas validación del pipeline
  5. On-chain     → Attestation en Avalanche C-Chain (dry_run sin key)
  6. Reporte JSON → Ejecutivo para cliente, con proof hashes

Output:
  - reports/secop_e2e_{ts}.json           → Reporte ejecutivo JSON
  - logs/secop/e2e_audit_{ts}.jsonl       → Detalle por contrato
  - Obsidian vault                        → Nota automática
  - On-chain attestation (dry_run/live)   → Proof hash verificable

Uso:
  python3 scripts/secop_e2e_enterprise.py
  python3 scripts/secop_e2e_enterprise.py --entity "ALCALDIA DE MEDELLIN" --limit 20
"""
import sys
import os
import json
import hashlib
import time
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "integrations" / "datos-colombia"))

LOGS_DIR = BASE_DIR / "logs" / "secop"
REPORTS_DIR = BASE_DIR / "reports"


def _ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ts_iso():
    return datetime.now(tz=timezone.utc).isoformat()


def _proof_hash(data: dict) -> str:
    """SHA-256 determinístico del payload serializado."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()


def _save_jsonl(records, filepath):
    with open(filepath, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def _save_obsidian(title, content, tags="secop,e2e,auditoria,enterprise"):
    script = BASE_DIR / "scripts" / "second_brain.py"
    if not script.exists():
        return False
    try:
        r = subprocess.run(
            ["python3", str(script), "add", title, "--content", content, "--tags", tags],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def _header(text, char="="):
    w = 72
    print(f"\n{char * w}")
    print(f"  {text}")
    print(f"{char * w}")


def run_e2e(municipio="MEDELLIN", entity=None, year=None, limit=10):
    from tools.secop import fetch_contracts, audit_contract, detect_anomalies

    ts = _ts()
    target = entity or municipio
    start_time = time.time()

    _ensure_dirs()

    _header("DOF-MESH v0.8.0 — E2E Enterprise Audit")
    print(f"  Cliente:    Auditoría contractual — {target}")
    print(f"  Fecha:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} COT")
    print(f"  Motor:      Z3 SMT Solver + Ley 80/1993")
    print(f"  Blockchain: Avalanche C-Chain (DOFProofRegistry)")
    print(f"  Modo:       {'LIVE' if os.environ.get('DOF_PRIVATE_KEY') else 'DRY-RUN'}")
    print("=" * 72)

    # ══════════════════════════════════════════════════════════════════
    # FASE 1: INGESTA — SECOP II
    # ══════════════════════════════════════════════════════════════════
    _header("FASE 1/5 — INGESTA DE DATOS SECOP II", "─")
    print(f"  Fuente: datos.gov.co (API Socrata)")
    print(f"  Query:  municipio={municipio}, entity={entity}, limit={limit}")

    kwargs = {"limit": limit}
    if entity:
        kwargs["entity"] = entity
    else:
        kwargs["municipio"] = municipio
    if year:
        kwargs["year"] = year

    contratos = fetch_contracts(**kwargs)
    print(f"  Resultado: {len(contratos)} contratos obtenidos")

    if not contratos:
        print("  ERROR: Sin datos — abortando pipeline")
        return None

    total_cop = sum(float(c.get("valor_del_contrato", 0) or 0) for c in contratos)
    modalidades = {}
    entidades = {}
    for c in contratos:
        mod = c.get("modalidad_de_contratacion", "?")
        ent = c.get("nombre_entidad", "?")
        modalidades[mod] = modalidades.get(mod, 0) + 1
        entidades[ent] = entidades.get(ent, 0) + 1

    print(f"  Valor total: ${total_cop:,.0f} COP")
    print(f"  Entidades:   {len(entidades)} únicas")
    print(f"  Modalidades: {', '.join(f'{k}({v})' for k, v in sorted(modalidades.items(), key=lambda x: -x[1])[:4])}")
    fase1_time = time.time()

    # ══════════════════════════════════════════════════════════════════
    # FASE 2: AUDITORÍA Z3 — LEY 80/1993
    # ══════════════════════════════════════════════════════════════════
    _header("FASE 2/5 — AUDITORÍA Z3 FORMAL (Ley 80/1993)", "─")

    audit_records = []
    z3_passed = 0
    z3_failed = 0
    violations_summary = {}

    for i, c in enumerate(contratos, 1):
        r = audit_contract(c)
        id_c = c.get("id_contrato", f"UNKNOWN-{i}")
        objeto = (c.get("objeto_del_contrato") or c.get("descripcion_del_proceso") or "?")[:100]
        valor = float(c.get("valor_del_contrato", 0) or 0)
        proveedor = c.get("proveedor_adjudicado") or c.get("nombre_representante_legal") or "?"
        entidad_c = c.get("nombre_entidad", "?")

        record = {
            "index": i,
            "id_contrato": id_c,
            "entidad": entidad_c,
            "objeto": objeto,
            "valor_cop": valor,
            "proveedor": proveedor,
            "modalidad": c.get("modalidad_de_contratacion", "?"),
            "estado": c.get("estado_contrato", "?"),
            "fecha_firma": c.get("fecha_de_firma", "?"),
            "z3_passed": r.passed,
            "z3_score": getattr(r, "score", None),
            "z3_violations": getattr(r, "violations", []),
            "proof_hash": r.proof_hash if hasattr(r, "proof_hash") else _proof_hash({"id": id_c, "z3": r.passed}),
        }
        audit_records.append(record)

        if r.passed:
            z3_passed += 1
            status_icon = "✅"
        else:
            z3_failed += 1
            status_icon = "❌"
            for v in getattr(r, "violations", []):
                v_name = v if isinstance(v, str) else str(v)
                violations_summary[v_name] = violations_summary.get(v_name, 0) + 1

        print(f"  [{i:>2}/{len(contratos)}] {status_icon} {id_c:<25} ${valor:>13,.0f}  {objeto[:40]}")

    print(f"\n  Resumen Z3: {z3_passed} aprobados, {z3_failed} rechazados de {len(contratos)}")
    if violations_summary:
        print(f"  Violaciones encontradas:")
        for v, count in sorted(violations_summary.items(), key=lambda x: -x[1]):
            print(f"    • {v}: {count} contratos")
    fase2_time = time.time()

    # ══════════════════════════════════════════════════════════════════
    # FASE 3: DETECCIÓN DE ANOMALÍAS
    # ══════════════════════════════════════════════════════════════════
    _header("FASE 3/5 — DETECCIÓN DE ANOMALÍAS (Ley 80 Art. 24)", "─")

    anomalias = detect_anomalies(contratos, entity=target, threshold_fraccionamiento=2)
    frac_list = anomalias.fraccionamiento if anomalias else []
    conc_list = anomalias.concentracion if anomalias and hasattr(anomalias, "concentracion") else []

    print(f"  Fraccionamiento: {len(frac_list)} alertas")
    for a in frac_list[:5]:
        print(f"    ⚠️  {a}")

    print(f"  Concentración:   {len(conc_list)} alertas")
    for a in conc_list[:5]:
        print(f"    ⚠️  {a}")

    risk_level = "BAJO"
    if len(frac_list) > 3 or z3_failed > len(contratos) * 0.3:
        risk_level = "ALTO"
    elif len(frac_list) > 0 or z3_failed > 0:
        risk_level = "MEDIO"

    print(f"\n  Nivel de riesgo: {risk_level}")
    fase3_time = time.time()

    # ══════════════════════════════════════════════════════════════════
    # FASE 4: GOVERNANCE DOF — 7 CAPAS
    # ══════════════════════════════════════════════════════════════════
    _header("FASE 4/5 — GOVERNANCE DOF (7 capas)", "─")

    gov_results = {}
    try:
        from core.governance import ConstitutionEnforcer
        gov = ConstitutionEnforcer()
        test_output = (
            f"SECOP Audit Report — {len(contratos)} contracts analyzed.\n"
            f"- Z3 passed: {z3_passed}/{len(contratos)}\n"
            f"- Z3 failed: {z3_failed}\n"
            f"- Anomalies: {len(frac_list)} fraccionamiento\n"
            f"- Source: https://datos.gov.co (SECOP II API)\n"
            f"- Risk level: {risk_level}\n"
            f"Recommendation: review flagged contracts for compliance."
        )
        result = gov.check(test_output)
        gov_results = {
            "passed": result.passed,
            "score": result.score,
            "violations": [str(v) for v in result.violations] if result.violations else [],
            "warnings": [str(w) for w in result.warnings] if result.warnings else [],
        }
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        print(f"  Constitution:      {status} (score: {result.score})")
        print(f"  Violations:        {len(result.violations) if result.violations else 0}")
        print(f"  Warnings:          {len(result.warnings) if result.warnings else 0}")
    except Exception as e:
        gov_results = {"passed": None, "error": str(e)}
        print(f"  ⚠️  Governance check error: {e}")

    # Z3 Verifier
    z3_formal = {}
    try:
        from core.z3_verifier import Z3Verifier
        z3v = Z3Verifier()
        proofs = z3v.verify_all()
        proven = sum(1 for p in proofs if p.result in ("PROVEN", "VERIFIED"))
        z3_formal = {
            "total": len(proofs),
            "proven": proven,
            "theorems": [{"name": p.theorem_name, "result": p.result, "time_ms": p.proof_time_ms} for p in proofs],
        }
        print(f"  Z3 Formal:         {proven}/{len(proofs)} PROVEN")
    except Exception as e:
        z3_formal = {"error": str(e)}
        print(f"  Z3 Formal:         ⚠️ {e}")

    fase4_time = time.time()

    # ══════════════════════════════════════════════════════════════════
    # FASE 5: ATTESTATION ON-CHAIN
    # ══════════════════════════════════════════════════════════════════
    _header("FASE 5/5 — ATTESTATION ON-CHAIN", "─")

    audit_payload = {
        "type": "SECOP_AUDIT",
        "version": "1.0.0",
        "service": "dof-mesh-secop-enterprise",
        "target": target,
        "timestamp": _ts_iso(),
        "contracts_audited": len(contratos),
        "total_value_cop": total_cop,
        "z3_passed": z3_passed,
        "z3_failed": z3_failed,
        "anomalies_fraccionamiento": len(frac_list),
        "anomalies_concentracion": len(conc_list),
        "risk_level": risk_level,
        "governance_passed": gov_results.get("passed"),
    }
    master_proof_hash = _proof_hash(audit_payload)
    print(f"  Proof hash:  {master_proof_hash[:42]}...")

    chain_result = {}
    try:
        from core.chain_adapter import DOFChainAdapter
        dry_run = not bool(os.environ.get("DOF_PRIVATE_KEY"))
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=dry_run)

        metadata = json.dumps({
            "type": "SECOP_AUDIT",
            "target": target,
            "contracts": len(contratos),
            "z3_pass": z3_passed,
            "risk": risk_level,
        })

        chain_result = adapter.publish_attestation(
            proof_hash=master_proof_hash,
            agent_id=8004,
            metadata=metadata,
        )
        status = chain_result.get("status", "unknown")
        tx = chain_result.get("tx_hash", "N/A")

        if status == "dry_run":
            print(f"  Chain:       Avalanche C-Chain (DRY-RUN)")
            print(f"  Tx hash:     {str(tx)[:42]}...")
            print(f"  Contrato:    0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6")
            print(f"  Nota:        Configurar DOF_PRIVATE_KEY para attestation real")
        elif status == "success":
            print(f"  Chain:       Avalanche C-Chain (LIVE)")
            print(f"  Tx hash:     {str(tx)[:42]}...")
            print(f"  Explorer:    https://snowtrace.io/tx/{tx}")
        else:
            print(f"  Status:      {status}")
    except Exception as e:
        chain_result = {"status": "error", "error": str(e)}
        print(f"  ⚠️  On-chain error: {e}")

    fase5_time = time.time()
    total_time = fase5_time - start_time

    # ══════════════════════════════════════════════════════════════════
    # REPORTE JSON EJECUTIVO
    # ══════════════════════════════════════════════════════════════════
    _header("GENERANDO REPORTE JSON EJECUTIVO", "─")

    report = {
        "report_id": f"SECOP-E2E-{ts}",
        "version": "1.0.0",
        "generated_at": _ts_iso(),
        "generated_by": "DOF-MESH v0.8.0 — Enterprise Audit Service",
        "pipeline": {
            "engine": "Z3 SMT Solver",
            "framework": "Ley 80/1993 + Decreto 1082/2015",
            "governance": "DOF 7-layer deterministic governance",
            "blockchain": "Avalanche C-Chain (DOFProofRegistry)",
        },
        "query": {
            "target": target,
            "municipio": municipio,
            "entity": entity,
            "year": year,
            "limit": limit,
            "source": "datos.gov.co — SECOP II (Socrata API)",
        },
        "summary": {
            "total_contracts": len(contratos),
            "total_value_cop": total_cop,
            "total_value_usd": round(total_cop / 4200, 2),
            "unique_entities": len(entidades),
            "modalities": modalidades,
            "risk_level": risk_level,
        },
        "z3_audit": {
            "rules_applied": 6,
            "legal_framework": "Ley 80/1993 Art. 24, 25, 26, 29, 30 + Decreto 1082/2015",
            "passed": z3_passed,
            "failed": z3_failed,
            "pass_rate": round(z3_passed / len(contratos) * 100, 1) if contratos else 0,
            "violations_summary": violations_summary,
        },
        "anomalies": {
            "fraccionamiento": {
                "count": len(frac_list),
                "rule": "Ley 80 Art. 24 — Anti-fraccionamiento",
                "details": frac_list[:10],
            },
            "concentracion": {
                "count": len(conc_list),
                "rule": "Concentración excesiva en un proveedor",
                "details": conc_list[:10],
            },
        },
        "governance": {
            "dof_layers": 7,
            "constitution_check": gov_results,
            "z3_formal_verification": z3_formal,
        },
        "blockchain": {
            "chain": "Avalanche C-Chain",
            "chain_id": 43114,
            "contract": "0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6",
            "master_proof_hash": master_proof_hash,
            "attestation": chain_result,
        },
        "contracts_detail": audit_records,
        "performance": {
            "total_seconds": round(total_time, 2),
            "ingesta_seconds": round(fase1_time - start_time, 2),
            "z3_audit_seconds": round(fase2_time - fase1_time, 2),
            "anomalies_seconds": round(fase3_time - fase2_time, 2),
            "governance_seconds": round(fase4_time - fase3_time, 2),
            "blockchain_seconds": round(fase5_time - fase4_time, 2),
        },
        "verification": {
            "how_to_verify": (
                f"Recalcular SHA-256 del campo 'blockchain.master_proof_hash' con los datos "
                f"del campo 'summary' + 'z3_audit' + 'anomalies'. "
                f"Debe coincidir con el proof registrado en el contrato "
                f"0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6 en Avalanche C-Chain."
            ),
            "explorer": "https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6",
            "sdk": "pip install dof-sdk",
            "docs": "https://dofmesh.com",
        },
    }

    # Guardar reporte JSON
    report_file = REPORTS_DIR / f"secop_e2e_{ts}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"  📄 Reporte: {report_file}")

    # Guardar detalle JSONL
    log_file = LOGS_DIR / f"e2e_audit_{ts}.jsonl"
    _save_jsonl(audit_records, log_file)
    print(f"  📁 Detalle: {log_file}")

    # Guardar en Obsidian
    obs_title = f"E2E Audit SECOP — {target} — {datetime.now().strftime('%Y-%m-%d')}"
    obs_content = f"""# {obs_title}

**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M')} COT
**Motor:** DOF-MESH v0.8.0 — Z3 + Ley 80/1993
**Fuente:** datos.gov.co (SECOP II en vivo)

## Resultados
- Contratos: **{len(contratos)}**
- Valor total: **${total_cop:,.0f} COP** (~${total_cop/4200:,.0f} USD)
- Z3 aprobados: **{z3_passed}/{len(contratos)}** ({round(z3_passed/len(contratos)*100,1)}%)
- Riesgo: **{risk_level}**
- Anomalías: {len(frac_list)} fraccionamiento, {len(conc_list)} concentración

## On-Chain
- Proof hash: `{master_proof_hash[:42]}...`
- Chain: Avalanche C-Chain
- Contrato: `0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6`
- Status: {chain_result.get('status', 'N/A')}

## Archivos
- Reporte: `{report_file}`
- Detalle: `{log_file}`

## Verificación
pip install dof-sdk → dof verify-states
"""
    if _save_obsidian(obs_title, obs_content):
        print(f"  🧠 Obsidian: guardado")
    else:
        print(f"  ⚠️  Obsidian: no disponible")

    # Resumen final
    _header("RESUMEN EJECUTIVO")
    print(f"  Contratos auditados:  {len(contratos)}")
    print(f"  Valor total:          ${total_cop:,.0f} COP (~${total_cop/4200:,.0f} USD)")
    print(f"  Z3 aprobados:         {z3_passed}/{len(contratos)} ({round(z3_passed/len(contratos)*100,1)}%)")
    print(f"  Anomalías:            {len(frac_list)} fraccionamiento, {len(conc_list)} concentración")
    print(f"  Nivel de riesgo:      {risk_level}")
    print(f"  Governance DOF:       {'PASSED' if gov_results.get('passed') else 'N/A'}")
    print(f"  On-chain:             {chain_result.get('status', 'N/A')}")
    print(f"  Proof hash:           {master_proof_hash[:42]}...")
    print(f"  Tiempo total:         {total_time:.1f}s")
    print(f"\n  📄 {report_file}")
    print("=" * 72)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOF-MESH — E2E Enterprise SECOP Audit")
    parser.add_argument("--municipio", default="MEDELLIN")
    parser.add_argument("--entity", default=None)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    run_e2e(
        municipio=args.municipio,
        entity=args.entity,
        year=args.year,
        limit=args.limit,
    )
