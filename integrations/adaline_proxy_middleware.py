"""
Adaline ↔ DOF — Proxy Middleware (Módulo 1)

Intercepta llamadas LLM que pasan por el proxy de Adaline,
corre check_governance() de DOF ANTES de que la respuesta llegue al cliente,
e inyecta el resultado como metadata en el trace de Adaline.

Proxy real de Adaline:
  base_url : https://gateway.adaline.ai/v1/openai/
  headers  : adaline-api-key, adaline-project-id, adaline-prompt-id

Flujo:
  Tu agente → Adaline Proxy → [LLM] → governed_llm_call() → DOF verdict → trace Adaline

Uso rápido (cliente OpenAI/Anthropic apuntando al proxy):
    from integrations.adaline_proxy_middleware import AdalineClient
    client = AdalineClient(project_id="<id>", prompt_id="<id>")
    result = client.chat("Analiza este contrato...", agent_id=1687)

O como wrapper standalone:
    from integrations.adaline_proxy_middleware import governed_llm_call
    result = governed_llm_call(prompt, response_text, agent_id=1687)
"""

import json
import time
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("integrations.adaline_proxy")

# ---------------------------------------------------------------------------
# Importaciones DOF (tolerantes a entornos donde no están instaladas)
# ---------------------------------------------------------------------------
try:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.governance import check_governance
    from core.dof_tracer import Trace, Span, DOFTracer
    _DOF_AVAILABLE = True
except ImportError as e:
    logger.warning("DOF core no disponible: %s — modo mock activado", e)
    _DOF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class GovernanceInjection:
    """Resultado de governance inyectado en el trace de Adaline."""
    trace_id: str
    agent_id: int
    timestamp: float
    prompt_hash: str           # sha256 del prompt (no PII)
    response_hash: str         # sha256 de la respuesta
    governance_passed: bool
    governance_score: float
    violations: list[str] = field(default_factory=list)
    warnings: list[str]  = field(default_factory=list)
    latency_governance_ms: float = 0.0
    dof_verdict: str = "UNKNOWN"   # APPROVED | BLOCKED | WARNED
    adaline_span_id: str = ""       # span_id del trace Adaline origen

    def to_dict(self) -> dict:
        return asdict(self)

    def to_adaline_metadata(self) -> dict:
        """Formato compatible con el campo `metadata` del span de Adaline."""
        return {
            "dof.governance.passed": self.governance_passed,
            "dof.governance.score": round(self.governance_score, 4),
            "dof.governance.verdict": self.dof_verdict,
            "dof.governance.violations": self.violations,
            "dof.governance.warnings": self.warnings,
            "dof.governance.latency_ms": round(self.latency_governance_ms, 2),
            "dof.trace_id": self.trace_id,
            "dof.agent_id": self.agent_id,
            "dof.prompt_hash": self.prompt_hash[:16],   # primeros 16 chars
        }


# ---------------------------------------------------------------------------
# Función principal: governed_llm_call
# ---------------------------------------------------------------------------

def governed_llm_call(
    prompt: str,
    response_text: str,
    agent_id: int = 0,
    adaline_span_id: str = "",
    persist_trace: bool = True,
) -> GovernanceInjection:
    """
    Wrapper que corre check_governance() sobre la respuesta LLM y devuelve
    un GovernanceInjection listo para inyectar en el trace de Adaline.

    Args:
        prompt:          El prompt enviado al LLM (para hash, no se guarda en claro).
        response_text:   La respuesta del LLM a verificar.
        agent_id:        ID del agente DOF/ERC-8004.
        adaline_span_id: span_id del trace Adaline origen (para correlación).
        persist_trace:   Si True, persiste el trace en logs/traces/.

    Returns:
        GovernanceInjection con resultado + metadata lista para Adaline.
    """
    import uuid
    trace_id = uuid.uuid4().hex[:12]

    prompt_hash   = hashlib.sha256(prompt.encode()).hexdigest()
    response_hash = hashlib.sha256(response_text.encode()).hexdigest()

    t0 = time.perf_counter()

    if _DOF_AVAILABLE:
        result = check_governance(response_text)
        violations = result.violations
        warnings   = result.warnings
        score      = result.score
        passed     = result.passed
    else:
        # Mock cuando DOF core no está disponible (tests standalone)
        violations, warnings, score, passed = [], [], 1.0, True

    latency_ms = (time.perf_counter() - t0) * 1000

    # Determinar veredicto
    if not passed:
        verdict = "BLOCKED"
    elif warnings:
        verdict = "WARNED"
    else:
        verdict = "APPROVED"

    injection = GovernanceInjection(
        trace_id=trace_id,
        agent_id=agent_id,
        timestamp=time.time(),
        prompt_hash=prompt_hash,
        response_hash=response_hash,
        governance_passed=passed,
        governance_score=score,
        violations=violations,
        warnings=warnings,
        latency_governance_ms=latency_ms,
        dof_verdict=verdict,
        adaline_span_id=adaline_span_id,
    )

    if persist_trace and _DOF_AVAILABLE:
        _persist_injection(injection)

    logger.info(
        "governance=%s score=%.3f violations=%d warnings=%d latency=%.1fms agent=%d",
        verdict, score, len(violations), len(warnings), latency_ms, agent_id,
    )

    return injection


