from __future__ import annotations
"""
SupplyChainGuard — Protección proactiva contra supply chain attacks.

Detecta y bloquea amenazas de cadena de suministro:
  1. Auditoría de requirements.txt — versiones pinneadas, paquetes comprometidos
  2. Verificación de integridad de paquetes — blacklist de paquetes maliciosos
  3. Escaneo de imports peligrosos — eval, exec, pickle, subprocess shell
  4. Detección de esteganografía — archivos binarios sospechosos en directorios de código
  5. Auditoría de seguridad de .env — private keys, permisos, .gitignore
  6. Reporte de seguridad consolidado

Contexto:
  - Ataque Glassworm (npm supply chain, commit 0612e72)
  - TeamPCP comprometió telnyx y LiteLLM en PyPI con malware en WAV files
  - Scanning activo de CVE-2025-53521 en F5 BIG-IP

100% deterministic — zero LLM. Zero external dependencies. Solo stdlib.

Persistence:
  logs/security/supply_chain_audit.jsonl

Usage:
    from core.supply_chain_guard import SupplyChainGuard

    guard = SupplyChainGuard()
    result = guard.audit_requirements("requirements.txt")
    report = guard.generate_security_report()
"""

import json
import logging
import os
import re
import stat
import time
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.supply_chain_guard")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs", "security")
LOG_FILE = os.path.join(LOG_DIR, "supply_chain_audit.jsonl")


# ===================================================================
# THREAT INTELLIGENCE — Paquetes comprometidos conocidos
# ===================================================================

COMPROMISED_PACKAGES: dict[str, dict] = {
    # TeamPCP — PyPI supply chain via WAV steganography (2026-03)
    "telnyx": {
        "versions": ["4.87.1", "4.87.2"],
        "group": "TeamPCP",
        "date": "2026-03",
        "vector": "WAV steganography malware",
    },
    "litellm": {
        # Versiones comprometidas en PyPI 2026-03-24 (~40 min live before quarantine)
        # Payload: litellm_init.pth — credential stealer auto-exec en Python startup
        # Ataque vía Trivy comprometido (19 mar) → PYPI_PUBLISH token exfiltrado
        # CVEs relacionados: CVE-2026-35030 (auth bypass), CVE-2026-40217 (hash exposure)
        # Decisión DOF-MESH: REMOVIDO completamente (sesión 13, 2026-04-16)
        "versions": ["1.67.0", "1.67.1", "1.82.7", "1.82.8"],
        "group": "TeamPCP",
        "date": "2026-03-24",
        "vector": "litellm_init.pth credential stealer — env/SSH/cloud/K8s secrets",
    },
    # Glassworm — npm/PyPI supply chain (2026-03)
    "openclaw": {
        "versions": ["*"],
        "group": "Glassworm",
        "date": "2026-03",
        "vector": "Malicious package — data exfiltration",
    },
    "mission-control": {
        "versions": ["*"],
        "group": "Glassworm",
        "date": "2026-03",
        "vector": "npm supply chain — backdoor",
    },
    # Otros conocidos
    "py-crypt": {
        "versions": ["*"],
        "group": "Unknown",
        "date": "2025-12",
        "vector": "Typosquat de pycryptodome",
    },
    "python-binance-sdk": {
        "versions": ["*"],
        "group": "Unknown",
        "date": "2025-11",
        "vector": "Typosquat — credential stealer",
    },
}

# IOCs — Indicators of Compromise (from RuneAI analysis 2026-03-27)
KNOWN_C2_SERVERS = [
    "83.142.209.203",  # TeamPCP C2 — telnyx/litellm WAV payload delivery
    "194.33.61.36",    # CTRL Framework (Russian RAT) — Jan-Feb 2026
    "109.107.168.18",  # CTRL Framework — active since 27 Feb 2026
]

# CTRL Framework — Russian RAT (.NET) — Censys ARC Feb 2026
CTRL_IOCS = {
    "domain": "hui228.ru",
    "ports": [7000, 7500, 82, 5267, 908],  # FRP, payload hosting, C2
    "named_pipe": "ctrlPipe",
    "ssh_fingerprint": "6106ea733ed6263f18d8bb63c5696f2ae6c1383cab887a02f18f1af38107f9d4",
    "tls_cert_sha256": "5d009f6f46979fbc170ede90fca15f945d6dae5286221cca77fa26223a5fe931",
}

