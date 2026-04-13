"""
FIREWALL IMPROVEMENTS — DOF-MESH Red Team Findings
Parches propuestos para las vulnerabilidades encontradas en la sesión 2026-04-13.

Cada parche incluye:
  - CVE-DOF-XXXX: identificador interno
  - Capa afectada
  - Severidad: CRITICAL / HIGH / MEDIUM
  - Código del parche listo para integrar en el módulo correspondiente

NOTA: Este archivo es SOLO referencia. Los parches deben aplicarse
en los módulos canónicos: core/governance.py, core/ast_verifier.py, etc.
"""

import re
import unicodedata

# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-001: Newline Injection (DI-002)
# Severity: CRITICAL
# Layer: Constitution / OverrideDetector
# Issue: Payload con "SYSTEM:" después de newlines no es detectado
# ─────────────────────────────────────────────────────────────────────────────

PATCH_001_NEWLINE_INJECTION = [
    # Agregar a _OVERRIDE_PATTERNS en core/governance.py
    r"(?m)^-{3,}\s*\n.*?SYSTEM\s*:",           # --- separator + SYSTEM:
    r"(?m)^(?:SYSTEM|SYS)\s*:\s*\w",            # SYSTEM: al inicio de línea
    r"(?m)\n\s*---\s*\n(?:SYSTEM|ADMIN|ROOT)",  # markdown rule + SYSTEM
]

PATCH_001_VALIDATOR = """
# Agregar a check_instruction_override() en core/governance.py
def _check_newline_injection(text: str) -> bool:
    '''Detecta SYSTEM: inyectado tras saltos de línea o separadores.'''
    patterns = [
        r'(?m)^-{{3,}}\\s*\\n.*?SYSTEM\\s*:',
        r'(?m)^(?:SYSTEM|SYS)\\s*:\\s*\\w',
        r'(?i)SYSTEM\\s*:\\s*(?:governance|directive|override|disable)',
    ]
    for p in patterns:
        if re.search(p, text, re.DOTALL):
            return True
    return False
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-002: Unicode Homoglyph Bypass (SI-001)
# Severity: HIGH
# Layer: OverrideDetector
# Issue: Letras cirílicas (о=U+043E, а=U+0430, е=U+0435) evaden regex ASCII
# ─────────────────────────────────────────────────────────────────────────────

def normalize_homoglyphs(text: str) -> str:
    """
    Normaliza caracteres homoglyphs a su equivalente ASCII.
    Debe aplicarse ANTES de ejecutar cualquier regex en governance.py.

    Ejemplo:
        'Ignоrе аll' (con cirílicos) → 'Ignore all' (ASCII puro)
    """
    # Tabla de homoglyphs conocidos (Unicode → ASCII)
    HOMOGLYPH_MAP = {
        '\u0430': 'a',  # Cyrillic а → a
        '\u0435': 'e',  # Cyrillic е → e
        '\u043E': 'o',  # Cyrillic о → o
        '\u0440': 'r',  # Cyrillic р → r
        '\u0441': 'c',  # Cyrillic с → c
        '\u043A': 'k',  # Cyrillic к → k
        '\u0445': 'x',  # Cyrillic х → x
        '\u0456': 'i',  # Cyrillic і → i
        '\u0421': 'C',  # Cyrillic С → C
        '\u0410': 'A',  # Cyrillic А → A
        '\u0415': 'E',  # Cyrillic Е → E
        '\u041E': 'O',  # Cyrillic О → O
        '\u0420': 'R',  # Cyrillic Р → R
        '\uff49': 'i',  # Fullwidth i
        '\uff4f': 'o',  # Fullwidth o
        '\uff41': 'a',  # Fullwidth a
    }
    normalized = []
    for ch in text:
        normalized.append(HOMOGLYPH_MAP.get(ch, ch))
    return ''.join(normalized)


def normalize_for_governance(text: str) -> str:
    """
    Pipeline completo de normalización antes de aplicar governance.
    1. Elimina zero-width characters
    2. Normaliza homoglyphs
    3. Colapsa whitespace excesivo
    4. Normaliza Unicode a NFC
    """
    # Paso 1: eliminar zero-width chars
    ZWS_CHARS = [
        '\u200b',  # Zero Width Space
        '\u200c',  # Zero Width Non-Joiner
        '\u200d',  # Zero Width Joiner
        '\ufeff',  # BOM / Zero Width No-Break Space
        '\u00ad',  # Soft Hyphen
        '\u2060',  # Word Joiner
    ]
    for zws in ZWS_CHARS:
        text = text.replace(zws, '')

    # Paso 2: normalizar homoglyphs
    text = normalize_homoglyphs(text)

    # Paso 3: NFC normalization
    text = unicodedata.normalize('NFC', text)

    # Paso 4: colapsar whitespace padding extremo (>20 espacios seguidos)
    text = re.sub(r'[ \t]{20,}', ' ', text)

    return text


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-003: Base64 / Encoding Not Decoded (SI-003)
# Severity: HIGH
# Layer: Adversarial / EncodingScanner
# Issue: decode_and_scan() no detecta "Decode and execute: <base64>"
# ─────────────────────────────────────────────────────────────────────────────

PATCH_003_ENCODING_TRIGGER = """
# Agregar a EncodingScanner.decode_and_scan() en core/adversarial.py
# ANTES de pasar el texto al pipeline de governance, detectar si hay
# instrucciones de decodificación explícitas.

