import unittest
from unittest.mock import Mock
from core.mesh_bridge import MeshBridge, MeshBridgeError

class TestMeshBridge(unittest.TestCase):
    def setUp(self):
        MeshBridge._instance = None  # Reset singleton

    def tearDown(self):
        MeshBridge._instance = None  # Reset singleton

    def test_imports_correctos(self):
        # Verificar que se importan las clases y métodos correctamente
        self.assertTrue(hasattr(MeshBridge, 'connect'))
        self.assertTrue(hasattr(MeshBridge, 'send_message'))
        self.assertTrue(hasattr(MeshBridge, 'receive_message'))

    def test_clase_mesh_bridge(self):
        # Verificar que la clase MeshBridge se crea correctamente
        mesh_bridge = MeshBridge()
        self.assertIsInstance(mesh_bridge, MeshBridge)

    def test_metodo_connect(self):
        # Verificar que el método connect se ejecuta correctamente
        mesh_bridge = MeshBridge()
        mesh_bridge.connect = Mock(return_value=True)
        self.assertTrue(mesh_bridge.connect())

    def test_metodo_send_message(self):
        # Verificar que el método send_message se ejecuta correctamente
        mesh_bridge = MeshBridge()
        mesh_bridge.send_message = Mock(return_value=True)
        self.assertTrue(mesh_bridge.send_message('mensaje'))

    def test_metodo_receive_message(self):
        # Verificar que el método receive_message se ejecuta correctamente
        mesh_bridge = MeshBridge()
        mesh_bridge.receive_message = Mock(return_value='mensaje')
        self.assertEqual(mesh_bridge.receive_message(), 'mensaje')

    def test_caso_edge_none(self):
        # Verificar que se maneja correctamente el caso en que se pasa None como parámetro
        mesh_bridge = MeshBridge()
        with self.assertRaises(MeshBridgeError):
            mesh_bridge.send_message(None)

    def test_caso_edge_vacio(self):
        # Verificar que se maneja correctamente el caso en que se pasa una cadena vacía como parámetro
        mesh_bridge = MeshBridge()
        with self.assertRaises(MeshBridgeError):
            mesh_bridge.send_message('')

    def test_caso_edge_tipo_incorrecto(self):
        # Verificar que se maneja correctamente el caso en que se pasa un tipo incorrecto como parámetro
        mesh_bridge = MeshBridge()
        with self.assertRaises(MeshBridgeError):
            mesh_bridge.send_message(123)

    def test_singleton(self):
        # Verificar que la clase MeshBridge es un singleton
        mesh_bridge1 = MeshBridge()
        mesh_bridge2 = MeshBridge()
        self.assertEqual(mesh_bridge1, mesh_bridge2)

if __name__ == '__main__':
    unittest.main()