# tests/test_autonomous_planner.py

import unittest
from unittest.mock import MagicMock
from core.autonomous_planner import AutonomousPlanner, PlanningError

class TestAutonomousPlanner(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia de AutonomousPlanner para cada test
        AutonomousPlanner._instance = None

    def tearDown(self):
        # Limpia la instancia de AutonomousPlanner después de cada test
        AutonomousPlanner._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.autonomous_planner import AutonomousPlanner
        self.assertIsNotNone(AutonomousPlanner)

    def test_clase_autonomous_planner(self):
        # Verifica que la clase AutonomousPlanner exista y sea instanciable
        planner = AutonomousPlanner()
        self.assertIsInstance(planner, AutonomousPlanner)

    def test_metodo_plan(self):
        # Verifica que el método plan exista y sea callable
        planner = AutonomousPlanner()
        self.assertTrue(callable(planner.plan))

    def test_metodo_plan_con_none(self):
        # Verifica que el método plan lance un error con None como entrada
        planner = AutonomousPlanner()
        with self.assertRaises(PlanningError):
            planner.plan(None)

    def test_metodo_plan_con_vacio(self):
        # Verifica que el método plan lance un error con una lista vacía como entrada
        planner = AutonomousPlanner()
        with self.assertRaises(PlanningError):
            planner.plan([])

    def test_metodo_plan_con_tipos_incorrectos(self):
        # Verifica que el método plan lance un error con tipos incorrectos como entrada
        planner = AutonomousPlanner()
        with self.assertRaises(PlanningError):
            planner.plan("cadena")

    def test_metodo_plan_con_entrada_valida(self):
        # Verifica que el método plan devuelva un resultado con una entrada válida
        planner = AutonomousPlanner()
        resultado = planner.plan([1, 2, 3])
        self.assertIsNotNone(resultado)

    def test_singleton(self):
        # Verifica que la clase AutonomousPlanner sea un singleton
        planner1 = AutonomousPlanner()
        planner2 = AutonomousPlanner()
        self.assertEqual(planner1, planner2)

if __name__ == '__main__':
    unittest.main()