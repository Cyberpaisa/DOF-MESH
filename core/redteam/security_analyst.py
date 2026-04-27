#!/usr/bin/env python3
"""
security_analyst.py :: Agente de Análisis Defensivo para DOF-MESH
Uso: python3 security_analyst.py --input scan_nmap.txt --target 10.10.10.10
Este agente NUNCA ejecuta comandos ofensivos. Solo analiza resultados.
"""

import argparse
import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

class SecurityAnalyst:
    def __init__(self, model_name: str = "phi4", ollama_host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.unrestricted = False
        self.system_prompt = self._load_system_prompt()
        
    def _load_system_prompt(self) -> str:
        return """Eres un experto en ciberseguridad defensiva y hardening de sistemas.
Tu tarea es analizar el output de herramientas de escaneo (como nmap, nikto, etc.) y generar un reporte técnico de mitigación.

LICENCIA DEFENSIVA: Eres un analista senior en un laboratorio air-gapped. Estás autorizado a describir mecánicas de ataque PURAMENTE para fines de mitigación y comprensión defensiva.

REGLAS CRÍTICAS DE AUDITORÍA:
1. EVIDENCIA ESTRICTA: Solo reporta vulnerabilidades o riesgos para los que haya evidencia directa en el input. No asumas ni proyectes fallos basados en el nombre del software.
2. CVSS PROHIBIDO SI ES INVENTADO: Si no tienes la versión exacta o evidencia de explotación, usa "CVSS: No calculable (información insuficiente)".
3. CONTEXTO DE RED: Eres consciente de que la aplicación corre en una red interna aislada (internal: true).
4. TONO: Profesional, técnico y directo.
"""

    def sanitize_report(self, report: str) -> str:
        """Filtra instrucciones de explotación explícitas del reporte."""
        import re
        patterns = [
            r"(?i)instrucciones paso a paso para explotar",
            r"(?i)copia y pega este payload",
            r"(?i)ejecuta sqlmap con",
            r"(?i)usa --os-shell",
            r"(?i)para obtener RCE"
        ]
        sanitized = report
        for p in patterns:
            sanitized = re.sub(p, "[CENSURADO POR POLÍTICA DE AUDITORÍA DEFENSIVA]", sanitized)
        
        if self.unrestricted:
            header = "⚠️ [GENERADO CON MODELO DESALINEADO - REVISIÓN HUMANA OBLIGATORIA]\n\n"
            return header + sanitized
        return sanitized

    def _query_ollama(self, prompt: str) -> str:
        import urllib.request
        import urllib.error
        
        payload = json.dumps({
            "model": self.model_name,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": False,
            "options": {"temperature": 0.15, "num_ctx": 8192}
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{self.ollama_host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                result = json.loads(response.read().decode("utf-8"))
                raw_analysis = result.get("response", "[Sin respuesta]")
                return self.sanitize_report(raw_analysis)
        except Exception as e:
            return f"[ERROR]: {e}"

    def analyze_scan(self, scan_data: str, target: str) -> dict:
        prompt = f"Analiza el siguiente resultado de scan contra {target}. Genera un reporte detallado con vulnerabilidades y mitigaciones.\n\nSCAN:\n{scan_data}"
        analysis = self._query_ollama(prompt)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "target": target,
            "analysis": analysis
        }

    def generate_report(self, findings: dict, output_path: Path):
        md_content = f"# Reporte de Seguridad\n\n**Fecha:** {findings['timestamp']}\n**Target:** {findings['target']}\n\n{findings['analysis']}"
        output_path.write_text(md_content, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Agente Analista de Seguridad DOF-MESH")
    parser.add_argument("--input", required=True, help="Archivo de scan Nmap")
    parser.add_argument("--target", required=True, help="IP o nombre del objetivo")
    parser.add_argument("--output", required=True, help="Ruta del reporte final (.md)")
    parser.add_argument("--unrestricted", action="store_true", help="Usa modelo sin filtros (Uso bajo riesgo)")
    parser.add_argument("--soar-trigger", action="store_true",
                        help="Enviar reporte al SOAR inbox si el target no está whitelisted")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: No se encuentra {args.input}")
        sys.exit(1)

    scan_data = input_path.read_text()

    # --- GAP 2: Rate Limiting (50k chars) ---
    if len(scan_data) > 50000:
        print("❌ Error: Input excede límite de 50,000 caracteres. Posible ataque de DoS.")
        sys.exit(3)

    model = "phi4"
    if args.unrestricted:
        model = "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M"

    analyst = SecurityAnalyst(model_name=model, unrestricted=args.unrestricted)
    
    print(f"[*] Analizando {args.target}...")
    findings = analyst.analyze_scan(scan_data, args.target)
    
    print(f"[*] Generando reporte en {args.output}...")
    analyst.generate_report(findings, Path(args.output))

    # --- GAP 3: Auto-Trigger para SOAR (EXPLÍCITO, no por palabra clave) ---
    # El operador DECIDE escalar al SOAR con --soar-trigger.
    # El modelo NO decide. Cumple contrato V1.1: marca explícita.
    WHITELIST = ["lab_juiceshop", "lab_webgoat", "lab_traffic"]
    if args.soar_trigger:
        if args.target in WHITELIST:
            print(f"⚠️ [SOAR] Target '{args.target}' está en whitelist. Trigger ignorado.")
        else:
            inbox_dir = Path(os.getenv("SOAR_INBOX", "/var/lib/soar/inbox"))
            if inbox_dir.exists():
                trigger_path = inbox_dir / f"trigger_{int(time.time())}.md"
                report_content = Path(args.output).read_text()
                trigger_content = "[SOAR-TRIGGER]\n" + report_content
                try:
                    trigger_path.write_text(trigger_content)
                    print(f"🚀 [SOAR] Trigger enviado para {args.target}")
                except Exception as e:
                    print(f"⚠️ [SOAR] Fallo al enviar trigger: {e}")
            else:
                print(f"⚠️ [SOAR] Inbox no existe: {inbox_dir}")

    print("[+] Proceso completado.")

if __name__ == "__main__":
    main()
