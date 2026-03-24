import unittest
from unittest.mock import patch, MagicMock
from core.local_node_runner import LocalNodeRunner

class TestLocalNodeRunner(unittest.TestCase):
    def setUp(self):
        # Reinicializa la instancia de LocalNodeRunner para cada test
        LocalNodeRunner._instance = None

    def tearDown(self):
        # Limpia la instancia de LocalNodeRunner después de cada test
        LocalNodeRunner._instance = None

    def test_imports_correctos(self):
        # Verifica que se importen las clases y métodos correctamente
        self.assertTrue(hasattr(LocalNodeRunner, 'run'))
        self.assertTrue(hasattr(LocalNodeRunner, 'stop'))

    def test_clase_local_node_runner(self):
        # Verifica que la clase LocalNodeRunner se cree correctamente
        runner = LocalNodeRunner()
        self.assertIsInstance(runner, LocalNodeRunner)

    def test_metodo_run(self):
        # Verifica que el método run se ejecute correctamente
        runner = LocalNodeRunner()
        with patch.object(runner, 'run_node') as mock_run_node:
            runner.run()
            mock_run_node.assert_called_once()

    def test_metodo_stop(self):
        # Verifica que el método stop se ejecute correctamente
        runner = LocalNodeRunner()
        with patch.object(runner, 'stop_node') as mock_stop_node:
            runner.stop()
            mock_stop_node.assert_called_once()

    def test_caso_edge_none(self):
        # Verifica que se maneje el caso edge donde se pasa None como parámetro
        with self.assertRaises(TypeError):
            LocalNodeRunner(None)

    def test_caso_edge_vacio(self):
        # Verifica que se maneje el caso edge donde se pasa un parámetro vacío
        with self.assertRaises(TypeError):
            LocalNodeRunner('')

    def test_caso_edge_tipo_incorrecto(self):
        # Verifica que se maneje el caso edge donde se pasa un parámetro de tipo incorrecto
        with self.assertRaises(TypeError):
            LocalNodeRunner(123)

    def test_singleton(self):
        # Verifica que la clase LocalNodeRunner sea un singleton
        runner1 = LocalNodeRunner()
        runner2 = LocalNodeRunner()
        self.assertEqual(runner1, runner2)

if __name__ == '__main__':
    unittest.main()