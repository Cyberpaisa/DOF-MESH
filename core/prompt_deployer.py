from __future__ import annotations
"""
Prompt Deployment Pipeline for DOF-MESH.

Prompts change faster than code and need their own deployment flow.
This module provides staging, validation, deployment, rollback, and
promotion across environments (development, staging, production).

All decisions are deterministic — zero LLM involvement.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.governance import check_governance

# ── Constants ────────────────────────────────────────────────────────────────

ENVIRONMENTS = ["development", "staging", "production"]

SECRET_PATTERNS = [
    r"0x[a-fA-F0-9]{64}",
    r"sk-",
    r"gsk_",
    r"Bearer ",
]

MAX_PROMPT_LENGTH = 50_000

REPO_ROOT = Path(__file__).parent.parent

# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class StagedPrompt:
    """A prompt prepared for deployment but not yet active."""
    name: str
    content: str
    hash: str
    author: str
    staged_at: str
    governance_passed: bool


@dataclass
class ValidationResult:
    """Result of pre-deploy validation checks."""
    passed: bool
    checks: list  # list[dict] with keys: name, passed, detail
    warnings: list  # list[str]


@dataclass
class Deployment:
    """Record of a prompt deployed to an environment."""
    name: str
    version: int
    environment: str
    deployed_at: str
    hash: str
    rollback_hash: Optional[str]
    author: str


# ── PromptDeployer ───────────────────────────────────────────────────────────


class PromptDeployer:
    """
    Pipeline de deploy para prompts con staging, validación,
    deploy multi-ambiente, rollback y promoción.

    Storage:
      - logs/prompts/staged.jsonl     — prompts en staging
      - logs/prompts/deployments.jsonl — historial de deployments
    """

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else REPO_ROOT / "logs" / "prompts"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.staged_path = self.log_dir / "staged.jsonl"
        self.deployments_path = self.log_dir / "deployments.jsonl"

    # ── Helpers ──────────────────────────────────────────────────────────

    def _hash_content(self, content: str) -> str:
        """SHA-256 hash of prompt content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _append_jsonl(self, path: Path, data: dict) -> None:
        """Append a JSON line to a JSONL file."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict]:
        """Read all lines from a JSONL file."""
        if not path.exists():
            return []
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Stage ────────────────────────────────────────────────────────────

    def stage(self, name: str, content: str, author: str) -> StagedPrompt:
        """
        Prepara un prompt para deploy (staging). NO lo activa aún.
        Genera hash, valida formato, corre governance check.

        Raises ValueError si el contenido está vacío.
        """
        if not content or not content.strip():
            raise ValueError("Prompt content cannot be empty")

        if not name or not name.strip():
            raise ValueError("Prompt name cannot be empty")

        content_hash = self._hash_content(content)
        gov_result = check_governance(content)

        staged = StagedPrompt(
            name=name.strip(),
            content=content,
            hash=content_hash,
            author=author,
            staged_at=self._now_iso(),
            governance_passed=gov_result.passed,
        )

        self._append_jsonl(self.staged_path, asdict(staged))
        return staged

    # ── Validate ─────────────────────────────────────────────────────────

    def validate(self, staged_prompt: StagedPrompt) -> ValidationResult:
        """
        Validaciones pre-deploy:
        - Governance pass
        - No vacío
        - No contiene secrets
        - Longitud razonable (<50K chars)
        - Placeholders válidos ({variable})
        """
        checks = []
        warnings = []

        # 1. Governance
        checks.append({
            "name": "governance",
            "passed": staged_prompt.governance_passed,
            "detail": "Governance check passed" if staged_prompt.governance_passed
                      else "Governance check failed — dangerous content detected",
        })

        # 2. Not empty
        not_empty = bool(staged_prompt.content and staged_prompt.content.strip())
        checks.append({
            "name": "not_empty",
            "passed": not_empty,
            "detail": "Content is not empty" if not_empty else "Content is empty",
        })

        # 3. No secrets
        has_secret = False
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, staged_prompt.content):
                has_secret = True
                break
        checks.append({
            "name": "no_secrets",
            "passed": not has_secret,
            "detail": "No secrets detected" if not has_secret
                      else "Secret pattern detected in prompt content",
        })

        # 4. Length
        within_limit = len(staged_prompt.content) < MAX_PROMPT_LENGTH
        checks.append({
            "name": "length",
            "passed": within_limit,
            "detail": f"Length {len(staged_prompt.content)} within limit"
                      if within_limit
                      else f"Length {len(staged_prompt.content)} exceeds {MAX_PROMPT_LENGTH}",
        })

        # 5. Placeholders — check {variable} format is well-formed
        placeholder_ok = True
        # Find all { } patterns and check they are valid identifiers
        open_braces = staged_prompt.content.count("{")
        close_braces = staged_prompt.content.count("}")
        if open_braces != close_braces:
            placeholder_ok = False
            warnings.append("Mismatched braces in placeholders")

        # Check for malformed placeholders like {}, { }, {123}
        placeholders = re.findall(r"\{([^}]*)\}", staged_prompt.content)
        for ph in placeholders:
            ph_stripped = ph.strip()
            if not ph_stripped:
                placeholder_ok = False
                warnings.append("Empty placeholder {} found")
                break
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ph_stripped):
                warnings.append(f"Non-standard placeholder: {{{ph_stripped}}}")

        checks.append({
            "name": "placeholders",
            "passed": placeholder_ok,
            "detail": "Placeholders are well-formed" if placeholder_ok
                      else "Malformed placeholders detected",
        })

        all_passed = all(c["passed"] for c in checks)
        return ValidationResult(passed=all_passed, checks=checks, warnings=warnings)

    # ── Deploy ───────────────────────────────────────────────────────────

    def deploy(
        self,
        staged_prompt: StagedPrompt,
        environment: str,
    ) -> Deployment:
        """
        Activa el prompt en un ambiente.
        Solo deploya si validate() pasa.

        Raises ValueError si environment inválido o validación falla.
        """
        if environment not in ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{environment}'. "
                f"Must be one of {ENVIRONMENTS}"
            )

        validation = self.validate(staged_prompt)
        if not validation.passed:
            failed = [c["name"] for c in validation.checks if not c["passed"]]
            raise ValueError(
                f"Validation failed for checks: {failed}. "
                f"Cannot deploy to '{environment}'."
            )

        # Find previous deployment for rollback hash
        previous = self.get_active(staged_prompt.name, environment)
        rollback_hash = previous.hash if previous else None

        # Determine version number
        history = self.list_deployments(
            name=staged_prompt.name, environment=environment,
        )
        version = len(history) + 1

        deployment = Deployment(
            name=staged_prompt.name,
            version=version,
            environment=environment,
            deployed_at=self._now_iso(),
            hash=staged_prompt.hash,
            rollback_hash=rollback_hash,
            author=staged_prompt.author,
        )

        self._append_jsonl(self.deployments_path, asdict(deployment))
        return deployment

    # ── Rollback ─────────────────────────────────────────────────────────

    def rollback(self, name: str, environment: str) -> Optional[Deployment]:
        """
        Revierte al prompt anterior en ese ambiente.
        Lee el deployment anterior y lo re-activa.

        Returns the new rollback deployment or None if nothing to rollback to.
        """
        if environment not in ENVIRONMENTS:
            raise ValueError(f"Invalid environment '{environment}'")

        history = self.list_deployments(name=name, environment=environment)
        if len(history) < 2:
            return None

        # The previous deployment (second to last)
        previous = history[-2]
        current = history[-1]

        rollback_deployment = Deployment(
            name=name,
            version=current["version"] + 1,
            environment=environment,
            deployed_at=self._now_iso(),
            hash=previous["hash"],
            rollback_hash=current["hash"],
            author="system:rollback",
        )

        self._append_jsonl(self.deployments_path, asdict(rollback_deployment))
        return rollback_deployment

    # ── Get Active ───────────────────────────────────────────────────────

    def get_active(self, name: str, environment: str) -> Optional[Deployment]:
        """
        Obtiene el prompt activo (último deployment) en un ambiente.
        Returns Deployment or None.
        """
        history = self.list_deployments(name=name, environment=environment)
        if not history:
            return None
        latest = history[-1]
        return Deployment(**latest)

    # ── List Deployments ─────────────────────────────────────────────────

    def list_deployments(
        self,
        name: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> list[dict]:
        """
        Historial de deploys, filtrado opcionalmente por name y/o environment.
        Returns list of dicts ordered by deployed_at.
        """
        all_entries = self._read_jsonl(self.deployments_path)
        filtered = []
        for entry in all_entries:
            if name and entry.get("name") != name:
                continue
            if environment and entry.get("environment") != environment:
                continue
            filtered.append(entry)
        return filtered

    # ── Promote ──────────────────────────────────────────────────────────

    def promote(self, name: str, from_env: str, to_env: str) -> Deployment:
        """
        Promueve un prompt de un ambiente a otro.
        Ej: development -> staging -> production.

        Requiere que haya un deployment activo en from_env.
        Raises ValueError si no hay deployment o environments inválidos.
        """
        if from_env not in ENVIRONMENTS:
            raise ValueError(f"Invalid source environment '{from_env}'")
        if to_env not in ENVIRONMENTS:
            raise ValueError(f"Invalid target environment '{to_env}'")
        if ENVIRONMENTS.index(from_env) >= ENVIRONMENTS.index(to_env):
            raise ValueError(
                f"Cannot promote from '{from_env}' to '{to_env}'. "
                f"Promotion must go forward: development -> staging -> production."
            )

        source = self.get_active(name, from_env)
        if source is None:
            raise ValueError(
                f"No active deployment for '{name}' in '{from_env}'"
            )

        # Find previous in target env for rollback
        previous = self.get_active(name, to_env)
        rollback_hash = previous.hash if previous else None

        target_history = self.list_deployments(name=name, environment=to_env)
        version = len(target_history) + 1

        deployment = Deployment(
            name=name,
            version=version,
            environment=to_env,
            deployed_at=self._now_iso(),
            hash=source.hash,
            rollback_hash=rollback_hash,
            author=source.author,
        )

        self._append_jsonl(self.deployments_path, asdict(deployment))
        return deployment
