import unittest
from unittest.mock import patch
from core.audit_log import AuditLog

class TestAuditLog(unittest.TestCase):
    def setUp(self):
        # Reinicializa la instancia de AuditLog para cada test
        AuditLog._instance = None

    def tearDown(self):
        # Limpia la instancia de AuditLog después de cada test
        AuditLog._instance = None

    def test_imports_correctos(self):
        # Verifica que los imports sean correctos
        from core.audit_log import AuditLog
        self.assertIsNotNone(AuditLog)

    def test_clase_audit_log(self):
        # Verifica que la clase AuditLog exista y tenga los métodos públicos esperados
        self.assertTrue(hasattr(AuditLog, 'log'))
        self.assertTrue(hasattr(AuditLog, 'get_logs'))

    def test_metodo_log(self):
        # Verifica que el método log funcione correctamente
        audit_log = AuditLog()
        mensaje = 'Mensaje de prueba'
        audit_log.log(mensaje)
        self.assertIn(mensaje, audit_log.get_logs())

    def test_metodo_get_logs(self):
        # Verifica que el método get_logs funcione correctamente
        audit_log = AuditLog()
        mensaje1 = 'Mensaje de prueba 1'
        mensaje2 = 'Mensaje de prueba 2'
        audit_log.log(mensaje1)
        audit_log.log(mensaje2)
        logs = audit_log.get_logs()
        self.assertIn(mensaje1, logs)
        self.assertIn(mensaje2, logs)

    def test_caso_edge_none(self):
        # Verifica que el método log maneje correctamente el caso de None
        audit_log = AuditLog()
        with self.assertRaises(TypeError):
            audit_log.log(None)

    def test_caso_edge_vacio(self):
        # Verifica que el método log maneje correctamente el caso de una cadena vacía
        audit_log = AuditLog()
        with self.assertRaises(ValueError):
            audit_log.log('')

    def test_caso_edge_tipo_incorrecto(self):
        # Verifica que el método log maneje correctamente el caso de un tipo incorrecto
        audit_log = AuditLog()
        with self.assertRaises(TypeError):
            audit_log.log(123)

    def test_singleton(self):
        # Verifica que la clase AuditLog sea un singleton
        audit_log1 = AuditLog()
        audit_log2 = AuditLog()
        self.assertEqual(audit_log1, audit_log2)

if __name__ == '__main__':
    unittest.main()