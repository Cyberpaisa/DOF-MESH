"""Tests para SupplyChainGuard — protección contra supply chain attacks.

Usa unittest + tmpdir. No lee archivos reales del repo.
Zero external dependencies.
"""

import os
import stat
import tempfile
import unittest

from core.supply_chain_guard import (
    SupplyChainGuard,
    AuditResult,
    PackageCheck,
    ImportRisk,
    SuspiciousFile,
    EnvAudit,
    SecurityReport,
    COMPROMISED_PACKAGES,
)


class TestAuditRequirements(unittest.TestCase):
    """Tests para audit_requirements()."""

    def setUp(self):
        self.guard = SupplyChainGuard()
        self.tmpdir = tempfile.mkdtemp()

    def test_pinned_requirements(self):
        """Todas las versiones pinneadas = safe."""
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("requests==2.31.0\n")
            f.write("flask==3.0.0\n")
            f.write("pydantic==2.5.3\n")

        result = self.guard.audit_requirements(req_path)

        self.assertIsInstance(result, AuditResult)
        self.assertEqual(result.safe_count, 3)
        self.assertEqual(result.unpinned_count, 0)
        self.assertEqual(result.compromised_count, 0)
        self.assertEqual(len(result.warnings), 0)

    def test_unpinned_requirements(self):
        """Detecta paquetes sin versión pinneada."""
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("requests>=2.31.0\n")
            f.write("flask\n")
            f.write("pydantic==2.5.3\n")

        result = self.guard.audit_requirements(req_path)

        self.assertEqual(result.unpinned_count, 2)
        self.assertEqual(result.safe_count, 1)
        self.assertTrue(any("flask" in w for w in result.warnings))
        self.assertTrue(any("requests" in w for w in result.warnings))

    def test_compromised_package_in_requirements(self):
        """Detecta paquete comprometido (telnyx 4.87.1)."""
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("requests==2.31.0\n")
            f.write("telnyx==4.87.1\n")

        result = self.guard.audit_requirements(req_path)

        self.assertEqual(result.compromised_count, 1)
        self.assertTrue(any("CRITICAL" in w for w in result.warnings))
        self.assertTrue(any("telnyx" in w for w in result.warnings))

    def test_comments_and_blanks_skipped(self):
        """Comentarios y líneas vacías se ignoran."""
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("requests==2.31.0\n")
            f.write("# Another comment\n")

        result = self.guard.audit_requirements(req_path)

        self.assertEqual(result.safe_count, 1)
        self.assertEqual(result.unpinned_count, 0)

    def test_missing_requirements_file(self):
        """Archivo inexistente retorna warning."""
        result = self.guard.audit_requirements("/nonexistent/requirements.txt")

        self.assertEqual(result.safe_count, 0)
        self.assertTrue(len(result.warnings) > 0)


class TestCheckPackageIntegrity(unittest.TestCase):
    """Tests para check_package_integrity()."""

    def setUp(self):
        self.guard = SupplyChainGuard()

    def test_compromised_package(self):
        """Detecta telnyx 4.87.1 como comprometido."""
        result = self.guard.check_package_integrity("telnyx", "4.87.1")

        self.assertIsInstance(result, PackageCheck)
        self.assertFalse(result.safe)
        self.assertIn("TeamPCP", result.reason)
        self.assertIn("comprometid", result.reason)

    def test_safe_package(self):
        """Paquete normal pasa verificación."""
        result = self.guard.check_package_integrity("requests", "2.31.0")

        self.assertTrue(result.safe)
        self.assertIn("No está en la blacklist", result.reason)

    def test_wildcard_compromised(self):
        """Paquete con wildcard (*) bloquea todas las versiones."""
        result = self.guard.check_package_integrity("openclaw", "1.0.0")

        self.assertFalse(result.safe)
        self.assertIn("Glassworm", result.reason)

    def test_safe_version_of_compromised_package(self):
        """Versión no comprometida de paquete en watchlist pasa."""
        result = self.guard.check_package_integrity("telnyx", "4.86.0")

        self.assertTrue(result.safe)
        self.assertIn("watchlist", result.reason)

    def test_case_insensitive(self):
        """La búsqueda es case-insensitive."""
        result = self.guard.check_package_integrity("TELNYX", "4.87.1")

        self.assertFalse(result.safe)


