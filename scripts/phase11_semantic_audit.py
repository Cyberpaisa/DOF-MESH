import ast
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("semantic.audit")

def get_symbols(file_path):
    """Extrae nombres de funciones y clases de un archivo Python."""
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r") as f:
        tree = ast.parse(f.read())
    
    symbols = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            symbols.add(node.name)
    return symbols

def perform_audit(file_path, prev_symbols):
    """Compara símbolos actuales con previos para detectar refactorizaciones."""
    current_symbols = get_symbols(file_path)
    
    added = current_symbols - prev_symbols
    removed = prev_symbols - current_symbols
    
    report = {
        "timestamp": os.path.getmtime(file_path),
        "file": file_path,
        "added": list(added),
        "removed": list(removed),
        "semantic_ops": []
    }
    
    # Detección simple de refactorización (extracción/renombrado)
    if added and removed:
        report["semantic_ops"].append("Posible refactorización/extracción detectada.")
        
    logger.info(f"[AUDITOR] Escaneado {file_path}: {len(added)} nuevos, {len(removed)} eliminados.")
    return report, current_symbols

if __name__ == "__main__":
    # Auditoría inicial de prueba
    _, symbols = perform_audit("core/qaion_router.py", set())
    print(f"Símbolos detectados: {symbols}")
