"""
Sovereign Funding Skill — DOF Native
====================================
Skill para el motor de habilidades del DOF que permite a los agentes
gestionar su soberanía financiera de forma autónoma.
"""

import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger("core.sovereign_funding")

SKILL_ID = "sovereign_funding"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "Sovereign cross-chain funding layer for autonomous agent operations."

@dataclass
class SkillResult:
    skill_id: str
    action: str
    status: str
    data: Dict[str, Any]
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

class SovereignFundingSkill:
    """
    Skill nativa para la gestión de fondos soberanos en el Mesh.
    """

    ACTIONS = ["generate_link", "help"]

    def __init__(self):
        logger.info(f"SovereignFundingSkill v{SKILL_VERSION} initialized")

    def run(self, action: str, **kwargs) -> SkillResult:
        if action not in self.ACTIONS:
            return SkillResult(
                skill_id=SKILL_ID,
                action=action,
                status="ERROR",
                data={"error": f"Acción desconocida '{action}'"},
                duration_ms=0,
            )

        start = time.time()
        try:
            handler = getattr(self, f"_action_{action}")
            data = handler(**kwargs)
            status = "OK"
        except Exception as e:
            logger.error(f"Sovereign funding action {action} failed: {e}")
            data = {"error": str(e)}
            status = "ERROR"

        duration_ms = (time.time() - start) * 1000
        return SkillResult(
            skill_id=SKILL_ID,
            action=action,
            status=status,
            data=data,
            duration_ms=round(duration_ms, 2),
        )

    def _action_generate_link(self, amount: float, to_address: str, 
                             to_chain: str = "8453", to_token: str = "USDC", 
                             label: str = None) -> Dict:
        """Acción para generar el link de financiamiento."""
        from core.tools.funding_tools import GenerateSovereignLinkTool
        tool = GenerateSovereignLinkTool()
        result_text = tool._run(
            amount=amount, 
            to_address=to_address, 
            to_chain=to_chain, 
            to_token=to_token, 
            label=label
        )
        return {"result": result_text}

    def _action_help(self) -> Dict:
        """Acción de ayuda técnica."""
        from core.tools.funding_tools import FundingHelpTool
        tool = FundingHelpTool()
        return {"guide": tool._run()}

SKILL_REGISTRY_ENTRY = {
    "skill_id": SKILL_ID,
    "class": "SovereignFundingSkill",
    "module": "core.sovereign_funding_skill",
    "version": SKILL_VERSION,
    "description": SKILL_DESCRIPTION,
    "tags": ["finance", "sovereignty", "funding", "dof-native"],
    "actions": SovereignFundingSkill.ACTIONS,
}