class TestScanImports(unittest.TestCase):
    """Tests para scan_imports()."""

    def setUp(self):
        self.guard = SupplyChainGuard()
        self.tmpdir = tempfile.mkdtemp()

    def test_dangerous_import_eval(self):
        """Detecta eval() en código Python."""
        py_path = os.path.join(self.tmpdir, "bad_eval.py")
        with open(py_path, "w") as f:
            f.write('data = input("Enter: ")\n')
            f.write('result = eval(data)\n')

        risks = self.guard.scan_imports(self.tmpdir)

        self.assertTrue(len(risks) > 0)
        eval_risks = [r for r in risks if "eval" in r.risk]
        self.assertTrue(len(eval_risks) > 0)
        self.assertEqual(eval_risks[0].severity, "HIGH")

    def test_dangerous_import_exec(self):
        """Detecta exec() en código Python."""
        py_path = os.path.join(self.tmpdir, "bad_exec.py")
        with open(py_path, "w") as f:
            f.write('code = "print(1)"\n')
            f.write('exec(code)\n')

        risks = self.guard.scan_imports(self.tmpdir)

        exec_risks = [r for r in risks if "exec" in r.risk]
        self.assertTrue(len(exec_risks) > 0)
        self.assertEqual(exec_risks[0].severity, "HIGH")

    def test_dangerous_pickle(self):
        """Detecta pickle.loads() como CRITICAL."""
        py_path = os.path.join(self.tmpdir, "bad_pickle.py")
        with open(py_path, "w") as f:
            f.write('import pickle\n')
            f.write('data = pickle.loads(raw_data)\n')

        risks = self.guard.scan_imports(self.tmpdir)

        pickle_risks = [r for r in risks if "pickle" in r.risk.lower()]
        self.assertTrue(len(pickle_risks) > 0)
        self.assertEqual(pickle_risks[0].severity, "CRITICAL")

    def test_safe_imports(self):
        """Código Python normal no genera alertas."""
        py_path = os.path.join(self.tmpdir, "safe_code.py")
        with open(py_path, "w") as f:
            f.write('import os\n')
            f.write('import json\n')
            f.write('from dataclasses import dataclass\n')
            f.write('\n')
            f.write('def hello():\n')
            f.write('    return "hello world"\n')

        risks = self.guard.scan_imports(self.tmpdir)

        self.assertEqual(len(risks), 0)

    def test_compromised_import(self):
        """Detecta import de paquete comprometido."""
        py_path = os.path.join(self.tmpdir, "bad_import.py")
        with open(py_path, "w") as f:
            f.write('import telnyx\n')
            f.write('client = telnyx.Client()\n')

        risks = self.guard.scan_imports(self.tmpdir)

        compromised = [r for r in risks if "comprometido" in r.risk]
        self.assertTrue(len(compromised) > 0)
        self.assertEqual(compromised[0].severity, "CRITICAL")

    def test_comments_skipped(self):
        """Comentarios con patrones peligrosos no alertan."""
        py_path = os.path.join(self.tmpdir, "commented.py")
        with open(py_path, "w") as f:
            f.write('# eval(dangerous_code)\n')
            f.write('x = 42\n')

        risks = self.guard.scan_imports(self.tmpdir)

        self.assertEqual(len(risks), 0)


