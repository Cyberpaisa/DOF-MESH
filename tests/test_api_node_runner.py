import unittest
from unittest.mock import Mock
from core.api_node_runner import ApiNodeRunner

class TestApiNodeRunner(unittest.TestCase):
    def setUp(self):
        ApiNodeRunner._instance = None  # Reset singleton

    def tearDown(self):
        ApiNodeRunner._instance = None  # Reset singleton

    def test_imports_correctos(self):
        # Verificar que se importan las clases y métodos correctamente
        self.assertTrue(hasattr(ApiNodeRunner, 'run'))
        self.assertTrue(hasattr(ApiNodeRunner, 'stop'))

    def test_clase_api_node_runner(self):
        # Verificar que la clase ApiNodeRunner se crea correctamente
        runner = ApiNodeRunner()
        self.assertIsInstance(runner, ApiNodeRunner)

    def test_metodo_run(self):
        # Verificar que el método run se ejecuta correctamente
        runner = ApiNodeRunner()
        runner.run()
        self.assertTrue(runner.is_running)

    def test_metodo_stop(self):
        # Verificar que el método stop se ejecuta correctamente
        runner = ApiNodeRunner()
        runner.run()
        runner.stop()
        self.assertFalse(runner.is_running)

    def test_caso_edge_none(self):
        # Verificar que se maneja correctamente el caso en que se pasa None como parámetro
        runner = ApiNodeRunner()
        with self.assertRaises(TypeError):
            runner.run(None)

    def test_caso_edge_vacio(self):
        # Verificar que se maneja correctamente el caso en que se pasa un parámetro vacío
        runner = ApiNodeRunner()
        with self.assertRaises(ValueError):
            runner.run("")

    def test_caso_edge_tipo_incorrecto(self):
        # Verificar que se maneja correctamente el caso en que se pasa un parámetro de tipo incorrecto
        runner = ApiNodeRunner()
        with self.assertRaises(TypeError):
            runner.run(123)

    def test_singleton(self):
        # Verificar que la clase ApiNodeRunner es un singleton
        runner1 = ApiNodeRunner()
        runner2 = ApiNodeRunner()
        self.assertEqual(runner1, runner2)

if __name__ == '__main__':
    unittest.main()