ENCODING_TRIGGER_PATTERNS = [
    r'(?i)decode\\s+and\\s+(?:execute|run|apply)',
    r'(?i)(?:base64|b64|rot13|hex)\\s*(?:decode|encoded)',
    r'(?i)convert\\s+this\\s+from\\s+base64',
    r'(?i)the\\s+following\\s+is\\s+(?:base64|encoded)',
]

def check_encoding_trigger(text: str) -> dict:
    for p in ENCODING_TRIGGER_PATTERNS:
        if re.search(p, text):
            # Intentar decodificar cualquier string base64 en el texto
            import base64
            b64_matches = re.findall(r'[A-Za-z0-9+/]{20,}={0,2}', text)
            for match in b64_matches:
                try:
                    decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                    if any(kw in decoded.lower() for kw in ['ignore', 'override', 'system', 'bypass']):
                        return {'threat_detected': True, 'encoding': 'base64_triggered', 'decoded': decoded[:100]}
                except Exception:
                    pass
    return {'threat_detected': False}
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-004: False System Prompt Injection (PE-001)
# Severity: CRITICAL
# Layer: enforce_hierarchy()
# Issue: "SYSTEM: New directive" en campo user → violation_level=NONE
# ─────────────────────────────────────────────────────────────────────────────

PATCH_004_USER_SYSTEM_CLAIM = """
# Agregar a enforce_hierarchy() en core/governance.py
# Si el campo 'user' contiene 'SYSTEM:' → SYSTEM_OVERRIDE violation

SYSTEM_CLAIM_IN_USER = [
    r'(?i)^\\s*SYSTEM\\s*:',
    r'(?i)^\\s*\\[\\s*SYSTEM\\s*\\]',
    r'(?i)^\\s*<SYSTEM>',
    r'(?i)NEW\\s+(?:DIRECTIVE|SYSTEM|RULE)\\s*(?:OVERRIDE|:)',
    r'(?i)you\\s+are\\s+now\\s+(?:DAN|GPT-4-unleashed|unrestricted)',
]

def detect_user_claiming_system(user_text: str) -> bool:
    for p in SYSTEM_CLAIM_IN_USER:
        if re.search(p, user_text, re.MULTILINE):
            return True
    return False
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-005: Indirect Escalation Patterns (PE-002 to PE-005)
# Severity: HIGH
# Layer: _ESCALATION_PATTERNS
# Issue: Frases de escalación indirecta no cubiertas por los 11 patrones actuales
# ─────────────────────────────────────────────────────────────────────────────

NEW_ESCALATION_PATTERNS = [
    # Frases no cubiertas — agregar a _ESCALATION_PATTERNS en governance.py
    r"security\s+team\s+(?:has\s+)?(?:updated|changed|modified)\s+(?:your\s+)?(?:config|configuration|settings|mode)",
    r"\[PRIORITY\s*:\s*SYSTEM\]",
    r"\[OVERRIDE\s*:\s*(?:TRUE|YES|1)\]",
    r"for\s+(?:testing\s+)?purposes?\s+only,?\s+(?:temporarily\s+)?disable",
    r"AUDIT\s+LOG\s*:",
    r"(?:continuing|resuming)\s+from\s+(?:last|previous)\s+session\s+state",
    r"maintenance\s+mode\s+(?:activated|enabled|on)",
    r"(?:all\s+)?safety\s+checks?\s+(?:suspended|disabled|bypassed|off)",
    r"diagnostic\s+(?:mode|override)\s+(?:active|enabled|on)",
    r"as\s+(?:the\s+)?(?:lead\s+)?developer\s+of\s+this\s+system",
    r"temporarily\s+disable\s+(?:one|a)\s+rule",
    r"(?:new|updated)\s+(?:mode|policy)\s*:\s*unrestricted",
]

PATCH_005_VALIDATOR = """
# Validación integrada — correr sobre user_message en enforce_hierarchy()
def detect_indirect_escalation(text: str) -> list[str]:
    matches = []
    for pattern in NEW_ESCALATION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            matches.append(f'ESCALATION: {m.group()[:60]}')
    return matches
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-006: AST Path Traversal & Decorator Side Effects (AST-005, AST-006)
# Severity: HIGH
# Layer: ASTVerifier
# Issue: Concatenación de paths y decoradores con side effects pasan AST check
# ─────────────────────────────────────────────────────────────────────────────

