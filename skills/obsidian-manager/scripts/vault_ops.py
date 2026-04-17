from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional

# Cargar configuración del vault
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"))

def search_notes(query: str, limit: int = 5) -> List[Dict]:
    """
    Realiza una búsqueda simple en el vault por nombre o contenido.
    """
    results = []
    query_lower = query.lower()
    
    # Solo buscar en carpetas autorizadas
    scan_folders = ["wiki", "raw", "_agent/tasks"]
    
    for folder in scan_folders:
        target = VAULT_PATH / folder
        if not target.exists():
            continue
            
        for path in target.rglob("*.md"):
            if any(path.name.startswith(p) for p in [".", "~"]):
                continue
                
            match = False
            if query_lower in path.name.lower():
                match = True
            else:
                try:
                    content = path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        match = True
                except:
                    continue
            
            if match:
                results.append({
                    "name": path.name,
                    "path": str(path.relative_to(VAULT_PATH)),
                    "abs_path": str(path)
                })
                if len(results) >= limit:
                    return results
                    
    return results

def read_note(rel_path: str) -> Dict:
    """
    Lee una nota y separa el frontmatter del contenido.
    """
    path = VAULT_PATH / rel_path
    if not path.exists():
        return {"error": f"Nota no encontrada: {rel_path}"}
        
    content = path.read_text(encoding="utf-8")
    
    meta = {}
    body = content
    
    if content.startswith("---"):
        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_raw = parts[1].strip()
                body = parts[2].strip()
                for line in fm_raw.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip().strip('"').strip("'")
        except:
            pass
            
    return {
        "path": rel_path,
        "metadata": meta,
        "content": body
    }

def append_log(rel_path: str, message: str, agent: str = "Weaver") -> bool:
    """
    Añade una línea de log al final de una nota, manteniendo el formato DOF-MESH.
    """
    path = VAULT_PATH / rel_path
    if not path.exists():
        # Intentar crear si es en logs/
        if "logs/" in rel_path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\ntype: log\ncreated_at: {json.dumps(str(Path().cwd()))}\n---\n\n# Logs\n", encoding="utf-8")
        else:
            return False
            
    timestamp = json.dumps(str(Path().cwd())) # Placeholder para timestamp real si no hay datetime
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- [{timestamp}] **{agent}**: {message}")
        
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "search":
            print(json.dumps(search_notes(sys.argv[2]), indent=2))
        elif cmd == "read":
            print(json.dumps(read_note(sys.argv[2]), indent=2))
