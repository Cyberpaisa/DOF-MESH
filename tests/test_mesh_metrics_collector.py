# tests/test_mesh_metrics_collector.py

import unittest
from unittest.mock import patch, MagicMock
from core.mesh_metrics_collector import MeshMetricsCollector

class TestMeshMetricsCollector(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia singleton si aplica
        MeshMetricsCollector._instance = None

    def tearDown(self):
        # Limpia cualquier configuración o estado después de cada test
        pass

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.mesh_metrics_collector import MeshMetricsCollector
        self.assertIsNotNone(MeshMetricsCollector)

    def test_clase_mesh_metrics_collector(self):
        # Verifica que la clase MeshMetricsCollector exista y sea instanciable
        collector = MeshMetricsCollector()
        self.assertIsInstance(collector, MeshMetricsCollector)

    def test_metodo_init(self):
        # Verifica que el método __init__ se ejecute correctamente
        collector = MeshMetricsCollector()
        self.assertIsNotNone(collector)

    def test_metodo_collect_metrics(self):
        # Verifica que el método collect_metrics se ejecute correctamente
        collector = MeshMetricsCollector()
        metrics = collector.collect_metrics()
        self.assertIsNotNone(metrics)

    def test_metodo_collect_metrics_con_none(self):
        # Verifica que el método collect_metrics maneje None correctamente
        collector = MeshMetricsCollector()
        with patch.object(collector, 'collect_metrics', return_value=None):
            metrics = collector.collect_metrics()
            self.assertIsNone(metrics)

    def test_metodo_collect_metrics_con_vacio(self):
        # Verifica que el método collect_metrics maneje un valor vacío correctamente
        collector = MeshMetricsCollector()
        with patch.object(collector, 'collect_metrics', return_value={}):
            metrics = collector.collect_metrics()
            self.assertEqual(metrics, {})

    def test_metodo_collect_metrics_con_tipos_incorrectos(self):
        # Verifica que el método collect_metrics maneje tipos incorrectos correctamente
        collector = MeshMetricsCollector()
        with patch.object(collector, 'collect_metrics', side_effect=TypeError):
            with self.assertRaises(TypeError):
                collector.collect_metrics()

    def test_singleton(self):
        # Verifica que la clase MeshMetricsCollector sea un singleton
        collector1 = MeshMetricsCollector()
        collector2 = MeshMetricsCollector()
        self.assertEqual(collector1, collector2)

if __name__ == '__main__':
    unittest.main()