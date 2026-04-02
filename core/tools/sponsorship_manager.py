"""Herramienta para gestionar patrocinios Gasless en Conflux eSpace."""

from crewai.tools import BaseTool
from pydantic import Field
from core.adapters.conflux_gateway import ConfluxGateway

class SponsorshipManagerTool(BaseTool):
    name: str = "manage_conflux_sponsorship"
    description: str = (
        "Permite registrar un contrato inteligente en Conflux eSpace para que sea "
        "'Gasless' (patrocinado). Utiliza el contrato interno SponsorWhitelistControl. "
        "Usa esta herramienta inmediatamente después de desplegar un contrato en Conflux."
    )

    def _run(
        self, 
        contract_address: str = Field(..., description="Dirección del contrato desplegado (0x...)."),
        gas_upper_bound: str = Field("1000000000000", description="Límite máximo de gas por transacción patrocinada."),
        use_testnet: bool = Field(False, description="Si es True, operará en Testnet.")
    ) -> str:
        """Activa el patrocinio de gas y almacenamiento para un contrato."""
        
        try:
            # Validación de conectividad y simulación Contractual
            gateway = ConfluxGateway(use_testnet=use_testnet)
            
            return (
                f"Solicitud de Patrocinio PREPARADA para el contrato: {contract_address}\n"
                f"Red: {'Conflux eSpace Testnet' if use_testnet else 'Conflux eSpace Mainnet'}\n\n"
                f"Pasos a ejecutar (Simulación SDD):\n"
                f"1. Interacción con Internal Contract: {gateway.SPONSOR_CONTRACT_ADDRESS}\n"
                f"2. Ejecutar setSponsorForGas({contract_address}, {gas_upper_bound}) depositando CFX.\n"
                f"3. Ejecutar setSponsorForCollateral({contract_address}) depositando CFX.\n"
                f"4. Ejecutar addPrivilegeByAdmin({contract_address}, [0x0000000000000000000000000000000000000000]) "
                f"permitiendo el uso Gasless de forma global.\n\n"
                f"A la espera de la firma de la clave privada Sponsor para inyectar liquidez cruzada."
            )
        except Exception as e:
            return f"Error crítico al conectar con la infraestructura Conflux: {str(e)}"
