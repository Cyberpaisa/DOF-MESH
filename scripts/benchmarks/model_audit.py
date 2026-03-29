#!/usr/bin/env python3
"""
Model Audit — SHA-256 hash verification for downloaded AI models.

Supports GGUF, MLX, safetensors, and bin model files.
Computes SHA-256 hashes, compares against a trusted manifest,
and logs every verification to JSONL for auditability.

Part of the Deterministic Observability Framework (DOF).
Action item from AgentMeet meeting (2026-03-22).

Usage:
    python3 scripts/model_audit.py scan ~/.ollama/models/
    python3 scripts/model_audit.py verify ~/.ollama/models/qwen3-32b.gguf
    python3 scripts/model_audit.py add ~/.ollama/models/qwen3-32b.gguf --name "Qwen3 32B Q4" --source "ollama"
    python3 scripts/model_audit.py list
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# ── Constants ──

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_DIR = os.path.expanduser("~/.dof")
MANIFEST_PATH = os.path.join(MANIFEST_DIR, "models_manifest.json")
AUDIT_LOG_DIR = os.path.join(BASE_DIR, "logs")
AUDIT_LOG_PATH = os.path.join(AUDIT_LOG_DIR, "model_audit.jsonl")

MODEL_EXTENSIONS = {".gguf", ".safetensors", ".bin", ".mlx"}
HASH_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks for large file hashing

logger = logging.getLogger("scripts.model_audit")


# ── Enums & Dataclasses ──

class VerificationStatus(str, Enum):
    """Result of comparing a file hash against the manifest."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    TAMPERED = "TAMPERED"


@dataclass
class ModelEntry:
    """A trusted model entry in the manifest."""
    name: str
    filename: str
    sha256: str
    size_bytes: int
    source: str = ""
    added_at: str = ""
    notes: str = ""


@dataclass
class VerificationResult:
    """Result of verifying a single model file."""
    filepath: str
    filename: str
    sha256: str
    size_bytes: int
    status: VerificationStatus
    expected_sha256: str = ""
    manifest_name: str = ""
    manifest_added_at: str = ""
    verified_at: str = ""
    governance_passed: Optional[bool] = None


@dataclass
class AuditLogEntry:
    """A single audit log record (persisted as JSONL)."""
    timestamp: str
    action: str  # scan | verify | add | list
    filepath: str = ""
    filename: str = ""
    sha256: str = ""
    status: str = ""
    size_bytes: int = 0
    details: str = ""
    governance_check: Optional[bool] = None


# ── Governance Integration ──

def _check_governance(filepath: str) -> Optional[bool]:
    """Run DOF ConstitutionEnforcer check if available.

    Returns True if governance passed, False if failed, None if unavailable.
    The governance check validates the file path and name against hard rules
    (e.g., no suspicious filenames that might indicate prompt injection).
    """
    try:
        sys.path.insert(0, BASE_DIR)
        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        # Check the filepath string for governance violations
        result = enforcer.check(f"Model file: {filepath}")
        return result.passed
    except ImportError:
        logger.debug("ConstitutionEnforcer not available — skipping governance check")
        return None
    except Exception as e:
        logger.warning(f"Governance check error: {e}")
        return None


# ── Manifest Management ──

class ManifestManager:
    """Manages the trusted models manifest at ~/.dof/models_manifest.json."""

    def __init__(self, manifest_path: str = MANIFEST_PATH):
        self._path = manifest_path
        self._entries: dict[str, ModelEntry] = {}
        self._load()

    def _load(self):
        """Load manifest from disk. Creates empty manifest if missing."""
        if not os.path.exists(self._path):
            self._entries = {}
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sha256, entry_dict in data.get("models", {}).items():
                self._entries[sha256] = ModelEntry(**entry_dict)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.error(f"Corrupted manifest at {self._path}: {e}")
            self._entries = {}

    def _save(self):
        """Persist manifest to disk."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "models": {
                sha256: asdict(entry)
                for sha256, entry in self._entries.items()
            },
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def lookup(self, sha256: str) -> Optional[ModelEntry]:
        """Look up a model by its SHA-256 hash."""
        return self._entries.get(sha256)

    def add(self, entry: ModelEntry) -> None:
        """Add or update a model entry in the manifest."""
        self._entries[entry.sha256] = entry
        self._save()

    def remove(self, sha256: str) -> bool:
        """Remove a model entry by SHA-256 hash. Returns True if found."""
        if sha256 in self._entries:
            del self._entries[sha256]
            self._save()
            return True
        return False

    def list_all(self) -> list[ModelEntry]:
        """Return all entries sorted by name."""
        return sorted(self._entries.values(), key=lambda e: e.name.lower())

    @property
    def count(self) -> int:
        return len(self._entries)


# ── Hashing ──

def compute_sha256(filepath: str, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Compute SHA-256 hash of a file, reading in chunks for large files.

    Args:
        filepath: Absolute or relative path to the file.
        chunk_size: Bytes to read per iteration (default 8 MB).

    Returns:
        Lowercase hex digest of the SHA-256 hash.
    """
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


