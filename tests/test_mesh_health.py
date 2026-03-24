import unittest
from unittest.mock import patch, MagicMock
from core.mesh_health import MeshHealth, MeshHealthError

class TestMeshHealth(unittest.TestCase):
    def setUp(self):
        MeshHealth._instance = None  # Reset singleton

    def tearDown(self):
        MeshHealth._instance = None  # Reset singleton

    def test_imports_correctos(self):
        # Verificar que se importan las clases y métodos correctamente
        self.assertTrue(hasattr(MeshHealth, 'get_instance'))
        self.assertTrue(hasattr(MeshHealth, 'check_health'))

    def test_clase_meshhealth(self):
        # Verificar que la clase MeshHealth se crea correctamente
        mesh_health = MeshHealth.get_instance()
        self.assertIsInstance(mesh_health, MeshHealth)

    def test_metodo_check_health(self):
        # Verificar que el método check_health se ejecuta correctamente
        mesh_health = MeshHealth.get_instance()
        result = mesh_health.check_health()
        self.assertTrue(result)

    def test_metodo_check_health_con_error(self):
        # Verificar que el método check_health lanza un error cuando corresponde
        mesh_health = MeshHealth.get_instance()
        with patch.object(mesh_health, 'check_nodes', side_effect=MeshHealthError('Error de prueba')):
            with self.assertRaises(MeshHealthError):
                mesh_health.check_health()

    def test_caso_edge_none(self):
        # Verificar que el método check_health maneja el caso de None correctamente
        mesh_health = MeshHealth.get_instance()
        with patch.object(mesh_health, 'check_nodes', return_value=None):
            result = mesh_health.check_health()
            self.assertFalse(result)

    def test_caso_edge_vacio(self):
        # Verificar que el método check_health maneja el caso de vacío correctamente
        mesh_health = MeshHealth.get_instance()
        with patch.object(mesh_health, 'check_nodes', return_value=[]):
            result = mesh_health.check_health()
            self.assertFalse(result)

    def test_caso_edge_tipo_incorrecto(self):
        # Verificar que el método check_health maneja el caso de tipo incorrecto correctamente
        mesh_health = MeshHealth.get_instance()
        with patch.object(mesh_health, 'check_nodes', return_value='cadena'):
            result = mesh_health.check_health()
            self.assertFalse(result)

    def test_singleton(self):
        # Verificar que la clase MeshHealth es un singleton
        mesh_health1 = MeshHealth.get_instance()
        mesh_health2 = MeshHealth.get_instance()
        self.assertEqual(mesh_health1, mesh_health2)

if __name__ == '__main__':
    unittest.main()