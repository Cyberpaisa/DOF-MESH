import os
import re

# Rango de Variaciones de Selector (U+FE00 - U+FE0F) y Tags (U+E0100 - U+E01EF)
GHOST_PATTERN = re.compile(r"[\uFE00-\uFE0F\U000E0100-\U000E01EF]")

def scan_directory(path):
    print(f"[*] Escaneando: {path}")
    found_count = 0
    for root, dirs, files in os.walk(path):
        if ".git" in root or ".gemini" in root:
            continue
        for file in files:
            if file.endswith((".py", ".js", ".json", ".md", ".sh", ".txt")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        matches = GHOST_PATTERN.findall(content)
                        if matches:
                            print(f"[!] ALERTA: Caracteres invisibles (Glassworm) detectados en: {file_path}")
                            print(f"    - Coincidencias: {len(matches)}")
                            found_count += 1
                except Exception:
                    continue
    
    if found_count == 0:
        print("[✓] No se detectaron patrones de Glassworm en el código fuente.")
    else:
        print(f"[!] SE DETECTARON {found_count} ARCHIVOS COMPROMETIDOS.")

if __name__ == "__main__":
    scan_directory("/Users/jquiceva/equipo-de-agentes")
