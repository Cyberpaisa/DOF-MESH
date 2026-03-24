# tests/test_crew_runner.py

import unittest
from unittest.mock import Mock
from core.crew_runner import CrewRunner

class TestCrewRunner(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia de CrewRunner para cada test
        CrewRunner._instance = None

    def tearDown(self):
        # Limpia la instancia de CrewRunner después de cada test
        CrewRunner._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports en core/crew_runner.py sean correctos
        try:
            from core.crew_runner import CrewRunner
        except ImportError:
            self.fail("Error al importar CrewRunner")

    def test_clase_crew_runner(self):
        # Verifica que la clase CrewRunner exista y sea instanciable
        self.assertTrue(hasattr(CrewRunner, '__init__'))
        crew_runner = CrewRunner()
        self.assertIsInstance(crew_runner, CrewRunner)

    def test_metodo_run(self):
        # Verifica que el método run exista y sea callable
        crew_runner = CrewRunner()
        self.assertTrue(hasattr(crew_runner, 'run'))
        self.assertTrue(callable(crew_runner.run))

    def test_metodo_stop(self):
        # Verifica que el método stop exista y sea callable
        crew_runner = CrewRunner()
        self.assertTrue(hasattr(crew_runner, 'stop'))
        self.assertTrue(callable(crew_runner.stop))

    def test_caso_edge_none(self):
        # Verifica que el constructor de CrewRunner maneje None correctamente
        with self.assertRaises(TypeError):
            CrewRunner(None)

    def test_caso_edge_vacio(self):
        # Verifica que el constructor de CrewRunner maneje valores vacíos correctamente
        with self.assertRaises(TypeError):
            CrewRunner("")

    def test_caso_edge_tipos_incorrectos(self):
        # Verifica que el constructor de CrewRunner maneje tipos incorrectos correctamente
        with self.assertRaises(TypeError):
            CrewRunner(123)

    def test_singleton(self):
        # Verifica que CrewRunner sea un singleton
        crew_runner1 = CrewRunner()
        crew_runner2 = CrewRunner()
        self.assertEqual(crew_runner1, crew_runner2)

if __name__ == '__main__':
    unittest.main()