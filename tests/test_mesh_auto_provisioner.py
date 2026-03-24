import unittest
import json
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.mesh_auto_provisioner import AutoProvisioner

class TestAutoProvisionerExtended(unittest.TestCase):
    def setUp(self):
        # Aislar el entorno completamente usando tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_nodes_path = Path(self.temp_dir.name) / "nodes.json"
        self.test_log_path = Path(self.temp_dir.name) / "provisioner.jsonl"
        
        # Parchear las rutas al nivel del módulo
        self.patcher1 = patch("core.mesh_auto_provisioner.NODES_JSON_PATH", self.test_nodes_path)
        self.patcher2 = patch("core.mesh_auto_provisioner.PROVISIONER_LOG_PATH", self.test_log_path)
        self.patcher1.start()
        self.patcher2.start()
        
        self.fake_nodes = {
            "local-qwen": {
                "provider": "ollama",
                "specialty": "code_generation",
                "context_window": 32000,
                "active_tasks": 0
            },
            "cerebras-llama": {
                "provider": "cerebras",
                "specialty": "fast_inference",
                "context_window": 128000,
                "active_tasks": 2
            }
        }
        with open(self.test_nodes_path, "w", encoding="utf-8") as f:
            json.dump(self.fake_nodes, f)
            
        AutoProvisioner._instance = None
    
    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        AutoProvisioner._instance = None
        self.temp_dir.cleanup()

    def test_01_singleton(self):
        """1. Singleton: dos instancias son la misma"""
        prov1 = AutoProvisioner()
        prov2 = AutoProvisioner()
        self.assertIs(prov1, prov2)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_02_provision_returns_string(self, mock_optimizer):
        """2. provision() retorna un string no vacio"""
        mock_optimizer.return_value = "local-qwen"
        prov = AutoProvisioner()
        res = prov.provision("code", 1000)
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_03_provision_returns_known_node(self, mock_optimizer):
        """3. provision() retorna un node_id conocido"""
        mock_optimizer.return_value = "cerebras-llama"
        prov = AutoProvisioner()
        res = prov.provision("fast", 500)
        self.assertEqual(res, "cerebras-llama")

    def test_04_deprovision_reduces_active(self):
        """4. deprovision() reduce active_provisions"""
        prov = AutoProvisioner()
        prov.deprovision("cerebras-llama")
        with open(self.test_nodes_path, "r") as f:
            nodes = json.load(f)
        # Tenía 2 inicialmente, debe bajar a 1
        self.assertEqual(nodes["cerebras-llama"]["active_tasks"], 1)

    def test_05_get_active_provisions_type(self):
        """5. get_active_provisions() retorna dict"""
        prov = AutoProvisioner()
        active = prov.get_active_provisions()
        self.assertIsInstance(active, dict)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_06_provision_deprovision_balance(self, mock_optimizer):
        """6. provision + deprovision = balance cero"""
        mock_optimizer.return_value = "local-qwen"
        prov = AutoProvisioner()
        prov.provision("test", 100)
        self.assertEqual(prov.get_active_provisions()["local-qwen"], 1)
        prov.deprovision("local-qwen")
        self.assertEqual(prov.get_active_provisions()["local-qwen"], 0)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_07_thread_safety(self, mock_optimizer):
        """7. Thread safety: 5 threads provisionando simultaneamente"""
        mock_optimizer.return_value = "local-qwen"
        prov = AutoProvisioner()
        
        def worker():
            for _ in range(20):
                prov.provision("spam", 100)
                
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        with open(self.test_nodes_path, "r") as f:
            nodes = json.load(f)
        self.assertEqual(nodes["local-qwen"]["active_tasks"], 100)
        self.assertEqual(prov.get_active_provisions()["local-qwen"], 100)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_08_different_task_types(self, mock_optimizer):
        """8. provision con diferentes task_types (code, research, docs)"""
        mock_optimizer.return_value = "local-qwen"
        prov = AutoProvisioner()
        prov.provision("code", 100)
        prov.provision("research", 100)
        prov.provision("docs", 100)
        self.assertEqual(mock_optimizer.call_count, 3)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_09_different_context_tokens(self, mock_optimizer):
        """9. provision con diferentes context_tokens (512, 4096, 32000)"""
        prov = AutoProvisioner()
        mock_optimizer.return_value = "cerebras-llama"
        prov.provision("x", 512)
        prov.provision("y", 4096)
        prov.provision("z", 32000)
        calls = mock_optimizer.call_args_list
        self.assertEqual(calls[0][0][0], 512)
        self.assertEqual(calls[1][0][0], 4096)
        self.assertEqual(calls[2][0][0], 32000)

    @patch("core.mesh_cost_optimizer.CostOptimizer.get_cheapest_node")
    def test_10_consistency_multiple_ops(self, mock_optimizer):
        """10. get_active_provisions() es consistente despues de multiples ops"""
        mock_optimizer.return_value = "cerebras-llama"
        prov = AutoProvisioner()
        
        for _ in range(10):
            prov.provision("test", 10)
        for _ in range(3):
            prov.deprovision("cerebras-llama")
            
        active = prov.get_active_provisions()
        # cerebras-llama ya tenia 2, sumamos 10 = 12, restamos 3 = 9
        # Pero mock optimizer ignora el estado inicial en disco si estamos mirando active_provisions cache,
        # sin embargo self._active_tasks empieza vacio hasta cargar, active_tasks += 1
        # Así que the in-memory dictionary 'active' returns relative updates or reads correct
        # Para evitar problemas con inicializacion de ram (si no arranca cargando JSON al vuelo),
        # usamos test simple
        pass
        
        # Corrección precisa:
        active_cnt = prov.get_active_provisions().get("cerebras-llama", 0)
        self.assertEqual(active_cnt, 9)
        
        with open(self.test_nodes_path, "r") as f:
            nodes = json.load(f)
        # Disco subio 10 y bajo 3 (7 delta) sobre la base inicial 2. Result = 9.
        self.assertEqual(nodes["cerebras-llama"]["active_tasks"], 9)
        
if __name__ == "__main__":
    unittest.main()
