#!/usr/bin/env python3
"""
DOF-MESH × datos-colombia-mcp
Demo para Ruta N — Auditoría de contratación pública en tiempo real

Ejecutar: python3 scripts/demo_rutan.py
Requiere: python3 -m pip install requests z3-solver httpx
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "integrations", "datos-colombia"))


def _sep(char="═", width=62):
    print(char * width)


def demo():
    _sep()
    print("  DOF-MESH × Ruta N — Demo Auditoría SECOP en Vivo")
    print("  Contratación pública de Medellín · Verificación Z3")
    _sep()

    try:
        from tools.secop import fetch_contracts, audit_contract, detect_anomalies
    except ImportError as e:
        print(f"\n❌ No se pudo importar SECOP: {e}")
        print("   Verifica: pip install requests z3-solver")
        return

    # ── 1. Contratos en vivo ────────────────────────────────────────────────
    print("\n1. CONTRATOS PÚBLICOS — Medellín (SECOP II en vivo)")
    print("   Fuente: datos.gov.co — actualizado en tiempo real\n")

    contratos = fetch_contracts(municipio="MEDELLIN", limit=10)
    if not contratos:
        print("   ⚠️  No se pudo conectar a SECOP II. Verifica conexión.")
        return

    print(f"   Contratos encontrados: {len(contratos)}")
    c = contratos[0]
    print(f"   Entidad:  {c.get('nombre_entidad', '')[:55]}")
    obj = c.get("objeto_del_contrato", "") or ""
    print(f"   Objeto:   {obj[:70]}")
    val_raw = c.get("valor_del_contrato", "0") or "0"
    try:
        val = float(str(val_raw).replace(",", ""))
        print(f"   Valor:    ${val:>20,.0f} COP")
    except ValueError:
        print(f"   Valor:    {val_raw}")

    # ── 2. Auditoría Z3 ─────────────────────────────────────────────────────
    print("\n2. AUDITORÍA Z3 — 6 Reglas Legales (Ley 80/1993)")
    print("   Verificación formal determinística — sin LLM\n")

    resultado = audit_contract(c)
    for regla in resultado.rules:
        icon = "✅" if regla.passed else "❌"
        print(f"   {icon} {regla.rule_id} [{regla.norma[:25]}]")
        print(f"      {regla.detail[:72]}")

    score_pct = resultado.score * 100
    z3_icon = "✅" if resultado.z3_sat else "❌"
    print(f"\n   Score: {score_pct:.0f}% · Z3-SAT: {z3_icon} · "
          f"Hash: {resultado.proof_hash[:20]}...")

    # ── 3. Detección de anomalías ────────────────────────────────────────────
    print("\n3. DETECTOR DE FRACCIONAMIENTO — Ley 80 Art. 24")
    print("   Agrupa por contratista + mes · detecta suma > umbral licitación\n")

    anomalies = detect_anomalies(
        contratos,
        entity="MEDELLIN",
        threshold_fraccionamiento=2,
    )
    if anomalies.fraccionamiento:
        print(f"   ⚠️  {len(anomalies.fraccionamiento)} alerta(s) de fraccionamiento:")
        for a in anomalies.fraccionamiento[:3]:
            print(f"      {a['alerta'][:80]}")
    else:
        print(f"   ✅ Sin alertas de fraccionamiento en {len(contratos)} contratos")

    if anomalies.concentracion:
        print(f"\n   ⚠️  {len(anomalies.concentracion)} alerta(s) de concentración:")
        for a in anomalies.concentracion[:2]:
            print(f"      {a['alerta'][:80]}")
    else:
        print(f"   ✅ Sin alertas de concentración")

    print(f"\n   Proof hash: {anomalies.proof_hash[:28]}...")

    # ── 4. Búsqueda por entidad ──────────────────────────────────────────────
    print("\n4. BÚSQUEDA POR ENTIDAD — Secretaría de Desarrollo Económico")

    contratos_sde = fetch_contracts(
        entity="SECRETARIA DE DESARROLLO ECONOMICO",
        limit=5,
    )
    print(f"   Contratos encontrados: {len(contratos_sde)}")
    if contratos_sde:
        for i, ct in enumerate(contratos_sde[:3], 1):
            val_r = ct.get("valor_del_contrato", "0") or "0"
            try:
                v = float(str(val_r).replace(",", ""))
                v_str = f"${v:,.0f}"
            except ValueError:
                v_str = val_r
            obj_short = (ct.get("objeto_del_contrato", "") or "")[:55]
            print(f"   {i}. {obj_short}")
            print(f"      {v_str} COP · {ct.get('nombre_entidad','')[:40]}")

    # ── Cierre ───────────────────────────────────────────────────────────────
    _sep()
    print("  SISTEMA LISTO PARA RUTA N")
    print()
    print("  ✅ Datos en tiempo real desde SECOP II (datos.gov.co)")
    print("  ✅ Verificación formal Z3 — prueba matemática de compliance")
    print("  ✅ Detección automática de fraccionamiento (fraude más común)")
    print("  ✅ Proof hash on-chain verificable en Avalanche/Conflux")
    print()
    print("  API: POST /mcp/tools/secop_search   {'municipio': 'MEDELLIN'}")
    print("  API: POST /mcp/tools/secop_anomalies {'entity': 'ALCALDIA...'}")
    _sep()


if __name__ == "__main__":
    demo()
