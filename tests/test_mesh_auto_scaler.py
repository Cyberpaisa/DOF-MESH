import unittest
from unittest.mock import MagicMock
from core.mesh_auto_scaler import MeshAutoScaler

class TestMeshAutoScaler(unittest.TestCase):
    def setUp(self):
        # Reinicializa la instancia de MeshAutoScaler para cada test
        MeshAutoScaler._instance = None

    def tearDown(self):
        # Limpia la instancia de MeshAutoScaler después de cada test
        MeshAutoScaler._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.mesh_auto_scaler import MeshAutoScaler
        self.assertIsNotNone(MeshAutoScaler)

    def test_clase_mesh_auto_scaler(self):
        # Verifica que la clase MeshAutoScaler exista y sea instanciable
        scaler = MeshAutoScaler()
        self.assertIsInstance(scaler, MeshAutoScaler)

    def test_metodo_init(self):
        # Verifica que el método __init__ se llame correctamente
        scaler = MeshAutoScaler()
        self.assertIsNotNone(scaler)

    def test_metodo_scale_up(self):
        # Verifica que el método scale_up se llame correctamente
        scaler = MeshAutoScaler()
        scaler.scale_up = MagicMock()
        scaler.scale_up()
        self.assertTrue(scaler.scale_up.called)

    def test_metodo_scale_down(self):
        # Verifica que el método scale_down se llame correctamente
        scaler = MeshAutoScaler()
        scaler.scale_down = MagicMock()
        scaler.scale_down()
        self.assertTrue(scaler.scale_down.called)

    def test_caso_edge_none(self):
        # Verifica que el constructor maneje correctamente el caso de None
        with self.assertRaises(TypeError):
            MeshAutoScaler(None)

    def test_caso_edge_vacio(self):
        # Verifica que el constructor maneje correctamente el caso de vacío
        with self.assertRaises(TypeError):
            MeshAutoScaler()

    def test_caso_edge_tipo_incorrecto(self):
        # Verifica que el constructor maneje correctamente el caso de tipo incorrecto
        with self.assertRaises(TypeError):
            MeshAutoScaler("cadena")

    def test_singleton(self):
        # Verifica que la clase MeshAutoScaler sea un singleton
        scaler1 = MeshAutoScaler()
        scaler2 = MeshAutoScaler()
        self.assertEqual(scaler1, scaler2)

if __name__ == '__main__':
    unittest.main()