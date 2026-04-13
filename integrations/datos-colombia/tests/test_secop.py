"""
tests/test_secop.py — Tests del auditor SECOP con Z3.

Cobertura:
  - 6 reglas Z3/Python con casos válidos e inválidos
  - detect_anomalies: fraccionamiento + concentración
  - Integración real con SECOP II API (marcados como slow)

Correr: python3 -m unittest tests.test_secop -v
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.secop import (
    audit_contract,
    detect_anomalies,
    fetch_contracts,
    SMMLV_2025,
    LIMITE_LICITACION,
    LIMITE_ABREVIADA,
)


def _make_contract(**kwargs) -> dict:
    """Helper: contrato base válido, sobreescribible con kwargs."""
    base = {
        "id_contrato": "TEST-001",
        "nombre_de_la_entidad": "ALCALDIA DE MEDELLIN",
        "objeto_del_contrato": "Prestación de servicios de mantenimiento de infraestructura vial",
        "valor_del_contrato": str(100 * SMMLV_2025),   # ~100 SMMLV
        "modalidad_de_contratacion": "Selección Abreviada",
        "tipo_de_contrato": "Prestación de Servicios",
        "nombre_del_contratista": "CONSTRUCTORA EJEMPLO S.A.S",
        "documento_contratista": "900123456",
        "fecha_de_firma": "2025-01-15T00:00:00",
        "fecha_de_fin_del_contrato": "2025-12-31T00:00:00",
        "ciudad": "MEDELLIN",
        "departamento": "ANTIOQUIA",
    }
    base.update(kwargs)
    return base


class TestR1ValorPositivo(unittest.TestCase):
    """Regla 1 — Ley 80 Art. 25: valor > 0."""

    def test_valor_positivo_pasa(self):
        c = _make_contract(valor_del_contrato="5000000")
        r = audit_contract(c)
        r1 = next(x for x in r.rules if x.rule_id == "R1")
        self.assertTrue(r1.passed)

    def test_valor_cero_falla(self):
        c = _make_contract(valor_del_contrato="0")
        r = audit_contract(c)
        r1 = next(x for x in r.rules if x.rule_id == "R1")
        self.assertFalse(r1.passed)

    def test_valor_negativo_falla(self):
        c = _make_contract(valor_del_contrato="-1000000")
        r = audit_contract(c)
        r1 = next(x for x in r.rules if x.rule_id == "R1")
        self.assertFalse(r1.passed)

    def test_valor_malformado_falla(self):
        c = _make_contract(valor_del_contrato="abc")
        r = audit_contract(c)
        r1 = next(x for x in r.rules if x.rule_id == "R1")
        self.assertFalse(r1.passed)


class TestR2Modalidad(unittest.TestCase):
    """Regla 2 — Decreto 1082/2015: modalidad correcta según SMMLV."""

    def test_licitacion_requerida_con_licitacion_pasa(self):
        valor = str(int(LIMITE_LICITACION * 1.1))
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Licitación Pública")
        r = audit_contract(c)
        r2 = next(x for x in r.rules if x.rule_id == "R2")
        self.assertTrue(r2.passed)

    def test_licitacion_requerida_sin_licitacion_falla(self):
        valor = str(int(LIMITE_LICITACION * 1.1))
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Contratación Directa")
        r = audit_contract(c)
        r2 = next(x for x in r.rules if x.rule_id == "R2")
        self.assertFalse(r2.passed)

    def test_rango_abreviada_con_abreviada_pasa(self):
        valor = str(int(LIMITE_ABREVIADA * 5))   # 250 SMMLV — rango abreviada
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Selección Abreviada")
        r = audit_contract(c)
        r2 = next(x for x in r.rules if x.rule_id == "R2")
        self.assertTrue(r2.passed)

    def test_contratacion_directa_valor_bajo_siempre_pasa(self):
        valor = str(int(LIMITE_ABREVIADA * 0.3))  # 15 SMMLV
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Contratación Directa")
        r = audit_contract(c)
        r2 = next(x for x in r.rules if x.rule_id == "R2")
        self.assertTrue(r2.passed)


class TestR3Plazo(unittest.TestCase):
    """Regla 3 — Ley 80 Art. 40: plazo dentro del límite."""

    def test_obra_dentro_limite_pasa(self):
        firma = "2025-01-01T00:00:00"
        fin = "2025-12-31T00:00:00"  # ~364 días
        c = _make_contract(
            tipo_de_contrato="Obra Pública",
            fecha_de_firma=firma,
            fecha_de_fin_del_contrato=fin,
        )
        r = audit_contract(c)
        r3 = next(x for x in r.rules if x.rule_id == "R3")
        self.assertTrue(r3.passed)

    def test_servicios_supera_3_anos_falla(self):
        firma = "2020-01-01T00:00:00"
        fin = "2025-01-01T00:00:00"   # ~1826 días >> 1095
        c = _make_contract(
            tipo_de_contrato="Prestación de Servicios",
            fecha_de_firma=firma,
            fecha_de_fin_del_contrato=fin,
        )
        r = audit_contract(c)
        r3 = next(x for x in r.rules if x.rule_id == "R3")
        self.assertFalse(r3.passed)

    def test_fechas_ausentes_no_penaliza(self):
        c = _make_contract(fecha_de_firma="", fecha_de_fin_del_contrato="")
        r = audit_contract(c)
        r3 = next(x for x in r.rules if x.rule_id == "R3")
        self.assertTrue(r3.passed)  # sin datos → no penalizar


class TestR4Contratista(unittest.TestCase):
    """Regla 4 — Ley 80 Art. 5: contratista identificado."""

    def test_con_nombre_y_doc_pasa(self):
        c = _make_contract(nombre_del_contratista="EMPRESA S.A.S", documento_contratista="900123456")
        r = audit_contract(c)
        r4 = next(x for x in r.rules if x.rule_id == "R4")
        self.assertTrue(r4.passed)

    def test_sin_nombre_falla(self):
        c = _make_contract(nombre_del_contratista="", documento_contratista="900123456")
        r = audit_contract(c)
        r4 = next(x for x in r.rules if x.rule_id == "R4")
        self.assertFalse(r4.passed)

    def test_sin_documento_falla(self):
        c = _make_contract(nombre_del_contratista="EMPRESA S.A.S", documento_contratista="")
        r = audit_contract(c)
        r4 = next(x for x in r.rules if x.rule_id == "R4")
        self.assertFalse(r4.passed)


class TestR5Objeto(unittest.TestCase):
    """Regla 5 — Ley 80 Art. 24: objeto definido >= 20 chars."""

    def test_objeto_suficiente_pasa(self):
        c = _make_contract(objeto_del_contrato="Mantenimiento de vías secundarias del municipio")
        r = audit_contract(c)
        r5 = next(x for x in r.rules if x.rule_id == "R5")
        self.assertTrue(r5.passed)

    def test_objeto_corto_falla(self):
        c = _make_contract(objeto_del_contrato="Mantenimiento")  # 13 chars
        r = audit_contract(c)
        r5 = next(x for x in r.rules if x.rule_id == "R5")
        self.assertFalse(r5.passed)

    def test_objeto_vacio_falla(self):
        c = _make_contract(objeto_del_contrato="")
        r = audit_contract(c)
        r5 = next(x for x in r.rules if x.rule_id == "R5")
        self.assertFalse(r5.passed)


class TestR6Fraccionamiento(unittest.TestCase):
    """Regla 6 — Ley 80 Art. 24: sin fraccionamiento individual."""

    def test_valor_normal_no_sospechoso_pasa(self):
        valor = str(int(LIMITE_LICITACION * 0.5))  # 50% del umbral
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Selección Abreviada")
        r = audit_contract(c)
        r6 = next(x for x in r.rules if x.rule_id == "R6")
        self.assertTrue(r6.passed)

    def test_valor_cerca_umbral_sin_licitacion_falla(self):
        # 96% del límite de licitación pero modalidad = contratación directa
        valor = str(int(LIMITE_LICITACION * 0.96))
        c = _make_contract(valor_del_contrato=valor, modalidad_de_contratacion="Contratación Directa")
        r = audit_contract(c)
        r6 = next(x for x in r.rules if x.rule_id == "R6")
        self.assertFalse(r6.passed)


class TestZ3Proof(unittest.TestCase):
    """Z3 proof_hash debe ser reproducible y único."""

    def test_proof_hash_determinista(self):
        c = _make_contract()
        r1 = audit_contract(c)
        r2 = audit_contract(c)
        self.assertEqual(r1.proof_hash, r2.proof_hash)

    def test_proof_hash_cambia_con_valor(self):
        c1 = _make_contract(valor_del_contrato="1000000")
        c2 = _make_contract(valor_del_contrato="2000000")
        r1 = audit_contract(c1)
        r2 = audit_contract(c2)
        self.assertNotEqual(r1.proof_hash, r2.proof_hash)

    def test_z3_sat_contrato_valido(self):
        c = _make_contract()
        r = audit_contract(c)
        self.assertTrue(r.z3_sat, "Z3 debe encontrar modelo SAT para contrato válido")

    def test_z3_unsat_objeto_vacio(self):
        c = _make_contract(objeto_del_contrato="Corto")  # < 20 chars → z3 UNSAT
        r = audit_contract(c)
        self.assertFalse(r.z3_sat, "Z3 debe ser UNSAT cuando objeto < 20 chars")


class TestDetectAnomalies(unittest.TestCase):
    """detect_anomalies: fraccionamiento + concentración."""

    def _contracts_fraccionamiento(self) -> list[dict]:
        """4 contratos del mismo contratista en enero 2025, suma > LIMITE_LICITACION."""
        valor_individual = str(int(LIMITE_LICITACION * 0.3))  # 30% cada uno → 120% total
        return [
            _make_contract(
                documento_contratista="900999001",
                nombre_del_contratista="EMPRESA SOSPECHOSA S.A.S",
                valor_del_contrato=valor_individual,
                fecha_de_firma=f"2025-01-{10+i:02d}T00:00:00",
            )
            for i in range(4)
        ]

    def test_detecta_fraccionamiento(self):
        contratos = self._contracts_fraccionamiento()
        report = detect_anomalies(contratos, entity="ALCALDIA TEST", threshold_fraccionamiento=3)
        self.assertGreater(len(report.fraccionamiento), 0)
        self.assertGreater(report.anomaly_count, 0)

    def test_sin_fraccionamiento_no_alerta(self):
        contratos = [
            _make_contract(
                documento_contratista=f"900{i:06d}",
                nombre_del_contratista=f"EMPRESA {i}",
                valor_del_contrato=str(int(LIMITE_ABREVIADA * 0.5)),
            )
            for i in range(5)
        ]
        report = detect_anomalies(contratos, entity="ALCALDIA TEST", threshold_fraccionamiento=4)
        self.assertEqual(len(report.fraccionamiento), 0)

    def test_detecta_concentracion(self):
        # 7 de 10 contratos van al mismo contratista → 70% > 50% umbral
        contratos = [
            _make_contract(
                documento_contratista="900MONO001",
                nombre_del_contratista="MONOPOLIO S.A.S",
            )
            for _ in range(7)
        ] + [
            _make_contract(
                documento_contratista=f"900{i:06d}",
                nombre_del_contratista=f"OTRA EMPRESA {i}",
            )
            for i in range(3)
        ]
        report = detect_anomalies(contratos, entity="ALCALDIA TEST", threshold_concentracion=0.5)
        self.assertGreater(len(report.concentracion), 0)
        alerta = report.concentracion[0]
        self.assertAlmostEqual(alerta["porcentaje"], 70.0, places=0)

    def test_proof_hash_anomalias_determinista(self):
        contratos = self._contracts_fraccionamiento()
        r1 = detect_anomalies(contratos, entity="TEST")
        r2 = detect_anomalies(contratos, entity="TEST")
        self.assertEqual(r1.proof_hash, r2.proof_hash)


class TestFetchContracts(unittest.TestCase):
    """fetch_contracts — mock para evitar dependencia de red en tests unitarios."""

    @patch("tools.secop.httpx.get")
    def test_fetch_con_entity_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [_make_contract()]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_contracts(entity="ALCALDIA DE MEDELLIN", limit=5)
        self.assertEqual(len(result), 1)
        # URL construida manualmente — verificar que contiene $where y la entidad
        called_url = mock_get.call_args[0][0]
        self.assertIn("$where", called_url)
        self.assertIn("ALCALDIA DE MEDELLIN", called_url)

    @patch("tools.secop.httpx.get")
    def test_fetch_error_retorna_lista_vacia(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = fetch_contracts()
        self.assertEqual(result, [])


class TestIntegracionReal(unittest.TestCase):
    """
    Tests de integración con SECOP II real.
    Solo corren si SECOP_INTEGRATION=1.
    """

    @unittest.skipUnless(os.getenv("SECOP_INTEGRATION") == "1", "set SECOP_INTEGRATION=1")
    def test_fetch_y_auditar_contratos_reales(self):
        contratos = fetch_contracts(limit=5)
        self.assertGreater(len(contratos), 0, "SECOP II debe retornar contratos")
        for c in contratos:
            r = audit_contract(c)
            self.assertIsInstance(r.proof_hash, str)
            self.assertEqual(len(r.proof_hash), 64)  # sha256 hex
            self.assertEqual(len(r.rules), 6)

    @unittest.skipUnless(os.getenv("SECOP_INTEGRATION") == "1", "set SECOP_INTEGRATION=1")
    def test_detect_anomalies_contratos_reales_medellin(self):
        contratos = fetch_contracts(entity="ALCALDIA DE MEDELLIN", limit=50)
        if contratos:
            report = detect_anomalies(contratos, entity="ALCALDIA DE MEDELLIN")
            self.assertIsInstance(report.proof_hash, str)
            print(f"\n[REAL] ALCALDÍA MEDELLÍN: {report.total_contracts} contratos, "
                  f"{report.anomaly_count} anomalías")


if __name__ == "__main__":
    unittest.main(verbosity=2)
