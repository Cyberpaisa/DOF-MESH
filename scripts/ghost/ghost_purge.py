import os
import re

# Glassworm/Unicode Malware Protection Pattern
GHOST_PATTERN = re.compile(r"[\uFE00-\uFE0F\U000E0100-\U000E01EF]")

def purge_directory(path):
    print(f"[*] INICIANDO PURGA EN: {path}")
    purged_count = 0
    for root, dirs, files in os.walk(path):
        # EXCLUIR node_modules (demasiado pesado para esta herramienta, requiere reinstall)
        # y directorios internos del asistente
        if "node_modules" in root or ".git" in root or ".gemini" in root:
            continue
            
        for file in files:
            if file.endswith((".py", ".js", ".json", ".md", ".sh", ".txt", ".yaml", ".yml")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    sanitized = GHOST_PATTERN.sub("", content)
                    
                    if sanitized != content:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(sanitized)
                        print(f"[!] ARCHIVO DECONTAMINADO: {file_path}")
                        purged_count += 1
                except Exception as e:
                    # print(f"[?] Error en {file_path}: {e}")
                    continue
    
    print(f"\n[✓] PURGA COMPLETADA. {purged_count} archivos restaurados.")
    print("[!] RECOMENDACIÓN: Ejecuta 'npm install' en mission-control para limpiar dependencias externas.")

if __name__ == "__main__":
    purge_directory("/Users/jquiceva/equipo-de-agentes")
