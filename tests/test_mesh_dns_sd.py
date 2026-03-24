import unittest
import time
from core.mesh_dns_sd import DNSSDService, ServiceRecord, get_dns_sd, reset_dns_sd

class TestTestMeshDNSSD(unittest.TestCase):
    def setUp(self):
        reset_dns_sd()
        self.service = get_dns_sd()

    def test_singleton(self):
        s1 = get_dns_sd()
        s2 = get_dns_sd()
        self.assertIs(s1, s2)

    def test_register_service(self):
        record = self.service.register_service("test-service", 1234, {"attr": "val"})
        self.assertEqual(record.name, "test-service")
        self.assertEqual(record.port, 1234)
        self.assertEqual(record.properties["attr"], "val")

    def test_discover_services(self):
        self.service.register_service("web-service", 80, {})
        self.service.register_service("db-service", 5432, {})
        
        web = self.service.discover_services("web")
        self.assertEqual(len(web), 1)
        self.assertEqual(web[0].name, "web-service")

    def test_get_all(self):
        self.service.register_service("s1", 1, {})
        self.service.register_service("s2", 2, {})
        self.assertEqual(len(self.service.get_all()), 2)

    def test_expire_old(self):
        # Create a record that expires in 1 second
        record = self.service.register_service("exp-service", 8000, {})
        record.ttl = 1
        record.registered_at = time.time() - 2 # Set in the past
        
        # Should be removed during next read operation
        all_services = self.service.get_all()
        self.assertEqual(len(all_services), 0)

    def test_service_record_ttl_logic(self):
        record = ServiceRecord("test", "host", 80, {}, ttl=10)
        self.assertFalse(record.is_expired())
        record.registered_at = time.time() - 20
        self.assertTrue(record.is_expired())

    def test_multiple_registrations(self):
        for i in range(15):
            with self.subTest(i=i):
                self.service.register_service(f"service-{i}", 8000+i, {})
        self.assertEqual(len(self.service.get_all()), 15)

if __name__ == '__main__':
    unittest.main()
