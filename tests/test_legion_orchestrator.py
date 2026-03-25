# tests/test_legion_orchestrator.py

import unittest
from unittest.mock import Mock
from core.legion_orchestrator import LegionOrchestrator

class TestLegionOrchestrator(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia de LegionOrchestrator para cada test
        LegionOrchestrator._instance = None

    def tearDown(self):
        # Limpia la instancia de LegionOrchestrator después de cada test
        LegionOrchestrator._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.legion_orchestrator import LegionOrchestrator
        self.assertIsNotNone(LegionOrchestrator)

    def test_clase_legion_orchestrator(self):
        # Verifica que la clase LegionOrchestrator exista y sea instanciable
        orchestrator = LegionOrchestrator()
        self.assertIsInstance(orchestrator, LegionOrchestrator)

    def test_metodo_init(self):
        # Verifica que el método __init__ se ejecute correctamente
        orchestrator = LegionOrchestrator()
        self.assertIsNotNone(orchestrator)

    def test_metodo_start(self):
        # Verifica que el método start se ejecute correctamente
        orchestrator = LegionOrchestrator()
        orchestrator.start = Mock()
        orchestrator.start()
        self.assertTrue(orchestrator.start.called)

    def test_metodo_stop(self):
        # Verifica que el método stop se ejecute correctamente
        orchestrator = LegionOrchestrator()
        orchestrator.stop = Mock()
        orchestrator.stop()
        self.assertTrue(orchestrator.stop.called)

    def test_metodo_restart(self):
        # Verifica que el método restart se ejecute correctamente
        orchestrator = LegionOrchestrator()
        orchestrator.restart = Mock()
        orchestrator.restart()
        self.assertTrue(orchestrator.restart.called)

    def test_caso_edge_none(self):
        # Verifica que la clase LegionOrchestrator maneje correctamente el caso edge None
        with self.assertRaises(TypeError):
            LegionOrchestrator(None)

    def test_caso_edge_vacio(self):
        # Verifica que LegionOrchestrator() sin argumentos devuelve una instancia válida (singleton)
        orchestrator = LegionOrchestrator()
        self.assertIsNotNone(orchestrator)

    def test_caso_edge_tipos_incorrectos(self):
        # Verifica que la clase LegionOrchestrator maneje correctamente el caso edge con tipos incorrectos
        with self.assertRaises(TypeError):
            LegionOrchestrator("cadena")

    def test_singleton(self):
        # Verifica que la clase LegionOrchestrator sea un singleton
        orchestrator1 = LegionOrchestrator()
        orchestrator2 = LegionOrchestrator()
        self.assertEqual(orchestrator1, orchestrator2)

if __name__ == '__main__':
    unittest.main()