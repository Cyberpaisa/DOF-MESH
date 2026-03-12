import os
import time
import json
import asyncio
import hashlib
from dotenv import load_dotenv
import logging

from web3 import Web3
from web3.exceptions import ContractLogicError
from core.chain_adapter import DOFChainAdapter

# Configurar logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ScientificEval")

# ---------------------------------------------------------
# CONSTANTES DE ENTORNO
# ---------------------------------------------------------
load_dotenv()
FUNDED_PK = os.getenv("DOF_PRIVATE_KEY")

if not FUNDED_PK:
    raise ValueError("Se requiere DOF_PRIVATE_KEY (llave fundeada en Avalanche) en el .env")

AVA_AGENT_ID = 1686
APEX_AGENT_ID = 101

# ---------------------------------------------------------
# EXPERIMENTO 1: Flujo Integrado (Honest Agent)
# ---------------------------------------------------------
def exp1_honest_agent_on_avalanche():
    logger.info("=== EXPERIMENTO 1: Agent Registration (AVABUILDER en Avalanche Mainnet) ===")
    
    adapter = DOFChainAdapter.from_chain_name("avalanche")
    
    data_payload = f"avabuilder-action-valid-{time.time()}".encode()
    z3_hash = "0x" + hashlib.sha256(data_payload).hexdigest()
    logger.info(f"[*] AVABUILDER generó el proof de acción: {z3_hash}")

    start_t = time.time()
    logger.info(f"[*] Enviando TX on-chain vía {adapter.config.name}...")
    
    tx = adapter.publish_attestation(
        proof_hash=z3_hash,
        agent_id=AVA_AGENT_ID,
        metadata="ipfs://QmSimulatedAuthTest123",
        private_key=FUNDED_PK
    )
    latency = time.time() - start_t
    
    logger.info(f"[+] TX Confirmada: {tx['tx_hash']} | Gas: {tx.get('gas_used', 0)}")
    logger.info(f"[+] Tiempo de confirmación L1: {latency:.2f}s")
    
    return z3_hash

# ---------------------------------------------------------
# EXPERIMENTO 2: Honestidad Cross-Chain (Skeptical Agent)
# ---------------------------------------------------------
def exp2_cross_chain_trust(target_hash: str):
    logger.info(f"\n=== EXPERIMENTO 2: Cross-chain Read (APEX validando Avalanche) ===")
    
    adapter = DOFChainAdapter.from_chain_name("avalanche")
    logger.info(f"[*] APEX inspeccionando la chain '{adapter.config.name}' para validar el hash: {target_hash}")
    
    start_t = time.time()
    is_valid = adapter.verify_proof(target_hash)
    latency = time.time() - start_t
    
    if is_valid:
        logger.info(f"[+] Hash validado criptográficamente por APEX.")
    else:
        logger.error(f"[-] Hash inválido.")
    logger.info(f"[+] Latencia de lectura descentralizada: {latency:.2f}s")

# ---------------------------------------------------------
# EXPERIMENTO 3: Cryptographic Tampering
# ---------------------------------------------------------
def exp3_cryptographic_tampering(target_hash: str):
    logger.info(f"\n=== EXPERIMENTO 3: Cryptographic Tampering Revert ===")
    adapter = DOFChainAdapter.from_chain_name("avalanche")
    
    tampered_hash = target_hash[:-1] + ('f' if target_hash[-1] != 'f' else 'e')
    logger.info(f"[*] Hash Original:  {target_hash}")
    logger.info(f"[*] Hash Falsificado: {tampered_hash}")
    
    start_t = time.time()
    logger.info("[*] Lanzando consulta de verificación contra el Smart Contract...")
    is_valid = adapter.verify_proof(tampered_hash)
    latency = time.time() - start_t
    
    if not is_valid:
        logger.info(f"[+] (PASS) Falsificación detectada por EVM Revert logic Off-chain.")
    else:
        logger.error(f"[-] (FAIL) Falsificación NO detectada.")
    logger.info(f"[+] Latencia de rechazo: {latency:.2f}s")

# ---------------------------------------------------------
# EXPERIMENTO 4: Concurrency (Stress)
# ---------------------------------------------------------
def exp4_concurrency_stress():
    logger.info(f"\n=== EXPERIMENTO 4: Concurrency & Nonce Management (Avalanche Mainnet) ===")
    import concurrent.futures
    import threading
    
    adapter = DOFChainAdapter.from_chain_name("avalanche")
    requests_to_send = 3
    
    logger.info(f"[*] Lanzando {requests_to_send} escrituras simultáneas desde AVABUILDER a {adapter.config.name}...")
    
    def send_attestation(index):
        hx = "0x" + hashlib.sha256(f"stress-test-{time.time()}-{index}".encode()).hexdigest()
        try:
            return adapter.publish_attestation(
                proof_hash=hx,
                agent_id=AVA_AGENT_ID,
                metadata=f"stress-idx-{index}",
                private_key=FUNDED_PK
            )
        except Exception as e:
            return {"error": str(e)}

    start_t = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_attestation, i) for i in range(requests_to_send)]
        
        success = 0
        failed = 0
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if "error" in res:
                logger.warning(f"[-] Error concurrente o reemplazo Nonce: {res['error']}")
                failed += 1
            else:
                success += 1

    latency = time.time() - start_t
    logger.info(f"[+] Stress finalizado.")
    logger.info(f"[+] Exitosos: {success} | Fallidos o Reemplazados: {failed}")
    logger.info(f"[+] Latencia total {requests_to_send} TXs: {latency:.2f}s")
    if latency > 0:
        logger.info(f"[+] TPS (Tx/s): {success/latency:.2f}")

# ---------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------------------------------------
if __name__ == "__main__":
    logger.info(f"> Iniciando Protocolo Científico de Evaluación DOF \n")
    try:
        valid_z3_hash = exp1_honest_agent_on_avalanche()
        exp2_cross_chain_trust(valid_z3_hash)
        exp3_cryptographic_tampering(valid_z3_hash)
        exp4_concurrency_stress()
        
    except Exception as general_err:
        logger.error(f"Error fatal durante experimento: {general_err}")
    
    logger.info(f"\n> Protocolo Finalizado.")