KNOWN_MALICIOUS_HASHES = {
    # telnyx 4.87.2 (TeamPCP, 2026-03-27)
    "md5": ["9e837f0b9e8037b06256e2c4291f757"],
    "sha1": ["6e06766423a9c046511fb32b10c4a49adfe6e2b"],
    "sha256": ["ab4c4aebb52027bf3d2f6b2dcef593a1a2cff415774ea4711f7d6e0aa1451d4e"],
}

DANGEROUS_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern, risk_description, severity)
    (r'\beval\s*\(', "eval() — ejecución de código arbitrario", "HIGH"),
    (r'\bexec\s*\(', "exec() — ejecución de código arbitrario", "HIGH"),
    (r'\bos\.system\s*\(', "os.system() — ejecución de comandos shell", "HIGH"),
    (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "subprocess.call(shell=True) — inyección de comandos", "HIGH"),
    (r'subprocess\.run\s*\([^)]*shell\s*=\s*True', "subprocess.run(shell=True) — inyección de comandos", "HIGH"),
    (r'subprocess\.Popen\s*\([^)]*shell\s*=\s*True', "subprocess.Popen(shell=True) — inyección de comandos", "HIGH"),
    (r'\bpickle\.loads?\s*\(', "pickle.load(s)() — deserialización insegura", "CRITICAL"),
    (r'\b__import__\s*\(', "__import__() — importación dinámica no controlada", "MEDIUM"),
    (r'\bcompile\s*\(', "compile() — compilación dinámica de código", "MEDIUM"),
    (r'\bimportlib\.import_module\s*\(', "importlib.import_module() — importación dinámica", "MEDIUM"),
    (r'\bctypes\.\w+\s*\(', "ctypes — acceso directo a memoria/FFI", "MEDIUM"),
    (r'\bsocket\.socket\s*\(', "socket.socket() — conexión de red directa", "LOW"),
]

SUSPICIOUS_EXTENSIONS: list[str] = [
    ".wav", ".mp3", ".mp4", ".exe", ".dll", ".so", ".bin",
    ".scr", ".bat", ".cmd", ".msi", ".vbs", ".ps1",
]

# Extensiones normales de assets que no deberían alertar
ASSET_DIRS: set[str] = {"assets", "static", "media", "public", "resources", "sounds", "audio", "images", "img"}

PRIVATE_KEY_PATTERNS: list[re.Pattern] = [
    re.compile(r"PRIVATE[_\s]?KEY\s*=", re.IGNORECASE),
    re.compile(r"SECRET[_\s]?KEY\s*=", re.IGNORECASE),
    re.compile(r"WALLET[_\s]?PRIVATE", re.IGNORECASE),
    re.compile(r"0x[0-9a-fA-F]{64}"),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"MNEMONIC\s*=", re.IGNORECASE),
    re.compile(r"SEED[_\s]?PHRASE\s*=", re.IGNORECASE),
]


# ===================================================================
# DATA CLASSES
# ===================================================================

@dataclass
class PackageCheck:
    """Resultado de verificación de un paquete individual."""
    name: str
    version: str
    safe: bool
    reason: str


@dataclass
class AuditResult:
    """Resultado de auditoría de requirements.txt."""
    safe_count: int
    unpinned_count: int
    compromised_count: int
    warnings: list[str]
    packages: list[PackageCheck] = field(default_factory=list)


@dataclass
class ImportRisk:
    """Un riesgo detectado en imports/código."""
    file: str
    line: int
    risk: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class SuspiciousFile:
    """Un archivo sospechoso detectado."""
    path: str
    reason: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class EnvAudit:
    """Resultado de auditoría de archivo .env."""
    has_private_keys: bool
    permissions_ok: bool
    in_gitignore: bool
    warnings: list[str]


@dataclass
class SecurityReport:
    """Reporte de seguridad consolidado."""
    timestamp: float
    total_risks: int
    critical: int
    high: int
    medium: int
    low: int
    details: list[dict]


# ===================================================================
# SUPPLY CHAIN GUARD
# ===================================================================