class TestSteganography(unittest.TestCase):
    """Tests para scan_for_steganography()."""

    def setUp(self):
        self.guard = SupplyChainGuard()
        self.tmpdir = tempfile.mkdtemp()

    def test_steganography_wav_in_code(self):
        """Detecta .wav en directorio con archivos Python."""
        # Crear un directorio con archivos .py y un .wav sospechoso
        code_dir = os.path.join(self.tmpdir, "src")
        os.makedirs(code_dir)

        with open(os.path.join(code_dir, "main.py"), "w") as f:
            f.write("print('hello')\n")

        with open(os.path.join(code_dir, "payload.wav"), "wb") as f:
            f.write(b"\x00" * 100)

        suspicious = self.guard.scan_for_steganography(self.tmpdir)

        wav_files = [s for s in suspicious if ".wav" in s.path]
        self.assertTrue(len(wav_files) > 0)
        self.assertIn("TeamPCP", wav_files[0].reason)

    def test_steganography_normal_assets(self):
        """Archivos en directorio 'assets' no alertan."""
        assets_dir = os.path.join(self.tmpdir, "assets")
        os.makedirs(assets_dir)

        with open(os.path.join(assets_dir, "sound.wav"), "wb") as f:
            f.write(b"\x00" * 100)

        suspicious = self.guard.scan_for_steganography(self.tmpdir)

        # Los archivos en 'assets' no deberían generar alertas HIGH
        high_alerts = [s for s in suspicious if s.severity in ("CRITICAL", "HIGH")]
        self.assertEqual(len(high_alerts), 0)

    def test_double_extension(self):
        """Detecta extensión engañosa (script.py.wav)."""
        code_dir = os.path.join(self.tmpdir, "lib")
        os.makedirs(code_dir)

        with open(os.path.join(code_dir, "helper.py.wav"), "wb") as f:
            f.write(b"\x00" * 50)

        suspicious = self.guard.scan_for_steganography(self.tmpdir)

        critical = [s for s in suspicious if s.severity == "CRITICAL"]
        self.assertTrue(len(critical) > 0)
        self.assertIn("engañosa", critical[0].reason)

    def test_exe_in_code_dir(self):
        """Detecta .exe en directorio de código."""
        code_dir = os.path.join(self.tmpdir, "scripts")
        os.makedirs(code_dir)

        with open(os.path.join(code_dir, "run.py"), "w") as f:
            f.write("import os\n")

        with open(os.path.join(code_dir, "backdoor.exe"), "wb") as f:
            f.write(b"\x4d\x5a" + b"\x00" * 100)

        suspicious = self.guard.scan_for_steganography(self.tmpdir)

        exe_files = [s for s in suspicious if ".exe" in s.path]
        self.assertTrue(len(exe_files) > 0)


class TestEnvSecurity(unittest.TestCase):
    """Tests para validate_env_security()."""

    def setUp(self):
        self.guard = SupplyChainGuard()
        self.tmpdir = tempfile.mkdtemp()

    def test_env_private_key_warning(self):
        """Detecta private key en .env."""
        env_path = os.path.join(self.tmpdir, ".env")
        with open(env_path, "w") as f:
            f.write("DATABASE_URL=postgres://localhost:5432/db\n")
            f.write("WALLET_PRIVATE_KEY=0x1234567890abcdef\n")
            f.write("API_KEY=abc123\n")

        result = self.guard.validate_env_security(env_path)

        self.assertIsInstance(result, EnvAudit)
        self.assertTrue(result.has_private_keys)
        self.assertTrue(any("CRITICAL" in w for w in result.warnings))

    def test_env_permissions(self):
        """Verifica chmod 600 en .env."""
        env_path = os.path.join(self.tmpdir, ".env")
        with open(env_path, "w") as f:
            f.write("API_KEY=abc123\n")

        # Poner permisos inseguros (644)
        os.chmod(env_path, 0o644)

        result = self.guard.validate_env_security(env_path)

        self.assertFalse(result.permissions_ok)
        self.assertTrue(any("600" in w for w in result.warnings))

    def test_env_correct_permissions(self):
        """Permisos 600 pasan la verificación."""
        env_path = os.path.join(self.tmpdir, ".env")
        with open(env_path, "w") as f:
            f.write("API_KEY=abc123\n")

        os.chmod(env_path, 0o600)

        result = self.guard.validate_env_security(env_path)

        self.assertTrue(result.permissions_ok)

    def test_env_gitignore_check(self):
        """Verifica que .env está en .gitignore."""
        env_path = os.path.join(self.tmpdir, ".env")
        gitignore_path = os.path.join(self.tmpdir, ".gitignore")

        with open(env_path, "w") as f:
            f.write("SECRET=value\n")

        with open(gitignore_path, "w") as f:
            f.write("*.pyc\n")
            f.write(".env\n")
            f.write("__pycache__/\n")

        result = self.guard.validate_env_security(env_path)

        self.assertTrue(result.in_gitignore)

    def test_env_not_in_gitignore(self):
        """Warn si .env NO está en .gitignore."""
        env_path = os.path.join(self.tmpdir, ".env")
        gitignore_path = os.path.join(self.tmpdir, ".gitignore")

        with open(env_path, "w") as f:
            f.write("SECRET=value\n")

        with open(gitignore_path, "w") as f:
            f.write("*.pyc\n")

        result = self.guard.validate_env_security(env_path)

        self.assertFalse(result.in_gitignore)
        self.assertTrue(any("gitignore" in w.lower() for w in result.warnings))

    def test_env_missing(self):
        """Archivo .env inexistente retorna warning."""
        result = self.guard.validate_env_security("/nonexistent/.env")

        self.assertFalse(result.has_private_keys)
        self.assertTrue(len(result.warnings) > 0)


