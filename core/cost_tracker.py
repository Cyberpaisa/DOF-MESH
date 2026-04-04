"""
core/cost_tracker.py
────────────────────
Trazabilidad de consumo de tokens y costo por sesión del DaemonAutonomous.

Problema: sin esta capa es imposible saber qué roles consumen más presupuesto
ni detectar providers que se salen de los límites de costo.

Uso básico:
    from core.cost_tracker import CostTracker

    tracker = CostTracker(session_id="abc-123")
    tracker.record(
        role="architect",
        model="deepseek/deepseek-chat",
        prompt_tokens=1200,
        completion_tokens=400,
    )
    print(tracker.total_cost_usd())   # → 0.000764
    print(tracker.summary_dict())

Con persistencia JSONL (audit trail):
    tracker = CostTracker(
        session_id="abc-123",
        persist_path="logs/daemon/costs.jsonl",
    )

Sigue el patrón singleton DOF: tiene reset() para aislamiento entre tests.
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("dof.cost_tracker")

# ─────────────────────────────────────────────────────────────────────────────
# Tabla de precios — USD por 1M tokens (input / output)
# ─────────────────────────────────────────────────────────────────────────────

PRICE_TABLE: Dict[str, Dict[str, float]] = {
    "deepseek/deepseek-chat":         {"input": 0.27,  "output": 1.10},
    "deepseek/deepseek-reasoner":     {"input": 0.55,  "output": 2.19},
    "groq/llama-3.3-70b-versatile":   {"input": 0.59,  "output": 0.79},
    "groq/llama-3.3-70b":             {"input": 0.59,  "output": 0.79},
    "nvidia_nim/qwen3.5-397b":        {"input": 0.00,  "output": 0.00},
    "nvidia_nim/kimi-k2.5":           {"input": 0.00,  "output": 0.00},
    "cerebras/llama3.1-8b":           {"input": 0.10,  "output": 0.10},
    "cerebras/llama3.1-70b":          {"input": 0.60,  "output": 0.60},
    "minimax/minimax-m2.1":           {"input": 0.30,  "output": 1.10},
    "openrouter/nousresearch/hermes-3-llama-3.1-405b": {"input": 0.80, "output": 0.80},
    # Mocks — costo cero para tests
    "mock/model":                     {"input": 0.00,  "output": 0.00},
    "mock/patched":                   {"input": 0.00,  "output": 0.00},
    "mock/success":                   {"input": 0.00,  "output": 0.00},
    "mock/rate-limit":                {"input": 0.00,  "output": 0.00},
    "mock/auth-error":                {"input": 0.00,  "output": 0.00},
    "mock/timeout":                   {"input": 0.00,  "output": 0.00},
    # Fallback para modelos no listados
    "_default":                       {"input": 1.00,  "output": 3.00},
}


# ─────────────────────────────────────────────────────────────────────────────
# CallRecord — un registro por llamada LLM
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CallRecord:
    """
    Registro de una llamada LLM individual.

    Campos:
        timestamp:          Tiempo UNIX de la llamada
        role:               Rol del agente ("architect", "researcher", ...)
        model:              ID del modelo ("deepseek/deepseek-chat", ...)
        prompt_tokens:      Tokens de entrada
        completion_tokens:  Tokens de salida
        cost_usd:           Costo calculado en el momento del registro
    """
    timestamp: float
    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict:
        """Serializa a dict JSON-compatible."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CallRecord":
        """
        Deserializa desde dict.

        Raises:
            KeyError:   si faltan campos obligatorios.
            TypeError:  si los tipos son incompatibles.
        """
        return cls(
            timestamp=float(d["timestamp"]),
            role=str(d["role"]),
            model=str(d["model"]),
            prompt_tokens=int(d["prompt_tokens"]),
            completion_tokens=int(d["completion_tokens"]),
            cost_usd=float(d["cost_usd"]),
        )

    def __repr__(self) -> str:
        return (
            f"CallRecord(role={self.role!r}, model={self.model!r}, "
            f"tokens={self.total_tokens}, cost=${self.cost_usd:.6f})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RoleSummary — agregado por rol
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RoleSummary:
    """
    Resumen de consumo para un rol específico.

    Se construye on-the-fly desde CostTracker.by_role().
    """
    role: str
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "total_calls": self.total_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }

    def __repr__(self) -> str:
        return (
            f"RoleSummary(role={self.role!r}, calls={self.total_calls}, "
            f"tokens={self.total_tokens}, cost=${self.total_cost_usd:.6f})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CostTracker — acumula, calcula, persiste
# ─────────────────────────────────────────────────────────────────────────────

class CostTracker:
    """
    Acumula registros de llamadas LLM y expone resúmenes de costo.

    Thread-safety: las operaciones de lista en CPython son thread-safe para
    append (GIL garantiza atomicidad de append). Para escenarios con alto
    paralelismo, la escritura JSONL usa open/append que es segura por O_APPEND.

    Sigue el patrón singleton DOF: tiene reset() para aislamiento entre tests.
    """

    def __init__(
        self,
        session_id: str = "",
        price_table: Optional[Dict[str, Dict[str, float]]] = None,
        persist_path: Optional[str] = None,
    ) -> None:
        self._session_id = session_id
        self._price_table = price_table if price_table is not None else PRICE_TABLE
        self._persist_path = persist_path
        self._records: List[CallRecord] = []
        logger.debug(
            "CostTracker init: session=%s persist=%s",
            session_id or "(none)",
            persist_path or "(none)",
        )

    # ── Registro ─────────────────────────────────────────────────────────────

    def record(
        self,
        role: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CallRecord:
        """
        Registra una llamada LLM y calcula su costo.

        Si persist_path está configurado, hace append a JSONL (una línea).
        El directorio se crea automáticamente si no existe.

        Returns:
            CallRecord con cost_usd ya calculado.
        """
        cost = self.calculate_cost(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            price_table=self._price_table,
        )
        rec = CallRecord(
            timestamp=time.time(),
            role=role,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )
        self._records.append(rec)
        logger.debug(
            "CostTracker.record: role=%s model=%s tokens=%d cost=$%.6f",
            role, model, rec.total_tokens, cost,
        )
        if self._persist_path:
            self._append_jsonl(rec)
        return rec

    # ── Consultas ─────────────────────────────────────────────────────────────

    def total_cost_usd(self) -> float:
        """Costo total acumulado de todas las llamadas."""
        return sum(r.cost_usd for r in self._records)

    def total_calls(self) -> int:
        """Número total de llamadas registradas."""
        return len(self._records)

    def total_tokens(self) -> int:
        """Total de tokens (prompt + completion) de todas las llamadas."""
        return sum(r.total_tokens for r in self._records)

    def by_role(self) -> Dict[str, RoleSummary]:
        """
        Resumen por rol.

        Returns:
            Dict {role: RoleSummary} — vacío si no hay registros.
        """
        summaries: Dict[str, RoleSummary] = {}
        for rec in self._records:
            if rec.role not in summaries:
                summaries[rec.role] = RoleSummary(
                    role=rec.role,
                    total_calls=0,
                    total_prompt_tokens=0,
                    total_completion_tokens=0,
                    total_cost_usd=0.0,
                )
            s = summaries[rec.role]
            s.total_calls += 1
            s.total_prompt_tokens += rec.prompt_tokens
            s.total_completion_tokens += rec.completion_tokens
            s.total_cost_usd += rec.cost_usd
        return summaries

    def most_expensive_role(self) -> Optional[str]:
        """
        Rol con mayor costo total acumulado.

        Returns:
            Nombre del rol, o None si no hay registros.
        """
        summaries = self.by_role()
        if not summaries:
            return None
        return max(summaries, key=lambda role: summaries[role].total_cost_usd)

    def summary_dict(self) -> dict:
        """
        Dict JSON-serializable con resumen completo de la sesión.

        Estructura:
            {
              "session_id": "...",
              "total_calls": N,
              "total_cost_usd": X.XXXXXX,
              "total_tokens": N,
              "by_role": { role: RoleSummary.to_dict(), ... }
            }
        """
        return {
            "session_id": self._session_id,
            "total_calls": self.total_calls(),
            "total_cost_usd": round(self.total_cost_usd(), 6),
            "total_tokens": self.total_tokens(),
            "by_role": {
                role: summary.to_dict()
                for role, summary in self.by_role().items()
            },
        }

    # ── Utilitarios ───────────────────────────────────────────────────────────

    def reset(self) -> None:
        """
        Limpia registros en memoria. No toca el archivo JSONL en disco.

        Requerido por el patrón singleton DOF para aislamiento entre tests.
        """
        self._records.clear()
        logger.debug("CostTracker.reset: session=%s", self._session_id or "(none)")

    @staticmethod
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        price_table: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> float:
        """
        Calcula costo en USD para una llamada.

        Usa la entrada "_default" del price_table si el modelo no está listado.
        Nunca lanza excepción — retorna 0.0 en caso de error de configuración.

        Args:
            model:              ID del modelo (ej. "deepseek/deepseek-chat")
            prompt_tokens:      Tokens de entrada
            completion_tokens:  Tokens de salida
            price_table:        Tabla de precios (default: PRICE_TABLE global)

        Returns:
            Costo en USD como float.
        """
        if price_table is None:
            price_table = PRICE_TABLE

        prices = price_table.get(model) or price_table.get("_default", {})
        input_price = prices.get("input", 0.0)
        output_price = prices.get("output", 0.0)

        cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
        return round(cost, 8)

    # ── Internos ──────────────────────────────────────────────────────────────

    def _append_jsonl(self, rec: CallRecord) -> None:
        """Append atómico de una línea JSON al archivo de persistencia."""
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            line = json.dumps(rec.to_dict(), separators=(",", ":"))
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.error("CostTracker._append_jsonl: failed — %s", exc)

    def __repr__(self) -> str:
        return (
            f"CostTracker(session={self._session_id!r}, "
            f"calls={self.total_calls()}, "
            f"cost=${self.total_cost_usd():.6f})"
        )
