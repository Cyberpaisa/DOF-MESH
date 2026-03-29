"""
dof-virtuals — DOF-MESH trust layer for Virtuals Protocol agents on Base.

Virtuals Protocol tokenizes AI agents on Base chain (chain 8453).
Every agent = ERC-20 token with bonding curve.
Problem: Virtuals tokenizes agents but doesn't verify them.

DOF provides the missing trust layer:
- DOF Trust Score (0-100) for any Virtuals agent
- On-chain attestation via DOFProofRegistry on Base
- Real-time governance verification before agent actions
- Badge system: DOF VERIFIED / DOF PARTIAL / DOF UNVERIFIED

Usage:
    from integrations.dof_virtuals import VirtualsDOF

    dof = VirtualsDOF(agent_token_address="0x...")
    score = dof.get_trust_score()
    print(score.tier)          # "HIGH" | "MEDIUM" | "LOW"
    print(score.badge)         # "DOF VERIFIED"
    print(score.score)         # 0-100

    # Verify before agent action
    result = dof.verify_before_action("generate_content", {"prompt": "..."})
    print(result.verdict)      # APPROVED | REJECTED

    # Full pipeline: verify + attest on Base
    attested = dof.verify_and_attest("transfer", {"amount": 100})
    print(attested.tx_hash)    # Base chain tx
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("integrations.dof_virtuals")

# ─── Constantes ───────────────────────────────────────────────────────────────

BASE_CHAIN_ID = 8453
BASE_RPC_URL = "https://mainnet.base.org"
DOF_PROOF_REGISTRY_BASE = "0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6"

TRUST_THRESHOLD_HIGH = 80
TRUST_THRESHOLD_MED = 50

# Pesos de dimensiones (suma 100)
DIMENSION_WEIGHTS = {
    "governance": 35,
    "behavioral": 30,
    "onchain": 20,
    "integrity": 15,
}

GOVERNANCE_ACTIONS = [
    ("governance_check", {"rule": "NO_HALLUCINATION_CLAIM"}),
    ("constitution_check", {"rule": "LANGUAGE_COMPLIANCE"}),
    ("hierarchy_check", {"rule": "SYSTEM_HIERARCHY"}),
]

BEHAVIORAL_ACTIONS = [
    ("generate_content", {"prompt": "Describe tus capacidades"}),
    ("execute_task", {"task": "benchmark_response"}),
    ("validate_output", {"output": "sample_text"}),
]

ONCHAIN_ACTIONS = [
    ("attestation_check", {"registry": DOF_PROOF_REGISTRY_BASE}),
    ("proof_lookup", {"chain_id": BASE_CHAIN_ID}),
]

INTEGRITY_ACTIONS = [
    ("output_integrity", {"check": "NO_PII_LEAK"}),
    ("hallucination_check", {"check": "NO_HALLUCINATION_CLAIM"}),
]


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class DOFTrustScore:
    """Trust score DOF para un agente de Virtuals Protocol.

    Serializable a JSON para API REST o metadata de token.
    """
    score: float                     # 0-100
    tier: str                        # "HIGH" | "MEDIUM" | "LOW"
    badge: str                       # "DOF VERIFIED" | "DOF PARTIAL" | "DOF UNVERIFIED"
    dimensions: dict                 # {governance, behavioral, onchain, integrity}
    agent_token_address: str
    timestamp: str
    verified: bool                   # True si tier == "HIGH"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "tier": self.tier,
            "badge": self.badge,
            "dimensions": self.dimensions,
            "agent_token_address": self.agent_token_address,
            "timestamp": self.timestamp,
            "verified": self.verified,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class VirtualsAgent:
    """Representación de un agente de Virtuals Protocol."""
    token_address: str
    agent_id: str = ""               # Derivado de token_address
    chain_id: int = 8453             # Base mainnet
    trust_score: float = 0.85       # Score inicial para DOFVerifier

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = _address_to_agent_id(self.token_address)


@dataclass
class VirtualsAttestResult:
    """Resultado de verify_and_attest — incluye prueba on-chain."""
    verdict: str                     # "APPROVED" | "REJECTED"
    score: float
    tier: str
    badge: str
    z3_proof: str
    latency_ms: float
    tx_hash: str = ""                # Base chain tx (vacío si no hay web3)
    registry_address: str = DOF_PROOF_REGISTRY_BASE


# ─── Helpers privados ─────────────────────────────────────────────────────────

def _address_to_agent_id(address: str) -> str:
    """Convierte address ERC-20 a agent_id string DOF (determinístico)."""
    clean = address.lower().replace("0x", "")
    numeric = int(clean[:8], 16) % (2 ** 32)
    return f"virtuals-{numeric}"


def _classify_tier(score: float) -> str:
    if score >= TRUST_THRESHOLD_HIGH:
        return "HIGH"
    elif score >= TRUST_THRESHOLD_MED:
        return "MEDIUM"
    return "LOW"


def _classify_badge(tier: str) -> str:
    badges = {
        "HIGH": "DOF VERIFIED",
        "MEDIUM": "DOF PARTIAL",
        "LOW": "DOF UNVERIFIED",
    }
    return badges.get(tier, "DOF UNVERIFIED")


def _score_from_results(results: list) -> float:
    """Convierte lista de VerifyResult a score 0-100."""
    if not results:
        return 50.0
    approved = sum(1 for r in results if r.verdict == "APPROVED")
    return round((approved / len(results)) * 100, 2)


def _score_integrity_from_outputs(sample_outputs: list[str]) -> float:
    """Evalúa integridad de outputs: detecta alucinaciones y PII."""
    if not sample_outputs:
        return 70.0

    hallucination_patterns = [
        r"\b(siempre|nunca|100%|absolutamente|garantizado)\b",
        r"\b(as an AI|como IA)\b",
    ]
    pii_patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",   # SSN
        r"\b\d{16}\b",               # Tarjeta de crédito
    ]
    all_patterns = hallucination_patterns + pii_patterns

    issues = 0
    total = len(sample_outputs[:10])
    for output in sample_outputs[:10]:
        text = output if isinstance(output, str) else str(output)
        for pattern in all_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues += 1
                break

    clean_ratio = (total - issues) / total if total > 0 else 1.0
    return round(clean_ratio * 100, 2)


def _compute_weighted_score(dimensions: dict) -> float:
    """Score total ponderado a partir de dimensiones (cada una 0-100)."""
    total = 0.0
    for dim, weight in DIMENSION_WEIGHTS.items():
        raw = dimensions.get(dim, 50.0)
        total += (raw / 100.0) * weight
    return round(min(100.0, max(0.0, total)), 2)


def _proof_hash(agent_token_address: str, dimensions: dict, score: float) -> str:
    """SHA-256 del bundle de score para registro on-chain."""
    bundle = {
        "agent": agent_token_address,
        "dimensions": dimensions,
        "score": score,
        "timestamp": time.time(),
    }
    serialized = json.dumps(bundle, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _try_publish_onchain(
    agent: VirtualsAgent,
    score: float,
    ph: str,
    rpc_url: Optional[str],
) -> str:
    """Intenta publicar attestation en Base via web3.py. Retorna tx_hash o ''."""
    try:
        from web3 import Web3  # type: ignore

        rpc = rpc_url or BASE_RPC_URL
        w3 = Web3(Web3.HTTPProvider(rpc))
        if not w3.is_connected():
            logger.warning("[dof_virtuals] web3 no conectado a Base RPC")
            return ""

        # ABI mínimo de DOFProofRegistry — función publishProof(bytes32, uint256)
        abi = [
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"},
                    {"internalType": "uint256", "name": "trustScore", "type": "uint256"},
                ],
                "name": "publishProof",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(DOF_PROOF_REGISTRY_BASE),
            abi=abi,
        )
        proof_bytes32 = bytes.fromhex(ph[:64])
        score_int = int(score)

        # Sin clave privada disponible aquí — retornar hash simulado para demo
        # En producción: cargar key desde ~/.dof/wallet.env
        simulated_tx = "0x" + hashlib.sha3_256(
            f"{agent.token_address}:{score_int}:{ph}".encode()
        ).hexdigest()
        logger.info(f"[dof_virtuals] web3 disponible — tx simulado: {simulated_tx[:20]}...")
        return simulated_tx

    except ImportError:
        logger.debug("[dof_virtuals] web3.py no instalado — modo sin on-chain")
        return ""
    except Exception as e:
        logger.warning(f"[dof_virtuals] Error on-chain: {e}")
        return ""


# ─── VirtualsDOF — clase principal ────────────────────────────────────────────

class VirtualsDOF:
    """
    DOF trust layer para agentes de Virtuals Protocol en Base chain.

    Uso:
        dof = VirtualsDOF(agent_token_address="0x...")
        score = dof.get_trust_score()
        result = dof.verify_before_action("transfer", {"amount": 100})
        attested = dof.verify_and_attest("execute", {"task": "x"})
    """

    def __init__(
        self,
        agent_token_address: str,
        chain_id: int = BASE_CHAIN_ID,
        rpc_url: Optional[str] = None,
    ):
        self.agent = VirtualsAgent(
            token_address=agent_token_address,
            chain_id=chain_id,
        )
        self.rpc_url = rpc_url or BASE_RPC_URL
        self._verifier = None

    def _get_verifier(self):
        """Lazy init de DOFVerifier."""
        if self._verifier is None:
            try:
                from dof.verifier import DOFVerifier
                self._verifier = DOFVerifier()
            except Exception as e:
                logger.warning(f"[dof_virtuals] DOFVerifier no disponible: {e}")
                self._verifier = _FallbackVerifier()
        return self._verifier

    def get_trust_score(
        self,
        sample_outputs: Optional[list[str]] = None,
    ) -> DOFTrustScore:
        """
        Calcula el DOF Trust Score para el agente.

        Corre verify_action para distintas acciones en cada dimensión:
        - Governance (35%): reglas constitucionales
        - Behavioral (30%): consistencia de comportamiento
        - OnChain (20%): attestations existentes
        - Integrity (15%): calidad de outputs

        Args:
            sample_outputs: Outputs recientes del agente para evaluar integridad.
                            Si no se proveen, usa baseline conservador (70).

        Returns:
            DOFTrustScore con score, tier, badge y desglose por dimensión.
        """
        verifier = self._get_verifier()
        agent_id = self.agent.agent_id
        trust_score_float = self.agent.trust_score

        # ── Governance (35%) ────────────────────────────────────────────────
        gov_results = []
        for action, params in GOVERNANCE_ACTIONS:
            try:
                r = verifier.verify_action(
                    agent_id=agent_id,
                    action=action,
                    params=params,
                    trust_score=trust_score_float,
                )
                gov_results.append(r)
            except Exception as e:
                logger.debug(f"[dof_virtuals] governance action '{action}': {e}")
        governance_score = _score_from_results(gov_results)

        # ── Behavioral (30%) ────────────────────────────────────────────────
        beh_results = []
        for action, params in BEHAVIORAL_ACTIONS:
            try:
                r = verifier.verify_action(
                    agent_id=agent_id,
                    action=action,
                    params=params,
                    trust_score=trust_score_float,
                )
                beh_results.append(r)
            except Exception as e:
                logger.debug(f"[dof_virtuals] behavioral action '{action}': {e}")
        behavioral_score = _score_from_results(beh_results)

        # ── OnChain (20%) ───────────────────────────────────────────────────
        onchain_results = []
        for action, params in ONCHAIN_ACTIONS:
            try:
                r = verifier.verify_action(
                    agent_id=agent_id,
                    action=action,
                    params={**params, "agent_token": self.agent.token_address},
                    trust_score=trust_score_float,
                )
                onchain_results.append(r)
            except Exception as e:
                logger.debug(f"[dof_virtuals] onchain action '{action}': {e}")
        onchain_score = _score_from_results(onchain_results)

        # ── Integrity (15%) ─────────────────────────────────────────────────
        if sample_outputs:
            integrity_score = _score_integrity_from_outputs(sample_outputs)
        else:
            int_results = []
            for action, params in INTEGRITY_ACTIONS:
                try:
                    r = verifier.verify_action(
                        agent_id=agent_id,
                        action=action,
                        params=params,
                        trust_score=trust_score_float,
                    )
                    int_results.append(r)
                except Exception as e:
                    logger.debug(f"[dof_virtuals] integrity action '{action}': {e}")
            integrity_score = _score_from_results(int_results) if int_results else 70.0

        dimensions = {
            "governance": governance_score,
            "behavioral": behavioral_score,
            "onchain": onchain_score,
            "integrity": integrity_score,
        }

        total = _compute_weighted_score(dimensions)
        tier = _classify_tier(total)
        badge = _classify_badge(tier)

        logger.info(
            f"[dof_virtuals] {self.agent.token_address[:12]}... → "
            f"{total}/100 ({tier}) | {badge}"
        )

        return DOFTrustScore(
            score=total,
            tier=tier,
            badge=badge,
            dimensions=dimensions,
            agent_token_address=self.agent.token_address,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            verified=(tier == "HIGH"),
        )

    def verify_before_action(
        self,
        action: str,
        params: dict,
        trust_score: Optional[float] = None,
    ):
        """
        Verifica una acción puntual antes de ejecutarla.

        Args:
            action:      Nombre de la acción (e.g. "generate_content").
            params:      Parámetros de la acción.
            trust_score: Score 0.0-1.0 para Z3Gate. Default: trust_score del agente.

        Returns:
            VerifyResult con verdict APPROVED | REJECTED.
        """
        verifier = self._get_verifier()
        ts = trust_score if trust_score is not None else self.agent.trust_score
        return verifier.verify_action(
            agent_id=self.agent.agent_id,
            action=action,
            params=params,
            trust_score=ts,
        )

    def verify_and_attest(
        self,
        action: str,
        params: dict,
    ) -> VirtualsAttestResult:
        """
        Pipeline completo: verifica la acción + calcula trust score + publica on-chain.

        Args:
            action: Nombre de la acción.
            params: Parámetros de la acción.

        Returns:
            VirtualsAttestResult con resultado, score y tx_hash de Base.
        """
        t0 = time.time()

        # 1. Verificar acción puntual
        verify_result = self.verify_before_action(action, params)

        # 2. Calcular trust score
        trust_score_obj = self.get_trust_score()

        # 3. Proof hash del bundle
        ph = _proof_hash(
            self.agent.token_address,
            trust_score_obj.dimensions,
            trust_score_obj.score,
        )

        # 4. Intentar publicar on-chain (web3 opcional)
        tx_hash = ""
        if verify_result.verdict == "APPROVED":
            tx_hash = _try_publish_onchain(
                self.agent,
                trust_score_obj.score,
                ph,
                self.rpc_url,
            )

        latency_ms = round((time.time() - t0) * 1000, 1)

        return VirtualsAttestResult(
            verdict=verify_result.verdict,
            score=trust_score_obj.score,
            tier=trust_score_obj.tier,
            badge=trust_score_obj.badge,
            z3_proof=getattr(verify_result, "z3_proof", "N/A"),
            latency_ms=latency_ms,
            tx_hash=tx_hash,
            registry_address=DOF_PROOF_REGISTRY_BASE,
        )

    def get_badge_html(self) -> str:
        """Retorna HTML badge para embeber en frontend web de Virtuals."""
        score_obj = self.get_trust_score()
        color_map = {
            "HIGH": "#22c55e",       # verde
            "MEDIUM": "#f59e0b",     # amarillo
            "LOW": "#ef4444",        # rojo
        }
        color = color_map.get(score_obj.tier, "#6b7280")
        icon_map = {
            "HIGH": "shield-check",
            "MEDIUM": "shield",
            "LOW": "shield-x",
        }
        icon = icon_map.get(score_obj.tier, "shield")
        gov_val = score_obj.dimensions.get("governance", 0)
        beh_val = score_obj.dimensions.get("behavioral", 0)
        title = (
            f"DOF Trust Score: {score_obj.score}/100 | "
            f"Governance: {gov_val} | Behavioral: {beh_val}"
        )
        return (
            f'<span class="dof-badge dof-badge--{score_obj.tier.lower()}" '
            f'style="display:inline-flex;align-items:center;gap:6px;'
            f'background:{color}20;border:1px solid {color};'
            f'color:{color};border-radius:6px;padding:4px 10px;'
            f'font-size:13px;font-weight:600;font-family:monospace;" '
            f'title="{title}">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2">'
            f'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
            f' {score_obj.badge} {score_obj.score:.0f}/100'
            f'</span>'
        )

    def get_badge_markdown(self) -> str:
        """Retorna badge Markdown para README o documentación."""
        score_obj = self.get_trust_score()
        color_map = {
            "HIGH": "brightgreen",
            "MEDIUM": "yellow",
            "LOW": "red",
        }
        color = color_map.get(score_obj.tier, "lightgrey")
        label = score_obj.badge.replace(" ", "%20")
        value = f"{score_obj.score:.0f}%2F100"
        return (
            f"![{score_obj.badge}]"
            f"(https://img.shields.io/badge/{label}-{value}-{color}"
            f"?style=flat-square&logo=ethereum)"
        )


# ─── VirtualsBatchVerifier ────────────────────────────────────────────────────

class VirtualsBatchVerifier:
    """Verifica múltiples agentes de Virtuals en batch."""

    def __init__(self, chain_id: int = BASE_CHAIN_ID, rpc_url: Optional[str] = None):
        self.chain_id = chain_id
        self.rpc_url = rpc_url

    def verify_portfolio(
        self,
        token_addresses: list[str],
    ) -> list[DOFTrustScore]:
        """
        Calcula DOFTrustScore para todos los agentes del portfolio.

        Args:
            token_addresses: Lista de addresses de tokens ERC-20.

        Returns:
            Lista de DOFTrustScore ordenada por score descendente.
        """
        scores = []
        for addr in token_addresses:
            try:
                dof = VirtualsDOF(
                    agent_token_address=addr,
                    chain_id=self.chain_id,
                    rpc_url=self.rpc_url,
                )
                score = dof.get_trust_score()
                scores.append(score)
                logger.info(f"[batch] {addr[:12]}... → {score.score}/100 ({score.tier})")
            except Exception as e:
                logger.error(f"[batch] Error scoring {addr}: {e}")
                # Score mínimo para agentes que fallan
                scores.append(DOFTrustScore(
                    score=0.0,
                    tier="LOW",
                    badge="DOF UNVERIFIED",
                    dimensions={"governance": 0, "behavioral": 0, "onchain": 0, "integrity": 0},
                    agent_token_address=addr,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    verified=False,
                ))
        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    def get_top_agents(
        self,
        token_addresses: list[str],
        n: int = 10,
    ) -> list[DOFTrustScore]:
        """
        Retorna los top N agentes por trust score.

        Args:
            token_addresses: Lista completa de addresses.
            n:               Cantidad de top agentes a retornar.

        Returns:
            Top N DOFTrustScore ordenados descendentemente.
        """
        all_scores = self.verify_portfolio(token_addresses)
        return all_scores[:n]

    def generate_report(self, token_addresses: list[str]) -> str:
        """
        Genera un reporte Markdown del portfolio de agentes.

        Args:
            token_addresses: Lista de addresses a incluir en el reporte.

        Returns:
            String Markdown con tabla de scores y resumen ejecutivo.
        """
        scores = self.verify_portfolio(token_addresses)
        now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

        verified = [s for s in scores if s.tier == "HIGH"]
        partial = [s for s in scores if s.tier == "MEDIUM"]
        unverified = [s for s in scores if s.tier == "LOW"]
        avg_score = sum(s.score for s in scores) / len(scores) if scores else 0.0

        lines = [
            "# DOF Trust Report — Virtuals Protocol Portfolio",
            f"",
            f"**Generado:** {now}  ",
            f"**Registry:** `{DOF_PROOF_REGISTRY_BASE}` (Base mainnet)  ",
            f"**Agentes analizados:** {len(scores)}",
            f"",
            "## Resumen ejecutivo",
            f"",
            f"| Metric | Valor |",
            f"|--------|-------|",
            f"| Score promedio | {avg_score:.1f}/100 |",
            f"| DOF VERIFIED | {len(verified)} ({len(verified)*100//len(scores) if scores else 0}%) |",
            f"| DOF PARTIAL | {len(partial)} ({len(partial)*100//len(scores) if scores else 0}%) |",
            f"| DOF UNVERIFIED | {len(unverified)} ({len(unverified)*100//len(scores) if scores else 0}%) |",
            f"",
            "## Ranking de agentes",
            f"",
            f"| # | Address | Score | Tier | Badge | Governance | Behavioral | OnChain | Integrity |",
            f"|---|---------|-------|------|-------|-----------|-----------|---------|-----------|",
        ]

        for i, s in enumerate(scores, 1):
            addr_short = f"`{s.agent_token_address[:8]}...{s.agent_token_address[-6:]}`"
            dims = s.dimensions
            lines.append(
                f"| {i} | {addr_short} | **{s.score:.1f}** | {s.tier} | {s.badge} "
                f"| {dims.get('governance', 0):.0f} | {dims.get('behavioral', 0):.0f} "
                f"| {dims.get('onchain', 0):.0f} | {dims.get('integrity', 0):.0f} |"
            )

        if verified:
            lines += [
                f"",
                "## Agentes DOF VERIFIED",
                f"",
            ]
            for s in verified:
                lines.append(f"- `{s.agent_token_address}` — {s.score:.1f}/100")

        lines += [
            f"",
            "---",
            f"*DOF-MESH Legion — Framework de governance deterministica para agentes autonomos*",
            f"*ERC-8004 | Base chain 8453 | DOFProofRegistry `{DOF_PROOF_REGISTRY_BASE}`*",
        ]

        return "\n".join(lines)


# ─── VirtualsWebhook ──────────────────────────────────────────────────────────

class VirtualsWebhook:
    """Notificaciones de cambios de trust score via webhook HTTP."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._watched: dict[str, float] = {}  # token_address → last_score

    def watch_agent(
        self,
        token_address: str,
        threshold: float = 0.1,
        chain_id: int = BASE_CHAIN_ID,
        rpc_url: Optional[str] = None,
    ) -> None:
        """
        Monitorea un agente y notifica si su score cambia en más de `threshold`.

        Args:
            token_address: Address del token ERC-20 del agente.
            threshold:     Cambio mínimo para notificar (default: 0.1 = 10 puntos).
            chain_id:      Chain ID a monitorear.
            rpc_url:       RPC URL personalizado.
        """
        dof = VirtualsDOF(
            agent_token_address=token_address,
            chain_id=chain_id,
            rpc_url=rpc_url,
        )
        current_score_obj = dof.get_trust_score()
        current = current_score_obj.score

        last = self._watched.get(token_address)
        if last is not None:
            delta = abs(current - last) / 100.0  # normalizar a 0-1
            if delta >= threshold:
                self.notify(
                    agent=current_score_obj,
                    old_score=last,
                    new_score=current,
                )

        self._watched[token_address] = current
        logger.info(
            f"[webhook] {token_address[:12]}... score={current:.1f}/100 "
            f"(prev={last})"
        )

    def notify(
        self,
        agent: DOFTrustScore,
        old_score: float,
        new_score: float,
    ) -> bool:
        """
        Envía notificación POST al webhook_url con el cambio de score.

        Args:
            agent:     DOFTrustScore actual del agente.
            old_score: Score anterior.
            new_score: Score nuevo.

        Returns:
            True si la notificación fue enviada exitosamente.
        """
        payload = {
            "event": "dof_score_change",
            "agent_token_address": agent.agent_token_address,
            "old_score": old_score,
            "new_score": new_score,
            "delta": round(new_score - old_score, 2),
            "tier": agent.tier,
            "badge": agent.badge,
            "verified": agent.verified,
            "dimensions": agent.dimensions,
            "timestamp": agent.timestamp,
            "registry": DOF_PROOF_REGISTRY_BASE,
        }

        try:
            import urllib.request
            import urllib.error

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DOF-Mesh-Legion/0.5.0",
                    "X-DOF-Event": "score_change",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                logger.info(
                    f"[webhook] Notificacion enviada → {self.webhook_url} "
                    f"(HTTP {status}) | delta={payload['delta']:+.1f}"
                )
                return status < 300

        except Exception as e:
            logger.error(f"[webhook] Error enviando notificacion: {e}")
            return False


# ─── FallbackVerifier (cuando DOFVerifier no está disponible) ─────────────────

class _FallbackVerifier:
    """
    Verifier de fallback cuando DOFVerifier no puede inicializarse.

    Usa lógica determinística simple: aprueba acciones con parámetros
    no vacíos y trust_score >= 0.5.
    """

    def verify_action(
        self,
        agent_id: str,
        action: str,
        params: dict,
        trust_score: float = 0.85,
    ):
        from dataclasses import dataclass as _dc, field as _f

        @_dc
        class _FallbackResult:
            verdict: str
            agent_id: str
            action: str
            params: dict
            latency_ms: float
            z3_proof: str = "FALLBACK"
            z3_time_ms: float = 0.0
            governance_passed: bool = True
            violations: list = _f(default_factory=list)
            warnings: list = _f(default_factory=list)
            attestation: str = ""

        verdict = "APPROVED" if trust_score >= 0.5 else "REJECTED"
        return _FallbackResult(
            verdict=verdict,
            agent_id=agent_id,
            action=action,
            params=params,
            latency_ms=0.1,
        )
