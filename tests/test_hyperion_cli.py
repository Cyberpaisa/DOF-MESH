"""Tests for core.hyperion_cli — CLI argument parsing and command dispatch."""
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch, call


class TestMainHelp(unittest.TestCase):
    def test_no_args_prints_help(self):
        """Running with no subcommand should print usage and exit 0/2."""
        with patch("sys.argv", ["hyperion_cli"]):
            from core.hyperion_cli import main
            with self.assertRaises(SystemExit):
                main()

    def test_help_flag(self):
        with patch("sys.argv", ["hyperion_cli", "--help"]):
            from core.hyperion_cli import main
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)


class TestArgParsing(unittest.TestCase):
    """Test that argparse correctly routes subcommands."""

    def _run_with(self, argv, cmd_mock_target):
        with patch("sys.argv", ["hyperion_cli"] + argv), \
             patch(cmd_mock_target) as mock_fn:
            from core import hyperion_cli
            import importlib
            importlib.reload(hyperion_cli)  # ensure fresh parser
            mock_fn.return_value = None
            hyperion_cli.main()
            return mock_fn

    def test_status_dispatches_cmd_status(self):
        with patch("sys.argv", ["hyperion_cli", "status"]), \
             patch("core.hyperion_cli.cmd_status") as mock_status:
            from core.hyperion_cli import main
            main()
            self.assertTrue(mock_status.called)

    def test_bench_dispatches_cmd_bench(self):
        with patch("sys.argv", ["hyperion_cli", "bench"]), \
             patch("core.hyperion_cli.cmd_bench") as mock_bench:
            from core.hyperion_cli import main
            main()
            self.assertTrue(mock_bench.called)

    def test_raft_dispatches_cmd_raft(self):
        with patch("sys.argv", ["hyperion_cli", "raft"]), \
             patch("core.hyperion_cli.cmd_raft") as mock_raft:
            from core.hyperion_cli import main
            main()
            self.assertTrue(mock_raft.called)

    def test_http_dispatches_cmd_http(self):
        with patch("sys.argv", ["hyperion_cli", "http"]), \
             patch("core.hyperion_cli.cmd_http") as mock_http:
            from core.hyperion_cli import main
            main()
            self.assertTrue(mock_http.called)

    def test_default_machines(self):
        with patch("sys.argv", ["hyperion_cli", "bench"]), \
             patch("core.hyperion_cli.cmd_bench") as mock_bench:
            from core.hyperion_cli import main
            main()
            args = mock_bench.call_args[0][0]
            self.assertIn("machine-a", args.machines)

    def test_custom_machines(self):
        with patch("sys.argv", ["hyperion_cli", "--machines", "x,y,z", "bench"]), \
             patch("core.hyperion_cli.cmd_bench") as mock_bench:
            from core.hyperion_cli import main
            main()
            args = mock_bench.call_args[0][0]
            self.assertEqual(args.machines, "x,y,z")

    def test_default_shards_five(self):
        with patch("sys.argv", ["hyperion_cli", "status"]), \
             patch("core.hyperion_cli.cmd_status") as mock_status:
            from core.hyperion_cli import main
            main()
            args = mock_status.call_args[0][0]
            self.assertEqual(args.shards, 5)

    def test_custom_shards(self):
        with patch("sys.argv", ["hyperion_cli", "--shards", "8", "status"]), \
             patch("core.hyperion_cli.cmd_status") as mock_status:
            from core.hyperion_cli import main
            main()
            args = mock_status.call_args[0][0]
            self.assertEqual(args.shards, 8)

    def test_bench_default_tasks(self):
        with patch("sys.argv", ["hyperion_cli", "bench"]), \
             patch("core.hyperion_cli.cmd_bench") as mock_bench:
            from core.hyperion_cli import main
            main()
            args = mock_bench.call_args[0][0]
            self.assertEqual(args.tasks, 10_000)

    def test_bench_custom_tasks(self):
        with patch("sys.argv", ["hyperion_cli", "bench", "--tasks", "500"]), \
             patch("core.hyperion_cli.cmd_bench") as mock_bench:
            from core.hyperion_cli import main
            main()
            args = mock_bench.call_args[0][0]
            self.assertEqual(args.tasks, 500)

    def test_http_default_port(self):
        with patch("sys.argv", ["hyperion_cli", "http"]), \
             patch("core.hyperion_cli.cmd_http") as mock_http:
            from core.hyperion_cli import main
            main()
            args = mock_http.call_args[0][0]
            self.assertEqual(args.port, 8765)

    def test_http_custom_port(self):
        with patch("sys.argv", ["hyperion_cli", "http", "--port", "9000"]), \
             patch("core.hyperion_cli.cmd_http") as mock_http:
            from core.hyperion_cli import main
            main()
            args = mock_http.call_args[0][0]
            self.assertEqual(args.port, 9000)

    def test_http_default_host(self):
        with patch("sys.argv", ["hyperion_cli", "http"]), \
             patch("core.hyperion_cli.cmd_http") as mock_http:
            from core.hyperion_cli import main
            main()
            args = mock_http.call_args[0][0]
            self.assertEqual(args.host, "0.0.0.0")


