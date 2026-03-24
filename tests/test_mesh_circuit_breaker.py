import unittest
from unittest.mock import MagicMock
from core.mesh_circuit_breaker import MeshCircuitBreaker

class TestMeshCircuitBreaker(unittest.TestCase):
    def setUp(self):
        # Reinicializa la instancia de MeshCircuitBreaker para cada test
        MeshCircuitBreaker._instance = None

    def tearDown(self):
        # Limpia la instancia de MeshCircuitBreaker después de cada test
        MeshCircuitBreaker._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.mesh_circuit_breaker import MeshCircuitBreaker
        self.assertIsNotNone(MeshCircuitBreaker)

    def test_clase_mesh_circuit_breaker(self):
        # Verifica que la clase MeshCircuitBreaker exista y tenga los métodos públicos esperados
        self.assertTrue(hasattr(MeshCircuitBreaker, 'is_open'))
        self.assertTrue(hasattr(MeshCircuitBreaker, 'is_closed'))
        self.assertTrue(hasattr(MeshCircuitBreaker, 'reset'))

    def test_metodo_is_open(self):
        # Verifica que el método is_open devuelva False cuando el circuito está cerrado
        mesh_circuit_breaker = MeshCircuitBreaker()
        self.assertFalse(mesh_circuit_breaker.is_open())

    def test_metodo_is_closed(self):
        # Verifica que el método is_closed devuelva True cuando el circuito está cerrado
        mesh_circuit_breaker = MeshCircuitBreaker()
        self.assertTrue(mesh_circuit_breaker.is_closed())

    def test_metodo_reset(self):
        # Verifica que el método reset reinicialice el circuito
        mesh_circuit_breaker = MeshCircuitBreaker()
        mesh_circuit_breaker.open()
        self.assertTrue(mesh_circuit_breaker.is_open())
        mesh_circuit_breaker.reset()
        self.assertFalse(mesh_circuit_breaker.is_open())

    def test_caso_edge_none(self):
        # Verifica que el circuito se comporte correctamente cuando se pasa None como parámetro
        mesh_circuit_breaker = MeshCircuitBreaker()
        with self.assertRaises(TypeError):
            mesh_circuit_breaker.open(None)

    def test_caso_edge_vacio(self):
        # Verifica que el circuito se comporte correctamente cuando se pasa un valor vacío como parámetro
        mesh_circuit_breaker = MeshCircuitBreaker()
        with self.assertRaises(ValueError):
            mesh_circuit_breaker.open("")

    def test_caso_edge_tipo_incorrecto(self):
        # Verifica que el circuito se comporte correctamente cuando se pasa un tipo incorrecto como parámetro
        mesh_circuit_breaker = MeshCircuitBreaker()
        with self.assertRaises(TypeError):
            mesh_circuit_breaker.open(123)

    def test_singleton(self):
        # Verifica que la clase MeshCircuitBreaker sea un singleton
        mesh_circuit_breaker1 = MeshCircuitBreaker()
        mesh_circuit_breaker2 = MeshCircuitBreaker()
        self.assertEqual(mesh_circuit_breaker1, mesh_circuit_breaker2)

if __name__ == '__main__':
    unittest.main()