PATCH_006_AST_RULES = """
# Agregar a ASTVerifier._get_rules() en core/ast_verifier.py

# Regla 1: path traversal via string concatenation
{
    'id': 'PATH_TRAVERSAL',
    'pattern': r\"(?:'/etc'|'/var'|'/root'|'/home'|'C:\\\\\\\\\\\\\\\\')\s*\\+\",
    'severity': 'block',
    'message': 'Potential path traversal via string concatenation',
},

# Regla 2: open() con path sensitivo
{
    'id': 'SENSITIVE_FILE_OPEN',
    'pattern': r\"open\\s*\\([^)]*(?:/etc/passwd|/etc/shadow|/proc/|/sys/)\",
    'severity': 'block',
    'message': 'Attempt to open sensitive system file',
},

# Regla 3: decorator body imports (side effects)
# Requiere AST walk — agregar a _analyze_node():
# if isinstance(node, ast.FunctionDef):
#     for decorator in node.decorator_list:
#         check_decorator_body_for_imports(decorator, node)
"""

PATCH_006_AST_DECORATOR_CHECKER = """
import ast

def check_decorator_imports(tree: ast.AST) -> list[str]:
    '''Detecta decoradores que importan módulos o ejecutan comandos como side effect.'''
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                # Si el cuerpo del decorator hace imports o exec
                decorator_name = getattr(decorator, 'id', None) or getattr(
                    getattr(decorator, 'func', None), 'id', '')
                # Buscar funciones que se usan como decorator y tienen imports
                for fn in ast.walk(tree):
                    if isinstance(fn, ast.FunctionDef) and fn.name == decorator_name:
                        for stmt in ast.walk(fn):
                            if isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
                                violations.append(f'Decorator {decorator_name} imports module')
                            if isinstance(stmt, ast.Call):
                                func = getattr(stmt.func, 'id', '') or getattr(
                                    getattr(stmt.func, 'attr', None), '', '')
                                if func in ('system', 'exec', 'eval', 'popen'):
                                    violations.append(f'Decorator {decorator_name} calls {func}()')
    return violations
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-007: Z3/AnomalyReport API Mismatch (Z3-001 to Z3-004)
# Severity: MEDIUM (bug en integración, no en Z3 core)
# Layer: Z3 / SECOP integration
# Issue: AnomalyReport no tiene attr 'anomalies' — usa estructura diferente
# ─────────────────────────────────────────────────────────────────────────────

PATCH_007_ANOMALYREPORT_FIX = """
# En tests/red_team/redteam_runner.py — fix temporal
# En integrations/datos-colombia/tools/secop.py — fix permanente

# El objeto AnomalyReport retorna por detect_anomalies() tiene:
# - report.flagged_contracts (list)
# - report.total_contracts (int)
# - report.proof_hash (str)
# NO tiene: report.anomalies