class TestCmdStatus(unittest.TestCase):
    """cmd_status prints mesh status without crashing."""

    def test_cmd_status_runs(self):
        mock_q = MagicMock()
        mock_q.status.return_value = {
            "node_id": "test", "shards": 3, "total_queued": 0,
            "enqueued_total": 5, "dequeued_total": 3, "wal": True, "per_shard": {},
        }
        mock_sm = MagicMock()

        with patch("core.hyperion_cli.DOFShardManager", return_value=mock_sm), \
             patch("core.hyperion_cli.DistributedMeshQueue", return_value=mock_q), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            import argparse
            args = argparse.Namespace(
                machines="a,b,c", shards=3
            )
            from core.hyperion_cli import cmd_status
            cmd_status(args)
            output = mock_out.getvalue()
            self.assertIn("HYPERION", output)

    def test_cmd_status_shows_node_id(self):
        mock_q = MagicMock()
        mock_q.status.return_value = {
            "node_id": "my-node", "shards": 5, "total_queued": 7,
            "enqueued_total": 100, "dequeued_total": 93, "wal": True, "per_shard": {},
        }
        with patch("core.hyperion_cli.DOFShardManager"), \
             patch("core.hyperion_cli.DistributedMeshQueue", return_value=mock_q), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            import argparse
            args = argparse.Namespace(machines="a,b", shards=5)
            from core.hyperion_cli import cmd_status
            cmd_status(args)
            self.assertIn("my-node", mock_out.getvalue())


class TestCmdBench(unittest.TestCase):
    """cmd_bench runs benchmark without crashing (mocked)."""

    def _mock_args(self, tasks=100, machines="a,b,c", shards=3):
        import argparse
        return argparse.Namespace(tasks=tasks, machines=machines, shards=shards)

    def test_cmd_bench_runs(self):
        mock_ring = MagicMock()
        mock_ring.get_node.return_value = "machine-a"
        mock_sm = MagicMock()
        mock_q = MagicMock()
        mock_q.qsize.side_effect = [10, 5, 0]
        mock_task = MagicMock()
        mock_q.dequeue_any.return_value = mock_task

        with patch("core.hyperion_cli.ConsistentHashRing", return_value=mock_ring), \
             patch("core.hyperion_cli.DOFShardManager", return_value=mock_sm), \
             patch("core.hyperion_cli.DistributedMeshQueue", return_value=mock_q), \
             patch("core.hyperion_cli.DistributedTask", return_value=MagicMock()), \
             patch("sys.stdout", new_callable=StringIO) as out:
            from core.hyperion_cli import cmd_bench
            cmd_bench(self._mock_args(tasks=50))
            self.assertIn("Benchmark", out.getvalue())


class TestCmdHttp(unittest.TestCase):
    def test_cmd_http_calls_server_run(self):
        mock_srv = MagicMock()
        with patch("core.hyperion_cli.HyperionHTTPServer", return_value=mock_srv):
            import argparse
            args = argparse.Namespace(host="127.0.0.1", port=8765, machines="a,b", shards=3)
            from core.hyperion_cli import cmd_http
            cmd_http(args)
            mock_srv.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
