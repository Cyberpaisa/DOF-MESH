"""Herramientas para organización de archivos y proyectos."""

import os
import json
from pathlib import Path
from collections import defaultdict
from crewai.tools import BaseTool


class ScanDirectoryTool(BaseTool):
    name: str = "scan_directory"
    description: str = (
        "Escanea un directorio y genera un reporte detallado de su estructura: "
        "tipos de archivo, tamaños, archivos más grandes, posibles problemas. "
        "Input: ruta al directorio."
    )

    def _run(self, directory_path: str) -> str:
        path = Path(directory_path)
        if not path.exists():
            return f"❌ Directorio no encontrado: {directory_path}"

        exclude_dirs = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", ".cache",
        }

        stats = {
            "total_files": 0,
            "total_size": 0,
            "by_extension": defaultdict(lambda: {"count": 0, "size": 0}),
            "largest_files": [],
            "empty_files": [],
            "deep_nesting": [],
        }

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            depth = str(root).count(os.sep) - str(path).count(os.sep)

            for f in files:
                fp = Path(root) / f
                try:
                    size = fp.stat().st_size
                except OSError:
                    continue

                ext = fp.suffix.lower() or "(sin extensión)"
                rel = fp.relative_to(path)

                stats["total_files"] += 1
                stats["total_size"] += size
                stats["by_extension"][ext]["count"] += 1
                stats["by_extension"][ext]["size"] += size
                stats["largest_files"].append((str(rel), size))

                if size == 0:
                    stats["empty_files"].append(str(rel))
                if depth > 6:
                    stats["deep_nesting"].append(str(rel))

        # Top 10 archivos más grandes
        stats["largest_files"].sort(key=lambda x: -x[1])
        top_files = stats["largest_files"][:10]

        report = f"""
📁 ESCANEO DE DIRECTORIO: {directory_path}
{'='*60}

📊 Resumen:
  - Total archivos: {stats['total_files']:,}
  - Tamaño total: {stats['total_size']/1024/1024:.1f} MB

📋 Por tipo de archivo:
"""
        sorted_exts = sorted(
            stats["by_extension"].items(),
            key=lambda x: -x[1]["count"]
        )
        for ext, info in sorted_exts[:15]:
            report += f"  {ext}: {info['count']} archivos ({info['size']/1024:.1f} KB)\n"

        report += f"\n📦 Top 10 archivos más grandes:\n"
        for fpath, size in top_files:
            report += f"  {fpath} ({size/1024:.1f} KB)\n"

        if stats["empty_files"]:
            report += f"\n⚠ Archivos vacíos ({len(stats['empty_files'])}):\n"
            for f in stats["empty_files"][:10]:
                report += f"  {f}\n"

        if stats["deep_nesting"]:
            report += f"\n⚠ Archivos con anidamiento profundo (>6 niveles): {len(stats['deep_nesting'])}\n"

        return report


class OrganizeProjectTool(BaseTool):
    name: str = "suggest_project_structure"
    description: str = (
        "Analiza la estructura actual de un proyecto y sugiere una organización "
        "óptima basada en el tipo de proyecto detectado (React, Python, Full-stack, etc.). "
        "Input: ruta al directorio del proyecto."
    )

    def _run(self, project_path: str) -> str:
        path = Path(project_path)
        if not path.exists():
            return f"❌ Directorio no encontrado: {project_path}"

        # Detectar tipo de proyecto
        indicators = {
            "react": ["package.json", "src/App.jsx", "src/App.tsx"],
            "nextjs": ["next.config.js", "next.config.mjs", "pages/", "app/"],
            "python": ["setup.py", "pyproject.toml", "requirements.txt"],
            "django": ["manage.py", "settings.py"],
            "fastapi": ["main.py", "requirements.txt"],
            "fullstack": ["frontend/", "backend/", "api/"],
        }

        detected = []
        existing_files = set()
        for root, dirs, files in os.walk(path):
            if any(x in root for x in ["node_modules", ".git", "__pycache__"]):
                continue
            for f in files:
                rel = str(Path(root, f).relative_to(path))
                existing_files.add(rel)
            for d in dirs:
                rel = str(Path(root, d).relative_to(path)) + "/"
                existing_files.add(rel)

        for ptype, files in indicators.items():
            if any(f in existing_files or any(f in ef for ef in existing_files) for f in files):
                detected.append(ptype)

        project_type = detected[0] if detected else "generic"

        # Estructuras recomendadas
        structures = {
            "react": """
📂 Estructura recomendada (React):
src/
├── components/          # Componentes reutilizables
│   ├── ui/              # Componentes UI base (Button, Input, Card)
│   └── features/        # Componentes de funcionalidad específica
├── hooks/               # Custom hooks
├── services/            # Llamadas API, lógica de negocio
├── stores/              # Estado global (Zustand/Redux)
├── utils/               # Funciones utilitarias
├── types/               # TypeScript types/interfaces
├── constants/           # Constantes y configuración
├── assets/              # Imágenes, fuentes, etc.
└── pages/               # Páginas/vistas principales
""",
            "python": """
📂 Estructura recomendada (Python):
project_name/
├── src/
│   ├── __init__.py
│   ├── core/            # Lógica de negocio principal
│   ├── models/          # Modelos de datos
│   ├── services/        # Servicios y lógica externa
│   ├── utils/           # Funciones utilitarias
│   └── config.py        # Configuración
├── tests/
│   ├── unit/
│   └── integration/
├── data/                # Datos de entrada/salida
├── scripts/             # Scripts de automatización
├── docs/                # Documentación
├── pyproject.toml
├── requirements.txt
└── README.md
""",
            "fullstack": """
📂 Estructura recomendada (Full-Stack):
project/
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── backend/
│   ├── src/
│   ├── tests/
│   └── requirements.txt
├── shared/              # Tipos/contratos compartidos
├── database/
│   ├── migrations/
│   └── seeds/
├── scripts/             # DevOps y automatización
├── docs/
├── docker-compose.yml
└── README.md
""",
        }

        structure = structures.get(project_type, structures["python"])

        report = f"""
🔍 ANÁLISIS DE ESTRUCTURA: {project_path}
{'='*60}

🏷 Tipo de proyecto detectado: {project_type.upper()}
📌 Indicadores encontrados: {detected}

{structure}

📋 Archivos actuales que necesitan atención:
"""
        # Detectar archivos fuera de lugar
        root_files = [f for f in existing_files if "/" not in f and not f.startswith(".")]
        if root_files:
            report += f"\n  Archivos en raíz ({len(root_files)}): {root_files[:10]}\n"

        return report
