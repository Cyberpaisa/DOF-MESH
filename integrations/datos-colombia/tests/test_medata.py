"""Tests para MEData CKAN client."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# CRÍTICO: sys.path para directorio con guión
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from medata import fetch_datasets, get_dataset, search_datasets


class TestFetchDatasets(unittest.TestCase):

    def _make_ckan_response(self, results=None, count=0):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "result": {
                "results": results or [],
                "count": count,
            },
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("medata.httpx.get")
    def test_fetch_datasets_no_category(self, mock_get):
        mock_get.return_value = self._make_ckan_response(
            results=[{"id": "abc", "title": "Dataset 1"}], count=1
        )
        result = fetch_datasets()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["result"]), 1)
        self.assertEqual(result["count"], 1)

    @patch("medata.httpx.get")
    def test_fetch_datasets_with_category(self, mock_get):
        mock_get.return_value = self._make_ckan_response(
            results=[{"id": "xyz", "title": "Movilidad Dataset"}], count=1
        )
        result = fetch_datasets(category="movilidad", limit=5)
        self.assertTrue(result["success"])
        # Verificar que se pasó el parámetro fq
        call_kwargs = mock_get.call_args[1]
        self.assertIn("fq", call_kwargs.get("params", {}))
        self.assertEqual(call_kwargs["params"]["fq"], "tags:movilidad")

    @patch("medata.httpx.get")
    def test_fetch_datasets_empty(self, mock_get):
        mock_get.return_value = self._make_ckan_response(results=[], count=0)
        result = fetch_datasets()
        self.assertEqual(result["result"], [])
        self.assertEqual(result["count"], 0)

    @patch("medata.httpx.get")
    def test_fetch_datasets_limit(self, mock_get):
        mock_get.return_value = self._make_ckan_response()
        fetch_datasets(limit=20)
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs["params"]["rows"], 20)

    @patch("medata.httpx.get")
    def test_fetch_datasets_http_error(self, mock_get):
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP 500")
        with self.assertRaises(Exception):
            fetch_datasets()


class TestGetDataset(unittest.TestCase):

    @patch("medata.httpx.get")
    def test_get_dataset_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "result": {"id": "test-id", "title": "Test Dataset", "resources": []},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_dataset("test-id")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["id"], "test-id")

    @patch("medata.httpx.get")
    def test_get_dataset_passes_id(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "result": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        get_dataset("mi-dataset-nombre")
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs["params"]["id"], "mi-dataset-nombre")

    @patch("medata.httpx.get")
    def test_get_dataset_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": False, "result": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_dataset("nonexistent")
        self.assertFalse(result["success"])


class TestSearchDatasets(unittest.TestCase):

    @patch("medata.httpx.get")
    def test_search_returns_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "result": {
                "results": [{"id": "r1"}, {"id": "r2"}],
                "count": 2,
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_datasets("transporte")
        self.assertEqual(len(result["result"]), 2)
        self.assertEqual(result["query"], "transporte")

    @patch("medata.httpx.get")
    def test_search_passes_query(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "result": {"results": [], "count": 0}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        search_datasets("educacion superior", limit=3)
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs["params"]["q"], "educacion superior")
        self.assertEqual(call_kwargs["params"]["rows"], 3)

    @patch("medata.httpx.get")
    def test_search_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "result": {"results": [], "count": 0}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_datasets("zzznoresults")
        self.assertEqual(result["result"], [])
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
