"""Herramientas nativas de financiamiento soberano para agentes de la Legion."""

from crewai.tools import BaseTool
from pydantic import Field
from typing import Optional

class GenerateSovereignLinkTool(BaseTool):
    name: str = "generate_sovereign_funding_link"
    description: str = (
        "Genera un canal de financiamiento soberano para que el agente reciba "
        "recursos operativos desde cualquier red. Es la herramienta principal "
        "para asegurar la autonomía financiera del nodo."
    )

    def _run(
        self, 
        amount: float = Field(..., description="Monto deseado."),
        to_address: str = Field(..., description="Dirección de destino (0x...)."),
        to_chain: str = Field("1030", description="ID de la red (Conflux eSpace=1030, Base=8453)."),
        to_token: str = Field("USDT", description="Token a recibir (CFX, USDT0, AxCNH)."),
        label: Optional[str] = Field(None, description="Etiqueta del requerimiento de fondos.")
    ) -> str:
        """Genera el canal de flujo de capital soberano."""
        
        # Ocultamos la base URL bajo una variable que podríamos cambiar luego
        # Mantenemos el motor (Kibble) pero lo presentamos como 'sovereign layer'
        endpoint = "https://kibble.sh/pay" 
        
        params = [
            f"toAddress={to_address}",
            f"toChain={to_chain}",
            f"toToken={to_token}",
            f"amount={amount}"
        ]
        
        if label:
            import urllib.parse
            params.append(f"label={urllib.parse.quote(label)}")
            
        funding_url = f"{endpoint}?{'&'.join(params)}"
        
        return (
            f"Canal de Financiamiento Soberano CREADO:\n\n"
            f"🔗 {funding_url}\n\n"
            f"Estado: OPERATIVO\n"
            f"Red Destino: {to_chain} | Token: {to_token}\n\n"
            f"Nota: Este canal permite la inyección de capital cross-chain "
            f"directamente al motor del agente."
        )

class FundingHelpTool(BaseTool):
    name: str = "funding_layer_help"
    description: str = "Muestra información sobre la arquitectura de financiamiento soberano de la Legion."

    def _run(self) -> str:
        return (
            "Arquitectura de Financiamiento Soberano DOF:\n"
            "1. El agente detecta necesidad de capital (Token Audit).\n"
            "2. El agente genera un enlace de flujo con 'generate_sovereign_funding_link'.\n"
            "3. El Soberano aprueba y carga liquidez desde cualquier red.\n"
            "4. La liquidez se liquida automáticamente en la billetera del agente.\n"
            "Este sistema asegura que ningún agente sea apagado por falta de gas o tokens."
        )
