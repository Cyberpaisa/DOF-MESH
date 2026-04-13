"""Tests para Registraduría CSV client."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from registraduria import (
    get_results,
    get_abstention_by_zone,
    compare_elections,
    _build_csv_url,
    _parse_csv_response,
)


SAMPLE_CSV = """DEPARTAMENTO,MUNICIPIO,POTENCIAL_ELECTORAL,TOTAL_VOTOS
ANTIOQUIA,MEDELLIN,1800000,900000
ANTIOQUIA,BELLO,350000,140000
CUNDINAMARCA,BOGOTA,5000000,2500000
ANTIOQUIA,ITAGUI,200000,80000
"""


class TestBuildCsvUrl(unittest.TestCase):

    def test_url_contains_year(self):
        url = _build_csv_url(2023)
        self.assertIn("2023", url)

    def test_url_contains_base(self):
        url = _build_csv_url(2023)
        self.assertIn("registraduria", url)

    def test_default_election_type(self):
        url = _build_csv_url(2023)
        self.assertIn("alcalde", url)

    def test_custom_election_type(self):
        url = _build_csv_url(2022, "presidente")
        self.assertIn("presidente", url)


class TestParseCsvResponse(unittest.TestCase):

    def test_parse_returns_list(self):
        rows = _parse_csv_response(SAMPLE_CSV)
        self.assertIsInstance(rows, list)

    def test_parse_row_count(self):
        rows = _parse_csv_response(SAMPLE_CSV)
        self.assertEqual(len(rows), 4)

    def test_parse_has_department_key(self):
        rows = _parse_csv_response(SAMPLE_CSV)
        self.assertIn("DEPARTAMENTO", rows[0])

    def test_parse_empty_csv(self):
        rows = _parse_csv_response("DEPARTAMENTO,MUNICIPIO\n")
        self.assertEqual(rows, [])


class TestGetResults(unittest.TestCase):

    def _mock_response(self, text=SAMPLE_CSV, status=200):
        mock_resp = MagicMock()
        mock_resp.text = text
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("registraduria.httpx.get")
    def test_get_results_filters_by_department(self, mock_get):
        mock_get.return_value = self._mock_response()
        result = get_results(2023, department="ANTIOQUIA")
        self.assertEqual(result["department"], "ANTIOQUIA")
        # Solo filas de ANTIOQUIA (3)
        self.assertEqual(result["total"], 3)

    @patch("registraduria.httpx.get")
    def test_get_results_filters_by_municipality(self, mock_get):
        mock_get.return_value = self._mock_response()
        result = get_results(2023, department="ANTIOQUIA", municipality="MEDELLIN")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["rows"][0]["MUNICIPIO"], "MEDELLIN")

    @patch("registraduria.httpx.get")
    def test_get_results_case_insensitive(self, mock_get):
        mock_get.return_value = self._mock_response()
        result = get_results(2023, department="antioquia")
        self.assertEqual(result["total"], 3)

    @patch("registraduria.httpx.get")
    def test_get_results_no_match(self, mock_get):
        mock_get.return_value = self._mock_response()
        result = get_results(2023, department="CHOCO")
        self.assertEqual(result["total"], 0)

    @patch("registraduria.httpx.get")
    def test_get_results_returns_year(self, mock_get):
        mock_get.return_value = self._mock_response()
        result = get_results(2023)
        self.assertEqual(result["year"], 2023)


class TestGetAbstentionByZone(unittest.TestCase):

    @patch("registraduria.httpx.get")
    def test_abstention_calculation(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_abstention_by_zone(2023, "MEDELLIN")
        # 900000/1800000 = 50% participación, 50% abstención
        self.assertEqual(result["participacion_pct"], 50.0)
        self.assertEqual(result["abstension_pct"], 50.0)

    @patch("registraduria.httpx.get")
    def test_abstention_returns_municipality(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_abstention_by_zone(2023, "MEDELLIN")
        self.assertEqual(result["municipality"], "MEDELLIN")
        self.assertEqual(result["year"], 2023)

    @patch("registraduria.httpx.get")
    def test_abstention_zero_inscritos(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "DEPARTAMENTO,MUNICIPIO,POTENCIAL_ELECTORAL,TOTAL_VOTOS\n"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_abstention_by_zone(2023, "XYZTOWN")
        self.assertEqual(result["participacion_pct"], 0.0)
        self.assertEqual(result["abstension_pct"], 100.0)


class TestCompareElections(unittest.TestCase):

    CSV_2019 = """DEPARTAMENTO,MUNICIPIO,POTENCIAL_ELECTORAL,TOTAL_VOTOS
ANTIOQUIA,MEDELLIN,1700000,680000
"""
    CSV_2023 = """DEPARTAMENTO,MUNICIPIO,POTENCIAL_ELECTORAL,TOTAL_VOTOS
ANTIOQUIA,MEDELLIN,1800000,900000
"""

    @patch("registraduria.httpx.get")
    def test_compare_returns_both_years(self, mock_get):
        mock_resp_2019 = MagicMock()
        mock_resp_2019.text = self.CSV_2019
        mock_resp_2019.raise_for_status = MagicMock()

        mock_resp_2023 = MagicMock()
        mock_resp_2023.text = self.CSV_2023
        mock_resp_2023.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_resp_2019, mock_resp_2023]
        result = compare_elections(2019, 2023, "MEDELLIN")
        self.assertEqual(result["year1"], 2019)
        self.assertEqual(result["year2"], 2023)

    @patch("registraduria.httpx.get")
    def test_compare_trend_mejora(self, mock_get):
        # 2019: 680000/1700000 = 40% participación, 60% abstención
        # 2023: 900000/1800000 = 50% participación, 50% abstención
        # delta_abstension = 50 - 60 = -10 → mejora
        mock_resp_2019 = MagicMock()
        mock_resp_2019.text = self.CSV_2019
        mock_resp_2019.raise_for_status = MagicMock()

        mock_resp_2023 = MagicMock()
        mock_resp_2023.text = self.CSV_2023
        mock_resp_2023.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_resp_2019, mock_resp_2023]
        result = compare_elections(2019, 2023, "MEDELLIN")
        self.assertEqual(result["trend"], "mejora")

    @patch("registraduria.httpx.get")
    def test_compare_delta_value(self, mock_get):
        mock_resp_2019 = MagicMock()
        mock_resp_2019.text = self.CSV_2019
        mock_resp_2019.raise_for_status = MagicMock()

        mock_resp_2023 = MagicMock()
        mock_resp_2023.text = self.CSV_2023
        mock_resp_2023.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_resp_2019, mock_resp_2023]
        result = compare_elections(2019, 2023, "MEDELLIN")
        self.assertIn("delta_abstension", result)
        self.assertIsInstance(result["delta_abstension"], float)


if __name__ == "__main__":
    unittest.main()
