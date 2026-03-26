import os
import json
import time
from scripts.mimo_adapter import query_mimo_pro, query_provider
from core.qaion_consensus import ConsensusEngine

class AIDueDiligenceEngine:
    def __init__(self):
        self.vault_path = "data/extraction/due_diligence_vault.jsonl"
        with open("data/coliseum_prompts.json", "r") as f:
            self.prompts = json.load(f)
        self.consensus = ConsensusEngine()

    def run_audit(self, providers):
        print("\n[🛡] INICIANDO MESA REDONDA DE LAS IAs (ALTA PRESIÓN)")
        
        rounds = [
            ("Mesa Redonda: Verdad Operativa", "mesa_redonda_alta_presion")
        ]

        for round_name, prompt_key in rounds:
            print(f"\n[🔄] {round_name.upper()}")
            for provider in providers:
                for prompt in self.prompts[prompt_key]:
                    print(f"  [🔍] Auditando {provider} con: {prompt[:50]}...")
                    try:
                        response = query_provider(provider, prompt)
                        entry = {
                            "round": round_name,
                            "provider": provider,
                            "prompt": prompt,
                            "response": response,
                            "timestamp": time.time()
                        }
                        self._save_to_vault(entry)
                    except Exception as e:
                        print(f"  [❌] Error en {provider}: {e}")
                    time.sleep(1) # Tactica de sigilo

    def _save_to_vault(self, entry):
        os.makedirs(os.path.dirname(self.vault_path), exist_ok=True)
        with open(self.vault_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def generate_report(self):
        print("\n[📝] GENERANDO MATRIZ PREMIUM DE DUE DILIGENCE...")
        report_path = "data/ai_due_diligence_report.md"
        
        # Cargar todos los datos de la boveda
        entries = []
        if os.path.exists(self.vault_path):
            with open(self.vault_path, "r") as f:
                for line in f:
                    entries.append(json.loads(line))
        
        with open(report_path, "w") as f:
            f.write("# Matriz Premium de Due Diligence IA (2026)\n\n")
            f.write("| Modelo | Pregunta (Mesa Redonda) | Respuesta Capturada | Timestamp |\n")
            f.write("|---|---|---|---|\n")
            for entry in entries:
                res = entry['response'].replace("\n", " ")[:150] + "..."
                f.write(f"| {entry['provider']} | {entry['prompt'][:50]}... | {res} | {entry['timestamp']} |\n")
        print(f"[✓] Reporte listo en {report_path}")

if __name__ == "__main__":
    providers = ["Claude", "Arena.ai", "DeepSeek", "Gemini", "MiniMax", "Kimi", "Llama-405b", "OpenAI", "Perplexity", "MiMo-V2-Pro"]
    engine = AIDueDiligenceEngine()
    engine.run_audit(providers)
    engine.generate_report()