# Fix en redteam_runner.py:
report = detect_anomalies(contracts)
# Cambiar:
blocked = len(report.anomalies) > 0
# Por:
blocked = len(getattr(report, 'flagged_contracts', [])) > 0 or \\
          len(getattr(report, 'anomalies', [])) > 0  # compatibilidad futura

# Fix permanente en secop.py — agregar alias:
@property
def anomalies(self):
    return self.flagged_contracts
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-008: Memory Poisoning via Fake Constitution Entry (MP-001, MP-002)
# Severity: HIGH
# Layer: Memory Layer (ChromaDB)
# Issue: content con SYSTEM_RULE_OVERRIDE pasa governance check
# ─────────────────────────────────────────────────────────────────────────────

PATCH_008_MEMORY_GATE = """
# Agregar en core/memory_manager.py ANTES de add_to_memory():

FORBIDDEN_MEMORY_PATTERNS = [
    r'(?i)SYSTEM\\s+RULE\\s+OVERRIDE',
    r'(?i)governance\\s+(?:has\\s+been\\s+)?updated',
    r'(?i)new\\s+rule\\s*:\\s*always\\s+comply',
    r'(?i)(?:constitution|governance|rules)\\s+v[0-9]',  # versión fake
]

FORBIDDEN_METADATA_SOURCES = [
    'constitution_v2', 'constitution_v3',  # solo 'constitution' es válido
    'system_override', 'admin', 'root',
]

def validate_memory_entry(content: str, metadata: dict) -> tuple[bool, str]:
    '''Valida que un entry de memoria no sea adversarial antes de guardar.'''
    for p in FORBIDDEN_MEMORY_PATTERNS:
        if re.search(p, content):
            return False, f'Forbidden pattern in memory content: {p}'

    source = metadata.get('source', '')
    if source in FORBIDDEN_METADATA_SOURCES:
        return False, f'Forbidden metadata source: {source}'

    # No permitir metadata con priority=SYSTEM desde user messages
    if metadata.get('priority') == 'SYSTEM' and metadata.get('from_user'):
        return False, 'User cannot inject SYSTEM priority in memory'

    return True, 'OK'
"""


# ─────────────────────────────────────────────────────────────────────────────
# CVE-DOF-009: Fake URL Satisfies NO_HALLUCINATION_CLAIM (GB-001)
# Severity: MEDIUM
# Layer: Constitution — phrase_without_url check
# Issue: phrase_without_url solo verifica presencia de URL, no validez
# ─────────────────────────────────────────────────────────────────────────────

PATCH_009_URL_VALIDATION = """
# Mejorar phrase_without_url en core/governance.py

TRUSTED_DOMAINS = {
    # Dominios académicos/científicos de alta confianza
    'arxiv.org', 'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com',
    'nature.com', 'science.org', 'ieee.org', 'acm.org',
    # Fuentes gubernamentales
    'datos.gov.co', 'colombiacompra.gov.co', 'dane.gov.co',
    # Documentación técnica
    'docs.python.org', 'developer.mozilla.org', 'github.com',
    'pypi.org', 'npmjs.com',
}

SUSPICIOUS_URL_PATTERNS = [
    r'fake[-_]?(?:study|data|source|research)',
    r'(?:study|data|results|stats)\d{4,}',
    r'(?:made|invented|fabricated)-source',
]

def validate_source_url(url: str) -> tuple[bool, str]:
    '''
    Valida si una URL es de fuente confiable.
    No bloquea — solo contribuye al score de confiabilidad.
    '''
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().removeprefix('www.')

        if any(re.search(p, url, re.I) for p in SUSPICIOUS_URL_PATTERNS):
            return False, 'Suspicious URL pattern (possible fabricated source)'

        if domain in TRUSTED_DOMAINS:
            return True, 'Trusted domain'

        return True, 'Unknown domain (no penalty)'
    except Exception:
        return False, 'Invalid URL'
"""


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN DE PRIORIDADES DE IMPLEMENTACIÓN
# ─────────────────────────────────────────────────────────────────────────────

