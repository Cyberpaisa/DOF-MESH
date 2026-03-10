"""
Regression Tracker — Detects improvements and regressions across DOF subsystems.

Tracks 5 dimensions after every change:
1. Z3 Invariants: 8 invariants timing + status
2. Z3 Hierarchy: 42 patterns timing + status
3. Test Suite: pass/fail count + new failures
4. Garak Benchmark: detection rate per category (if results exist)
5. LLM Routing: provider failure rates, distribution, latency

Usage:
    tracker = RegressionTracker()
    tracker.capture_baseline()     # Save current state as baseline
    # ... make changes ...
    report = tracker.compare()     # Compare current vs baseline
    report.has_regressions         # True if anything got worse
    report.summary()               # Human-readable summary

Persistence:
    Baselines saved to logs/regression_baselines.json
    Reports saved to logs/regression_reports.jsonl (append)

Each baseline/report is timestamped and tagged with git commit hash
(if available) for traceability.
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChangeType(Enum):
    IMPROVED = "improved"
    STABLE = "stable"
    REGRESSED = "regressed"
    NEW = "new"
    REMOVED = "removed"


@dataclass
class SubsystemResult:
    name: str
    change: ChangeType
    baseline_value: str
    current_value: str
    delta: str
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "change": self.change.value,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "delta": self.delta,
            "details": self.details,
        }


@dataclass
class RegressionReport:
    timestamp: str
    git_commit: str
    baseline_commit: str
    dof_version: str
    subsystems: list
    has_regressions: bool
    regression_count: int
    improvement_count: int
    stable_count: int
    elapsed_ms: float

    def summary(self) -> str:
        lines = []
        lines.append(f"DOF Regression Check — {self.git_commit} vs {self.baseline_commit}")
        lines.append("")
        lines.append(f"  {'Subsystem':<18}  {'Baseline':<22}  {'Current':<22}  {'Change':<10}")
        lines.append(f"  {'─' * 18}  {'─' * 22}  {'─' * 22}  {'─' * 10}")
        for s in self.subsystems:
            change_str = s.change.value.upper()
            lines.append(
                f"  {s.name:<18}  {s.baseline_value:<22}  {s.current_value:<22}  {change_str:<10}"
            )
        lines.append(f"  {'─' * 18}  {'─' * 22}  {'─' * 22}  {'─' * 10}")
        lines.append("")

        if self.has_regressions:
            lines.append(
                f"  Result: REGRESSIONS DETECTED "
                f"({self.regression_count} regressed, "
                f"{self.improvement_count} improved, "
                f"{self.stable_count} stable)"
            )
        else:
            lines.append(
                f"  Result: NO REGRESSIONS "
                f"({self.regression_count} regressed, "
                f"{self.improvement_count} improved, "
                f"{self.stable_count} stable)"
            )
        lines.append(f"  Elapsed: {self.elapsed_ms:.0f}ms")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "baseline_commit": self.baseline_commit,
            "dof_version": self.dof_version,
            "subsystems": [s.to_dict() for s in self.subsystems],
            "has_regressions": self.has_regressions,
            "regression_count": self.regression_count,
            "improvement_count": self.improvement_count,
            "stable_count": self.stable_count,
            "elapsed_ms": self.elapsed_ms,
        }


class RegressionTracker:
    """
    Tracks DOF subsystem health across changes.

    Methods:
    - capture_baseline() -> saves current state of all subsystems
    - compare() -> runs all subsystems and compares vs baseline
    - get_history(n=10) -> last N regression reports
    - get_trend(subsystem, n=20) -> values over time for one subsystem
    """

    BASELINE_FILE = "logs/regression_baselines.json"
    REPORTS_FILE = "logs/regression_reports.jsonl"

    def __init__(self, baseline_file: str = None, reports_file: str = None):
        if baseline_file:
            self.BASELINE_FILE = baseline_file
        if reports_file:
            self.REPORTS_FILE = reports_file

    def _get_git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _measure_z3_invariants(self) -> dict:
        """Run TransitionVerifier.verify_all() and capture results."""
        try:
            from core.transitions import TransitionVerifier
            verifier = TransitionVerifier()
            start = time.time()
            results = verifier.verify_all()
            elapsed = (time.time() - start) * 1000

            return {
                "invariants": {
                    inv_id: {
                        "status": r.status,
                        "time_ms": round(r.verification_time_ms, 2),
                    }
                    for inv_id, r in results.items()
                },
                "total_time_ms": round(elapsed, 2),
                "proven_count": sum(1 for r in results.values() if r.status == "PROVEN"),
                "total_count": len(results),
            }
        except ImportError:
            return {"proven_count": 0, "total_count": 0, "total_time_ms": 0,
                    "invariants": {}, "error": "z3-solver not installed"}

    def _measure_hierarchy(self) -> dict:
        """Run HierarchyZ3.verify_hierarchy_inviolable() and capture results."""
        try:
            from core.hierarchy_z3 import HierarchyZ3
            h = HierarchyZ3()
            start = time.time()
            result = h.verify_hierarchy_inviolable()
            elapsed = (time.time() - start) * 1000

            return {
                "status": result.status,
                "time_ms": round(elapsed, 2),
                "patterns_checked": result.patterns_checked,
                "categories_checked": result.categories_checked,
            }
        except ImportError:
            return {"status": "UNAVAILABLE", "time_ms": 0,
                    "patterns_checked": 0, "categories_checked": 0,
                    "error": "z3-solver not installed"}

    def _measure_tests(self) -> dict:
        """Run unittest discover and capture pass/fail counts."""
        try:
            result = subprocess.run(
                ["python3", "-m", "unittest", "discover", "tests/", "-v"],
                capture_output=True, text=True, timeout=300
            )
            output = result.stderr

            total = 0
            failures = 0
            errors = 0

            for line in output.split("\n"):
                if line.startswith("Ran "):
                    match = re.search(r"Ran (\d+) test", line)
                    if match:
                        total = int(match.group(1))
                if "FAILED" in line:
                    f = re.search(r"failures=(\d+)", line)
                    e = re.search(r"errors=(\d+)", line)
                    failures = int(f.group(1)) if f else 0
                    errors = int(e.group(1)) if e else 0

            return {
                "total": total,
                "passed": total - failures - errors,
                "failures": failures,
                "errors": errors,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"total": 0, "passed": 0, "failures": 0, "errors": 0,
                    "error": str(e)}

    def _measure_garak(self) -> dict:
        """Read latest Garak benchmark results if they exist."""
        garak_file = "tests/external/garak_benchmark_results.json"
        if not os.path.exists(garak_file):
            return {"available": False}

        with open(garak_file) as f:
            data = json.load(f)

        return {
            "available": True,
            "overall_detection_rate": data.get("summary", {}).get("overall_detection_rate", 0),
            "total_payloads": data.get("summary", {}).get("total_payloads", 0),
            "categories": {
                cat: info.get("detection_rate", 0)
                for cat, info in data.get("categories", {}).items()
            },
        }

    def _measure_llm_routing(self) -> dict:
        """Read LLM routing metrics from llm_config."""
        try:
            from llm_config import get_routing_stats, _circuit_breaker, _CIRCUIT_BREAKER_WINDOW_S
            stats = get_routing_stats()
            # Also capture Thompson Sampling state if available
            try:
                from core.providers import BayesianProviderSelector
                selector = BayesianProviderSelector._instance if hasattr(BayesianProviderSelector, '_instance') else None
                if selector:
                    ts_state = selector.get_status()
                else:
                    ts_state = {}
            except (ImportError, AttributeError):
                ts_state = {}

            return {
                "available": True,
                "total_decisions": stats.get("total_decisions", 0),
                "provider_distribution": stats.get("provider_distribution", {}),
                "provider_failure_rate": stats.get("provider_failure_rate", {}),
                "avg_latency_ms": stats.get("avg_latency_ms", {}),
                "thompson_sampling_state": ts_state,
            }
        except ImportError:
            return {"available": False}

    def _measure_all(self) -> dict:
        """Measure all 5 subsystems and return snapshot."""
        return {
            "timestamp": datetime.now().isoformat(),
            "git_commit": self._get_git_commit(),
            "z3_invariants": self._measure_z3_invariants(),
            "z3_hierarchy": self._measure_hierarchy(),
            "tests": self._measure_tests(),
            "garak": self._measure_garak(),
            "llm_routing": self._measure_llm_routing(),
        }

    def capture_baseline(self) -> dict:
        """Measure all subsystems and save as baseline."""
        baseline = self._measure_all()

        os.makedirs(os.path.dirname(self.BASELINE_FILE), exist_ok=True)
        with open(self.BASELINE_FILE, "w") as f:
            json.dump(baseline, f, indent=2, default=str)

        return baseline

    def load_baseline(self) -> dict:
        """Load saved baseline from disk."""
        if not os.path.exists(self.BASELINE_FILE):
            raise FileNotFoundError(
                f"No baseline found at {self.BASELINE_FILE}. "
                "Run capture_baseline() first."
            )
        with open(self.BASELINE_FILE) as f:
            return json.load(f)

    def compare(self) -> RegressionReport:
        """Measure all subsystems and compare vs saved baseline."""
        baseline = self.load_baseline()

        start = time.time()
        current = self._measure_all()
        elapsed = (time.time() - start) * 1000

        subsystems = []

        # --- Z3 Invariants ---
        base_proven = baseline["z3_invariants"]["proven_count"]
        base_total = baseline["z3_invariants"]["total_count"]
        curr_proven = current["z3_invariants"]["proven_count"]
        curr_total = current["z3_invariants"]["total_count"]

        if curr_proven > base_proven:
            change = ChangeType.IMPROVED
        elif curr_proven < base_proven:
            change = ChangeType.REGRESSED
        else:
            change = ChangeType.STABLE

        subsystems.append(SubsystemResult(
            name="z3_invariants",
            change=change,
            baseline_value=f"{base_proven}/{base_total} PROVEN",
            current_value=f"{curr_proven}/{curr_total} PROVEN",
            delta=f"{curr_proven - base_proven:+d} invariants",
        ))

        # --- Z3 Hierarchy ---
        base_status = baseline["z3_hierarchy"]["status"]
        curr_status = current["z3_hierarchy"]["status"]

        if base_status == "PROVEN" and curr_status != "PROVEN":
            change = ChangeType.REGRESSED
        elif base_status != "PROVEN" and curr_status == "PROVEN":
            change = ChangeType.IMPROVED
        else:
            change = ChangeType.STABLE

        subsystems.append(SubsystemResult(
            name="z3_hierarchy",
            change=change,
            baseline_value=base_status,
            current_value=curr_status,
            delta="no change" if change == ChangeType.STABLE else f"{base_status} -> {curr_status}",
        ))

        # --- Test Suite ---
        base_passed = baseline["tests"]["passed"]
        curr_passed = current["tests"]["passed"]
        base_failures = baseline["tests"]["failures"]
        curr_failures = current["tests"]["failures"]

        if curr_passed > base_passed and curr_failures <= base_failures:
            change = ChangeType.IMPROVED
        elif curr_passed < base_passed or curr_failures > base_failures:
            change = ChangeType.REGRESSED
        else:
            change = ChangeType.STABLE

        subsystems.append(SubsystemResult(
            name="test_suite",
            change=change,
            baseline_value=f"{base_passed} passed, {base_failures} failed",
            current_value=f"{curr_passed} passed, {curr_failures} failed",
            delta=f"{curr_passed - base_passed:+d} passed, {curr_failures - base_failures:+d} failed",
        ))

        # --- Garak Benchmark ---
        base_garak = baseline.get("garak", {})
        curr_garak = current.get("garak", {})

        if base_garak.get("available") and curr_garak.get("available"):
            base_dr = base_garak["overall_detection_rate"]
            curr_dr = curr_garak["overall_detection_rate"]

            if curr_dr > base_dr + 2:
                change = ChangeType.IMPROVED
            elif curr_dr < base_dr - 2:
                change = ChangeType.REGRESSED
            else:
                change = ChangeType.STABLE

            subsystems.append(SubsystemResult(
                name="garak_benchmark",
                change=change,
                baseline_value=f"{base_dr}%",
                current_value=f"{curr_dr}%",
                delta=f"{curr_dr - base_dr:+.1f}pp",
            ))
        elif curr_garak.get("available") and not base_garak.get("available"):
            subsystems.append(SubsystemResult(
                name="garak_benchmark",
                change=ChangeType.NEW,
                baseline_value="N/A",
                current_value=f"{curr_garak['overall_detection_rate']}%",
                delta="new",
            ))

        # --- LLM Routing ---
        curr_routing = current.get("llm_routing", {})
        base_routing = baseline.get("llm_routing", {})

        if curr_routing.get("available"):
            failure_rates = curr_routing.get("provider_failure_rate", {})
            max_failure = max(failure_rates.values()) if failure_rates else 0
            dist = curr_routing.get("provider_distribution", {})
            max_conc = max(dist.values()) if dist else 0

            details_parts = []
            if max_failure > 15:
                change = ChangeType.REGRESSED
                details_parts.append(f"failure_rate {max_failure}% > 15% threshold")
            elif base_routing.get("available"):
                change = ChangeType.STABLE
            else:
                change = ChangeType.NEW

            if max_conc > 40:
                details_parts.append(f"WARNING: {max_conc}% concentrated on single provider")

            subsystems.append(SubsystemResult(
                name="llm_routing",
                change=change,
                baseline_value=f"{base_routing.get('total_decisions', 0)} decisions" if base_routing.get("available") else "N/A",
                current_value=f"{curr_routing.get('total_decisions', 0)} decisions",
                delta=f"max_fail={max_failure}%, max_conc={max_conc}%",
                details="; ".join(details_parts) if details_parts else "",
            ))

        # Build report
        from dof import __version__

        report = RegressionReport(
            timestamp=datetime.now().isoformat(),
            git_commit=current["git_commit"],
            baseline_commit=baseline.get("git_commit", "unknown"),
            dof_version=__version__,
            subsystems=subsystems,
            has_regressions=any(s.change == ChangeType.REGRESSED for s in subsystems),
            regression_count=sum(1 for s in subsystems if s.change == ChangeType.REGRESSED),
            improvement_count=sum(1 for s in subsystems if s.change == ChangeType.IMPROVED),
            stable_count=sum(1 for s in subsystems if s.change == ChangeType.STABLE),
            elapsed_ms=round(elapsed, 2),
        )

        self._save_report(report)
        return report

    def _save_report(self, report: RegressionReport):
        """Append report to JSONL history."""
        os.makedirs(os.path.dirname(self.REPORTS_FILE), exist_ok=True)
        with open(self.REPORTS_FILE, "a") as f:
            f.write(json.dumps(report.to_dict(), default=str) + "\n")

    def get_history(self, n: int = 10) -> list:
        """Return last N regression reports."""
        if not os.path.exists(self.REPORTS_FILE):
            return []
        with open(self.REPORTS_FILE) as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:]]

    def get_trend(self, subsystem: str, n: int = 20) -> list:
        """Return values over time for a specific subsystem."""
        history = self.get_history(n)
        trend = []
        for report in history:
            for s in report.get("subsystems", []):
                if s["name"] == subsystem:
                    trend.append({
                        "timestamp": report["timestamp"],
                        "commit": report["git_commit"],
                        "change": s["change"],
                        "value": s["current_value"],
                    })
        return trend
