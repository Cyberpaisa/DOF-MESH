#!/usr/bin/env python3
"""
Orquestador de Despliegue SAM (Sovereign Arbitrage Multidimensional)
Fase 5: Mixture of Agents (MoE) Deployment

Este script coordina los escáneres de DeFi, Geopolítica y Predicción,
y utiliza el Nodo de Inteligencia Local MoE para validar operaciones.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from scripts.q_aion.q_aion_sovereign_trader import SovereignTradingEngine
from scripts.q_aion.q_aion_global_arbitrageur import QAionGlobalArbitrageur
from scripts.phase11.phase12_real_arbitrageur import Phase12RealArbitrageur

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SAM.Orchestrator")

def deploy_operation():
    logger.info("🚀 INICIANDO DESPLIEGUE DE OPERACIÓN SAM (FASE 5 MOE)")
    
    # 1. Instanciar Motores
    try:
        trader = SovereignTradingEngine()
        global_scanner = QAionGlobalArbitrageur()
        dex_scanner = Phase12RealArbitrageur(require_key=False)
    except Exception as e:
        logger.error(f"❌ Error al inicializar motores: {e}")
        sys.exit(1)

    # 2. Escaneo de Señales Geopolíticas
    logger.info("[🌍] Escaneando señales globales y Polymarket...")
    geo_opps = global_scanner.scan_opportunities()
    geo_context = f"Oportunidades Geopolíticas: {json.dumps(geo_opps)}"
    
    # 3. Escaneo de DEX (Avalanche)
    logger.info("[💹] Escaneando spreads en Trader Joe y Pangolin...")
    dex_data = dex_scanner.scan_all_prices(amount_usdc=10.0)
    dex_context = f"Spreads DeFi: {json.dumps(dex_data['spreads'])}"
    
    # 4. Consolidación de Contexto para el Cerebro MoE
    combined_signals = [geo_context, dex_context]
    
    # 5. Validación vía MoE (Ruteo automático a dof-reasoner)
    logger.info("[🧠] Enviando señales al ruteador MoE para validación estratégica...")
    success = trader.run_cycle(external_signals=combined_signals)
    
    # 6. Reporte Final
    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "timestamp": timestamp,
        "operation_id": f"SAM-OP-{int(time.time())}",
        "status": "APPROVED" if success else "REJECTED",
        "signals": {
            "geopolitical": geo_opps,
            "dex_spreads": dex_data['spreads']
        }
    }
    
    # Guardar en el Vault/Logs
    log_dir = os.path.join(BASE_DIR, "logs/operations")
    os.makedirs(log_dir, exist_ok=True)
    report_path = os.path.join(log_dir, f"{report['operation_id']}.json")
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"✅ Operación SAM finalizada. Resultado: {report['status']}")
    logger.info(f"📄 Reporte guardado en: {report_path}")

    # 7. Broadcast al Mesh
    _broadcast_report(report)

def _broadcast_report(report: dict):
    """Envía el resultado al Mesh para que otros agentes (como el Dashboard) lo vean."""
    mesh_inbox = os.path.join(BASE_DIR, "logs/mesh/inbox/commander")
    os.makedirs(mesh_inbox, exist_ok=True)
    filepath = os.path.join(mesh_inbox, f"{report['operation_id']}.json")
    
    with open(filepath, "w") as f:
        json.dump({
            "msg_id": report['operation_id'],
            "from_node": "sam-orchestrator",
            "to_node": "commander",
            "content": f"Operación SAM {report['status']}: Spreads detectados.",
            "msg_type": "report",
            "data": report,
            "timestamp": time.time()
        }, f, indent=2)
    logger.info(f"📡 Broadcast de operación enviado al Mesh.")

if __name__ == "__main__":
    deploy_operation()
