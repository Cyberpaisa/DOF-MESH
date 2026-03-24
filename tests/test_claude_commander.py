# tests/test_claude_commander.py

import unittest
from unittest.mock import patch, MagicMock
from core.claude_commander import ClaudeCommander

class TestClaudeCommander(unittest.TestCase):

    def setUp(self):
        # Reinicializar la instancia de ClaudeCommander para cada test
        ClaudeCommander._instance = None

    def tearDown(self):
        # Reinicializar la instancia de ClaudeCommander después de cada test
        ClaudeCommander._instance = None

    def test_imports_correctos(self):
        # Verificar que los imports sean correctos
        from core.claude_commander import ClaudeCommander
        self.assertIsNotNone(ClaudeCommander)

    def test_clase_y_metodos_publicos(self):
        # Verificar que la clase ClaudeCommander tenga los métodos públicos esperados
        commander = ClaudeCommander()
        self.assertIsNotNone(commander)
        self.assertTrue(hasattr(commander, 'ejecutar_comando'))
        self.assertTrue(hasattr(commander, 'obtener_resultado'))

    def test_ejecutar_comando_con_comando_valido(self):
        # Verificar que el método ejecutar_comando funcione correctamente con un comando válido
        commander = ClaudeCommander()
        comando = 'comando_valido'
        resultado = commander.ejecutar_comando(comando)
        self.assertIsNotNone(resultado)

    def test_ejecutar_comando_con_comando_vacio(self):
        # Verificar que el método ejecutar_comando maneje correctamente un comando vacío
        commander = ClaudeCommander()
        comando = ''
        with self.assertRaises(ValueError):
            commander.ejecutar_comando(comando)

    def test_ejecutar_comando_con_comando_none(self):
        # Verificar que el método ejecutar_comando maneje correctamente un comando None
        commander = ClaudeCommander()
        comando = None
        with self.assertRaises(TypeError):
            commander.ejecutar_comando(comando)

    def test_ejecutar_comando_con_tipo_incorrecto(self):
        # Verificar que el método ejecutar_comando maneje correctamente un comando con tipo incorrecto
        commander = ClaudeCommander()
        comando = 123
        with self.assertRaises(TypeError):
            commander.ejecutar_comando(comando)

    def test_obtener_resultado_con_resultado_valido(self):
        # Verificar que el método obtener_resultado funcione correctamente con un resultado válido
        commander = ClaudeCommander()
        resultado = 'resultado_valido'
        commander._resultado = resultado
        self.assertEqual(commander.obtener_resultado(), resultado)

    def test_obtener_resultado_con_resultado_none(self):
        # Verificar que el método obtener_resultado maneje correctamente un resultado None
        commander = ClaudeCommander()
        commander._resultado = None
        self.assertIsNone(commander.obtener_resultado())

    def test_singleton(self):
        # Verificar que ClaudeCommander sea un singleton
        commander1 = ClaudeCommander()
        commander2 = ClaudeCommander()
        self.assertEqual(commander1, commander2)

if __name__ == '__main__':
    unittest.main()