# ── File Discovery ──

def find_model_files(directory: str) -> list[str]:
    """Recursively find model files in a directory.

    Searches for files matching MODEL_EXTENSIONS (.gguf, .safetensors, .bin, .mlx).

    Args:
        directory: Root directory to scan.

    Returns:
        Sorted list of absolute file paths.
    """
    models = []
    directory = os.path.expanduser(directory)
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return models

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in MODEL_EXTENSIONS:
                models.append(os.path.join(root, fname))

    return sorted(models)


# ── Audit Logging ──

def _log_audit(entry: AuditLogEntry) -> None:
    """Append an audit entry to the JSONL log."""
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


# ── Verification Engine ──

def verify_file(filepath: str, manifest: ManifestManager) -> VerificationResult:
    """Verify a single model file against the manifest.

    Computes the SHA-256 hash and checks whether it matches,
    is absent from, or conflicts with the trusted manifest.

    Args:
        filepath: Path to the model file.
        manifest: ManifestManager instance.

    Returns:
        VerificationResult with status VERIFIED, UNVERIFIED, or TAMPERED.
    """
    filepath = os.path.expanduser(filepath)
    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Model file not found: {filepath}")

    filename = os.path.basename(filepath)
    size_bytes = os.path.getsize(filepath)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Compute hash
    sha256 = compute_sha256(filepath)

    # Governance check
    gov_passed = _check_governance(filepath)

    # Look up in manifest by hash
    entry = manifest.lookup(sha256)
    if entry is not None:
        result = VerificationResult(
            filepath=filepath,
            filename=filename,
            sha256=sha256,
            size_bytes=size_bytes,
            status=VerificationStatus.VERIFIED,
            expected_sha256=entry.sha256,
            manifest_name=entry.name,
            manifest_added_at=entry.added_at,
            verified_at=now_iso,
            governance_passed=gov_passed,
        )
    else:
        # Check if any manifest entry has the same filename but different hash
        tampered = False
        expected_sha = ""
        for existing in manifest.list_all():
            if existing.filename == filename and existing.sha256 != sha256:
                tampered = True
                expected_sha = existing.sha256
                break

        if tampered:
            result = VerificationResult(
                filepath=filepath,
                filename=filename,
                sha256=sha256,
                size_bytes=size_bytes,
                status=VerificationStatus.TAMPERED,
                expected_sha256=expected_sha,
                verified_at=now_iso,
                governance_passed=gov_passed,
            )
        else:
            result = VerificationResult(
                filepath=filepath,
                filename=filename,
                sha256=sha256,
                size_bytes=size_bytes,
                status=VerificationStatus.UNVERIFIED,
                verified_at=now_iso,
                governance_passed=gov_passed,
            )

    # Audit log
    _log_audit(AuditLogEntry(
        timestamp=now_iso,
        action="verify",
        filepath=filepath,
        filename=filename,
        sha256=sha256,
        status=result.status.value,
        size_bytes=size_bytes,
        governance_check=gov_passed,
    ))

    return result


# ── Formatting ──

def _format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string (GB/MB/KB)."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _format_result(result: VerificationResult) -> str:
    """Format a VerificationResult as a human-readable line."""
    status_tag = f"[{result.status.value}]"
    sha_short = result.sha256[:12] + "..."
    size_str = _format_size(result.size_bytes)

    if result.status == VerificationStatus.VERIFIED:
        added = result.manifest_added_at[:10] if result.manifest_added_at else "unknown"
        return (
            f"{status_tag:14s} {result.filename:40s} "
            f"SHA256: {sha_short}  ({size_str}, added {added})"
        )
    elif result.status == VerificationStatus.TAMPERED:
        expected_short = result.expected_sha256[:12] + "..."
        return (
            f"{status_tag:14s} {result.filename:40s} "
            f"SHA256: {sha_short}  (expected: {expected_short})"
        )
    else:  # UNVERIFIED
        return (
            f"{status_tag:14s} {result.filename:40s} "
            f"SHA256: {sha_short}  ({size_str}, not in manifest)"
        )


# ── CLI Commands ──

