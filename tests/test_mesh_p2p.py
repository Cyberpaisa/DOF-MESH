import unittest
from unittest.mock import patch, MagicMock
from core.mesh_p2p import P2PManager, P2PConnection, get_p2p_manager

class TestP2PConnection(unittest.TestCase):

    def setUp(self):
        self.mock_socket = MagicMock()
        self.conn = P2PConnection(self.mock_socket, '127.0.0.1', 8000)

    def test_connection_initialization(self):
        self.assertEqual(self.conn.ip, '127.0.0.1')
        self.assertEqual(self.conn.port, 8000)
        self.assertEqual(self.conn.socket, self.mock_socket)
        self.assertTrue(hasattr(self.conn, 'conn_id'))
        self.assertIsInstance(self.conn.conn_id, str)
        self.assertGreater(len(self.conn.conn_id), 0)

    def test_send_calls_socket_send(self):
        message = {'type': 'test'}
        self.conn.send(message)
        self.mock_socket.send.assert_called_once()

    def test_close_calls_socket_close(self):
        self.conn.close()
        self.mock_socket.close.assert_called_once()


class TestP2PManager(unittest.TestCase):

    def setUp(self):
        self.manager = P2PManager()
        self.manager.connections.clear()  # Ensure clean state

    @patch('core.mesh_p2p.socket')
    def test_connect_creates_connection(self, mock_socket):
        mock_sock_instance = MagicMock()
        mock_socket.socket.return_value = mock_sock_instance

        conn = self.manager.connect('127.0.0.1', 8000)

        self.assertIsInstance(conn, P2PConnection)
        self.assertEqual(conn.ip, '127.0.0.1')
        self.assertEqual(conn.port, 8000)
        mock_socket.socket.assert_called()
        mock_sock_instance.connect.assert_called_with(('127.0.0.1', 8000))

    def test_get_connections_returns_list(self):
        self.assertIsInstance(self.manager.get_connections(), list)

    def test_get_connections_includes_new_connection(self):
        conn = MagicMock()
        conn.conn_id = 'test-conn'
        self.manager.connections['test-conn'] = conn
        conns = self.manager.get_connections()
        self.assertIn(conn, conns)
        self.assertEqual(len(conns), 1)

    def test_disconnect_removes_connection(self):
        conn = MagicMock()
        conn.conn_id = 'test-conn'
        self.manager.connections['test-conn'] = conn
        self.manager.disconnect('test-conn')
        self.assertNotIn('test-conn', self.manager.connections)
        conn.close.assert_called_once()

    def test_disconnect_nonexistent_id_no_error(self):
        self.manager.disconnect('nonexistent')  # Should not raise

    def test_broadcast_sends_to_all_connections(self):
        conn1 = MagicMock()
        conn2 = MagicMock()
        self.manager.connections['c1'] = conn1
        self.manager.connections['c2'] = conn2

        message = {'type': 'broadcast'}
        self.manager.broadcast(message)

        conn1.send.assert_called_with(message)
        conn2.send.assert_called_with(message)

    def test_broadcast_empty_connections_no_error(self):
        message = {'type': 'test'}
        self.manager.broadcast(message)  # Should not fail

    def test_connect_generates_unique_conn_ids(self):
        conns = []
        for _ in range(5):
            c = self.manager.connect('127.0.0.1', 8000)
            conns.append(c.conn_id)
        self.assertEqual(len(set(conns)), 5)

    def test_singleton_via_get_p2p_manager(self):
        m1 = get_p2p_manager()
        m2 = get_p2p_manager()
        self.assertIs(m1, m2)

    def test_singleton_instance_reuse(self):
        m1 = P2PManager()
        m2 = P2PManager()
        self.assertIs(m1, m2)

    def test_connection_id_type_string(self):
        conn = self.manager.connect('127.0.0.1', 8000)
        self.assertIsInstance(conn.conn_id, str)

    def test_connection_id_non_empty(self):
        conn = self.manager.connect('127.0.0.1', 8000)
        self.assertTrue(conn.conn_id.strip() != '')

    def test_get_connections_returns_copy(self):
        conn = self.manager.connect('127.0.0.1', 8000)
        conns = self.manager.get_connections()
        conns.clear()
        self.assertGreaterEqual(len(self.manager.get_connections()), 1)

    def test_disconnect_after_connect(self):
        conn = self.manager.connect('127.0.0.1', 8000)
        conn_id = conn.conn_id
        self.assertIn(conn_id, self.manager.connections)
        self.manager.disconnect(conn_id)
        self.assertNotIn(conn_id, self.manager.connections)

    def test_multiple_connect_calls_different_peers(self):
        conn1 = self.manager.connect('127.0.0.1', 8000)
        conn2 = self.manager.connect('127.0.0.1', 8001)
        self.assertNotEqual(conn1.conn_id, conn2.conn_id)
        self.assertEqual(len(self.manager.get_connections()), 2)

    def test_connect_with_same_peer_multiple_times(self):
        # Assuming allowed; each call creates new connection
        conn1 = self.manager.connect('127.0.0.1', 8000)
        conn2 = self.manager.connect('127.0.0.1', 8000)
        self.assertEqual(len(self.manager.get_connections()), 2)
        self.assertNotEqual(conn1.conn_id, conn2.conn_id)

    def test_broadcast_with_one_disconnected_connection(self):
        conn1 = MagicMock()
        conn1.send.side_effect = Exception("Disconnected")
        conn2 = MagicMock()
        self.manager.connections['c1'] = conn1
        self.manager.connections['c2'] = conn2

        message = {'type': 'test'}
        self.manager.broadcast(message)

        conn2.send.assert_called_with(message)  # Others still get it

    def test_manager_initialization_idempotent(self):
        m1 = P2PManager()
        m2 = P2PManager()
        self.assertIs(m1, m2)
        self.assertIsInstance(m1.connections, dict)

    def test_get_p2p_manager_returns_instance(self):
        manager = get_p2p_manager()
        self.assertIsInstance(manager, P2PManager)

    def test_p2p_connection_has_required_attributes(self):
        conn = self.manager.connect('127.0.0.1', 8000)
        self.assertTrue(hasattr(conn, 'ip'))
        self.assertTrue(hasattr(conn, 'port'))
        self.assertTrue(hasattr(conn, 'socket'))
        self.assertTrue(hasattr(conn, 'conn_id'))
        self.assertTrue(callable(conn.send))
        self.assertTrue(callable(conn.close))

    def test_p2p_manager_methods_exist(self):
        self.assertTrue(callable(self.manager.connect))
        self.assertTrue(callable(self.manager.get_connections))
        self.assertTrue(callable(self.manager.disconnect))
        self.assertTrue(callable(self.manager.broadcast))

    def test_p2p_manager_connections_dict_starts_empty(self):
        self.assertEqual(len(self.manager.connections), 0)

    def test_singleton_thread_safety_not_required_for_now(self):
        # Future concern; current impl assumes single-threaded
        self.assertTrue(True)  # Placeholder for architecture note

if __name__ == '__main__':
    unittest.main()