import os
import time
from web3 import Web3
from dotenv import load_dotenv

# Configuración
BASE_DIR = "/Users/jquiceva/equipo-de-agentes"
VAULT_KEY_PATH = os.path.join(BASE_DIR, "scripts/.q_aion_vault.key")
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ABIs Mínimos para Router
ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"}
]

class Q_AION_HFT_Monitor:
    def __init__(self):
        self.rpc_url = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Direcciones Avalanche (Checksums)
        self.usdc = Web3.to_checksum_address("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E")
        self.wavax = Web3.to_checksum_address("0xB31f66AA3C1e785363F022A129d06C7C261561ac")
        
        # Routers
        self.routers = {
            "TraderJoe": Web3.to_checksum_address("0x60aE616a2155Ee3d9A68541Ba4544862310933d4"),
            "Pangolin": Web3.to_checksum_address("0xE54Ca86531e17Ef3616d22Ca28b0D2e55812D05C")
        }
        
    def get_price(self, router_addr, amount_in):
        router = self.w3.eth.contract(address=router_addr, abi=ROUTER_ABI)
        try:
            amounts = router.functions.getAmountsOut(amount_in, [self.usdc, self.wavax]).call()
            return amounts[1]
        except Exception as e:
            return 0

    def run_obs_loop(self, iterations=10):
        """
        Observa el mercado durante N iteraciones buscando spreads.
        """
        print(f"[📡] HFT_MONITOR: Iniciando observación táctica ({iterations} ciclos)...")
        amount_in = 1000000 # 1 USDC
        
        for i in range(iterations):
            prices = {}
            for name, addr in self.routers.items():
                prices[name] = self.get_price(addr, amount_in)
            
            # Comparar Spreads
            tj = prices.get("TraderJoe", 0)
            pg = prices.get("Pangolin", 0)
            
            if tj > 0 and pg > 0:
                diff = abs(tj - pg)
                spread_pct = (diff / min(tj, pg)) * 100
                print(f"Cycle {i+1}: TJ={tj/1e18:.6f} AVAX | PG={pg/1e18:.6f} AVAX | Spread={spread_pct:.4f}%")
                
                if spread_pct > 0.5: # Umbral de oportunidad (ajustable)
                    print(f"  [⚡] OPORTUNIDAD DETECTADA: Spread {spread_pct:.2f}%")
            
            time.sleep(5)

if __name__ == "__main__":
    monitor = Q_AION_HFT_Monitor()
    monitor.run_obs_loop(20) # Correr 20 ciclos (~1:40 min)