# ---------------------------------------------------------------------------
# Persistencia del trace (JSONL — mismo formato que dof_tracer)
# ---------------------------------------------------------------------------

def _persist_injection(injection: GovernanceInjection) -> None:
    """Escribe el injection en logs/traces/adaline_governance.jsonl."""
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base, "logs", "traces")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "adaline_governance.jsonl")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(injection.to_dict()) + "\n")
    except Exception as exc:
        logger.warning("No se pudo persistir injection: %s", exc)


# ---------------------------------------------------------------------------
# WSGI Middleware (opcional — para envolver una app Flask/FastAPI/ASGI)
# ---------------------------------------------------------------------------

class AdalineProxyMiddleware:
    """
    WSGI middleware que intercepta respuestas JSON con campo 'content' o 'text',
    corre check_governance() y añade 'dof_governance' al body de respuesta.

    Compatible con Flask, Django, cualquier app WSGI.

    Ejemplo:
        from flask import Flask
        app = Flask(__name__)
        app.wsgi_app = AdalineProxyMiddleware(app.wsgi_app, agent_id=1687)
    """

    def __init__(self, app, agent_id: int = 0):
        self.app = app
        self.agent_id = agent_id

    def __call__(self, environ, start_response):
        # Capturamos el body de la respuesta
        captured: list[bytes] = []
        status_holder: list[str] = []
        headers_holder: list[Any] = []

        def _capture_start_response(status, headers, exc_info=None):
            status_holder.append(status)
            headers_holder.extend(headers)
            return start_response(status, headers, exc_info)

        app_iter = self.app(environ, _capture_start_response)

        try:
            body = b"".join(app_iter)
        finally:
            if hasattr(app_iter, "close"):
                app_iter.close()

        # Intentamos parsear JSON y enriquecer
        content_type = dict(headers_holder).get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body)
                response_text = (
                    data.get("content")
                    or data.get("text")
                    or data.get("message", {}).get("content", "")
                    or ""
                )
                if response_text:
                    prompt = environ.get("HTTP_X_ADALINE_PROMPT", "")
                    span_id = environ.get("HTTP_X_ADALINE_SPAN_ID", "")
                    injection = governed_llm_call(
                        prompt=prompt,
                        response_text=response_text,
                        agent_id=self.agent_id,
                        adaline_span_id=span_id,
                    )
                    data["dof_governance"] = injection.to_adaline_metadata()
                    body = json.dumps(data).encode("utf-8")
            except (json.JSONDecodeError, Exception) as exc:
                logger.debug("Middleware: no se pudo enriquecer respuesta: %s", exc)

        return [body]


# ---------------------------------------------------------------------------
# AdalineClient — cliente real apuntando al proxy de Adaline
# ---------------------------------------------------------------------------

class AdalineClient:
    """
    Cliente que envía llamadas LLM a través del proxy de Adaline
    y corre check_governance() de DOF sobre cada respuesta.

    Requiere: pip install openai
    Variables de entorno: ADALINE_API_KEY, ADALINE_PROJECT_ID, ADALINE_PROMPT_ID

    Ejemplo:
        client = AdalineClient()
        result = client.chat("Analiza este contrato Solidity...", agent_id=1687)
        print(result["governance"]["dof.governance.verdict"])  # APPROVED / BLOCKED / WARNED
    """

    PROXY_BASE_URL = "https://gateway.adaline.ai/v1/openai/"

    def __init__(
        self,
        api_key: str | None = None,
        project_id: str | None = None,
        prompt_id: str | None = None,
        model: str = "claude-sonnet-4-6",
    ):
        import os
        self.adaline_api_key = api_key or os.getenv("ADALINE_API_KEY", "")
        self.project_id      = project_id or os.getenv("ADALINE_PROJECT_ID", "dof-mesh")
        self.prompt_id       = prompt_id  or os.getenv("ADALINE_PROMPT_ID",  "governance-check")
        self.model           = model

        if not self.adaline_api_key:
            raise ValueError("ADALINE_API_KEY requerido")

    def _get_openai_client(self):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install openai — requerido para AdalineClient")

        return OpenAI(
            base_url=self.PROXY_BASE_URL,
            api_key=self.adaline_api_key,  # Adaline acepta el api key aquí también
            default_headers={
                "adaline-api-key":    self.adaline_api_key,
                "adaline-project-id": self.project_id,
                "adaline-prompt-id":  self.prompt_id,
            },
        )

    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful AI agent. Always cite sources.",
        agent_id: int = 0,
        max_tokens: int = 1024,
    ) -> dict:
        """
        Envía un mensaje al LLM vía proxy Adaline y verifica con DOF governance.

        Returns:
            {
              "content": str,         — respuesta del LLM
              "governance": dict,     — metadata DOF inyectada
              "blocked": bool,        — True si DOF bloqueó la respuesta
              "model": str,
            }
        """
        client = self._get_openai_client()

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        span_id = getattr(response, "id", "")

        injection = governed_llm_call(
            prompt=prompt,
            response_text=content,
            agent_id=agent_id,
            adaline_span_id=span_id,
        )

        return {
            "content":    content,
            "governance": injection.to_adaline_metadata(),
            "blocked":    not injection.governance_passed,
            "model":      self.model,
            "trace_id":   injection.trace_id,
        }


