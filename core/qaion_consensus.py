import logging
import hashlib
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger("core.qaion_consensus")

class ConsensusEngine:
    """
    PBFT-light Consensus Engine for Q-AION.
    Garantiza que las respuestas de los expertos sean validadas por la red.
    """
    def __init__(self, threshold: float = 0.66):
        self.threshold = threshold  # 2/3 para consenso bizantino
        self.pending_validations: Dict[str, List[Dict[str, Any]]] = {}

    def propose_result(self, task_id: str, expert_id: str, payload: str, signature: str):
        """Un experto propone un resultado para una tarea."""
        if task_id not in self.pending_validations:
            self.pending_validations[task_id] = []
        
        vote = {
            "expert_id": expert_id,
            "payload_hash": hashlib.sha256(payload.encode()).hexdigest(),
            "signature": signature,
            "timestamp": time.time()
        }
        self.pending_validations[task_id].append(vote)
        logger.info(f"[CONSENSUS] Voto recibido de {expert_id} para tarea {task_id}.")

    def reach_consensus(self, task_id: str) -> Optional[str]:
        """Verifica si se ha alcanzado el quórum para una tarea."""
        votes = self.pending_validations.get(task_id, [])
        if not votes:
            return None

        # Contar hashes idénticos
        hash_counts = {}
        for v in votes:
            h = v["payload_hash"]
            hash_counts[h] = hash_counts.get(h, 0) + 1

        total_votes = len(votes)
        for h, count in hash_counts.items():
            if count / total_votes >= self.threshold:
                logger.info(f"[CONSENSUS] Quórum alcanzado para {task_id} con hash {h[:10]}...")
                return h
        
        logger.warning(f"[CONSENSUS] No hay consenso aún para {task_id} ({total_votes} votos).")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ce = ConsensusEngine()
    task = "q-aion-test-01"
    
    # Simular votos concordantes
    ce.propose_result(task, "exp-01", "resultado_valido", "sig1")
    ce.propose_result(task, "exp-02", "resultado_valido", "sig2")
    ce.propose_result(task, "exp-03", "resultado_diferente", "sig3")
    
    result = ce.reach_consensus(task)
    if result:
        print(f"[✓] Consenso logrado: {result}")
    else:
        print("[!] Consenso fallido.")
