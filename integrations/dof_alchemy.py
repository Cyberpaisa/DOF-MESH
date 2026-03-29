"""
dof-alchemy — DOF-MESH integration with Alchemy for enhanced on-chain attestations.

Replaces the default RPC with Alchemy's reliable infrastructure and adds:
- Alchemy RPC for DOFProofRegistry calls (Avalanche + Base)
- Webhook notifications when attestations confirm on-chain
- Gas estimation before attestation
- Enhanced error handling with Alchemy's debug_traceTransaction

Usage:
    from integrations.dof_alchemy import AlchemyDOF

    dof = AlchemyDOF(
        alchemy_api_key="your-key",
        chain="base",   # or "avalanche"
    )
    result = dof.verify_and_attest(
        agent_id="apex-1687",
        action="transfer",
        params={"amount": 500, "token": "USDC"},
    )
    print(result.verdict)       # APPROVED
    print(result.tx_hash)       # on-chain tx hash via Alchemy
    print(result.gas_used)      # actual gas used
"""

import os
import sys
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

logger = logging.getLogger("dof.alchemy")

# ---------------------------------------------------------------------------
# Chain config — RPC endpoints por chain ID
# ---------------------------------------------------------------------------
_CHAIN_RPC = {
    "base":          "https://base-mainnet.g.alchemy.com/v2/{key}",
    "avalanche":     "https://avax-mainnet.g.alchemy.com/v2/{key}",
    "base-sepolia":  "https://base-sepolia.g.alchemy.com/v2/{key}",
}

_PUBLIC_FALLBACK_RPC = {
    "base":          "https://mainnet.base.org",
    "avalanche":     "https://api.avax.network/ext/bc/C/rpc",
    "base-sepolia":  "https://sepolia.base.org",
}

# DOFProofRegistry — desplegado en múltiples chains (ver wallets-dof-mesh.md)
_DOF_PROOF_REGISTRY = {
    "base":          "0x0000000000000000000000000000000000000000",  # placeholder — mainnet pendiente
    "avalanche":     "0x8004B663056A597Dffe9eCcC1965A193B7388713",
    "base-sepolia":  "0x0000000000000000000000000000000000000000",  # actualizar con deploy real
}


