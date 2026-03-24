import unittest
from unittest.mock import patch, MagicMock
from core.e2e_encryption import E2EEncryption, encrypt, decrypt

class TestE2EEncryption(unittest.TestCase):
    def setUp(self):
        # Reset _instance si es un singleton
        if hasattr(E2EEncryption, '_instance'):
            E2EEncryption._instance = None

    def tearDown(self):
        # Reset _instance si es un singleton
        if hasattr(E2EEncryption, '_instance'):
            E2EEncryption._instance = None

    def test_imports_correctos(self):
        # Verificar que los imports sean correctos
        self.assertTrue(hasattr(E2EEncryption, 'encrypt'))
        self.assertTrue(hasattr(E2EEncryption, 'decrypt'))

    def test_clase_e2e_encryption(self):
        # Verificar que la clase E2EEncryption exista y tenga los métodos públicos correctos
        self.assertTrue(hasattr(E2EEncryption, 'encrypt'))
        self.assertTrue(hasattr(E2EEncryption, 'decrypt'))

    def test_metodo_encrypt(self):
        # Verificar que el método encrypt funcione correctamente
        texto_plano = 'Hola, mundo!'
        encrypted_text = E2EEncryption().encrypt(texto_plano)
        self.assertNotEqual(encrypted_text, texto_plano)

    def test_metodo_decrypt(self):
        # Verificar que el método decrypt funcione correctamente
        texto_plano = 'Hola, mundo!'
        encrypted_text = E2EEncryption().encrypt(texto_plano)
        decrypted_text = E2EEncryption().decrypt(encrypted_text)
        self.assertEqual(decrypted_text, texto_plano)

    def test_caso_edge_none(self):
        # Verificar que el método encrypt maneje correctamente el caso edge None
        with self.assertRaises(TypeError):
            E2EEncryption().encrypt(None)

    def test_caso_edge_vacio(self):
        # Verificar que el método encrypt maneje correctamente el caso edge vacío
        encrypted_text = E2EEncryption().encrypt('')
        self.assertEqual(encrypted_text, '')

    def test_caso_edge_tipo_incorrecto(self):
        # Verificar que el método encrypt maneje correctamente el caso edge tipo incorrecto
        with self.assertRaises(TypeError):
            E2EEncryption().encrypt(123)

    def test_singleton(self):
        # Verificar que la clase E2EEncryption sea un singleton
        instance1 = E2EEncryption()
        instance2 = E2EEncryption()
        self.assertEqual(instance1, instance2)

if __name__ == '__main__':
    unittest.main()