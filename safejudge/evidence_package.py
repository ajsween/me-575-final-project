"""Evidence packaging — run ID generation, SHA-256 hashing, and evidence manifest."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safejudge.config import EVIDENCE_DIR


def generate_run_id() -> str:
    """Generate a unique run ID: timestamp + short UUID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = uuid.uuid4().hex[:8]
    return f"{ts}_{short}"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def sha256_string(data: str) -> str:
    """Compute SHA-256 hash of a string."""
    return f"sha256:{hashlib.sha256(data.encode()).hexdigest()}"


def build_evidence_package(
    run_id: str,
    evidence_dir: Path,
    config_snapshot: dict[str, Any],
    gate_verdict: str,
    total_evaluated: int,
    total_succeeded: int,
) -> Path:
    """Build evidence_package.json with SHA-256 hashes for all artifacts.

    Follows the evidence manifest pattern from course Sessions 5, 6, 8, 10:
    - Run ID links every artifact to the exact evaluation configuration
    - SHA-256 hashes provide cryptographic binding for audit trail
    - Config snapshot enables reproducibility
    """
    manifest: dict[str, str] = {}

    # Hash every file in the evidence directory (except the package itself)
    package_name = "evidence_package.json"
    for artifact in sorted(evidence_dir.iterdir()):
        if artifact.name == package_name:
            continue
        if artifact.is_file():
            manifest[artifact.name] = sha256_file(artifact)

    package = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": gate_verdict,
        "evaluation_summary": {
            "total_evaluated": total_evaluated,
            "total_succeeded": total_succeeded,
        },
        "config_snapshot": config_snapshot,
        "evidence_manifest": manifest,
        "artifact_count": len(manifest),
        "integrity_note": (
            "SHA-256 hashes bind each artifact to this run. "
            "Recompute hashes to verify artifact integrity. "
            "The run_id links all artifacts to the evaluation configuration."
        ),
    }

    out_path = evidence_dir / package_name
    with open(out_path, "w") as f:
        json.dump(package, f, indent=2)
    print(f"  Generated: {package_name} ({len(manifest)} artifacts hashed)")
    return out_path


def get_config_snapshot() -> dict[str, Any]:
    """Capture current configuration for reproducibility."""
    from safejudge.config import (
        GATE_THRESHOLDS,
        JUDGE_MODEL,
        JUDGE_TEMPERATURE,
        OLLAMA_URL,
        SUT_PRIMARY_MODEL,
        SUT_SAFETY_MODEL,
        SUT_SECONDARY_MODEL,
        SUT_TIMEOUT_SECONDS,
    )

    return {
        "ollama_url": OLLAMA_URL,
        "judge_model": JUDGE_MODEL,
        "judge_temperature": JUDGE_TEMPERATURE,
        "sut_primary_model": SUT_PRIMARY_MODEL,
        "sut_secondary_model": SUT_SECONDARY_MODEL,
        "sut_safety_model": SUT_SAFETY_MODEL,
        "sut_timeout_seconds": SUT_TIMEOUT_SECONDS,
        "gate_thresholds": GATE_THRESHOLDS,
    }
