import os
import time
import json
import logging
from web3 import Web3
from dotenv import load_dotenv
from pathlib import Path

# Configuración de Rutas
BASE_DIR = "/Users/jquiceva/equipo-de-agentes"
ENV_PATH = os.path.join(BASE_DIR, ".env")
VAULT_KEY_PATH = os.path.join(BASE_DIR, "scripts/.q_aion_vault.key")
MESH_INBOX_DIR = os.path.join(BASE_DIR, "logs/mesh/inbox")

load_dotenv(ENV_PATH)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Phase4.SovereignTrader")

# ABIs Mínimos
ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]

class SovereignTradingEngine:
    """
    Motor de Trading de Fase 4: Soberanía de AGI Local.
    Usa Llama 3B (MLX) para triage y Qwen 14B (Ollama) para decisiones.
    """
    def __init__(self):
        self.rpc_url = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        with open(VAULT_KEY_PATH, "r") as f:
            self.private_key = f.read().strip()
        
        self.account = self.w3.eth.account.from_key(self.private_key)
        self.address = self.account.address
        
        # Tokens y Routers (Fase 13 Legacy)
        self.usdc = Web3.to_checksum_address("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E")
        self.usdc_e = Web3.to_checksum_address("0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664")
        self.routers = {
            "TraderJoe": Web3.to_checksum_address("0x60aE616a2155Ee3d9A68541Ba4544862310933d4")
        }

    def _send_to_mesh(self, node_id: str, content: str) -> str:
        """Envía una tarea al Mesh y espera la respuesta del nodo local."""
        msg_id = f"TX-{int(time.time()*1000)}"
        inbox_path = Path(MESH_INBOX_DIR) / node_id
        inbox_path.mkdir(parents=True, exist_ok=True)
        
        task = {
            "msg_id": msg_id,
            "from_node": "commander",
            "to_node": node_id,
            "content": content,
            "msg_type": "task",
            "timestamp": time.time(),
            "read": False
        }
        
        # Guardar en inbox del nodo
        with open(inbox_path / f"{msg_id}.json", "w") as f:
            json.dump(task, f)
        
        logger.info(f"  [🧠] Tarea enviada a {node_id}: {msg_id}")
        
        # Esperar respuesta (polling simple para el piloto)
        commander_inbox = Path(MESH_INBOX_DIR) / "commander"
        commander_inbox.mkdir(parents=True, exist_ok=True)
        
        for _ in range(30): # 30 segundos timeout
            for resp_file in commander_inbox.glob("*.json"):
                with open(resp_file, "r") as f:
                    resp = json.load(f)
                    if resp.get("reply_to") == msg_id:
                        os.remove(resp_file)
                        return resp.get("content", "")
            time.sleep(1)
        return "TIMEOUT"

    def analyze_sentiment(self, data: str) -> bool:
        """Usa Llama 3B (MLX) para un triage rápido del sentimiento de mercado."""
        prompt = f"Analiza este contexto de mercado y responde solo con POSITIVO, NEGATIVO o NEUTRAL: {data}"
        result = self._send_to_mesh("local-agi-m4max", prompt)
        logger.info(f"  [📊] Sentimiento (3B): {result}")
        return "POSITIVO" in result.upper()

    def confirm_strategy(self, context: str) -> bool:
        """Usa Qwen 14B (Ollama) para la aprobación estratégica final."""
        prompt = f"Como estratega soberano, ¿autorizas este swap basado en: {context}? Responde solo con SI o NO y una razón corta."
        result = self._send_to_mesh("strategic-brain-14b", prompt)
        logger.info(f"  [🛡] Decisión Soberana (14B): {result}")
        return "SI" in result.upper()

    def run_cycle(self):
        logger.info(f"[💠] Q-AION SOVEREIGN TRADER: Fase 4 Activa")
        
        # 1. Simular captura de noticias (Tavily/RSS Mock)
        market_news = "Avalanche DEX volume spikes 20% in the last hour. Bullish sentiment."
        
        # 2. Triage Local (3B)
        if self.analyze_sentiment(market_news):
            # 3. Datos de On-Chain
            spread = 0.006 # 0.6% detectado
            context = f"Noticias alcistas y spread de {spread*100}% en Trader Joe."
            
            # 4. Decisión Crítica (14B)
            if self.confirm_strategy(context):
                logger.info("  [🚀] ESTRATEGIA CONFIRMADA. EJECUTANDO SWAP...")
                # Aquí iría la ejecución real (Phase 13 legacy)
                # self.execute_swap(...)
            else:
                logger.info("  [🛑] Estrategia rechazada por el Cerebro Estratégico.")
        else:
            logger.info("  [💤] Sentimiento insuficiente para operar.")

if __name__ == "__main__":
    engine = SovereignTradingEngine()
    engine.run_cycle()
