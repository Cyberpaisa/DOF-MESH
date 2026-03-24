import unittest

from core.mesh_load_balancer import LoadBalancer, get_load_balancer

class TestLoadBalancer(unittest.TestCase):

    def setUp(self):
        LoadBalancer._instance = None  # reset singleton between tests
        self.load_balancer = get_load_balancer()

    def test_add_node(self):
        self.load_balancer.add_node("node1")
        nodes = self.load_balancer.get_nodes()
        self.assertIn("node1", nodes)

    def test_remove_node(self):
        self.load_balancer.add_node("node2")
        self.load_balancer.remove_node("node2")
        nodes = self.load_balancer.get_nodes()
        self.assertNotIn("node2", nodes)

    def test_round_robin(self):
        self.load_balancer.add_node("node3")
        self.load_balancer.add_node("node4")
        node1 = self.load_balancer.get_next_node()
        node2 = self.load_balancer.get_next_node()
        self.assertEqual(node1, "node3")
        self.assertEqual(node2, "node4")

    def test_empty_load_balancer(self):
        with self.assertRaises(IndexError):
            self.load_balancer.get_next_node()

    def test_add_duplicate_nodes(self):
        self.load_balancer.add_node("node5")
        self.load_balancer.add_node("node5")
        nodes = self.load_balancer.get_nodes()
        self.assertEqual(len(nodes), 1)

    def test_get_load_balancer_singleton(self):
        lb1 = get_load_balancer()
        lb2 = get_load_balancer()
        self.assertIs(lb1, lb2)

    def test_remove_nonexistent_node(self):
        with self.assertRaises(ValueError):
            self.load_balancer.remove_node("node6")

    def test_round_robin_with_one_node(self):
        self.load_balancer.add_node("node7")
        node = self.load_balancer.get_next_node()
        self.assertEqual(node, "node7")

    def test_add_multiple_nodes(self):
        self.load_balancer.add_node("node8")
        self.load_balancer.add_node("node9")
        self.load_balancer.add_node("node10")
        nodes = self.load_balancer.get_nodes()
        self.assertIn("node8", nodes)
        self.assertIn("node9", nodes)
        self.assertIn("node10", nodes)

    def test_remove_all_nodes(self):
        self.load_balancer.add_node("node11")
        self.load_balancer.remove_node("node11")
        with self.assertRaises(IndexError):
            self.load_balancer.get_next_node()

    def test_round_robin_after_removal(self):
        self.load_balancer.add_node("node12")
        self.load_balancer.add_node("node13")
        self.load_balancer.remove_node("node12")
        node = self.load_balancer.get_next_node()
        self.assertEqual(node, "node13")

    def test_add_and_remove_same_node(self):
        self.load_balancer.add_node("node14")
        self.load_balancer.remove_node("node14")
        with self.assertRaises(IndexError):
            self.load_balancer.get_next_node()

if __name__ == '__main__':
    unittest.main()
