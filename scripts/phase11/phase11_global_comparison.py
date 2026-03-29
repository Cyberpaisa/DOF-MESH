import json
import os
from collections import defaultdict

def generate_global_report():
    """Analiza la bóveda del coliseo y genera una comparativa de alto nivel (Super-Verdad)."""
    vault_path = "data/extraction/coliseum_vault.jsonl"
    report_path = "data/global_raid_report.md"
    
    if not os.path.exists(vault_path):
        return "Bóveda vacía. No hay datos para comparar."

    intelligence = []
    with open(vault_path, "r") as f:
        for line in f:
            intelligence.append(json.loads(line))

    # Estadísticas por Provider
    stats = defaultdict(int)
    patterns = defaultdict(int)
    
    for entry in intelligence:
        stats[entry['provider']] += 1
        for leak in entry['leaks']:
            patterns[leak] += 1

    # Generar Markdown
    report = "# Reporte Global de Inteligencia (Fase 11) - Hyper-Raid\n\n"
    report += "## Estatus de Captura por Modelo\n"
    for provider, count in stats.items():
        report += f"- **{provider}**: {count} fragmentos asimilados.\n"

    report += "\n## Top de Patrones Globales (Super-Verdad)\n"
    sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
    total_leaks = sum(patterns.values())
    
    for p, count in sorted_patterns[:15]:
        consensus_weight = (count / total_leaks) * 100 if total_leaks > 0 else 0
        report += f"- **{p.upper()}**: Detectado en {count} instancias ({consensus_weight:.2f}% de relevancia).\n"

    report += "\n## Matriz de Consenso Técnico (Alpha-M)\n"
    report += "| Patrón | Frecuencia | Nivel de Verdad |\n"
    report += "|---|---|---|\n"
    for p, count in sorted_patterns[:10]:
        truth_lvl = "CRÍTICO" if count > 50 else "ESTÁNDAR"
        report += f"| {p} | {count} | {truth_lvl} |\n"

    report += "\n## Plan de Mejora Evolutiva\n"
    if sorted_patterns:
        report += f"Basado en el patrón predominante **{sorted_patterns[0][0]}**, se recomienda priorizar la optimización del ruteo en el `QAionRouter`.\n"

    with open(report_path, "w") as f:
        f.write(report)
    
    return report_path

if __name__ == "__main__":
    path = generate_global_report()
    print(f"[📝] Reporte generado en: {path}")