def cmd_scan(args: argparse.Namespace) -> int:
    """Scan a directory for model files and verify each one."""
    directory = args.directory
    manifest = ManifestManager()

    print(f"Scanning {directory} for model files...\n")

    files = find_model_files(directory)
    if not files:
        print("No model files found.")
        _log_audit(AuditLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="scan",
            filepath=directory,
            details="No model files found",
        ))
        return 0

    counts = {s: 0 for s in VerificationStatus}
    for filepath in files:
        try:
            result = verify_file(filepath, manifest)
            print(_format_result(result))
            counts[result.status] += 1
        except Exception as e:
            print(f"[ERROR]        {os.path.basename(filepath):40s} {e}")

    # Summary
    total = sum(counts.values())
    print(f"\n{'='*80}")
    print(
        f"Total: {total} | "
        f"Verified: {counts[VerificationStatus.VERIFIED]} | "
        f"Unverified: {counts[VerificationStatus.UNVERIFIED]} | "
        f"Tampered: {counts[VerificationStatus.TAMPERED]}"
    )

    _log_audit(AuditLogEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        action="scan",
        filepath=directory,
        details=f"total={total} verified={counts[VerificationStatus.VERIFIED]} "
                f"unverified={counts[VerificationStatus.UNVERIFIED]} "
                f"tampered={counts[VerificationStatus.TAMPERED]}",
    ))

    # Non-zero exit if any tampered
    return 1 if counts[VerificationStatus.TAMPERED] > 0 else 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a specific model file."""
    filepath = args.file
    manifest = ManifestManager()

    if not os.path.isfile(os.path.expanduser(filepath)):
        print(f"Error: File not found: {filepath}")
        return 1

    print(f"Verifying {filepath}...\n")
    result = verify_file(filepath, manifest)
    print(_format_result(result))

    if result.governance_passed is not None:
        gov_str = "PASSED" if result.governance_passed else "FAILED"
        print(f"  Governance: {gov_str}")

    return 1 if result.status == VerificationStatus.TAMPERED else 0


def cmd_add(args: argparse.Namespace) -> int:
    """Add a model file to the trusted manifest."""
    filepath = os.path.expanduser(args.file)
    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}")
        return 1

    filename = os.path.basename(filepath)
    size_bytes = os.path.getsize(filepath)
    now_iso = datetime.now(timezone.utc).isoformat()

    print(f"Computing SHA-256 for {filename} ({_format_size(size_bytes)})...")
    sha256 = compute_sha256(filepath)

    name = args.name if args.name else os.path.splitext(filename)[0]
    source = args.source if args.source else ""
    notes = args.notes if args.notes else ""

    manifest = ManifestManager()
    existing = manifest.lookup(sha256)
    if existing:
        print(f"Model already in manifest as '{existing.name}' (added {existing.added_at[:10]})")
        print(f"SHA256: {sha256}")
        return 0

    entry = ModelEntry(
        name=name,
        filename=filename,
        sha256=sha256,
        size_bytes=size_bytes,
        source=source,
        added_at=now_iso,
        notes=notes,
    )
    manifest.add(entry)

    print(f"Added to manifest: {name}")
    print(f"  File:   {filename}")
    print(f"  SHA256: {sha256}")
    print(f"  Size:   {_format_size(size_bytes)}")
    print(f"  Source: {source or '(none)'}")

    _log_audit(AuditLogEntry(
        timestamp=now_iso,
        action="add",
        filepath=filepath,
        filename=filename,
        sha256=sha256,
        status="ADDED",
        size_bytes=size_bytes,
        details=f"name={name} source={source}",
    ))

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all trusted models in the manifest."""
    manifest = ManifestManager()
    entries = manifest.list_all()

    if not entries:
        print("Manifest is empty. Use 'add' to register trusted models.")
        _log_audit(AuditLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="list",
            details="empty manifest",
        ))
        return 0

    print(f"Trusted models ({manifest.count}):\n")
    for entry in entries:
        sha_short = entry.sha256[:12] + "..."
        size_str = _format_size(entry.size_bytes)
        added = entry.added_at[:10] if entry.added_at else "unknown"
        source_str = f", source: {entry.source}" if entry.source else ""
        print(
            f"  {entry.name:40s} {entry.filename:30s} "
            f"SHA256: {sha_short}  ({size_str}, added {added}{source_str})"
        )

    _log_audit(AuditLogEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        action="list",
        details=f"count={manifest.count}",
    ))

    return 0


# ── CLI Entry Point ──

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="model_audit",
        description="SHA-256 hash verification for downloaded AI models (DOF)",
        epilog="Part of the Deterministic Observability Framework.",
    )
    parser.add_argument(
        "--manifest", default=MANIFEST_PATH,
        help=f"Path to manifest file (default: {MANIFEST_PATH})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_parser = subparsers.add_parser(
        "scan", help="Scan a directory for model files and verify each one",
    )
    scan_parser.add_argument(
        "directory", help="Directory to scan for model files",
    )

    # verify
    verify_parser = subparsers.add_parser(
        "verify", help="Verify a specific model file against the manifest",
    )
    verify_parser.add_argument(
        "file", help="Path to the model file to verify",
    )

    # add
    add_parser = subparsers.add_parser(
        "add", help="Add a model file to the trusted manifest",
    )
    add_parser.add_argument(
        "file", help="Path to the model file to add",
    )
    add_parser.add_argument(
        "--name", "-n", default="",
        help="Human-readable name for the model (default: filename stem)",
    )
    add_parser.add_argument(
        "--source", "-s", default="",
        help="Source of the model (e.g., ollama, huggingface, mlx-community)",
    )
    add_parser.add_argument(
        "--notes", default="",
        help="Optional notes about the model",
    )

    # list
    subparsers.add_parser(
        "list", help="List all trusted models in the manifest",
    )

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Store manifest path on args for commands to use
    args.manifest_path = args.manifest

    # Dispatch
    commands = {
        "scan": cmd_scan,
        "verify": cmd_verify,
        "add": cmd_add,
        "list": cmd_list,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
