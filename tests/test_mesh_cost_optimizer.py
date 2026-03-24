import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import core.mesh_cost_optimizer as optimizer
from core.mesh_cost_optimizer import CostOptimizer

class TestMeshCostOptimizer(unittest.TestCase):
    def setUp(self):
        # Reiniciar singleton
        CostOptimizer._instance = None
        self.optimizer = CostOptimizer()
        self.temp_dir = TemporaryDirectory()
        self.mock_nodes_path = Path(self.temp_dir.name) / "nodes.json"
        
        # Sobreescribir el path original para pruebas
        self.original_path = optimizer.NODES_JSON_PATH
        optimizer.NODES_JSON_PATH = self.mock_nodes_path

        # Mock data (1 falso local, 1 falso deepseek)
        self.mock_data = {
            "local-qwen": {
                "node_id": "local-qwen",
                "provider": "ollama",
                "specialty": "code_generation_local",
                "context_window": 32768
            },
            "deepseek-coder": {
                "node_id": "deepseek-coder",
                "provider": "deepseek",
                "specialty": "complex_coding",
                "context_window": 64000
            },
            "cerebras-llama": {
                "node_id": "cerebras-llama",
                "provider": "cerebras",
                "specialty": "ultra_fast_research",
                "context_window": 128000
            }
        }
        with open(self.mock_nodes_path, "w") as f:
            json.dump(self.mock_data, f)

    def tearDown(self):
        optimizer.NODES_JSON_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_singleton(self):
        """Testea que CostOptimizer sea un singleton puro (__new__)"""
        opt1 = CostOptimizer()
        opt2 = CostOptimizer()
        self.assertIs(opt1, opt2, "CostOptimizer no es Singleton!")

    def test_pricing_table(self):
        """Testea la inclusión de precios requeridos reales"""
        self.assertEqual(CostOptimizer.PRICING_TABLE.get("deepseek"), 0.001)
        self.assertEqual(CostOptimizer.PRICING_TABLE.get("cerebras"), 0.0)
        self.assertEqual(CostOptimizer.PRICING_TABLE.get("ollama"), 0.0)

    def test_get_cheapest_fallback(self):
        """Testea fallback a local cuando no hay registry o contexto coincide"""
        # Romper filesystem
        self.mock_nodes_path.unlink()
        self.optimizer._nodes_cache = {}
        
        res = self.optimizer.get_cheapest_node(2000, "general")
        self.assertEqual(res, "local-qwen")

    def test_get_cheapest_context_filter(self):
        """Testea seleccion filtrando x context_window estricta"""
        # Requiere 100k -> Solo Cerebras (128k) pasa
        res = self.optimizer.get_cheapest_node(100000, "anything")
        self.assertEqual(res, "cerebras-llama")

    def test_get_cheapest_priority_and_specialty(self):
        """Testea que prioriza costo 0.0 y hace match de especialidad"""
        # Requiere 10k context (todos aplican) - Deberia agarrar Ollama por prioridad, 
        # PERO si ponemos "research" deberia elegir cerebras por especialidad.
        res = self.optimizer.get_cheapest_node(10000, "research")
        self.assertEqual(res, "cerebras-llama")

        # Sin especialidad o con especialidad pura de local -> ollama
        res_local = self.optimizer.get_cheapest_node(10000, "code_generation_local")
        self.assertEqual(res_local, "local-qwen")

if __name__ == "__main__":
    unittest.main()
