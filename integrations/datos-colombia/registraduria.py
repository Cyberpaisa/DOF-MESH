"""Registraduría Nacional — Electoral data via CSV download.

La Registraduría NO tiene API JSON. Los datos electorales se obtienen
de archivos CSV descargables desde el observatorio electoral.
"""
from __future__ import annotations
import csv
import io
from typing import Optional
import httpx

BASE_URL = "https://observatorio.registraduria.gov.co"
_TIMEOUT = 15.0

# URLs de descarga CSV por tipo de elección
_CSV_URLS = {
    "presidente": "{base}/export/resultados_presidente_{year}.csv",
    "congreso": "{base}/export/resultados_congreso_{year}.csv",
    "gobernador": "{base}/export/resultados_gobernador_{year}.csv",
    "alcalde": "{base}/export/resultados_alcalde_{year}.csv",
}


def _build_csv_url(year: int, election_type: str = "alcalde") -> str:
    template = _CSV_URLS.get(election_type, _CSV_URLS["alcalde"])
    return template.format(base=BASE_URL, year=year)


def _parse_csv_response(content: str) -> list[dict]:
    """Parsea CSV de la Registraduría a lista de dicts."""
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]


def get_results(
    year: int,
    department: str = "ANTIOQUIA",
    municipality: Optional[str] = None,
    election_type: str = "alcalde",
) -> dict:
    """Obtiene resultados electorales por año y departamento.

    Args:
        year: año de la elección (ej: 2023, 2019)
        department: nombre del departamento en mayúsculas
        municipality: nombre del municipio (opcional)
        election_type: tipo de elección ('alcalde', 'gobernador', etc.)

    Returns:
        dict con 'year', 'department', 'rows' (lista de resultados)
    """
    url = _build_csv_url(year, election_type)
    resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()

    rows = _parse_csv_response(resp.text)

    # Filtrar por departamento
    filtered = [
        r for r in rows
        if r.get("DEPARTAMENTO", "").upper() == department.upper()
    ]

    # Filtrar por municipio si se especifica
    if municipality:
        filtered = [
            r for r in filtered
            if r.get("MUNICIPIO", "").upper() == municipality.upper()
        ]

    return {
        "year": year,
        "department": department,
        "municipality": municipality,
        "election_type": election_type,
        "rows": filtered,
        "total": len(filtered),
    }


def get_abstention_by_zone(year: int, municipality: str) -> dict:
    """Calcula abstención electoral por zona/municipio.

    Compara inscritos vs votantes para calcular tasa de abstención.

    Args:
        year: año de la elección
        municipality: nombre del municipio

    Returns:
        dict con tasas de participación y abstención
    """
    data = get_results(year=year, municipality=municipality)
    rows = data.get("rows", [])

    total_inscritos = 0
    total_votantes = 0

    for row in rows:
        try:
            inscritos = int(row.get("POTENCIAL_ELECTORAL", 0) or 0)
            votantes = int(row.get("TOTAL_VOTOS", 0) or 0)
            total_inscritos += inscritos
            total_votantes += votantes
        except (ValueError, TypeError):
            continue

    participacion = (total_votantes / total_inscritos * 100) if total_inscritos > 0 else 0.0
    abstension = 100.0 - participacion

    return {
        "year": year,
        "municipality": municipality,
        "inscritos": total_inscritos,
        "votantes": total_votantes,
        "participacion_pct": round(participacion, 2),
        "abstension_pct": round(abstension, 2),
    }


def compare_elections(year1: int, year2: int, municipality: str) -> dict:
    """Compara abstención entre dos elecciones en el mismo municipio.

    Args:
        year1: primer año de comparación
        year2: segundo año de comparación
        municipality: nombre del municipio

    Returns:
        dict con delta de abstención entre ambos años
    """
    data1 = get_abstention_by_zone(year1, municipality)
    data2 = get_abstention_by_zone(year2, municipality)

    delta_abstension = data2["abstension_pct"] - data1["abstension_pct"]
    delta_participacion = data2["participacion_pct"] - data1["participacion_pct"]

    return {
        "municipality": municipality,
        "year1": year1,
        "year2": year2,
        "abstension_year1": data1["abstension_pct"],
        "abstension_year2": data2["abstension_pct"],
        "delta_abstension": round(delta_abstension, 2),
        "delta_participacion": round(delta_participacion, 2),
        "trend": "mejora" if delta_abstension < 0 else "empeora",
    }