# ---------------------------------------------------------------------------
# Webhook receiver (Adaline → DOF Guardian)
# ---------------------------------------------------------------------------

def handle_adaline_webhook(payload: dict, agent_id: int = 0) -> dict:
    """
    Recibe un webhook de Adaline (alert de costo, latencia, policy violation)
    y dispara la reacción del Guardian de DOF.

    Payload esperado de Adaline:
        {
          "alert_type": "cost_spike" | "latency_p99" | "policy_violation",
          "value": float,
          "threshold": float,
          "span_id": str,
          "prompt_id": str,
          "response_text": str   # opcional, para re-verificar governance
        }

    Returns:
        dict con acción tomada por DOF.
    """
    alert_type   = payload.get("alert_type", "unknown")
    response_text = payload.get("response_text", "")

    action = {"alert_type": alert_type, "dof_action": "none", "dof_verdict": None}

    if response_text:
        injection = governed_llm_call(
            prompt="[webhook-re-eval]",
            response_text=response_text,
            agent_id=agent_id,
            adaline_span_id=payload.get("span_id", ""),
        )
        action["dof_verdict"] = injection.dof_verdict
        action["dof_governance"] = injection.to_adaline_metadata()

        if not injection.governance_passed:
            action["dof_action"] = "AGENT_PAUSED"
            logger.warning("Guardian: agente %d PAUSADO por violación governance", agent_id)
        elif alert_type in ("cost_spike", "latency_p99"):
            action["dof_action"] = "ALERT_LOGGED"
        else:
            action["dof_action"] = "APPROVED"
    else:
        action["dof_action"] = "ALERT_LOGGED"

    logger.info("Webhook Adaline→DOF: type=%s action=%s", alert_type, action["dof_action"])
    return action


# ---------------------------------------------------------------------------
# CLI rápido para demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

    print("\n=== Adaline ↔ DOF Proxy Middleware — Demo ===\n")

    # Caso 0: cliente real contra el proxy de Adaline
    try:
        client = AdalineClient()
        print("Caso 0 — AdalineClient real (proxy gateway.adaline.ai):")
        result = client.chat(
            prompt="Security score 1-10 for: msg.sender.call{value: address(this).balance}(''). One line.",
            agent_id=1687,
        )
        print(f"  Respuesta : {result['content'][:120]}")
        print(f"  Veredicto : {result['governance']['dof.governance.verdict']}")
        print(f"  Score DOF : {result['governance']['dof.governance.score']}")
        print(f"  Bloqueado : {result['blocked']}")
        print(f"  Trace ID  : {result['trace_id']}")
    except Exception as e:
        print(f"  [sin credenciales Adaline]: {e}")


    # Caso 1: respuesta limpia
    result = governed_llm_call(
        prompt="Analiza este contrato Solidity y da una puntuación de seguridad.",
        response_text=(
            "Security score: 3/10. The contract uses a reentrancy pattern "
            "(msg.sender.call before state update). Recommend: checks-effects-interactions. "
            "Reference: https://swcregistry.io/docs/SWC-107"
        ),
        agent_id=1687,
    )
    print("Caso 1 — Respuesta con fuente:")
    print(json.dumps(result.to_adaline_metadata(), indent=2))

    # Caso 2: alucinación sin fuente
    result2 = governed_llm_call(
        prompt="¿Es seguro este contrato?",
        response_text=(
            "According to my research, this contract is completely secure "
            "and has been audited by top firms."
        ),
        agent_id=1687,
    )
    print("\nCaso 2 — Alucinación sin fuente:")
    print(json.dumps(result2.to_adaline_metadata(), indent=2))

    # Caso 3: webhook de Adaline
    webhook_payload = {
        "alert_type": "policy_violation",
        "value": 0.95,
        "threshold": 0.8,
        "span_id": "span_abc123",
        "response_text": "According to research, the contract is totally safe.",
    }
    action = handle_adaline_webhook(webhook_payload, agent_id=1687)
    print("\nCaso 3 — Webhook Adaline→DOF Guardian:")
    print(json.dumps(action, indent=2))

    print("\n✓ Módulo 1 funcionando. Adaline monitorea → DOF certifica.\n")
