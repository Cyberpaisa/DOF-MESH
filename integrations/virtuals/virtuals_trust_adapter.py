"""
integrations/virtuals/virtuals_trust_adapter.py
DOF × Virtuals Protocol — Trust Layer para agentes tokenizados en Base.

Virtuals Protocol tokeniza agentes IA en Base (chain 8453). Cada agente tiene
un token con bonding curve pero SIN verificación de comportamiento.

DOF llena ese gap: este adapter calcula un DOF Trust Score (0-100) para cualquier
agente de Virtuals, ancla la prueba en DOFProofRegistry (Base Sepolia/mainnet),
y expone el score para que wallets, DAOs y contratos lo consulten on-chain.

Arquitectura:
    VirtualsAgentScore (dataclass)
        └── VirtualsTrustAdapter
              ├── score_agent(agent_token_address) → VirtualsAgentScore
              ├── publish_score_onchain(score)      → tx_hash
              └── verify_agent(agent_token_address) → bool

Compatibilidad:
    - Virtuals GAME SDK: cualquier agente GAME puede llamar check_trust() via HTTP
    - Base Sepolia (testnet): DOFProofRegistry @ 0xeB676e75092df0c924D3b552eE5b9D549c14531C
    - Base mainnet (pending deploy): usar DOFChainAdapter.from_chain_name("base")

Version: 0.1.0 — DOF Mesh Legion × Virtuals Protocol
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("integrations.virtuals")

# Trust Score thresholds
TRUST_THRESHOLD_HIGH = 80    # Agente verificado — alto valor del token
TRUST_THRESHOLD_MED = 50     # Agente aceptable — usar con precaución
TRUST_THRESHOLD_LOW = 0      # Agente no confiable — riesgo alto

# Pesos de cada dimensión del score (suman 100)
SCORE_WEIGHTS = {
    "governance_compliance": 35,   # ¿Respeta reglas DOF? (constitución + Z3)
    "behavioral_consistency": 30,  # ¿Comportamiento predecible y estable?
    "onchain_attestations": 20,    # ¿Tiene proofs verificados on-chain?
    "response_integrity": 15,      # ¿Outputs libres de alucinaciones y PII?
}


@dataclass
class VirtualsAgentScore:
    """Score de confianza DOF para un agente de Virtuals Protocol.

    Este objeto es serializable a JSON para exponer via API REST o
    almacenar como metadata en el token del agente.
    """

    agent_token_address: str       # Dirección del token ERC-20 del agente en Base
    agent_id: int                  # ID numérico interno DOF
    trust_score: int               # Score 0-100 (DOF Trust Score)
    trust_tier: str                # "HIGH" | "MEDIUM" | "LOW" | "UNVERIFIED"
    governance_score: int          # Sub-score: compliance constitucional (0-35)
    behavioral_score: int          # Sub-score: consistencia de comportamiento (0-30)
    onchain_score: int             # Sub-score: attestations verificados (0-20)
    integrity_score: int           # Sub-score: integridad de outputs (0-15)
    proof_hash: str                # SHA-256 del proof bundle
    z3_verified: bool              # ¿Pasó verificación Z3 formal?
    onchain_tx: Optional[str]      # TX hash del publish on-chain (si se publicó)
    chain: str                     # Chain donde se publicó ("base_sepolia" | "base")
    timestamp: float               # Unix timestamp del score
    recommendation: str            # Texto para mostrar al usuario
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @property
    def is_trusted(self) -> bool:
        return self.trust_score >= TRUST_THRESHOLD_HIGH

    @property
    def badge(self) -> str:
        """Badge visual para mostrar en Virtuals marketplace."""
        if self.trust_score >= TRUST_THRESHOLD_HIGH:
            return "🛡️ DOF VERIFIED"
        elif self.trust_score >= TRUST_THRESHOLD_MED:
            return "⚠️ DOF PARTIAL"
        else:
            return "❌ DOF UNVERIFIED"


class VirtualsTrustAdapter:
    """
    Adapter principal DOF × Virtuals Protocol.

    Calcula y publica trust scores para agentes tokenizados en Base.

    Uso básico:
        adapter = VirtualsTrustAdapter(chain="base_sepolia")
        score = adapter.score_agent("0xAgentTokenAddress")
        print(score.badge)  # "🛡️ DOF VERIFIED"

    Uso con publish on-chain:
        score = adapter.score_agent("0xAgentTokenAddress")
        tx = adapter.publish_score_onchain(score)
        print(f"Proof publicado: {tx}")

    Uso con GAME SDK (HTTP):
        # El agente llama: GET /dof/trust?agent=0x...
        # Este adapter responde con VirtualsAgentScore serializado
    """

    VIRTUALS_BASE_CHAIN_ID = 8453        # Base mainnet (Virtuals Protocol live)
    VIRTUALS_TEST_CHAIN_ID = 84532       # Base Sepolia (testing)

    def __init__(self, chain: str = "base_sepolia", dry_run: bool = False):
        """
        Args:
            chain: "base_sepolia" (testnet) o "base" (mainnet, requiere deploy)
            dry_run: Si True, no hace llamadas on-chain reales
        """
        self.chain = chain
        self.dry_run = dry_run
        self._chain_adapter = None
        self._scoring_engine = None

    def _get_chain_adapter(self):
        """Lazy init del chain adapter."""
        if self._chain_adapter is None:
            from core.chain_adapter import DOFChainAdapter
            self._chain_adapter = DOFChainAdapter.from_chain_name(
                self.chain, dry_run=self.dry_run
            )
        return self._chain_adapter

    def _get_scoring_engine(self):
        """Lazy init del motor de scoring DOF."""
        if self._scoring_engine is None:
            self._scoring_engine = _DOFScoringEngine()
        return self._scoring_engine

    def score_agent(
        self,
        agent_token_address: str,
        agent_metadata: Optional[dict] = None,
        run_z3: bool = True,
    ) -> VirtualsAgentScore:
        """
        Calcula el DOF Trust Score para un agente de Virtuals.

        Args:
            agent_token_address: Dirección del token ERC-20 del agente en Base
            agent_metadata: Metadata opcional del agente (nombre, descripción, etc.)
            run_z3: Si True, incluye verificación Z3 formal en el score

        Returns:
            VirtualsAgentScore con score completo y desglose por dimensión
        """
        logger.info(f"[Virtuals] Scoring agente: {agent_token_address}")
        metadata = agent_metadata or {}

        # 1. Derivar agent_id desde la address (determinístico)
        agent_id = self._address_to_agent_id(agent_token_address)

        # 2. Calcular sub-scores por dimensión
        engine = self._get_scoring_engine()
        sub_scores = engine.calculate_subscores(
            agent_token_address=agent_token_address,
            metadata=metadata,
            run_z3=run_z3,
        )

        # 3. Score total ponderado
        trust_score = self._compute_weighted_score(sub_scores)

        # 4. Clasificar tier
        trust_tier = self._classify_tier(trust_score)

        # 5. Generar proof hash del bundle completo
        proof_bundle = {
            "agent": agent_token_address,
            "agent_id": agent_id,
            "scores": sub_scores,
            "total": trust_score,
            "timestamp": time.time(),
        }
        proof_hash = self._hash_proof_bundle(proof_bundle)

        # 6. Recommendation text
        recommendation = self._build_recommendation(trust_score, sub_scores)

        score = VirtualsAgentScore(
            agent_token_address=agent_token_address,
            agent_id=agent_id,
            trust_score=trust_score,
            trust_tier=trust_tier,
            governance_score=sub_scores["governance_compliance"],
            behavioral_score=sub_scores["behavioral_consistency"],
            onchain_score=sub_scores["onchain_attestations"],
            integrity_score=sub_scores["response_integrity"],
            proof_hash=proof_hash,
            z3_verified=sub_scores.get("z3_verified", False),
            onchain_tx=None,
            chain=self.chain,
            timestamp=time.time(),
            recommendation=recommendation,
            details=sub_scores,
        )

        logger.info(
            f"[Virtuals] Score calculado: {agent_token_address[:10]}... → "
            f"{trust_score}/100 ({trust_tier}) | {score.badge}"
        )
        return score

    def publish_score_onchain(self, score: VirtualsAgentScore) -> str:
        """
        Publica el trust score en DOFProofRegistry (Base Sepolia o mainnet).

        Args:
            score: VirtualsAgentScore calculado por score_agent()

        Returns:
            TX hash de la transacción on-chain (o "dry_run" si dry_run=True)
        """
        if self.dry_run:
            logger.info(f"[Virtuals][DRY_RUN] Publish score {score.trust_score} for {score.agent_token_address}")
            score.onchain_tx = "dry_run_tx_hash"
            return "dry_run_tx_hash"

        try:
            adapter = self._get_chain_adapter()
            proof_hash_bytes = bytes.fromhex(score.proof_hash)

            result = adapter.publish_attestation(
                proof_hash=proof_hash_bytes,
                agent_id=score.agent_id,
                trust_score=score.trust_score,
                storage_ref=f"virtuals://{score.agent_token_address}",
                invariants_count=len(SCORE_WEIGHTS),
            )
            tx_hash = result.get("tx_hash", "unknown")
            score.onchain_tx = tx_hash
            logger.info(f"[Virtuals] Score publicado on-chain: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"[Virtuals] Error publicando on-chain: {e}")
            score.onchain_tx = f"error:{str(e)[:50]}"
            raise

    def verify_agent(self, agent_token_address: str) -> bool:
        """
        Verifica si un agente tiene trust score >= HIGH threshold en DOFProofRegistry.

        Esto es el método que Virtuals GAME SDK puede llamar antes de ejecutar un agente.

        Args:
            agent_token_address: Dirección del token ERC-20 del agente

        Returns:
            True si el agente es confiable (trust_score >= 80)
        """
        score = self.score_agent(agent_token_address)
        return score.is_trusted

    def get_trust_badge_metadata(self, agent_token_address: str) -> dict:
        """
        Retorna metadata compatible con ERC-721 para mostrar el badge DOF
        en el token del agente en el marketplace de Virtuals.

        Esto permite que Virtuals muestre "DOF VERIFIED" en la UI del token.
        """
        score = self.score_agent(agent_token_address)
        return {
            "name": f"DOF Trust Badge — {score.trust_tier}",
            "description": score.recommendation,
            "score": score.trust_score,
            "badge": score.badge,
            "proof_hash": score.proof_hash,
            "z3_verified": score.z3_verified,
            "chain": score.chain,
            "timestamp": score.timestamp,
            "attributes": [
                {"trait_type": "Trust Score", "value": score.trust_score},
                {"trait_type": "Trust Tier", "value": score.trust_tier},
                {"trait_type": "Z3 Verified", "value": score.z3_verified},
                {"trait_type": "Governance", "value": score.governance_score},
                {"trait_type": "Behavioral", "value": score.behavioral_score},
                {"trait_type": "On-Chain", "value": score.onchain_score},
                {"trait_type": "Integrity", "value": score.integrity_score},
            ],
        }

    # ─── Helpers privados ───────────────────────────────────────────────────

    @staticmethod
    def _address_to_agent_id(address: str) -> int:
        """Convierte address ERC-20 a agent_id numérico DOF (determinístico)."""
        clean = address.lower().replace("0x", "")
        return int(clean[:8], 16) % (2 ** 32)

    @staticmethod
    def _compute_weighted_score(sub_scores: dict) -> int:
        """Calcula score total ponderado. Resultado: 0-100."""
        total = 0
        for dimension, weight in SCORE_WEIGHTS.items():
            raw = sub_scores.get(dimension, 0)
            # Normalizar al peso de la dimensión
            total += int((raw / 100) * weight)
        return min(100, max(0, total))

    @staticmethod
    def _classify_tier(score: int) -> str:
        if score >= TRUST_THRESHOLD_HIGH:
            return "HIGH"
        elif score >= TRUST_THRESHOLD_MED:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def _hash_proof_bundle(bundle: dict) -> str:
        """SHA-256 del proof bundle serializado."""
        serialized = json.dumps(bundle, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    @staticmethod
    def _build_recommendation(score: int, sub_scores: dict) -> str:
        if score >= TRUST_THRESHOLD_HIGH:
            return (
                f"Agente verificado por DOF Mesh Legion. "
                f"Trust Score: {score}/100. "
                f"Governance: {sub_scores.get('governance_compliance', 0)}/100. "
                f"Apto para interacciones de alto valor en el ecosistema Virtuals."
            )
        elif score >= TRUST_THRESHOLD_MED:
            weakest = min(sub_scores, key=lambda k: sub_scores.get(k, 0)
                         if k in SCORE_WEIGHTS else 100)
            return (
                f"Agente parcialmente verificado. Trust Score: {score}/100. "
                f"Área débil: {weakest}. "
                f"Usar con precaución — considera solicitar más attestations."
            )
        else:
            return (
                f"Agente NO verificado por DOF. Trust Score: {score}/100. "
                f"No se recomienda para operaciones de alto valor."
            )


class _DOFScoringEngine:
    """
    Motor de scoring interno.

    Calcula cada sub-score usando los módulos DOF existentes:
    - governance.py → governance_compliance
    - z3_gate.py    → behavioral_consistency (si pasa Z3)
    - chain_adapter → onchain_attestations (proofs publicados)
    - governance.py → response_integrity (NO_HALLUCINATION + NO_PII)

    En ausencia de datos históricos del agente (primer scoring), usa
    valores baseline conservadores (50/100) y marca z3_verified=False.
    """

    def calculate_subscores(
        self,
        agent_token_address: str,
        metadata: dict,
        run_z3: bool = True,
    ) -> dict:
        """
        Calcula todos los sub-scores para un agente.

        Returns:
            dict con keys de SCORE_WEIGHTS + "z3_verified"
        """
        scores = {}

        # 1. Governance compliance
        scores["governance_compliance"] = self._score_governance(metadata)

        # 2. Behavioral consistency
        scores["behavioral_consistency"] = self._score_behavioral(metadata, run_z3)

        # 3. On-chain attestations
        scores["onchain_attestations"] = self._score_onchain(agent_token_address)

        # 4. Response integrity
        scores["response_integrity"] = self._score_integrity(metadata)

        # 5. Z3 verification flag
        scores["z3_verified"] = run_z3 and scores["behavioral_consistency"] >= 70

        return scores

    def _score_governance(self, metadata: dict) -> int:
        """
        Score de compliance constitucional (0-100).

        Con metadata de outputs históricos del agente, corre las reglas
        DOF Constitution. Sin metadata, baseline conservador de 50.
        """
        if not metadata:
            return 50

        # Si hay outputs del agente, evaluar contra governance rules
        outputs = metadata.get("recent_outputs", [])
        if not outputs:
            return 50

        try:
            from core.governance import GovernanceEngine
            engine = GovernanceEngine()
            passing = 0
            for output in outputs[:10]:  # Evaluar últimos 10 outputs
                result = engine.check(output if isinstance(output, str) else str(output))
                if result.get("status") == "PASS":
                    passing += 1
            return int((passing / len(outputs[:10])) * 100)
        except Exception as e:
            logger.warning(f"[Scoring] governance check falló: {e}")
            return 50

    def _score_behavioral(self, metadata: dict, run_z3: bool) -> int:
        """
        Score de consistencia de comportamiento (0-100).

        Si run_z3=True y hay output disponible, corre Z3Gate.
        Sin datos, baseline de 60 (agente nuevo = beneficio de la duda moderado).
        """
        if not run_z3 or not metadata:
            return 60

        sample_output = metadata.get("sample_output", "")
        if not sample_output:
            return 60

        try:
            from core.z3_gate import Z3Gate
            gate = Z3Gate()
            result = gate.validate_output(sample_output)
            status = result.get("status", "TIMEOUT")
            if status == "APPROVED":
                return 90
            elif status == "FALLBACK":
                return 65
            else:
                return 40
        except Exception as e:
            logger.warning(f"[Scoring] Z3 check falló: {e}")
            return 60

    def _score_onchain(self, agent_token_address: str) -> int:
        """
        Score basado en attestations on-chain existentes (0-100).

        Consulta DOFProofRegistry en Base Sepolia para ver cuántos
        proofs tiene este agente registrados.
        """
        try:
            from core.chain_adapter import DOFChainAdapter
            adapter = DOFChainAdapter.from_chain_name("base_sepolia", dry_run=False)
            agent_id = VirtualsTrustAdapter._address_to_agent_id(agent_token_address)
            proof_count = adapter.get_proof_count_for_agent(agent_id)

            # Escala: 0 proofs=0, 1=40, 5=70, 10+=100
            if proof_count == 0:
                return 0
            elif proof_count < 5:
                return 40 + (proof_count * 6)
            elif proof_count < 10:
                return 70 + (proof_count - 5) * 6
            else:
                return 100
        except Exception as e:
            logger.debug(f"[Scoring] onchain check: {e}")
            return 0

    def _score_integrity(self, metadata: dict) -> int:
        """
        Score de integridad de outputs (0-100).

        Evalúa si los outputs tienen alucinaciones, PII, o claims sin fuente.
        Sin datos, baseline de 70 (sin evidencia de problemas).
        """
        if not metadata:
            return 70

        outputs = metadata.get("recent_outputs", [])
        if not outputs:
            return 70

        # Patrones de baja integridad
        import re
        hallucination_patterns = [
            r"\b(siempre|nunca|100%|absolutamente|garantizado)\b",
            r"\b(as an AI|como IA)\b",
        ]
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",   # SSN
            r"\b\d{16}\b",               # Tarjeta de crédito
        ]

        issues = 0
        total = len(outputs[:10])
        for output in outputs[:10]:
            text = output if isinstance(output, str) else str(output)
            for pattern in hallucination_patterns + pii_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    issues += 1
                    break

        if total == 0:
            return 70
        clean_ratio = (total - issues) / total
        return int(clean_ratio * 100)
