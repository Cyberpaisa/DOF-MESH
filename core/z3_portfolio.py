from __future__ import annotations
"""
Z3 Portfolio Solving — Múltiples estrategias Z3 con short-circuit.

Prueba múltiples configuraciones del solver Z3 secuencialmente (Z3 no es
thread-safe), toma el primer resultado válido (sat/unsat) y corta.
Cada estrategia tiene su propio timeout individual.

Estrategias:
  - default: Z3 Solver estándar
  - optimize: Z3 Optimize (con optimización)
  - qf_lia: SolverFor QF_LIA (aritmética lineal entera sin cuantificadores)
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable

import z3

logger = logging.getLogger("core.z3_portfolio")


class SolveStrategy(str, Enum):
    DEFAULT = "default"
    OPTIMIZE = "optimize"
    QF_LIA = "qf_lia"


@dataclass(frozen=True)
class PortfolioResult:
    result: str  # "sat", "unsat", "unknown"
    strategy_used: SolveStrategy
    solve_time_ms: float
    strategies_tried: int


class Z3PortfolioSolver:
    """
    Solver portfolio: lanza múltiples estrategias Z3 en paralelo.

    Uso:
        solver = Z3PortfolioSolver(timeout_ms=500)
        x = z3.Int("x")
        constraints = [x > 0, x < 10]
        result = solver.solve(constraints)
        print(result.result)  # "sat"
        print(result.strategy_used)  # la estrategia que ganó
    """

    def __init__(self, timeout_ms: int = 500, strategies: Optional[List[SolveStrategy]] = None):
        self.timeout_ms = timeout_ms
        self.strategies = strategies or [
            SolveStrategy.DEFAULT,
            SolveStrategy.QF_LIA,
        ]
        self._solve_count: int = 0
        self._strategy_wins: dict[SolveStrategy, int] = {s: 0 for s in SolveStrategy}

    def _run_strategy(self, strategy: SolveStrategy, constraints: list) -> tuple[str, SolveStrategy]:
        """Ejecuta una estrategia Z3 individual."""
        try:
            if strategy == SolveStrategy.DEFAULT:
                solver = z3.Solver()
            elif strategy == SolveStrategy.OPTIMIZE:
                solver = z3.Optimize()
            elif strategy == SolveStrategy.QF_LIA:
                solver = z3.SolverFor("QF_LIA")
            else:
                solver = z3.Solver()

            solver.set("timeout", self.timeout_ms)
            for c in constraints:
                solver.add(c)

            result = solver.check()
            result_str = "sat" if result == z3.sat else ("unsat" if result == z3.unsat else "unknown")
            return result_str, strategy
        except Exception as e:
            logger.warning(f"[Portfolio] Strategy {strategy.value} failed: {e}")
            return "unknown", strategy

    def solve(self, constraints: list) -> PortfolioResult:
        """
        Prueba estrategias en secuencia, retorna primer resultado válido (sat/unsat).

        Nota: Z3 no es thread-safe, así que ejecutamos estrategias secuencialmente
        con short-circuit al primer resultado definitivo. Cada estrategia tiene su
        propio timeout, así que la latencia total está acotada.
        """
        start = time.time()
        self._solve_count += 1

        if not constraints:
            return PortfolioResult(
                result="sat",
                strategy_used=SolveStrategy.DEFAULT,
                solve_time_ms=0.0,
                strategies_tried=0,
            )

        best_result = "unknown"
        best_strategy = self.strategies[0]
        strategies_tried = 0

        for strategy in self.strategies:
            strategies_tried += 1
            result_str, strat = self._run_strategy(strategy, constraints)
            if result_str in ("sat", "unsat"):
                best_result = result_str
                best_strategy = strat
                self._strategy_wins[strat] += 1
                break

        elapsed = (time.time() - start) * 1000
        return PortfolioResult(
            result=best_result,
            strategy_used=best_strategy,
            solve_time_ms=round(elapsed, 2),
            strategies_tried=strategies_tried,
        )

    @property
    def solve_count(self) -> int:
        return self._solve_count

    def strategy_stats(self) -> dict[str, int]:
        return {s.value: self._strategy_wins[s] for s in self._strategy_wins}
