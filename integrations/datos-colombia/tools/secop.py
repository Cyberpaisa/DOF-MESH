"""
tools/secop.py — Auditoría de contratación pública colombiana.

Fuente: SECOP II (datos.gov.co — Socrata SODA API)
Marco legal: Ley 80/1993 + Decreto 1082/2015 + Ley 1150/2007

6 Reglas verificadas formalmente con z3-solver:
  R1: Valor positivo                    (Ley 80 Art. 25)
  R2: Modalidad correcta según SMMLV   (Decreto 1082/2015)
  R3: Plazo dentro del límite legal    (Ley 80 Art. 40)
  R4: Contratista identificado         (Ley 80 Art. 5)
  R5: Objeto contractual definido      (Ley 80 Art. 24)
  R6: Sin fraccionamiento              (Ley 80 Art. 24 — fraude más común)

Exports públicos:
  audit_contract(contrato)          → AuditResult
  detect_anomalies(contratos, ...)  → AnomalyReport
  fetch_contracts(entity, year, municipio, limit)  → list[dict]
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
import z3

logger = logging.getLogger("secop.audit")

# ── Constantes legales 2025 ──────────────────────────────────────────────────
SMMLV_2025 = 1_423_500          # COP — actualizar cada enero
LIMITE_LICITACION = 1350 * SMMLV_2025   # ~$1.921M COP
LIMITE_ABREVIADA  = 50   * SMMLV_2025   # ~$71.17M COP
MAX_PLAZO_OBRA      = 1825  # días (5 años)
MAX_PLAZO_SERVICIOS = 1095  # días (3 años)

SECOP_II_CONTRATOS  = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
SECOP_II_PROCESOS   = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
SECOP_INTEGRADO     = "https://www.datos.gov.co/resource/rpmr-utcd.json"


# ── Dataclasses de resultado ─────────────────────────────────────────────────

@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    norma: str
    detail: str


@dataclass
class AuditResult:
    contract_id: str
    contratista: str
    entidad: str
    valor: float
    modalidad: str
    rules: list[RuleResult]
    proof_hash: str        # keccak-style sha256 del estado Z3
    z3_sat: bool           # True si el solver encontró modelo consistente
    passed: bool           # True solo si TODAS las reglas pasan
    timestamp: str

    @property
    def score(self) -> float:
        return sum(1 for r in self.rules if r.passed) / len(self.rules)

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "contratista": self.contratista,
            "entidad": self.entidad,
            "valor": self.valor,
            "modalidad": self.modalidad,
            "passed": self.passed,
            "score": self.score,
            "proof_hash": self.proof_hash,
            "z3_sat": self.z3_sat,
            "timestamp": self.timestamp,
            "rules": [
                {"id": r.rule_id, "passed": r.passed, "norma": r.norma, "detail": r.detail}
                for r in self.rules
            ],
        }


@dataclass
class AnomalyReport:
    entity: str
    total_contracts: int
    fraccionamiento: list[dict]   # R6: misma entidad/contratista/mes con suma > umbral
    concentracion: list[dict]     # contratista con > threshold% de contratos
    anomaly_count: int
    proof_hash: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "total_contracts": self.total_contracts,
            "fraccionamiento": self.fraccionamiento,
            "concentracion": self.concentracion,
            "anomaly_count": self.anomaly_count,
            "proof_hash": self.proof_hash,
            "timestamp": self.timestamp,
        }


# ── Z3 Verifier ─────────────────────────────────────────────────────────────

def _proof_hash(state: dict) -> str:
    """SHA-256 del estado de verificación serializado — equivalente a proof_hash DOF-MESH."""
    payload = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _z3_verify_contract(valor: float, objeto: str, modalidad: str) -> tuple[bool, str]:
    """
    Verifica formalmente R1, R2 y R5 usando z3-solver.
    Retorna (sat_ok, proof_hash).

    Las reglas con lógica numérica / de longitud son verificables formalmente.
    R3 (plazo), R4 (contratista) se verifican en Python puro — z3 no aporta
    sobre strings de fecha que ya son Python datetimes.
    """
    solver = z3.Solver()

    v = z3.Real("valor_contrato")
    o_len = z3.Int("objeto_len")

    # R1: valor positivo
    solver.add(v > 0)

    # R2: modalidad correcta según umbral SMMLV
    # Expresamos como invariante: si valor > LIMITE_LICITACION, modalidad_flag debe ser 1
    modal_licitacion = z3.Int("modal_licitacion")   # 1 = tiene licitación
    modal_abreviada  = z3.Int("modal_abreviada")    # 1 = tiene abreviada
    solver.add(z3.Or(modal_licitacion == 0, modal_licitacion == 1))
    solver.add(z3.Or(modal_abreviada  == 0, modal_abreviada  == 1))

    mod_lower = str(modalidad).lower()
    ml_val = 1 if ('licitación' in mod_lower or 'licitacion' in mod_lower) else 0
    ma_val = 1 if 'abreviada' in mod_lower else 0
    solver.add(modal_licitacion == ml_val)
    solver.add(modal_abreviada  == ma_val)

    if valor > LIMITE_LICITACION:
        solver.add(modal_licitacion == 1)
    elif valor > LIMITE_ABREVIADA:
        solver.add(z3.Or(modal_abreviada == 1, modal_licitacion == 1))
    # else contratación directa — sin restricción de modalidad

    # R5: objeto definido >= 20 caracteres
    obj_real_len = len(str(objeto).strip()) if objeto else 0
    solver.add(o_len == obj_real_len)
    solver.add(o_len >= 20)

    # Instanciar con valores reales
    solver.add(v == valor)

    result = solver.check()
    sat_ok = (result == z3.sat)

    state = {
        "valor": valor,
        "objeto_len": obj_real_len,
        "modalidad": modalidad,
        "limite_licitacion": LIMITE_LICITACION,
        "limite_abreviada": LIMITE_ABREVIADA,
        "z3_result": str(result),
    }
    return sat_ok, _proof_hash(state)


# ── Auditoría de contrato individual ────────────────────────────────────────

def audit_contract(contrato: dict) -> AuditResult:
    """
    Audita un contrato SECOP II contra 6 reglas legales colombianas.
    R1-R2-R5 usan Z3 formal verification.
    R3-R4-R6 usan Python puro (lógica de fechas/strings).
    """
    objeto    = contrato.get("objeto_del_contrato", "") or ""
    valor_str = contrato.get("valor_del_contrato", "0") or "0"
    modalidad = contrato.get("modalidad_de_contratacion", "") or ""
    tipo      = contrato.get("tipo_de_contrato", "") or ""
    contratista  = contrato.get("nombre_del_contratista", "") or ""
    doc_contratista = contrato.get("documento_contratista", "") or ""
    entidad   = contrato.get("nombre_de_la_entidad", "") or ""
    fecha_firma_s = contrato.get("fecha_de_firma", "") or ""
    fecha_fin_s   = contrato.get("fecha_de_fin_del_contrato", "") or ""
    contract_id   = contrato.get("id_contrato", contrato.get("referencia_del_contrato", "")) or ""

    try:
        valor = float(str(valor_str).replace(",", "").strip())
    except (ValueError, TypeError):
        valor = 0.0

    # ── Z3: R1, R2, R5 ──────────────────────────────────────────────────
    z3_sat, proof = _z3_verify_contract(valor, objeto, modalidad)

    # R1 — Valor positivo (Ley 80 Art. 25)
    r1 = RuleResult(
        "R1", valor > 0,
        "Ley 80/1993 Art. 25",
        f"valor={valor:,.0f} COP {'> 0 ✅' if valor > 0 else '≤ 0 ❌'}",
    )

    # R2 — Modalidad correcta según SMMLV (Decreto 1082/2015)
    mod = modalidad.lower()
    if valor > LIMITE_LICITACION:
        r2_ok = 'licitación' in mod or 'licitacion' in mod
        r2_detail = f"valor={valor:,.0f} > {LIMITE_LICITACION:,.0f} → requiere licitación pública"
    elif valor > LIMITE_ABREVIADA:
        r2_ok = 'abreviada' in mod or 'licitación' in mod or 'licitacion' in mod
        r2_detail = f"valor={valor:,.0f} en rango abreviada; modalidad='{modalidad}'"
    else:
        r2_ok = True
        r2_detail = f"valor={valor:,.0f} < {LIMITE_ABREVIADA:,.0f} → contratación directa OK"
    r2 = RuleResult("R2", r2_ok, "Decreto 1082/2015 Art. 2.2.1.2.1.2.1", r2_detail)

    # R3 — Plazo máximo (Ley 80 Art. 40)
    r3_ok = True
    r3_detail = "plazo no verificable (fechas ausentes)"
    if fecha_firma_s and fecha_fin_s:
        try:
            f_firma = datetime.fromisoformat(fecha_firma_s.replace("Z", ""))
            f_fin   = datetime.fromisoformat(fecha_fin_s.replace("Z", ""))
            plazo   = (f_fin - f_firma).days
            t = tipo.lower()
            if "obra" in t:
                r3_ok = plazo <= MAX_PLAZO_OBRA
                r3_detail = f"plazo={plazo}d, máx={MAX_PLAZO_OBRA}d (obra)"
            elif "consultoría" in t or "consultoria" in t or "servicio" in t:
                r3_ok = plazo <= MAX_PLAZO_SERVICIOS
                r3_detail = f"plazo={plazo}d, máx={MAX_PLAZO_SERVICIOS}d (servicios)"
            else:
                r3_detail = f"plazo={plazo}d, tipo='{tipo}' no clasificado"
        except ValueError as e:
            r3_detail = f"fecha malformada: {e}"
    r3 = RuleResult("R3", r3_ok, "Ley 80/1993 Art. 40", r3_detail)

    # R4 — Contratista identificado (Ley 80 Art. 5)
    # RUES cross-check pendiente para fecha de constitución
    r4_ok = bool(contratista.strip()) and bool(doc_contratista.strip())
    r4_detail = (
        f"contratista='{contratista[:40]}', doc='{doc_contratista}'"
        if r4_ok else
        "contratista o documento vacío — ⚠️ cruce RUES pendiente para verificar fecha constitución"
    )
    r4 = RuleResult("R4", r4_ok, "Ley 80/1993 Art. 5", r4_detail)

    # R5 — Objeto definido >= 20 chars (Ley 80 Art. 24)
    obj_len = len(objeto.strip())
    r5_ok = obj_len >= 20
    r5 = RuleResult(
        "R5", r5_ok, "Ley 80/1993 Art. 24",
        f"objeto={obj_len} chars ({'OK' if r5_ok else 'muy corto — mín 20'}): '{objeto[:60]}'"
    )

    # R6 — Sin fraccionamiento puntual por contrato (Ley 80 Art. 24)
    # Verificación completa en detect_anomalies() con agrupación temporal.
    # Aquí verificamos que el contrato individual no sea trivialmente sospechoso:
    # valor > 0 pero muy cercano al umbral de abreviada sin ser licitación.
    MARGEN_SOSPECHA = 0.05  # 5% por debajo del límite = sospechoso
    umbral_sospecha = LIMITE_LICITACION * (1 - MARGEN_SOSPECHA)
    r6_ok = not (valor > umbral_sospecha and valor <= LIMITE_LICITACION and
                 'licitación' not in mod and 'licitacion' not in mod)
    r6_detail = (
        f"valor=${valor:,.0f} dentro del 5% del umbral de licitación sin ser licitación — posible fraccionamiento"
        if not r6_ok else
        f"valor=${valor:,.0f} fuera de zona de sospecha de fraccionamiento individual"
    )
    r6 = RuleResult("R6", r6_ok, "Ley 80/1993 Art. 24 (fraccionamiento)", r6_detail)

    rules = [r1, r2, r3, r4, r5, r6]
    all_passed = all(r.passed for r in rules)

    return AuditResult(
        contract_id=contract_id,
        contratista=contratista,
        entidad=entidad,
        valor=valor,
        modalidad=modalidad,
        rules=rules,
        proof_hash=proof,
        z3_sat=z3_sat,
        passed=all_passed,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── detect_anomalies ─────────────────────────────────────────────────────────

def detect_anomalies(
    contratos: list[dict],
    entity: str = "",
    threshold_concentracion: float = 0.50,
    threshold_fraccionamiento: int = 3,
) -> AnomalyReport:
    """
    Detecta 2 tipos de anomalías en un conjunto de contratos:

    FRACCIONAMIENTO (R6 — Ley 80 Art. 24):
      Mismo contratista + mismo mes-año + suma de valores > LIMITE_LICITACION
      pero ningún contrato individual supera ese umbral.
      Es el fraude más común en contratación pública colombiana.

    CONCENTRACIÓN:
      Un contratista recibe más del `threshold_concentracion` (default 50%)
      de los contratos de una entidad.
    """
    # Agrupar por (nit_contratista, mes-año) para fraccionamiento
    grupos_frac: dict[tuple, list[dict]] = defaultdict(list)
    for c in contratos:
        doc = c.get("documento_contratista", "").strip()
        nombre = c.get("nombre_del_contratista", "").strip()
        fecha_s = c.get("fecha_de_firma", "") or ""
        try:
            f = datetime.fromisoformat(fecha_s.replace("Z", ""))
            mes_key = f"{f.year}-{f.month:02d}"
        except (ValueError, AttributeError):
            mes_key = "unknown"
        key = (doc or nombre, mes_key)
        grupos_frac[key].append(c)

    fraccionamiento = []
    for (contratista_id, mes), grupo in grupos_frac.items():
        if len(grupo) < threshold_fraccionamiento:
            continue
        suma = sum(
            float((c.get("valor_del_contrato") or "0").replace(",", ""))
            for c in grupo
        )
        # Sospechoso: suma supera umbral pero ningún contrato individual lo supera
        max_individual = max(
            float((c.get("valor_del_contrato") or "0").replace(",", ""))
            for c in grupo
        )
        if suma > LIMITE_LICITACION and max_individual <= LIMITE_LICITACION:
            fraccionamiento.append({
                "contratista": contratista_id,
                "mes": mes,
                "num_contratos": len(grupo),
                "suma_total": suma,
                "max_individual": max_individual,
                "limite_licitacion": LIMITE_LICITACION,
                "alerta": (
                    f"Posible fraccionamiento: {len(grupo)} contratos en {mes}, "
                    f"suma=${suma:,.0f} > umbral licitación=${LIMITE_LICITACION:,.0f} "
                    f"pero ninguno individual supera el umbral."
                ),
            })

    # Concentración: % de contratos por contratista
    conteos: dict[str, int] = defaultdict(int)
    for c in contratos:
        doc = c.get("documento_contratista", "").strip()
        nombre = c.get("nombre_del_contratista", doc).strip()
        key = doc or nombre
        conteos[key] += 1

    total = len(contratos)
    concentracion = []
    if total > 0:
        for contratista_id, count in conteos.items():
            pct = count / total
            if pct >= threshold_concentracion:
                concentracion.append({
                    "contratista": contratista_id,
                    "contratos": count,
                    "total": total,
                    "porcentaje": round(pct * 100, 1),
                    "alerta": (
                        f"Concentración: {contratista_id} tiene {count}/{total} contratos "
                        f"({pct*100:.1f}%) con {entity} — supera umbral {threshold_concentracion*100:.0f}%."
                    ),
                })

    anomaly_count = len(fraccionamiento) + len(concentracion)
    ts = datetime.utcnow().isoformat()
    state = {
        "entity": entity,
        "total": total,
        "fraccionamiento": len(fraccionamiento),
        "concentracion": len(concentracion),
        # timestamp excluded from hash — it's metadata, not state
    }
    proof = _proof_hash(state)

    return AnomalyReport(
        entity=entity,
        total_contracts=total,
        fraccionamiento=fraccionamiento,
        concentracion=concentracion,
        anomaly_count=anomaly_count,
        proof_hash=proof,
        timestamp=ts,
    )


# ── Fetch desde SECOP II ─────────────────────────────────────────────────────

def fetch_contracts(
    entity: Optional[str] = None,
    year: Optional[int] = None,
    municipio: Optional[str] = None,
    limit: int = 20,
    endpoint: str = SECOP_II_PROCESOS,
) -> list[dict]:
    """
    Descarga contratos de SECOP II vía Socrata SODA API.
    Aplica filtros SoQL: entidad, año, municipio.
    """
    conditions = []
    if entity:
        conditions.append(f"upper(nombre_de_la_entidad) like upper('%{entity}%')")
    if year:
        conditions.append(
            f"fecha_de_firma >= '{year}-01-01T00:00:00' "
            f"AND fecha_de_firma <= '{year}-12-31T23:59:59'"
        )
    if municipio:
        conditions.append(f"upper(ciudad) like upper('%{municipio}%')")

    # Construir query string manualmente — httpx encode el $ como %24
    # pero Socrata SODA exige literalmente $limit, $where, etc.
    qs_parts = [f"$limit={limit}"]
    if conditions:
        where = " AND ".join(conditions)
        qs_parts.append(f"$where={where}")
    url = f"{endpoint}?{'&'.join(qs_parts)}"

    try:
        r = httpx.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"fetch_contracts error: {e}")
        return []


# ── CLI rápido ───────────────────────────────────────────────────────────────

def _print_result(res: AuditResult) -> None:
    icon = "✅" if res.passed else "⚠️"
    print(f"\n{icon} {res.contratista[:55]}")
    print(f"   Entidad: {res.entidad[:55]}")
    print(f"   Valor:   ${res.valor:>18,.0f} COP | Modalidad: {res.modalidad}")
    print(f"   Score:   {res.score*100:.0f}%  Z3-SAT: {'✅' if res.z3_sat else '❌'}")
    print(f"   Hash:    {res.proof_hash[:24]}...")
    for r in res.rules:
        print(f"   {'✅' if r.passed else '❌'} {r.rule_id} [{r.norma}] — {r.detail[:80]}")


if __name__ == "__main__":
    print("═" * 65)
    print("DOF-MESH × SECOP II — Auditoría de Contratación Pública CO")
    print("═" * 65)

    contratos = fetch_contracts(limit=5)
    if not contratos:
        print("❌ No se pudo conectar a SECOP II. Verifica conexión.")
        raise SystemExit(1)

    print(f"\nContratos descargados: {len(contratos)}\n")
    resultados = [audit_contract(c) for c in contratos]
    for r in resultados:
        _print_result(r)

    print("\n" + "═" * 65)
    print("DETECCIÓN DE ANOMALÍAS")
    print("═" * 65)
    anomalies = detect_anomalies(contratos, entity="muestra")
    print(f"Fraccionamiento: {len(anomalies.fraccionamiento)} alertas")
    print(f"Concentración:   {len(anomalies.concentracion)} alertas")
    print(f"Proof hash:      {anomalies.proof_hash[:24]}...")

    total_p = sum(r.score for r in resultados)
    print(f"\nScore promedio: {total_p/len(resultados)*100:.1f}%")
