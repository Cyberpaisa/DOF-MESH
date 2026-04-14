from __future__ import annotations
import os
import shutil
from pathlib import Path

# Configuración
REPO_ROOT = Path(__file__).parent.parent
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"))
SKILLS_DIR = REPO_ROOT / "skills"
DEST_DIR = VAULT_PATH / "wiki" / "skills"

def sync_skills():
    """Copia los SKILL.md de cada habilidad al vault de Obsidian."""
    if not VAULT_PATH.exists():
        print(f"[ERROR] Vault no encontrado en: {VAULT_PATH}")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for skill_path in SKILLS_DIR.iterdir():
        if skill_path.is_dir():
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                # Nombre del archivo basado en el nombre de la habilidad
                dest_file = DEST_DIR / f"{skill_path.name}.md"
                
                # Leer y añadir metadato de origen si es necesario
                content = skill_md.read_text(encoding="utf-8")
                
                # Copiar archivo
                print(f"Sincronizando {skill_path.name} -> {dest_file}")
                dest_file.write_text(content, encoding="utf-8")
                count += 1
                
    print(f"\n[OK] Sincronización completada: {count} habilidades en el vault.")

if __name__ == "__main__":
    sync_skills()
