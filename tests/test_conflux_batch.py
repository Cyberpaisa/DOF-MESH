"""Tests for scripts/conflux_batch_attest.py"""
import sys
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfluxBatchAttest(unittest.TestCase):

    def _run_batch(self, count=5, dry_run=True, delay_ms=0):
        """Helper — importa y corre el batch en modo controlado."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "conflux_batch_attest",
            Path(__file__).parent.parent / "scripts" / "conflux_batch_attest.py"
        )
        mod = importlib.util.load_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_dry_run_completes_without_error(self):
        """Batch en dry_run con 5 ciclos no lanza excepción."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/conflux_batch_attest.py",
             "--count", "5", "--dry-run", "--delay-ms", "0"],
            capture_output=True, text=True,
            cwd=Path(__file__).parent.parent
        )
        self.assertEqual(result.returncode, 0,
                         msg=f"stdout: {result.stdout}\nstderr: {result.stderr}")

    def test_jsonl_output_has_correct_count(self):
        """Batch genera N líneas en el JSONL de resultados."""
        import subprocess
        output_file = Path(__file__).parent.parent / "logs" / "conflux_batch_results.jsonl"

        # Contar líneas antes
        before = 0
        if output_file.exists():
            with open(output_file) as f:
                before = sum(1 for _ in f)

        subprocess.run(
            [sys.executable, "scripts/conflux_batch_attest.py",
             "--count", "3", "--dry-run", "--delay-ms", "0"],
            capture_output=True, cwd=Path(__file__).parent.parent
        )

        # Verificar que se agregaron 3 líneas
        with open(output_file) as f:
            after = sum(1 for _ in f)
        self.assertEqual(after - before, 3)

    def test_proof_hash_unique_per_cycle(self):
        """Cada ciclo genera un proof_hash único."""
        import subprocess
        output_file = Path(__file__).parent.parent / "logs" / "conflux_batch_results.jsonl"

        before = 0
        if output_file.exists():
            with open(output_file) as f:
                before = sum(1 for _ in f)

        subprocess.run(
            [sys.executable, "scripts/conflux_batch_attest.py",
             "--count", "5", "--dry-run", "--delay-ms", "0"],
            capture_output=True, cwd=Path(__file__).parent.parent
        )

        hashes = []
        with open(output_file) as f:
            lines = f.readlines()
        new_lines = lines[before:]
        for line in new_lines:
            record = json.loads(line)
            hashes.append(record["proof_hash"])

        self.assertEqual(len(hashes), len(set(hashes)),
                         "Proof hashes deben ser únicos por ciclo")


if __name__ == "__main__":
    unittest.main()