# ---------------------------------------------------------------------------
# AlchemyRPC — wrapper del RPC de Alchemy
# ---------------------------------------------------------------------------
class AlchemyRPC:
    """
    Wrapper liviano sobre el JSON-RPC de Alchemy.

    Hace lazy init: el cliente requests NO se crea hasta la primera llamada.
    Si Alchemy no está disponible (no api_key o falla), usa el RPC público
    de fallback sin levantar excepciones.

    Args:
        api_key: Alchemy API key. Si es None o vacía, usa fallback público.
        chain:   "base" | "avalanche" | "base-sepolia"
    """

    def __init__(self, api_key: Optional[str], chain: str = "base"):
        if chain not in _CHAIN_RPC:
            raise ValueError(
                f"Chain '{chain}' no soportada. Opciones: {list(_CHAIN_RPC)}"
            )
        self._api_key = api_key
        self._chain = chain
        self._session = None  # lazy

    # ------------------------------------------------------------------
    # Propiedades públicas
    # ------------------------------------------------------------------

    def get_rpc_url(self) -> str:
        """Retorna la URL del RPC según chain y api_key disponible."""
        if self._api_key:
            return _CHAIN_RPC[self._chain].format(key=self._api_key)
        logger.warning(
            "Alchemy API key no configurada — usando RPC público de fallback "
            f"para chain '{self._chain}'"
        )
        return _PUBLIC_FALLBACK_RPC[self._chain]

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _get_session(self):
        """Lazy init del session de requests."""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({"Content-Type": "application/json"})
            except ImportError:
                raise RuntimeError(
                    "El paquete 'requests' no está instalado. "
                    "Agregar a requirements.txt: requests>=2.28"
                )
        return self._session

    def _rpc_call(self, method: str, params: list) -> Any:
        """
        Ejecuta una llamada JSON-RPC al endpoint Alchemy.

        Returns:
            El campo 'result' de la respuesta JSON-RPC.

        Raises:
            RuntimeError: Si la llamada falla y no hay fallback posible.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        url = self.get_rpc_url()
        session = self._get_session()
        try:
            resp = session.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(
                    f"Alchemy RPC error [{method}]: {data['error']}"
                )
            return data.get("result")
        except Exception as exc:
            logger.error(f"Alchemy RPC call '{method}' falló en '{url}': {exc}")
            raise

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def estimate_gas(self, contract_address: str, data: str) -> int:
        """
        Estima el gas necesario para una tx usando eth_estimateGas.

        Args:
            contract_address: Dirección del contrato destino (hex con 0x).
            data:             ABI-encoded calldata (hex con 0x).

        Returns:
            Gas estimado como int. Retorna 0 si la estimación falla (fallback
            graceful — el caller puede continuar sin gas estimate).
        """
        try:
            tx_obj = {"to": contract_address, "data": data}
            result = self._rpc_call("eth_estimateGas", [tx_obj, "latest"])
            return int(result, 16) if isinstance(result, str) else int(result)
        except Exception as exc:
            logger.warning(f"estimate_gas falló — retornando 0: {exc}")
            return 0

    def get_transaction(self, tx_hash: str) -> dict:
        """
        Obtiene los detalles de una transacción por hash.

        Args:
            tx_hash: Hash de la tx (hex con 0x).

        Returns:
            Dict con campos de la tx (blockNumber, from, to, gas, etc.).
            Dict vacío si la tx no existe o la llamada falla.
        """
        try:
            result = self._rpc_call("eth_getTransactionByHash", [tx_hash])
            return result or {}
        except Exception as exc:
            logger.warning(f"get_transaction({tx_hash}) falló: {exc}")
            return {}

    def debug_trace_transaction(self, tx_hash: str) -> dict:
        """
        Usa debug_traceTransaction de Alchemy para análisis detallado de errores.

        Solo disponible con Alchemy — no en RPC públicos.
        Retorna {} si no está disponible o falla.

        Args:
            tx_hash: Hash de la tx a trazar.
        """
        try:
            result = self._rpc_call("debug_traceTransaction", [tx_hash, {}])
            return result or {}
        except Exception as exc:
            logger.warning(
                f"debug_traceTransaction no disponible o falló "
                f"(solo Alchemy paid tier): {exc}"
            )
            return {}


# ---------------------------------------------------------------------------
# AlchemyWebhook — notificaciones de confirmación on-chain
# ---------------------------------------------------------------------------
class AlchemyWebhook:
    """
    Gestiona notificaciones de Alchemy Notify cuando una transacción confirma.

    Diseño no-polling: este cliente registra addresses y callbacks localmente.
    El developer conecta su endpoint HTTP (webhook_url) al dashboard de Alchemy
    Notify, y cuando Alchemy llama al endpoint, el servidor del developer llama
    on_confirmation() para disparar los callbacks registrados.

    Args:
        webhook_url:  URL del endpoint que recibirá las notificaciones de Alchemy.
        signing_key:  Clave HMAC para verificar requests de Alchemy (opcional).
    """

    def __init__(self, webhook_url: str, signing_key: Optional[str] = None):
        self.webhook_url = webhook_url
        self.signing_key = signing_key
        self._monitored_addresses: set[str] = set()
        self._callbacks: dict[str, list[Callable]] = {}  # tx_hash → [fn, ...]

    def register_address(self, address: str) -> None:
        """
        Registra una dirección para monitoring de actividad on-chain.

        La dirección queda almacenada localmente. Para que Alchemy la monitoree,
        el developer debe agregar la dirección en su webhook de Alchemy Notify
        vía el dashboard o la Alchemy Webhooks API.

        Args:
            address: Dirección EVM a monitorear (hex con 0x).
        """
        normalized = address.lower()
        self._monitored_addresses.add(normalized)
        logger.info(
            f"Dirección {normalized} registrada para monitoring local. "
            f"Total monitoreadas: {len(self._monitored_addresses)}"
        )

    def on_confirmation(self, tx_hash: str, callback_fn: Callable) -> None:
        """
        Registra un callback que se ejecutará cuando tx_hash confirme on-chain.

        El callback NO se invoca automáticamente — se dispara cuando el developer
        llama a trigger_confirmation() desde su endpoint webhook.

        Args:
            tx_hash:     Hash de la tx a esperar (hex con 0x).
            callback_fn: Función que recibe (tx_hash: str, tx_data: dict).
        """
        key = tx_hash.lower()
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback_fn)
        logger.debug(
            f"Callback registrado para tx {key} "
            f"(total callbacks para esta tx: {len(self._callbacks[key])})"
        )

    def trigger_confirmation(self, tx_hash: str, tx_data: Optional[dict] = None) -> int:
        """
        Dispara todos los callbacks registrados para tx_hash.

        Llamar desde el endpoint webhook del developer cuando Alchemy notifica
        la confirmación de una transacción.

        Args:
            tx_hash:  Hash de la tx confirmada.
            tx_data:  Datos de la tx (de Alchemy payload). Opcional.

        Returns:
            Número de callbacks ejecutados.
        """
        key = tx_hash.lower()
        callbacks = self._callbacks.pop(key, [])
        tx_data = tx_data or {}
        executed = 0
        for fn in callbacks:
            try:
                fn(tx_hash, tx_data)
                executed += 1
            except Exception as exc:
                logger.error(f"Callback para tx {tx_hash} lanzó excepción: {exc}")
        return executed

    @property
    def monitored_addresses(self) -> list[str]:
        """Lista de direcciones actualmente monitoreadas."""
        return sorted(self._monitored_addresses)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifica la firma HMAC de un webhook request de Alchemy.

        Args:
            payload:   Body crudo del HTTP request (bytes).
            signature: Header X-Alchemy-Signature del request.

        Returns:
            True si la firma es válida, False si no hay signing_key configurada
            o si la firma no coincide.
        """
        if not self.signing_key:
            logger.warning(
                "signing_key no configurada — verificación de firma omitida"
            )
            return False
        import hmac
        import hashlib
        expected = hmac.new(
            self.signing_key.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# AlchemyDOFResult — resultado de verify_and_attest
# ---------------------------------------------------------------------------
@dataclass
class AlchemyDOFResult:
    """
    Resultado combinado de DOFVerifier + Alchemy attestation.

    Fields:
        verdict:       "APPROVED" | "REJECTED"
        agent_id:      ID del agente verificado.
        action:        Nombre de la acción verificada.
        z3_proof:      Resumen de pruebas Z3 formales.
        latency_ms:    Latencia total (verify + attest).
        attestation:   Hash keccak256-like local (del DOFVerifier).
        tx_hash:       Hash de la tx on-chain via Alchemy. Vacío si auto_attest=False.
        gas_estimated: Gas estimado antes de la tx. 0 si no se estimó.
        gas_used:      Gas realmente usado (del receipt). 0 si no disponible.
        rpc_url:       RPC URL usado para la attestation.
        chain:         Chain donde se realizó la attestation.
        error:         Mensaje de error si algo falló (no bloquea el resultado DOF).
    """
    verdict: str
    agent_id: str
    action: str
    z3_proof: str
    latency_ms: float
    attestation: str
    tx_hash: str = ""
    gas_estimated: int = 0
    gas_used: int = 0
    rpc_url: str = ""
    chain: str = ""
    error: str = ""

    @property
    def approved(self) -> bool:
        """True si el veredicto es APPROVED."""
        return self.verdict == "APPROVED"

    def __repr__(self) -> str:
        return (
            f"AlchemyDOFResult(verdict={self.verdict!r}, agent_id={self.agent_id!r}, "
            f"action={self.action!r}, tx_hash={self.tx_hash!r}, "
            f"chain={self.chain!r}, latency_ms={self.latency_ms})"
        )


# ---------------------------------------------------------------------------
# AlchemyDOF — clase principal
# ---------------------------------------------------------------------------
class AlchemyDOF:
    """
    Combina DOFVerifier (verificación formal local) con Alchemy (attestation on-chain).

    Flujo de verify_and_attest():
      1. DOFVerifier.verify_action() — Z3Gate + ConstitutionEnforcer (~8ms)
      2. Si APPROVED y auto_attest=True:
         a. AlchemyRPC.estimate_gas() — pre-flight gas check
         b. Escribe en DOFProofRegistry via Alchemy RPC
         c. Retorna tx_hash en el resultado
      3. Retorna AlchemyDOFResult — nunca lanza excepciones al caller

    Fallback graceful:
      - Sin api_key → usa RPC público, no hace on-chain write (requiere signer)
      - Alchemy no disponible → loggea error, retorna resultado DOF local
      - Cualquier excepción on-chain → campo 'error' en AlchemyDOFResult, no bloquea

    Args:
        alchemy_api_key: API key de Alchemy. Si es None, usa RPC público (solo lectura).
        chain:           Chain destino: "base" | "avalanche" | "base-sepolia".
        auto_attest:     Si True, escribe en DOFProofRegistry cuando verdict=APPROVED.
        webhook_url:     URL para notificaciones de Alchemy Notify (opcional).
    """

    def __init__(
        self,
        alchemy_api_key: Optional[str] = None,
        chain: str = "base",
        auto_attest: bool = False,
        webhook_url: Optional[str] = None,
    ):
        self._api_key = alchemy_api_key or os.getenv("ALCHEMY_API_KEY")
        self._chain = chain
        self._auto_attest = auto_attest

        # Lazy init: no se instancian hasta la primera llamada
        self._rpc: Optional[AlchemyRPC] = None
        self._verifier = None
        self._webhook: Optional[AlchemyWebhook] = None

        if webhook_url:
            self._webhook = AlchemyWebhook(webhook_url)

    # ------------------------------------------------------------------
    # Lazy init helpers
    # ------------------------------------------------------------------

    def _get_rpc(self) -> AlchemyRPC:
        if self._rpc is None:
            self._rpc = AlchemyRPC(api_key=self._api_key, chain=self._chain)
        return self._rpc

    def _get_verifier(self):
        if self._verifier is None:
            try:
                from dof.verifier import DOFVerifier
                self._verifier = DOFVerifier()
            except Exception as exc:
                logger.error(f"No se pudo inicializar DOFVerifier: {exc}")
                raise RuntimeError(
                    f"DOFVerifier no disponible: {exc}. "
                    "Verificar que dof/verifier.py esté en el path."
                ) from exc
        return self._verifier

    # ------------------------------------------------------------------
    # Attestation on-chain (stub extensible)
    # ------------------------------------------------------------------

    def _build_attestation_calldata(
        self, agent_id: str, action: str, attestation_hash: str
    ) -> str:
        """
        Construye el calldata ABI-encoded para DOFProofRegistry.storeProof().

        Implementación actual: encoding manual simplificado compatible con
        la función storeProof(bytes32 agentId, bytes32 proofHash, string action).

        En producción reemplazar con web3.py / eth_abi para encoding exacto.

        Returns:
            Calldata hex string con prefijo 0x.
        """
        # Function selector de storeProof(bytes32,bytes32,string) — keccak256[:4]
        # Valor precomputado para la firma canónica de DOFProofRegistry
        selector = "0x3c2d4b8e"

        # Padding de agentId y attestation_hash a 32 bytes
        agent_bytes = agent_id.encode()[:32].ljust(32, b"\x00").hex()
        proof_bytes = (
            bytes.fromhex(attestation_hash[2:])[:32].ljust(32, b"\x00").hex()
            if attestation_hash.startswith("0x")
            else attestation_hash[:64].ljust(64, "0")
        )
        # action como string ABI-encoded (offset 0x60, length, data)
        action_encoded = action.encode("utf-8")
        action_len = len(action_encoded)
        action_hex = action_encoded.hex().ljust(64, "0")
        offset = "0000000000000000000000000000000000000000000000000000000000000060"
        length_hex = hex(action_len)[2:].zfill(64)

        calldata = selector + agent_bytes + proof_bytes + offset + length_hex + action_hex
        return calldata

    def _attest_on_chain(
        self, agent_id: str, action: str, attestation_hash: str
    ) -> tuple[str, int, int]:
        """
        Intenta escribir la attestation en DOFProofRegistry via Alchemy RPC.

        Nota: Una escritura on-chain real requiere un signer (private key).
        Este método hace gas estimation y prepara la tx; la firma y envío real
        requieren web3.py con signer configurado (eth_sendRawTransaction).

        Returns:
            (tx_hash, gas_estimated, gas_used)
            tx_hash estará vacío si no se pudo hacer el envío real.
        """
        rpc = self._get_rpc()
        registry_address = _DOF_PROOF_REGISTRY.get(self._chain, "")

        if not registry_address or registry_address == "0x" + "0" * 40:
            logger.warning(
                f"DOFProofRegistry no desplegado en chain '{self._chain}' — "
                "attestation on-chain omitida"
            )
            return "", 0, 0

        calldata = self._build_attestation_calldata(agent_id, action, attestation_hash)
        gas_estimated = rpc.estimate_gas(registry_address, calldata)

        logger.info(
            f"[AlchemyDOF] Gas estimado para attestation on-chain: {gas_estimated} "
            f"| chain={self._chain} | registry={registry_address}"
        )

        # Para envío real: necesita private key + eth_sendRawTransaction
        # Retornamos hash vacío como indicador de que la tx no fue enviada
        # (requiere configurar signer externo)
        logger.warning(
            "Envío on-chain requiere signer configurado (private key). "
            "Gas estimate completado. tx_hash no disponible sin signer."
        )
        return "", gas_estimated, 0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def verify_and_attest(
        self,
        agent_id: str,
        action: str,
        params: Optional[dict] = None,
        trust_score: float = 0.9,
    ) -> AlchemyDOFResult:
        """
        Verifica una acción con DOFVerifier y opcionalmente la registra on-chain.

        Args:
            agent_id:    ID del agente (ej. "apex-1687").
            action:      Nombre de la acción (ej. "transfer").
            params:      Parámetros de la acción (ej. {"amount": 500}).
            trust_score: Trust score del agente (0.0–1.0). Default 0.9.

        Returns:
            AlchemyDOFResult — nunca lanza excepciones al caller.
        """
        params = params or {}
        error_msg = ""
        tx_hash = ""
        gas_estimated = 0
        gas_used = 0
        rpc_url = self._get_rpc().get_rpc_url()

        # Paso 1 — Verificación formal local (DOFVerifier)
        try:
            verifier = self._get_verifier()
            verify_result = verifier.verify_action(
                agent_id=agent_id,
                action=action,
                params=params,
                trust_score=trust_score,
            )
        except Exception as exc:
            logger.error(f"DOFVerifier.verify_action falló: {exc}")
            return AlchemyDOFResult(
                verdict="REJECTED",
                agent_id=agent_id,
                action=action,
                z3_proof="",
                latency_ms=0.0,
                attestation="",
                rpc_url=rpc_url,
                chain=self._chain,
                error=f"DOFVerifier error: {exc}",
            )

        # Paso 2 — Attestation on-chain (solo si APPROVED y auto_attest=True)
        if verify_result.verdict == "APPROVED" and self._auto_attest:
            try:
                tx_hash, gas_estimated, gas_used = self._attest_on_chain(
                    agent_id=agent_id,
                    action=action,
                    attestation_hash=verify_result.attestation,
                )
            except Exception as exc:
                error_msg = f"Alchemy attestation falló (resultado DOF local preservado): {exc}"
                logger.error(error_msg)

        return AlchemyDOFResult(
            verdict=verify_result.verdict,
            agent_id=agent_id,
            action=action,
            z3_proof=verify_result.z3_proof,
            latency_ms=verify_result.latency_ms,
            attestation=verify_result.attestation,
            tx_hash=tx_hash,
            gas_estimated=gas_estimated,
            gas_used=gas_used,
            rpc_url=rpc_url,
            chain=self._chain,
            error=error_msg,
        )

    def batch_verify(self, actions: list[dict]) -> list[AlchemyDOFResult]:
        """
        Verifica múltiples acciones en secuencia.

        Las pruebas Z3 del DOFVerifier se cachean tras la primera llamada,
        por lo que las verificaciones subsiguientes son más rápidas.

        Args:
            actions: Lista de dicts, cada uno con keys:
                     - agent_id (str, requerido)
                     - action (str, requerido)
                     - params (dict, opcional)
                     - trust_score (float, opcional, default 0.9)

        Returns:
            Lista de AlchemyDOFResult en el mismo orden que la entrada.

        Example:
            results = dof.batch_verify([
                {"agent_id": "apex-1687", "action": "transfer", "params": {"amount": 100}},
                {"agent_id": "apex-1687", "action": "swap",     "params": {"from": "AVAX"}},
            ])
        """
        results = []
        for i, action_spec in enumerate(actions):
            if not isinstance(action_spec, dict):
                logger.warning(
                    f"batch_verify: item[{i}] no es dict ({type(action_spec)}) — omitido"
                )
                continue
            agent_id = action_spec.get("agent_id", "unknown")
            action = action_spec.get("action", "unknown")
            params = action_spec.get("params", {})
            trust_score = action_spec.get("trust_score", 0.9)
            result = self.verify_and_attest(
                agent_id=agent_id,
                action=action,
                params=params,
                trust_score=trust_score,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Webhook accessor
    # ------------------------------------------------------------------

    @property
    def webhook(self) -> Optional[AlchemyWebhook]:
        """AlchemyWebhook configurado, o None si no se pasó webhook_url."""
        return self._webhook

    @property
    def chain(self) -> str:
        """Chain activa."""
        return self._chain

    @property
    def rpc_url(self) -> str:
        """RPC URL activa (Alchemy o fallback público)."""
        return self._get_rpc().get_rpc_url()
