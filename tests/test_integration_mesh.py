"""Tests de integración: ByzantineNodeGuard + NodeCapabilityRegistry en NodeMesh."""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.node_mesh import NodeMesh


class TestNodeMeshByzantineIntegration(unittest.TestCase):
    """Verifica que NodeMesh integra ByzantineNodeGuard correctamente."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mesh = NodeMesh(
            cwd=self.tmp_dir,
            mesh_dir=os.path.join(self.tmp_dir, "mesh"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_node_mesh_has_byzantine_guard(self):
        """NodeMesh debe tener byzantine_guard inicializado."""
        self.assertIsNotNone(self.mesh.byzantine_guard)

    def test_node_mesh_has_capability_registry(self):
        """NodeMesh debe tener capability_registry inicializado."""
        self.assertIsNotNone(self.mesh.capability_registry)

    def test_record_success_works(self):
        """record_node_success() no debe lanzar excepcion."""
        self.mesh.record_node_success("test-node-1")

    def test_record_failure_works(self):
        """record_node_failure() no debe lanzar excepcion."""
        self.mesh.record_node_failure("test-node-1", reason="timeout")

    def test_is_node_allowed_default_true(self):
        """Un nodo nuevo debe estar permitido por defecto."""
        self.assertTrue(self.mesh.is_node_allowed("fresh-node"))

    def test_register_capability(self):
        """register_node_capability() no debe lanzar excepcion."""
        self.mesh.register_node_capability(
            node_id="node-42",
            memory_gb=32.0,
            z3_timeout_ms=50,
            chain_support=["avalanche-c"],
            agent_type="validator",
        )

    def test_get_best_node_returns_none_empty(self):
        """Sin nodos registrados, get_best_node() retorna None."""
        result = self.mesh.get_best_node(complexity="high")
        self.assertIsNone(result)

    def test_get_best_node_after_register(self):
        """Despues de registrar un nodo, get_best_node() lo retorna."""
        self.mesh.register_node_capability(
            node_id="node-core",
            memory_gb=32.0,
            z3_timeout_ms=50,
            chain_support=["avalanche-c"],
            agent_type="validator",
        )
        result = self.mesh.get_best_node(complexity="high")
        self.assertEqual(result, "node-core")

    def test_quarantined_node_excluded_from_best(self):
        """Un nodo en cuarentena no debe ser retornado por get_best_node()."""
        self.mesh.register_node_capability(
            node_id="bad-node",
            memory_gb=32.0,
            z3_timeout_ms=50,
            chain_support=["avalanche-c"],
            agent_type="validator",
        )
        # Forzar cuarentena con muchos fallos
        for _ in range(30):
            self.mesh.record_node_failure("bad-node", reason="crash")
        self.assertFalse(self.mesh.is_node_allowed("bad-node"))
        result = self.mesh.get_best_node(complexity="high")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
