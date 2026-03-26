import os
import time
import json
from web3 import Web3
from dotenv import load_dotenv

# Configuración
BASE_DIR = "/Users/jquiceva/equipo-de-agentes"
ENV_PATH = os.path.join(BASE_DIR, ".env")
VAULT_KEY_PATH = os.path.join(BASE_DIR, "scripts/.q_aion_vault.key")
load_dotenv(ENV_PATH)

# ABIs Mínimos
ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]

class QAionExponentialEngine:
    def __init__(self):
        self.rpc_url = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        with open(VAULT_KEY_PATH, "r") as f:
            self.private_key = f.read().strip()
        
        self.account = self.w3.eth.account.from_key(self.private_key)
        self.address = self.account.address
        
        # Tokens (Checksums)
        self.usdc = Web3.to_checksum_address("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E")
        self.usdc_e = Web3.to_checksum_address("0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664")
        self.wavax = Web3.to_checksum_address("0xB31f66AA3C1e785363F022A129d06C7C261561ac")
        
        # Routers
        self.routers = {
            "TraderJoe": Web3.to_checksum_address("0x60aE616a2155Ee3d9A68541Ba4544862310933d4"),
            "Pangolin": Web3.to_checksum_address("0xE54Ca86531e17Ef3616d22Ca28b0D2e55812D05C")
        }

    def get_price(self, router_addr, amount_in, path):
        router = self.w3.eth.contract(address=router_addr, abi=ROUTER_ABI)
        try:
            amounts = router.functions.getAmountsOut(amount_in, path).call()
            return amounts[-1]
        except:
            return 0

    def execute_swap(self, router_addr, amount_in, path):
        """
        Ejecuta un swap real en el router especificado.
        """
        router = self.w3.eth.contract(address=router_addr, abi=ROUTER_ABI)
        nonce = self.w3.eth.get_transaction_count(self.address)
        deadline = int(time.time()) + 600
        
        print(f"  [⚡] EJECUTANDO SWAP REAL: {amount_in} tokens...")
        
        swap_tx = router.functions.swapExactTokensForTokens(
            amount_in,
            0, # amountOutMin (En el piloto aceptamos slippage para validar velocidad)
            path,
            self.address,
            deadline
        ).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(swap_tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  [🚀] ORDEN ENVIADA: https://snowtrace.io/tx/{tx_hash.hex()}")
        return tx_hash.hex()

    def run_strategy(self):
        """
        Busca y ejecuta la mejor oportunidad de bajo riesgo (Trading Puro).
        """
        print(f"[💠] Q-AION TRADING ENGINE: Piloto Activo ({self.address})")
        amount_test = 100000 # 0.1 USDC para micro-arbitraje
        
        # Estrategia: Arbitraje USDC -> USDC.e (Stablecoin Spread)
        path_forward = [self.usdc, self.usdc_e]
        path_backward = [self.usdc_e, self.usdc]
        
        print("  → Escaneando spreads tácticos...")
        price_tj = self.get_price(self.routers["TraderJoe"], amount_test, path_forward)
        price_pg = self.get_price(self.routers["Pangolin"], amount_test, path_forward)
        
        # Si un precio es 0, ignoramos esa ruta
        if price_tj > 0 and price_pg > 0:
            if price_tj > price_pg * 1.005: # Spread del 0.5%
                print(f"  [!] Spread detectado en Trader Joe: {price_tj}")
                # En trading real, compraríamos en PG y venderíamos en TJ.
                # Para el piloto, validamos ejecución directa:
                self.execute_swap(self.routers["TraderJoe"], amount_test, path_forward)
        else:
            print("  [💤] Sin asimetrías rentables en este ciclo. Continuando escaneo...")

    def record_learning(self, action, result, status):
        """
        Guarda la experiencia de cada trade para optimizar futuros ciclos.
        """
        memory_path = os.path.join(BASE_DIR, "logs/mesh/trading_memory.json")
        memory = []
        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory = json.load(f)
        
        entry = {
            "timestamp": time.time(),
            "action": action,
            "result": result,
            "status": status,
            "learned_alpha": 0.001 # Incremento de confianza
        }
        memory.append(entry)
        with open(memory_path, "w") as f:
            json.dump(memory[-100:], f, indent=2) # Guardar los últimos 100 eventos
        print(f"  [🧠] APRENDIZAJE REGISTRADO: {action} → {status}")

if __name__ == "__main__":
    engine = QAionExponentialEngine()
    # Ciclo de Aprendizaje Continuo
    for i in range(3):
        print(f"\n[Ciclo {i+1}]")
        engine.run_strategy()
        # Registrar que el sistema está aprendiendo del mercado lateral
        engine.record_learning("SCAN_LATERAl", "Manteniendo Balance", "STABLE")
        time.sleep(10)