class TestSecurityReport(unittest.TestCase):
    """Tests para generate_security_report()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.guard = SupplyChainGuard(project_dir=self.tmpdir)

    def test_security_report(self):
        """Reporte completo se genera correctamente."""
        # Crear requirements con paquete comprometido
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("requests==2.31.0\n")
            f.write("telnyx==4.87.1\n")

        # Crear archivo .py con eval
        src_dir = os.path.join(self.tmpdir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "bad.py"), "w") as f:
            f.write('result = eval(user_input)\n')

        report = self.guard.generate_security_report(
            requirements_path=req_path,
            scan_dir=self.tmpdir,
        )

        self.assertIsInstance(report, SecurityReport)
        self.assertGreater(report.total_risks, 0)
        self.assertGreater(report.critical, 0)
        self.assertIsInstance(report.timestamp, float)
        self.assertIsInstance(report.details, list)
        self.assertTrue(len(report.details) > 0)

    def test_clean_project_report(self):
        """Proyecto limpio tiene 0 riesgos."""
        # Crear requirements limpio
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("requests==2.31.0\n")
            f.write("flask==3.0.0\n")

        # Crear código limpio
        with open(os.path.join(self.tmpdir, "app.py"), "w") as f:
            f.write("import json\n")
            f.write("def main():\n")
            f.write("    return {'status': 'ok'}\n")

        report = self.guard.generate_security_report(
            requirements_path=req_path,
            scan_dir=self.tmpdir,
        )

        self.assertEqual(report.critical, 0)
        self.assertEqual(report.high, 0)


class TestBlacklist(unittest.TestCase):
    """Tests para la blacklist dinámica."""

    def setUp(self):
        self.guard = SupplyChainGuard()

    def test_blacklist_update(self):
        """Blacklist se puede actualizar en runtime."""
        # Verificar que paquete nuevo no está bloqueado
        result = self.guard.check_package_integrity("evil-pkg", "1.0.0")
        self.assertTrue(result.safe)

        # Agregar a la blacklist
        self.guard.add_to_blacklist(
            "evil-pkg", ["1.0.0", "1.0.1"],
            group="TestGroup", vector="Test vector"
        )

        # Ahora debe estar bloqueado
        result = self.guard.check_package_integrity("evil-pkg", "1.0.0")
        self.assertFalse(result.safe)
        self.assertIn("TestGroup", result.reason)

    def test_default_blacklist_populated(self):
        """Blacklist por defecto contiene las amenazas conocidas."""
        self.assertIn("telnyx", COMPROMISED_PACKAGES)
        self.assertIn("openclaw", COMPROMISED_PACKAGES)
        self.assertIn("mission-control", COMPROMISED_PACKAGES)
        self.assertIn("litellm", COMPROMISED_PACKAGES)

    def test_blacklist_isolation(self):
        """Cada instancia tiene su propia blacklist (no muta el global)."""
        guard1 = SupplyChainGuard()
        guard2 = SupplyChainGuard()

        guard1.add_to_blacklist("only-in-guard1", ["*"], group="Test")

        result1 = guard1.check_package_integrity("only-in-guard1", "1.0")
        result2 = guard2.check_package_integrity("only-in-guard1", "1.0")

        self.assertFalse(result1.safe)
        self.assertTrue(result2.safe)


class TestParseRequirement(unittest.TestCase):
    """Tests para _parse_requirement()."""

    def test_pinned(self):
        name, ver, pinned = SupplyChainGuard._parse_requirement("requests==2.31.0")
        self.assertEqual(name, "requests")
        self.assertEqual(ver, "2.31.0")
        self.assertTrue(pinned)

    def test_greater_equal(self):
        name, ver, pinned = SupplyChainGuard._parse_requirement("flask>=3.0.0")
        self.assertEqual(name, "flask")
        self.assertFalse(pinned)

    def test_no_version(self):
        name, ver, pinned = SupplyChainGuard._parse_requirement("pydantic")
        self.assertEqual(name, "pydantic")
        self.assertEqual(ver, "")
        self.assertFalse(pinned)

    def test_empty_line(self):
        name, ver, pinned = SupplyChainGuard._parse_requirement("")
        self.assertEqual(name, "")


if __name__ == "__main__":
    unittest.main()
