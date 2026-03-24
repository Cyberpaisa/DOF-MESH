import unittest
from unittest.mock import patch, MagicMock
from core.mesh_firewall import MeshFirewall, Rule

class TestMeshFirewall(unittest.TestCase):
    def setUp(self):
        MeshFirewall._instance = None  # Reset singleton

    def tearDown(self):
        MeshFirewall._instance = None  # Reset singleton

    def test_imports_correctos(self):
        # Verificar que se importan las clases y métodos correctamente
        self.assertTrue(hasattr(MeshFirewall, 'add_rule'))
        self.assertTrue(hasattr(MeshFirewall, 'remove_rule'))
        self.assertTrue(hasattr(Rule, 'src_ip'))
        self.assertTrue(hasattr(Rule, 'dst_ip'))

    def test_clases_y_metodos_publicos(self):
        # Verificar que las clases y métodos públicos estén definidos
        self.assertIsInstance(MeshFirewall(), MeshFirewall)
        self.assertIsInstance(Rule('192.168.1.1', '192.168.1.2'), Rule)

        mesh_firewall = MeshFirewall()
        self.assertTrue(callable(mesh_firewall.add_rule))
        self.assertTrue(callable(mesh_firewall.remove_rule))

    def test_add_rule(self):
        # Verificar que se agregue una regla correctamente
        mesh_firewall = MeshFirewall()
        rule = Rule('192.168.1.1', '192.168.1.2')
        mesh_firewall.add_rule(rule)
        self.assertIn(rule, mesh_firewall.rules)

    def test_remove_rule(self):
        # Verificar que se elimine una regla correctamente
        mesh_firewall = MeshFirewall()
        rule = Rule('192.168.1.1', '192.168.1.2')
        mesh_firewall.add_rule(rule)
        mesh_firewall.remove_rule(rule)
        self.assertNotIn(rule, mesh_firewall.rules)

    def test_add_rule_none(self):
        # Verificar que no se agregue una regla None
        mesh_firewall = MeshFirewall()
        with self.assertRaises(TypeError):
            mesh_firewall.add_rule(None)

    def test_add_rule_vacio(self):
        # Verificar que no se agregue una regla vacía
        mesh_firewall = MeshFirewall()
        with self.assertRaises(ValueError):
            mesh_firewall.add_rule(Rule('', ''))

    def test_add_rule_tipos_incorrectos(self):
        # Verificar que no se agregue una regla con tipos incorrectos
        mesh_firewall = MeshFirewall()
        with self.assertRaises(TypeError):
            mesh_firewall.add_rule(Rule(123, '192.168.1.2'))

    def test_singleton(self):
        # Verificar que el singleton funcione correctamente
        mesh_firewall1 = MeshFirewall()
        mesh_firewall2 = MeshFirewall()
        self.assertEqual(mesh_firewall1, mesh_firewall2)

if __name__ == '__main__':
    unittest.main()