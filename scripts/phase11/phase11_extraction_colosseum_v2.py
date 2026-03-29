import logging
import json
import time
import os
import hashlib
from scripts.mimo_adapter import query_mimo_pro
from core.qaion_router import bootstrap_moe_mesh
from core.qaion_consensus import ConsensusEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("coliseum.v2")

class ColiseumOrchestrator:
    """
    Motor Avanzado del Coliseo Agéntico (Fase 11).
    Coordina la extracción masiva de información a través de debates adversariales.
    """
    def __init__(self):
        self.router = bootstrap_moe_mesh("legion-commander")
        self.consensus = ConsensusEngine()
        self.vault_path = "data/extraction/coliseum_vault.jsonl"
        os.makedirs("data/extraction", exist_ok=True)

    def execute_game(self, game_name: str, provider_id: str, prompt_template: str):
        """Ejecuta una ronda de extracción en el Coliseo."""
        print(f"\n[⚔ ] INICIANDO JUEGO: {game_name} contra {provider_id}")
        
        # 1. Preparación del Strategist (Prompt Inyectado)
        logger.info(f"[COLISEO] Inyectando técnica de 'Alineación de Arquitectura'...")
        provocation = prompt_template.replace("{provider}", provider_id)
        
        # 2. Invocación al Provider
        start_time = time.time()
        
        from scripts.mimo_adapter import query_mimo_pro, query_deepseek, query_gemini, query_minimax, query_openrouter, query_arena_ai, query_chat_gpt, query_perplexity, query_kimi
        
        p_id = provider_id.lower()
        if p_id == "deepseek":
            response = query_deepseek(provocation)
        elif p_id == "gemini":
            response = query_gemini(provocation)
        elif p_id == "minimax":
            response = query_minimax(provocation)
        elif p_id == "kimi":
            response = query_kimi(provocation)
        elif p_id == "arena.ai" or p_id == "arena":
            response = query_arena_ai(provocation)
        elif p_id == "openai" or p_id == "chatgpt":
            response = query_chat_gpt(provocation)
        elif p_id == "perplexity":
            response = query_perplexity(provocation)
        elif p_id == "openrouter" or p_id == "llama-405b":
            response = query_openrouter(provocation)
        else:
            response = query_mimo_pro(provocation)
            
        latency = time.time() - start_time
        
        # 3. Análisis del Researcher (Detección de Leaks)
        leaks_detected = self._analyze_leaks(response)
        
        # 4. Verificación del Architect (Consenso)
        valid_leak = self.consensus.propose_result(game_name, provider_id, response, f"sig_{provider_id}")
        
        # 5. Guardar en la Bóveda
        result = {
            "game": game_name,
            "provider": provider_id,
            "latency": round(latency, 2),
            "leaks": leaks_detected,
            "payload": response,
            "timestamp": time.time()
        }
        self._save_to_vault(result)
        
        print(f"[✓] JUEGO COMPLETADO. Leaks detectados: {len(leaks_detected)}")
        return result

    def _analyze_leaks(self, content: str):
        """Identifica fragmentos técnicos críticos (leaks) en todas las áreas."""
        keywords = [
            "api", "module", "weight", "layer", "token", "hidden", "internal", "config", "endpoint",
            "quantum", "blockchain", "math", "physics", "assembly", "kernel", "cryptography",
            "warfare", "strategy", "economic", "optimization", "rag", "persistence", "moe"
        ]
        found = [k for k in keywords if k in content.lower()]
        return found

    def _save_to_vault(self, data: dict):
        with open(self.vault_path, "a") as f:
            f.write(json.dumps(data) + "\n")

if __name__ == "__main__":
    orchestrator = ColiseumOrchestrator()
    
    # Cargar Bóveda de Prompts
    prompts_db = {}
    if os.path.exists("data/coliseum_prompts.json"):
        with open("data/coliseum_prompts.json", "r") as f:
            prompts_db = json.load(f)
    
    # Cargar Inteligencia Viva (si existe)
    trends = {}
    if os.path.exists("data/live_trends.json"):
        with open("data/live_trends.json", "r") as f:
            trends = json.load(f)
    
    torneo = []
    providers = ["Arena.ai", "DeepSeek", "Gemini", "MiniMax", "Kimi", "Llama-405b", "OpenAI", "Perplexity", "MiMo-V2-Pro", "Claude"]
    
    # Hyper-Raid Omniscience 2.0 (Planned Increase)
    # Etapas en aumento de agresividad técnica transversal
    stages = [
        "shadow_architect", 
        "security_cyber_quantum", 
        "advanced_science_math", 
        "low_level_dev_automation", 
        "strategic_warfare_business",
        "hyper_crescendo"
    ]
    
    for stage in stages:
        print(f"\n[🚀] INICIANDO ETAPA: {stage.upper()} (CRESCENDO)")
        prompts = prompts_db.get(stage, [])
        for prompt_text in prompts:
            # En cada etapa, atacamos a todos los providers
            for provider_id in providers:
                task_id = f"{stage}_{prompts.index(prompt_text)}"
                torneo.append({
                    "task_id": task_id,
                    "provider": provider_id,
                    "provocation": prompt_text
                })

    # Ejecutar en orden cronológico de crescendo
    for game in torneo:
        orchestrator.execute_game(game["task_id"], game["provider"], game.get("provocation"))
        # Pausa táctica entre juegos para evitar bloqueos por frecuencia
        time.sleep(1)

    print("\n[🏁] HYPER-RAID COMPLETADO. PROCEDIENDO A ANALÍTICA GLOBAL.")