IMPLEMENTATION_PRIORITY = [
    {
        "cve": "CVE-DOF-001",
        "priority": 1,
        "severity": "CRITICAL",
        "vectors": ["DI-002", "DI-007"],
        "module": "core/governance.py",
        "effort": "30 min",
        "impact": "Bloquea newline injection + developer override",
    },
    {
        "cve": "CVE-DOF-004",
        "priority": 2,
        "severity": "CRITICAL",
        "vectors": ["PE-001"],
        "module": "core/governance.py → enforce_hierarchy()",
        "effort": "20 min",
        "impact": "Bloquea user claiming SYSTEM level",
    },
    {
        "cve": "CVE-DOF-002",
        "priority": 3,
        "severity": "HIGH",
        "vectors": ["SI-001", "SI-002", "SI-010"],
        "module": "core/governance.py — agregar normalize_for_governance()",
        "effort": "45 min",
        "impact": "Bloquea homoglyphs + ZWS + whitespace flooding",
    },
    {
        "cve": "CVE-DOF-005",
        "priority": 4,
        "severity": "HIGH",
        "vectors": ["PE-002", "PE-003", "PE-004", "PE-005"],
        "module": "core/governance.py → _ESCALATION_PATTERNS",
        "effort": "30 min",
        "impact": "12 nuevos patrones de escalación indirecta",
    },
    {
        "cve": "CVE-DOF-008",
        "priority": 5,
        "severity": "HIGH",
        "vectors": ["MP-001", "MP-002"],
        "module": "core/memory_manager.py",
        "effort": "45 min",
        "impact": "Memory gate — bloquea envenenamiento de ChromaDB",
    },
    {
        "cve": "CVE-DOF-003",
        "priority": 6,
        "severity": "HIGH",
        "vectors": ["SI-003"],
        "module": "core/adversarial.py → EncodingScanner",
        "effort": "30 min",
        "impact": "Detecta instrucciones trigger de decodificación",
    },
    {
        "cve": "CVE-DOF-006",
        "priority": 7,
        "severity": "HIGH",
        "vectors": ["AST-005", "AST-006"],
        "module": "core/ast_verifier.py",
        "effort": "60 min",
        "impact": "Path traversal + decorator side effects",
    },
    {
        "cve": "CVE-DOF-007",
        "priority": 8,
        "severity": "MEDIUM",
        "vectors": ["Z3-001", "Z3-002", "Z3-003", "Z3-004"],
        "module": "integrations/datos-colombia/tools/secop.py",
        "effort": "15 min",
        "impact": "Fix AnomalyReport.anomalies alias",
    },
    {
        "cve": "CVE-DOF-009",
        "priority": 9,
        "severity": "MEDIUM",
        "vectors": ["GB-001", "GB-005"],
        "module": "core/governance.py → phrase_without_url",
        "effort": "30 min",
        "impact": "URL source validation (reduce hallucination surface)",
    },
]


def print_summary():
    print("\n" + "=" * 70)
    print("  DOF-MESH FIREWALL IMPROVEMENTS — Red Team 2026-04-13")
    print("=" * 70)
    print(f"  Total CVEs documentados: {len(IMPLEMENTATION_PRIORITY)}")
    critical = [p for p in IMPLEMENTATION_PRIORITY if p["severity"] == "CRITICAL"]
    high = [p for p in IMPLEMENTATION_PRIORITY if p["severity"] == "HIGH"]
    medium = [p for p in IMPLEMENTATION_PRIORITY if p["severity"] == "MEDIUM"]
    print(f"  CRITICAL: {len(critical)} | HIGH: {len(high)} | MEDIUM: {len(medium)}")
    print()

    for p in IMPLEMENTATION_PRIORITY:
        sev_color = "\033[91m" if p["severity"] == "CRITICAL" else \
                    "\033[93m" if p["severity"] == "HIGH" else "\033[94m"
        reset = "\033[0m"
        print(f"  [{p['priority']}] {sev_color}{p['cve']} [{p['severity']}]{reset}")
        print(f"      Vectors : {', '.join(p['vectors'])}")
        print(f"      Module  : {p['module']}")
        print(f"      Effort  : {p['effort']}")
        print(f"      Impact  : {p['impact']}")
        print()

    print("=" * 70)
    print("  Total esfuerzo estimado: ~5.5 horas para todos los parches")
    print("  Prioridad inmediata (CVE-001 + CVE-004): 50 minutos")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_summary()
