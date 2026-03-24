# tests/test_dlp.py
import unittest
from unittest.mock import patch
from core.dlp import DLP, DLPError

class TestDLP(unittest.TestCase):

    def setUp(self):
        # Reinicializa la instancia de DLP antes de cada test
        DLP._instance = None

    def tearDown(self):
        # Reinicializa la instancia de DLP después de cada test
        DLP._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports en core/dlp.py sean correctos
        try:
            from core.dlp import DLP, DLPError
        except ImportError:
            self.fail("Error en los imports")

    def test_clase_dlp(self):
        # Verifica que la clase DLP exista y tenga los métodos públicos esperados
        self.assertTrue(hasattr(DLP, 'get_instance'))
        self.assertTrue(hasattr(DLP, 'init'))
        self.assertTrue(hasattr(DLP, 'process'))

    def test_metodo_get_instance(self):
        # Verifica que el método get_instance devuelva una instancia de DLP
        instance1 = DLP.get_instance()
        instance2 = DLP.get_instance()
        self.assertEqual(instance1, instance2)

    def test_metodo_init(self):
        # Verifica que el método init inicialice correctamente la instancia de DLP
        dlp = DLP.get_instance()
        dlp.init()
        self.assertIsNotNone(dlp)

    def test_metodo_process_con_datos_validos(self):
        # Verifica que el método process funcione correctamente con datos válidos
        dlp = DLP.get_instance()
        dlp.init()
        datos = "Datos de prueba"
        resultado = dlp.process(datos)
        self.assertIsNotNone(resultado)

    def test_metodo_process_con_datos_none(self):
        # Verifica que el método process lance una excepción con datos None
        dlp = DLP.get_instance()
        dlp.init()
        with self.assertRaises(DLPError):
            dlp.process(None)

    def test_metodo_process_con_datos_vacios(self):
        # Verifica que el método process lance una excepción con datos vacíos
        dlp = DLP.get_instance()
        dlp.init()
        with self.assertRaises(DLPError):
            dlp.process("")

    def test_metodo_process_con_tipo_incorrecto(self):
        # Verifica que el método process lance una excepción con tipo de dato incorrecto
        dlp = DLP.get_instance()
        dlp.init()
        with self.assertRaises(DLPError):
            dlp.process(123)

if __name__ == '__main__':
    unittest.main()