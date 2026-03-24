# tests/test_kms.py
import unittest
from unittest.mock import patch, MagicMock
from core.kms import KMS, KeyManagementSystem  # Importar las clases y métodos a probar

class TestKMS(unittest.TestCase):

    def setUp(self):
        # Reinicializar la instancia de KMS antes de cada test
        KMS._instance = None

    def tearDown(self):
        # Reinicializar la instancia de KMS después de cada test
        KMS._instance = None

    def test_imports_correctos(self):
        # Verificar que los imports sean correctos
        self.assertIsNotNone(KMS)
        self.assertIsNotNone(KeyManagementSystem)

    def test_clase_kms(self):
        # Verificar que la clase KMS exista y sea instanciable
        kms = KMS()
        self.assertIsInstance(kms, KMS)

    def test_metodo_get_instance(self):
        # Verificar que el método get_instance devuelva la instancia de KMS
        kms1 = KMS.get_instance()
        kms2 = KMS.get_instance()
        self.assertEqual(kms1, kms2)

    def test_metodo_generate_key(self):
        # Verificar que el método generate_key genere una clave
        kms = KMS()
        key = kms.generate_key()
        self.assertIsNotNone(key)

    def test_metodo_generate_key_con_tipo_incorrecto(self):
        # Verificar que el método generate_key lance un error con tipo incorrecto
        kms = KMS()
        with self.assertRaises(TypeError):
            kms.generate_key(tipo="incorrecto")

    def test_metodo_encrypt(self):
        # Verificar que el método encrypt cifre un mensaje
        kms = KMS()
        mensaje = "Hola, mundo!"
        encrypted = kms.encrypt(mensaje)
        self.assertIsNotNone(encrypted)

    def test_metodo_encrypt_con_mensaje_vacio(self):
        # Verificar que el método encrypt lance un error con mensaje vacío
        kms = KMS()
        with self.assertRaises(ValueError):
            kms.encrypt("")

    def test_metodo_decrypt(self):
        # Verificar que el método decrypt descifre un mensaje
        kms = KMS()
        mensaje = "Hola, mundo!"
        encrypted = kms.encrypt(mensaje)
        decrypted = kms.decrypt(encrypted)
        self.assertEqual(mensaje, decrypted)

    def test_metodo_decrypt_con_mensaje_incorrecto(self):
        # Verificar que el método decrypt lance un error con mensaje incorrecto
        kms = KMS()
        with self.assertRaises(ValueError):
            kms.decrypt("mensaje incorrecto")

if __name__ == '__main__':
    unittest.main()