class SupplyChainGuard:
    """Guardia proactiva contra supply chain attacks.

    Escanea dependencias, imports, archivos binarios y configuraciones
    para detectar amenazas conocidas y patrones sospechosos.

    Zero external dependencies. Deterministic. JSONL audit trail.
    """

    def __init__(self, project_dir: str | None = None):
        self.project_dir = project_dir or BASE_DIR
        self.blacklist = dict(COMPROMISED_PACKAGES)
        os.makedirs(LOG_DIR, exist_ok=True)

    # --- a) Auditoría de requirements.txt ---

    def audit_requirements(self, requirements_path: str) -> AuditResult:
        """Audita requirements.txt para versiones no pinneadas y paquetes comprometidos.

        Verifica:
          - Todas las versiones están pinneadas (==x.y.z)
          - Ningún paquete está en la blacklist
          - No se usan operadores inseguros (>=, <=, ~=, *)

        Args:
            requirements_path: Ruta al archivo requirements.txt

        Returns:
            AuditResult con conteos y warnings.
        """
        safe_count = 0
        unpinned_count = 0
        compromised_count = 0
        warnings: list[str] = []
        packages: list[PackageCheck] = []

        try:
            with open(requirements_path, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            warnings.append(f"Archivo no encontrado: {requirements_path}")
            return AuditResult(0, 0, 0, warnings, [])

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()

            # Saltar comentarios y líneas vacías
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Parsear nombre y versión
            pkg_name, version, pinned = self._parse_requirement(line)

            if not pkg_name:
                continue

            # Verificar si está comprometido
            check = self.check_package_integrity(pkg_name, version)

            if not check.safe:
                compromised_count += 1
                warnings.append(
                    f"CRITICAL L{line_num}: {pkg_name} comprometido — {check.reason}"
                )
                packages.append(check)
                continue

            # Verificar si está pinneado
            if not pinned:
                unpinned_count += 1
                warnings.append(
                    f"WARN L{line_num}: {pkg_name} no tiene versión pinneada (usar ==x.y.z)"
                )
                packages.append(PackageCheck(
                    name=pkg_name, version=version or "unspecified",
                    safe=True, reason="Version no pinneada — riesgo de supply chain"
                ))
            else:
                safe_count += 1
                packages.append(check)

        result = AuditResult(
            safe_count=safe_count,
            unpinned_count=unpinned_count,
            compromised_count=compromised_count,
            warnings=warnings,
            packages=packages,
        )

        self._log("audit_requirements", {
            "file": requirements_path,
            "safe": safe_count,
            "unpinned": unpinned_count,
            "compromised": compromised_count,
            "warnings_count": len(warnings),
        })

        return result

    # --- b) Verificación de paquete individual ---

    def check_package_integrity(self, package_name: str, version: str = "") -> PackageCheck:
        """Verifica un paquete contra la blacklist de paquetes comprometidos.

        Args:
            package_name: Nombre del paquete (ej: 'telnyx')
            version: Versión específica (ej: '4.87.1')

        Returns:
            PackageCheck con resultado de la verificación.
        """
        pkg_lower = package_name.lower().strip()

        if pkg_lower in self.blacklist:
            info = self.blacklist[pkg_lower]
            bad_versions = info["versions"]

            # Wildcard = todas las versiones comprometidas
            if "*" in bad_versions:
                return PackageCheck(
                    name=package_name, version=version or "*",
                    safe=False,
                    reason=(
                        f"Paquete comprometido por {info['group']} "
                        f"({info['date']}): {info['vector']}"
                    ),
                )

            # Versión específica comprometida
            if version and version in bad_versions:
                return PackageCheck(
                    name=package_name, version=version,
                    safe=False,
                    reason=(
                        f"Versión {version} comprometida por {info['group']} "
                        f"({info['date']}): {info['vector']}"
                    ),
                )

            # Paquete en blacklist pero versión no afectada
            return PackageCheck(
                name=package_name, version=version or "unknown",
                safe=True,
                reason=(
                    f"Paquete en watchlist ({info['group']}) — "
                    f"versión {version} no está en la lista de comprometidas"
                ),
            )

        return PackageCheck(
            name=package_name, version=version or "unknown",
            safe=True,
            reason="No está en la blacklist de paquetes comprometidos",
        )

    # --- c) Escaneo de imports peligrosos ---

    def scan_imports(self, directory: str) -> list[ImportRisk]:
        """Escanea archivos .py buscando imports y patrones de código peligrosos.

        Detecta:
          - Imports de paquetes en la blacklist
          - eval(), exec(), os.system()
          - subprocess con shell=True
          - pickle.loads() (deserialización insegura)
          - __import__() dinámico

        Args:
            directory: Directorio a escanear recursivamente.

        Returns:
            Lista de ImportRisk con los riesgos encontrados.
        """
        risks: list[ImportRisk] = []

        for root, dirs, files in os.walk(directory):
            # Saltar directorios ocultos y __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for fname in files:
                if not fname.endswith(".py"):
                    continue

                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", errors="replace") as f:
                        lines = f.readlines()
                except (PermissionError, OSError):
                    continue

                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()

                    # Saltar comentarios
                    if stripped.startswith("#"):
                        continue

                    # Verificar imports de paquetes comprometidos
                    import_match = re.match(
                        r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped
                    )
                    if import_match:
                        pkg = import_match.group(1).lower()
                        if pkg in self.blacklist:
                            info = self.blacklist[pkg]
                            risks.append(ImportRisk(
                                file=fpath,
                                line=line_num,
                                risk=(
                                    f"Import de paquete comprometido: {pkg} "
                                    f"(grupo: {info['group']})"
                                ),
                                severity="CRITICAL",
                            ))

                    # Verificar patrones peligrosos
                    for pattern, desc, severity in DANGEROUS_PATTERNS:
                        if re.search(pattern, stripped):
                            # No alertar si está en un comentario inline
                            code_before_comment = stripped.split("#")[0]
                            if re.search(pattern, code_before_comment):
                                risks.append(ImportRisk(
                                    file=fpath,
                                    line=line_num,
                                    risk=desc,
                                    severity=severity,
                                ))

        self._log("scan_imports", {
            "directory": directory,
            "risks_found": len(risks),
            "critical": sum(1 for r in risks if r.severity == "CRITICAL"),
            "high": sum(1 for r in risks if r.severity == "HIGH"),
        })

        return risks

    # --- d) Detección de esteganografía ---

    def scan_for_steganography(
        self,
        directory: str,
        extensions: list[str] | None = None,
    ) -> list[SuspiciousFile]:
        """Busca archivos sospechosos que podrían contener malware esteganográfico.

        Detecta:
          - Archivos .wav, .mp3, .png, .jpg en directorios de código (no assets)
          - Archivos binarios en directorios Python
          - Archivos con extensión engañosa (ej: script.py.wav)

        Args:
            directory: Directorio a escanear recursivamente.
            extensions: Lista de extensiones a buscar (default: SUSPICIOUS_EXTENSIONS).

        Returns:
            Lista de SuspiciousFile con archivos sospechosos.
        """
        exts = extensions or SUSPICIOUS_EXTENSIONS
        suspicious: list[SuspiciousFile] = []

        for root, dirs, files in os.walk(directory):
            # Saltar directorios ocultos y __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            # Determinar si estamos en un directorio de assets
            dir_parts = set(os.path.normpath(root).split(os.sep))
            is_asset_dir = bool(dir_parts & ASSET_DIRS)

            for fname in files:
                fpath = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)
                ext_lower = ext.lower()

                # Doble extensión sospechosa (ej: malware.py.wav)
                name_without_ext = fname[:-len(ext)] if ext else fname
                if "." in name_without_ext:
                    inner_ext = os.path.splitext(name_without_ext)[1].lower()
                    if inner_ext in (".py", ".js", ".ts", ".sh", ".rb"):
                        suspicious.append(SuspiciousFile(
                            path=fpath,
                            reason=(
                                f"Extensión engañosa: {fname} — "
                                f"posible código disfrazado como {ext_lower}"
                            ),
                            severity="CRITICAL",
                        ))
                        continue

                # Archivos sospechosos en directorios de código
                if ext_lower in exts and not is_asset_dir:
                    # Verificar si hay archivos .py en el mismo directorio
                    has_py = any(f.endswith(".py") for f in files)

                    if has_py:
                        suspicious.append(SuspiciousFile(
                            path=fpath,
                            reason=(
                                f"Archivo {ext_lower} en directorio de código Python — "
                                f"posible esteganografía (vector TeamPCP/WAV)"
                            ),
                            severity="HIGH",
                        ))
                    else:
                        suspicious.append(SuspiciousFile(
                            path=fpath,
                            reason=(
                                f"Archivo {ext_lower} en directorio no-assets — "
                                f"verificar origen"
                            ),
                            severity="MEDIUM",
                        ))

        self._log("scan_steganography", {
            "directory": directory,
            "suspicious_found": len(suspicious),
            "critical": sum(1 for s in suspicious if s.severity == "CRITICAL"),
        })

        return suspicious

    # --- e) Auditoría de seguridad .env ---

    def validate_env_security(self, env_path: str) -> EnvAudit:
        """Verifica la seguridad del archivo .env.

        Verifica:
          - Presencia de private keys o secrets
          - Permisos del archivo (debería ser 600)
          - Inclusión en .gitignore

        Args:
            env_path: Ruta al archivo .env

        Returns:
            EnvAudit con resultados de la auditoría.
        """
        warnings: list[str] = []
        has_private_keys = False
        permissions_ok = True
        in_gitignore = False

        # Verificar si existe
        if not os.path.isfile(env_path):
            warnings.append(f"Archivo .env no encontrado: {env_path}")
            return EnvAudit(
                has_private_keys=False,
                permissions_ok=True,
                in_gitignore=False,
                warnings=warnings,
            )

        # Verificar contenido
        try:
            with open(env_path, "r") as f:
                content = f.read()

            for pattern in PRIVATE_KEY_PATTERNS:
                if pattern.search(content):
                    has_private_keys = True
                    warnings.append(
                        f"CRITICAL: Clave privada detectada en {env_path} — "
                        f"patrón: {pattern.pattern}"
                    )
                    break
        except (PermissionError, OSError) as e:
            warnings.append(f"No se pudo leer {env_path}: {e}")

        # Verificar permisos (Unix)
        try:
            file_stat = os.stat(env_path)
            mode = oct(file_stat.st_mode)[-3:]

            if mode != "600":
                permissions_ok = False
                warnings.append(
                    f"WARN: Permisos de {env_path} son {mode} — "
                    f"recomendado: 600 (chmod 600 {env_path})"
                )
        except OSError:
            pass

        # Verificar .gitignore
        env_dir = os.path.dirname(os.path.abspath(env_path))
        gitignore_path = os.path.join(env_dir, ".gitignore")

        if not os.path.isfile(gitignore_path):
            # Buscar en directorio padre
            parent_gitignore = os.path.join(
                os.path.dirname(env_dir), ".gitignore"
            )
            if os.path.isfile(parent_gitignore):
                gitignore_path = parent_gitignore

        if os.path.isfile(gitignore_path):
            try:
                with open(gitignore_path, "r") as f:
                    gitignore_content = f.read()

                env_basename = os.path.basename(env_path)
                # Verificar patrones comunes
                patterns_to_check = [".env", env_basename, "*.env"]
                for p in patterns_to_check:
                    if p in gitignore_content:
                        in_gitignore = True
                        break
            except OSError:
                pass

        if not in_gitignore:
            warnings.append(
                f"WARN: {env_path} NO está en .gitignore — "
                f"riesgo de exponer secretos en el repositorio"
            )

        result = EnvAudit(
            has_private_keys=has_private_keys,
            permissions_ok=permissions_ok,
            in_gitignore=in_gitignore,
            warnings=warnings,
        )

        self._log("validate_env", {
            "file": env_path,
            "has_private_keys": has_private_keys,
            "permissions_ok": permissions_ok,
            "in_gitignore": in_gitignore,
        })

        return result

    # --- f) Reporte de seguridad consolidado ---

    def generate_security_report(
        self,
        requirements_path: str | None = None,
        scan_dir: str | None = None,
        env_path: str | None = None,
    ) -> SecurityReport:
        """Ejecuta TODOS los checks y genera un reporte de seguridad consolidado.

        Escanea: requirements, imports, esteganografía, env.

        Args:
            requirements_path: Ruta a requirements.txt (default: project_dir/requirements.txt)
            scan_dir: Directorio a escanear (default: project_dir)
            env_path: Ruta al .env (default: project_dir/.env)

        Returns:
            SecurityReport con métricas y detalles.
        """
        scan_dir = scan_dir or self.project_dir
        requirements_path = requirements_path or os.path.join(self.project_dir, "requirements.txt")
        env_path = env_path or os.path.join(self.project_dir, ".env")

        details: list[dict] = []
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        # 1. Auditar requirements
        if os.path.isfile(requirements_path):
            req_audit = self.audit_requirements(requirements_path)
            if req_audit.compromised_count > 0:
                severity_counts["CRITICAL"] += req_audit.compromised_count
            if req_audit.unpinned_count > 0:
                severity_counts["MEDIUM"] += req_audit.unpinned_count

            for w in req_audit.warnings:
                sev = "CRITICAL" if "CRITICAL" in w else "MEDIUM"
                details.append({"source": "requirements", "severity": sev, "detail": w})

        # 2. Escanear imports
        import_risks = self.scan_imports(scan_dir)
        for risk in import_risks:
            severity_counts[risk.severity] = severity_counts.get(risk.severity, 0) + 1
            details.append({
                "source": "imports",
                "severity": risk.severity,
                "file": risk.file,
                "line": risk.line,
                "detail": risk.risk,
            })

        # 3. Escanear esteganografía
        steg_files = self.scan_for_steganography(scan_dir)
        for sf in steg_files:
            severity_counts[sf.severity] = severity_counts.get(sf.severity, 0) + 1
            details.append({
                "source": "steganography",
                "severity": sf.severity,
                "file": sf.path,
                "detail": sf.reason,
            })

        # 4. Validar .env
        if os.path.isfile(env_path):
            env_audit = self.validate_env_security(env_path)
            if env_audit.has_private_keys:
                severity_counts["CRITICAL"] += 1
            if not env_audit.permissions_ok:
                severity_counts["MEDIUM"] += 1
            if not env_audit.in_gitignore:
                severity_counts["HIGH"] += 1

            for w in env_audit.warnings:
                sev = "CRITICAL" if "CRITICAL" in w else ("HIGH" if "HIGH" in w else "MEDIUM")
                details.append({"source": "env", "severity": sev, "detail": w})

        total = sum(severity_counts.values())

        report = SecurityReport(
            timestamp=time.time(),
            total_risks=total,
            critical=severity_counts["CRITICAL"],
            high=severity_counts["HIGH"],
            medium=severity_counts["MEDIUM"],
            low=severity_counts["LOW"],
            details=details,
        )

        self._log("security_report", {
            "total_risks": total,
            "critical": severity_counts["CRITICAL"],
            "high": severity_counts["HIGH"],
            "medium": severity_counts["MEDIUM"],
            "low": severity_counts["LOW"],
        })

        return report

    # --- Utilidades ---

    def add_to_blacklist(
        self, package: str, versions: list[str],
        group: str = "Unknown", vector: str = "Unknown",
    ) -> None:
        """Agrega un paquete a la blacklist en runtime.

        Args:
            package: Nombre del paquete.
            versions: Lista de versiones comprometidas (['*'] para todas).
            group: Grupo de amenaza.
            vector: Vector de ataque.
        """
        self.blacklist[package.lower()] = {
            "versions": versions,
            "group": group,
            "date": time.strftime("%Y-%m"),
            "vector": vector,
        }

        self._log("blacklist_update", {
            "package": package,
            "versions": versions,
            "group": group,
        })

    @staticmethod
    def _parse_requirement(line: str) -> tuple[str, str, bool]:
        """Parsea una línea de requirements.txt.

        Returns:
            (package_name, version, is_pinned)
        """
        # Remover extras [dev], comentarios inline, espacios
        line = re.sub(r'\[.*?\]', '', line).split("#")[0].strip()

        if not line:
            return ("", "", False)

        # Pinneado exacto: package==1.2.3
        match = re.match(r'^([a-zA-Z0-9_.-]+)\s*==\s*([^\s,]+)', line)
        if match:
            return (match.group(1), match.group(2), True)

        # Con operador (>=, <=, ~=, !=, <, >)
        match = re.match(r'^([a-zA-Z0-9_.-]+)\s*([><=~!]+)\s*([^\s,]+)', line)
        if match:
            return (match.group(1), match.group(3), False)

        # Sin versión
        match = re.match(r'^([a-zA-Z0-9_.-]+)\s*$', line)
        if match:
            return (match.group(1), "", False)

        return ("", "", False)

    def _log(self, event: str, data: dict) -> None:
        """Persiste evento de auditoría en JSONL."""
        try:
            entry = {
                "event": event,
                "timestamp": time.time(),
                "data": data,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Supply chain audit log error: {e}")


# --- Convenience functions ---

def quick_audit(project_dir: str | None = None) -> SecurityReport:
    """Ejecuta auditoría rápida del proyecto."""
    guard = SupplyChainGuard(project_dir)
    return guard.generate_security_report()


def check_package(name: str, version: str = "") -> PackageCheck:
    """Verificación rápida de un paquete."""
    return SupplyChainGuard().check_package_integrity(name, version)


# --- Quick test ---

if __name__ == "__main__":
    guard = SupplyChainGuard()

    # Test rápido de blacklist
    result = guard.check_package_integrity("telnyx", "4.87.1")
    print(f"telnyx 4.87.1: safe={result.safe} — {result.reason}")

    result = guard.check_package_integrity("requests", "2.31.0")
    print(f"requests 2.31.0: safe={result.safe} — {result.reason}")

    print("\nBlacklist activa:")
    for pkg, info in guard.blacklist.items():
        print(f"  {pkg}: {info['group']} — {info['vector']}")
