# tests/test_claude_node_runner.py

import unittest
from unittest.mock import patch, MagicMock
from core.claude_node_runner import ClaudeNodeRunner

class TestClaudeNodeRunner(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia singleton si aplica
        if hasattr(ClaudeNodeRunner, '_instance'):
            del ClaudeNodeRunner._instance

    def tearDown(self):
        # Limpia cualquier configuración o estado después de cada test
        pass

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.claude_node_runner import ClaudeNodeRunner
        self.assertIsNotNone(ClaudeNodeRunner)

    def test_clase_y_metodos_publicos(self):
        # Verifica que la clase y métodos públicos estén definidos
        self.assertTrue(hasattr(ClaudeNodeRunner, 'run'))
        self.assertTrue(hasattr(ClaudeNodeRunner, 'stop'))

    def test_inicializacion(self):
        # Verifica que la inicialización sea correcta
        runner = ClaudeNodeRunner()
        self.assertIsNotNone(runner)

    def test_run_con_parametros_validos(self):
        # Verifica que el método run funcione con parámetros válidos
        runner = ClaudeNodeRunner()
        with patch.object(runner, '_run_node') as mock_run_node:
            runner.run('param1', 'param2')
            mock_run_node.assert_called_once_with('param1', 'param2')

    def test_run_con_parametros_invalidos(self):
        # Verifica que el método run maneje parámetros inválidos
        runner = ClaudeNodeRunner()
        with self.assertRaises(TypeError):
            runner.run(123, 'param2')

    def test_stop_con_node_en_ejecucion(self):
        # Verifica que el método stop funcione cuando el nodo está en ejecución
        runner = ClaudeNodeRunner()
        runner._running = True  # Simula que el nodo está en ejecución
        with patch.object(runner, '_stop_node') as mock_stop_node:
            runner.stop()
            mock_stop_node.assert_called_once()

    def test_stop_con_node_no_en_ejecucion(self):
        # Verifica que el método stop no haga nada cuando el nodo no está en ejecución
        runner = ClaudeNodeRunner()
        with patch.object(runner, '_stop_node') as mock_stop_node:
            runner.stop()
            mock_stop_node.assert_not_called()

    def test_caso_edge_none(self):
        # Verifica que el método run maneje el caso edge con None
        runner = ClaudeNodeRunner()
        with self.assertRaises(TypeError):
            runner.run(None, 'param2')

    def test_caso_edge_vacio(self):
        # Verifica que el método run maneje el caso edge con parámetros vacíos
        runner = ClaudeNodeRunner()
        with self.assertRaises(TypeError):
            runner.run('', '')

if __name__ == '__main__':
    unittest.main()