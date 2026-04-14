from __future__ import annotations
"""
Prompt Version Control Registry for DOF-MESH.

Addresses the critical gap identified by Adeline/Stanford:
DOF has governance for outputs but NO versioning for prompts.
This module provides full version control for prompt templates
with diff, rollback, and change evaluation capabilities.
"""

import hashlib
import json
import os
import difflib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class PromptVersion:
    """A single versioned prompt entry."""
    name: str
    version: int
    content: str
    hash: str
    author: str
    tags: list
    created_at: str
    active: bool = True


@dataclass
class PromptDiff:
    """Result of comparing two prompt versions."""
    name: str
    v1: int
    v2: int
    added_lines: list
    removed_lines: list
    changed_pct: float


class PromptRegistry:
    """
    Registry for versioned prompts with diff, rollback, and evaluation.

    Storage format: JSONL at logs/prompts/registry.jsonl
    Each line is a JSON object representing a PromptVersion.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base = Path(__file__).resolve().parent.parent
            storage_path = str(base / "logs" / "prompts" / "registry.jsonl")
        self._storage_path = storage_path
        self._versions: dict[str, list[PromptVersion]] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────────

    def _load(self) -> None:
        """Load all prompt versions from JSONL storage."""
        if not os.path.exists(self._storage_path):
            return
        with open(self._storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                pv = PromptVersion(**data)
                self._versions.setdefault(pv.name, []).append(pv)

    def _save(self) -> None:
        """Persist all prompt versions to JSONL storage."""
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        with open(self._storage_path, "w", encoding="utf-8") as f:
            for name in sorted(self._versions):
                for pv in self._versions[name]:
                    f.write(json.dumps(asdict(pv), ensure_ascii=False) + "\n")

    # ── public API ───────────────────────────────────────────────

    @staticmethod
    def _hash_content(content: str) -> str:
        """Deterministic SHA-256 hash of prompt content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def register(
        self,
        name: str,
        content: str,
        author: str,
        tags: Optional[list] = None,
    ) -> PromptVersion:
        """
        Register a new prompt version.

        Auto-increments version number. Generates SHA-256 hash.
        Deactivates previous versions so only the latest is active.
        Detects duplicate content and raises ValueError.
        """
        if not name or not name.strip():
            raise ValueError("Prompt name cannot be empty")
        if not content or not content.strip():
            raise ValueError("Prompt content cannot be empty")
        if not author or not author.strip():
            raise ValueError("Author cannot be empty")

        content_hash = self._hash_content(content)
        tags = tags or []

        existing = self._versions.get(name, [])

        # Duplicate content detection
        for pv in existing:
            if pv.hash == content_hash:
                raise ValueError(
                    f"Duplicate content: prompt '{name}' v{pv.version} "
                    f"already has identical content (hash={content_hash[:12]}...)"
                )

        # Determine next version
        next_version = (max(pv.version for pv in existing) + 1) if existing else 1

        # Deactivate previous versions
        for pv in existing:
            pv.active = False

        pv = PromptVersion(
            name=name,
            version=next_version,
            content=content,
            hash=content_hash,
            author=author,
            tags=tags,
            created_at=datetime.now(timezone.utc).isoformat(),
            active=True,
        )

        self._versions.setdefault(name, []).append(pv)
        self._save()
        return pv

    def get(self, name: str, version: Optional[int] = None) -> PromptVersion:
        """
        Get a prompt by name. If version is None, returns the active
        (latest active) version. Otherwise returns the exact version.
        """
        versions = self._versions.get(name)
        if not versions:
            raise KeyError(f"Prompt '{name}' not found")

        if version is not None:
            for pv in versions:
                if pv.version == version:
                    return pv
            raise KeyError(f"Prompt '{name}' version {version} not found")

        # Return the active version (there should be exactly one)
        for pv in reversed(versions):
            if pv.active:
                return pv

        # Fallback: return the latest version
        return versions[-1]

    def diff(self, name: str, v1: int, v2: int) -> PromptDiff:
        """
        Compare two versions of a prompt using difflib.
        Returns added lines, removed lines, and change percentage.
        """
        pv1 = self.get(name, v1)
        pv2 = self.get(name, v2)

        lines1 = pv1.content.splitlines(keepends=True)
        lines2 = pv2.content.splitlines(keepends=True)

        added = []
        removed = []

        for line in difflib.unified_diff(lines1, lines2, lineterm=""):
            stripped = line.rstrip("\n")
            if line.startswith("+") and not line.startswith("+++"):
                added.append(stripped[1:])  # remove the '+' prefix
            elif line.startswith("-") and not line.startswith("---"):
                removed.append(stripped[1:])  # remove the '-' prefix

        total_lines = max(len(lines1), len(lines2), 1)
        changed_pct = round(
            (len(added) + len(removed)) / (total_lines * 2) * 100, 2
        )

        return PromptDiff(
            name=name,
            v1=v1,
            v2=v2,
            added_lines=added,
            removed_lines=removed,
            changed_pct=changed_pct,
        )

    def rollback(self, name: str, version: int) -> PromptVersion:
        """
        Mark a previous version as the active one.
        Deactivates all other versions.
        """
        versions = self._versions.get(name)
        if not versions:
            raise KeyError(f"Prompt '{name}' not found")

        target = None
        for pv in versions:
            if pv.version == version:
                target = pv
                break

        if target is None:
            raise KeyError(f"Prompt '{name}' version {version} not found")

        # Deactivate all, activate target
        for pv in versions:
            pv.active = False
        target.active = True

        self._save()
        return target

    def list_versions(self, name: str) -> list[PromptVersion]:
        """List all versions of a prompt, ordered by version number."""
        versions = self._versions.get(name)
        if not versions:
            raise KeyError(f"Prompt '{name}' not found")
        return sorted(versions, key=lambda pv: pv.version)

    def list_prompts(self) -> list[str]:
        """List all registered prompt names."""
        return sorted(self._versions.keys())

    def evaluate_change(
        self,
        name: str,
        old_version: int,
        new_version: int,
        test_cases: list[dict],
    ) -> list[dict]:
        """
        Evaluate a prompt change against test cases.

        This is a structural evaluation framework -- it does NOT call an LLM.
        Each test_case should have at minimum an 'input' key.
        Returns a list of evaluation records with both prompt versions
        and placeholders for results that the user fills in.

        Args:
            name: prompt name
            old_version: version number of the old prompt
            new_version: version number of the new prompt
            test_cases: list of dicts, each with at least 'input'

        Returns:
            list of evaluation dicts with old_prompt, new_prompt,
            test_input, old_result (None), new_result (None),
            and comparison (None) for user to fill.
        """
        old_pv = self.get(name, old_version)
        new_pv = self.get(name, new_version)

        results = []
        for tc in test_cases:
            results.append({
                "test_input": tc.get("input", ""),
                "expected_output": tc.get("expected_output"),
                "old_prompt": old_pv.content,
                "old_version": old_pv.version,
                "new_prompt": new_pv.content,
                "new_version": new_pv.version,
                "old_result": None,  # user fills after running
                "new_result": None,  # user fills after running
                "comparison": None,  # user fills: "better" | "worse" | "same"
            })

        return results
