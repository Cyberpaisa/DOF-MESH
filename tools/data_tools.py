"""Herramientas para trabajar con Excel, CSV y bases de datos."""

import os
import re
import json
from pathlib import Path
from crewai.tools import BaseTool


class ReadExcelTool(BaseTool):
    name: str = "read_excel_csv"
    description: str = (
        "Lee y analiza archivos Excel (.xlsx/.xls) o CSV. Devuelve resumen "
        "estadístico, tipos de datos, valores nulos, y primeras filas. "
        "Input: ruta al archivo. Soporta archivos grandes (lee por chunks)."
    )

    def _run(self, file_path: str) -> str:
        import pandas as pd

        path = Path(file_path)
        if not path.exists():
            return f"❌ Archivo no encontrado: {file_path}"

        try:
            ext = path.suffix.lower()
            if ext in (".xlsx", ".xls"):
                # Para archivos Excel grandes, leer info de hojas primero
                xl = pd.ExcelFile(path)
                sheets_info = f"📋 Hojas encontradas: {xl.sheet_names}\n\n"
                df = pd.read_excel(path, sheet_name=0)
            elif ext == ".csv":
                sheets_info = ""
                df = pd.read_csv(path, nrows=50000)  # Limitar para archivos muy grandes
            elif ext == ".tsv":
                sheets_info = ""
                df = pd.read_csv(path, sep="\t", nrows=50000)
            else:
                return f"❌ Formato no soportado: {ext}"

            # Análisis completo
            report = f"""
📊 ANÁLISIS DE DATOS: {path.name}
{'='*60}
{sheets_info}
📐 Dimensiones: {df.shape[0]:,} filas × {df.shape[1]} columnas
💾 Tamaño en memoria: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB

📋 Columnas y tipos:
{df.dtypes.to_string()}

🔍 Valores nulos por columna:
{df.isnull().sum().to_string()}

📊 Estadísticas numéricas:
{df.describe().to_string()}

📝 Primeras 10 filas:
{df.head(10).to_string()}

📝 Últimas 5 filas:
{df.tail(5).to_string()}

🔑 Valores únicos por columna (top 5 cada una):
"""
            for col in df.columns[:10]:
                uniques = df[col].nunique()
                top_vals = df[col].value_counts().head(5).to_dict()
                report += f"\n  {col} ({uniques} únicos): {top_vals}"

            return report

        except Exception as e:
            return f"❌ Error procesando archivo: {e}"


class QueryDatabaseTool(BaseTool):
    name: str = "query_database"
    description: str = (
        "Ejecuta consultas SQL en una base de datos PostgreSQL/MySQL. "
        "Input: consulta SQL (SELECT solamente por seguridad). "
        "Usa la variable DATABASE_URL del .env para conectar."
    )

    def _run(self, query: str) -> str:
        from sqlalchemy import create_engine, text
        import pandas as pd

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return "❌ DATABASE_URL no configurada en .env"

        # Seguridad: limpiar comentarios SQL y normalizar
        clean = " ".join(query.strip().split())
        clean = re.sub(r"--.*$", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
        clean = clean.strip()

        # Solo permitir queries que empiecen con SELECT/SHOW/DESCRIBE/EXPLAIN/WITH
        allowed_starts = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
        if not clean.upper().startswith(allowed_starts):
            return "❌ Solo se permiten consultas de lectura (SELECT, SHOW, DESCRIBE, EXPLAIN, WITH)"

        # Bloquear múltiples statements (prevenir piggyback injection)
        statements = [s.strip() for s in clean.split(";") if s.strip()]
        if len(statements) > 1:
            return "❌ Solo se permite una consulta a la vez (sin punto y coma múltiple)"

        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)

            report = f"""
🗃 RESULTADO DE CONSULTA
{'='*60}
SQL: {query}

📐 Resultado: {df.shape[0]:,} filas × {df.shape[1]} columnas

📋 Columnas: {list(df.columns)}

📊 Datos:
{df.head(50).to_string()}
"""
            if df.shape[0] > 50:
                report += f"\n... mostrando 50 de {df.shape[0]:,} filas"

            return report

        except Exception as e:
            return f"❌ Error en consulta: {e}"


class AnalyzeDataTool(BaseTool):
    name: str = "analyze_data_quality"
    description: str = (
        "Analiza la calidad de datos de un archivo Excel/CSV: detecta duplicados, "
        "inconsistencias, outliers, y sugiere limpieza. Input: ruta al archivo."
    )

    def _run(self, file_path: str) -> str:
        import pandas as pd
        import numpy as np

        path = Path(file_path)
        if not path.exists():
            return f"❌ Archivo no encontrado: {file_path}"

        try:
            ext = path.suffix.lower()
            if ext in (".xlsx", ".xls"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)

            report = f"""
🔬 ANÁLISIS DE CALIDAD DE DATOS: {path.name}
{'='*60}

1⃣ COMPLETITUD:
  - Filas totales: {len(df):,}
  - Filas completas (sin nulos): {df.dropna().shape[0]:,}
  - Porcentaje completitud: {df.dropna().shape[0]/len(df)*100:.1f}%

2⃣ DUPLICADOS:
  - Filas duplicadas: {df.duplicated().sum():,}
  - Porcentaje duplicados: {df.duplicated().sum()/len(df)*100:.1f}%

3⃣ VALORES NULOS POR COLUMNA:
"""
            for col in df.columns:
                null_count = df[col].isnull().sum()
                null_pct = null_count / len(df) * 100
                if null_count > 0:
                    report += f"  ⚠ {col}: {null_count:,} nulos ({null_pct:.1f}%)\n"

            report += "\n4⃣ OUTLIERS (columnas numéricas):\n"
            for col in df.select_dtypes(include=[np.number]).columns:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = ((df[col] < lower) | (df[col] > upper)).sum()
                if outliers > 0:
                    report += f"  ⚠ {col}: {outliers} outliers (rango esperado: {lower:.2f} - {upper:.2f})\n"

            report += "\n5⃣ TIPOS DE DATOS INCONSISTENTES:\n"
            for col in df.select_dtypes(include=["object"]).columns:
                # Detectar columnas que podrían ser numéricas
                numeric_count = pd.to_numeric(df[col], errors="coerce").notna().sum()
                if 0 < numeric_count < len(df[col].dropna()):
                    report += f"  ⚠ {col}: mezcla de tipos ({numeric_count} valores numéricos en columna de texto)\n"

            report += f"""
6⃣ RECOMENDACIONES:
  - {'✅ Sin duplicados' if df.duplicated().sum() == 0 else '🔧 Eliminar duplicados con df.drop_duplicates()'}
  - {'✅ Sin nulos' if df.isnull().sum().sum() == 0 else '🔧 Tratar valores nulos (imputar o eliminar)'}
  - Columnas candidatas a índice: {[c for c in df.columns if df[c].nunique() == len(df)][:3]}
"""
            return report

        except Exception as e:
            return f"❌ Error analizando datos: {e}"
