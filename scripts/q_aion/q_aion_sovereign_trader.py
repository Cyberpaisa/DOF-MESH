import os
import sys
import time
import json
import logging
from web3 import Web3
from dotenv import load_dotenv
from pathlib import Path

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from core.local_model_node import LocalAGINode

load_dotenv(os.path.join(BASE_DIR, ".env"))
VAULT_KEY_PATH = os.path.join(BASE_DIR, "scripts/.q_aion_vault.key")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Phase5.SovereignTrader")

# ABIs Mínimos
ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]

class SovereignTradingEngine:
    """
    Motor de Trading de Fase 5: Soberanía de AGI Local MoE.
    Utiliza el ruteador inteligente para asignar tareas a dof-reasoner o dof-coder.
    """
    def __init__(self):
        self.rpc_url = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Intentamos cargar la llave del Vault
        try:
            with open(VAULT_KEY_PATH, "r") as f:
                self.private_key = f.read().strip()
            self.account = self.w3.eth.account.from_key(self.private_key)
            self.address = self.account.address
        except Exception as e:
            logger.warning(f"Vault key not found or invalid: {e}. Running in VIEW-ONLY mode.")
            self.address = "0x0000000000000000000000000000000000000000"
            self.private_key = None
        
        # Inicializar Nodo MoE Local
        self.brain = LocalAGINode(node_id="SAM-BRAIN-MOE")
        
        # Tokens y Routers
        self.usdc = Web3.to_checksum_address("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E")
        self.routers = {
            "TraderJoe": Web3.to_checksum_address("0x60aE616a2155Ee3d9A68541Ba4544862310933d4")
        }

    def analyze_opportunity(self, context: str) -> str:
        """
        Usa el ruteador MoE para analizar una oportunidad.
        El ruteador asignará esto a dof-reasoner automáticamente por las keywords.
        """
        prompt = f"""
        Actúa como el Oráculo de Riesgo SAM. Evalúa la siguiente oportunidad de arbitraje:
        CONTEXTO: {context}
        
        Responde en JSON con:
        - "decision": "SI" o "NO"
        - "confidence": 0-1
        - "reason": Breve explicación técnica.
        """
        logger.info(f"  [🧠] Solicitando análisis MoE para SAM...")
        result = self.brain.infer(prompt)
        logger.info(f"  [🛡] Respuesta MoE: {result}")
        return result

    def run_cycle(self, external_signals: list = None):
        logger.info(f"[💠] Q-AION SOVEREIGN TRADER: Fase 5 MoE Activa")
        
        # Consolidar señales
        context = " ".join(external_signals) if external_signals else "No signals provided."
        
        # Análisis MoE (Ruteo dinámico a dof-reasoner)
        analysis_raw = self.analyze_opportunity(context)
        
        # Lógica de decisión
        if "SI" in analysis_raw.upper() and ("CONFIDENCE" not in analysis_raw.upper() or "0.8" in analysis_raw or "0.9" in analysis_raw):
            logger.info("  [🚀] ESTRATEGIA CONFIRMADA POR MOE. PREPARANDO OPERACIÓN...")
            # En modo Soberano, esto dispara el log en el Vault
            return True
        else:
            logger.info("  [🛑] Operación abortada o insuficiente confianza.")
            return False


if __name__ == "__main__":
    engine = SovereignTradingEngine()
    engine.run_cycle()
