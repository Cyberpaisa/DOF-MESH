import os
import re

# Patterns to look for
PATTERNS = {
    "BASE64_DECODE": re.compile(r"base64\.b64decode\("),
    "EVAL_EXEC": re.compile(r"(eval|exec)\("),
    "SUSPICIOUS_HEX": re.compile(r"\\x[0-9a-fA-F]{2}"),
    "LARGE_NON_ASCII": re.compile(r"[^\x00-\x7F]{5,}")  # Clusters of non-ASCII
}

MONITOR_PATHS = [
    "/Users/jquiceva/equipo-de-agentes/core",
    "/Users/jquiceva/equipo-de-agentes/scripts",
    "/Users/jquiceva/equipo-de-agentes/interfaces"
]

def scan_forensic():
    print("[*] INICIANDO AUDITORIA FORENSE DE ALTA PROFUNDIDAD")
    found_any = False
    for path in MONITOR_PATHS:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith((".py", ".js")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        for p_name, pattern in PATTERNS.items():
                            matches = pattern.findall(content)
                            if matches:
                                if p_name == "EVAL_EXEC" and "argparse" in content: # Common in CLI
                                    continue
                                print(f"[!] {p_name} detectado en: {file_path} (Coincidencias: {len(matches)})")
                                found_any = True
                    except:
                        continue
    if not found_any:
        print("[✓] CERO PATRONES SOSPECHOSOS ENCONTRADOS.")

if __name__ == "__main__":
    scan_forensic()
