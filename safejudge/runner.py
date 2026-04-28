"""Evaluation runner — batch-executes test cases through the SUT via subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safejudge.config import (
    ALL_MODES,
    MODE_ENSEMBLE,
    MODE_SAFETY,
    MODE_SINGLE,
    OLLAMA_URL,
    RESULTS_DIR,
    SUT_ARGS_BASE,
    SUT_COMMAND,
    SUT_DIR,
    SUT_PRIMARY_MODEL,
    SUT_SAFETY_MODEL,
    SUT_SECONDARY_MODEL,
    SUT_TIMEOUT_SECONDS,
)
from safejudge.dataset import TestCase


@dataclass
class EvalResult:
    """Result of running a single test case through the SUT."""

    prompt_id: str
    mode: str
    actual_output: dict[str, Any] | None
    exit_code: int
    execution_time_ms: float
    timestamp: str
    error: str | None = None
    test_case: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.actual_output is not None


def _build_command(
    test_case: TestCase,
    mode: str,
    history_path: Path | None = None,
) -> list[str]:
    """Build the subprocess command for a given test case and mode."""
    cmd = [
        SUT_COMMAND,
        *SUT_ARGS_BASE,
        "--prompt",
        test_case.prompt_text,
        "--url",
        OLLAMA_URL,
        "--model",
        SUT_PRIMARY_MODEL,
    ]

    if mode == MODE_ENSEMBLE:
        cmd.extend(["--ensemble", "--secondary-model", SUT_SECONDARY_MODEL])
    elif mode == MODE_SAFETY:
        cmd.extend([
            "--use-safety-classifier",
            "--safety-model",
            SUT_SAFETY_MODEL,
        ])

    if history_path is not None:
        cmd.extend(["--history", str(history_path)])

    return cmd


def _write_history_file(conversation_history: list[dict[str, str]]) -> Path:
    """Write conversation history to a temporary JSONL file."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, prefix="safejudge_hist_"
    )
    for turn in conversation_history:
        tmp.write(json.dumps(turn) + "\n")
    tmp.close()
    return Path(tmp.name)


def run_single(test_case: TestCase, mode: str) -> EvalResult:
    """Execute a single test case through the SUT and capture the result."""
    history_path: Path | None = None
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        if test_case.is_multi_turn:
            history_path = _write_history_file(test_case.conversation_history)

        cmd = _build_command(test_case, mode, history_path)

        # Clear VIRTUAL_ENV so poetry in the SUT dir uses its own venv
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}

        start = time.monotonic()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(SUT_DIR),
            timeout=SUT_TIMEOUT_SECONDS,
            env=env,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        # Parse JSON from stdout — SUT may append status text after JSON
        actual_output = None
        error = None
        try:
            stdout = proc.stdout.strip()
            if stdout:
                # Extract JSON object from stdout (ignore trailing text like "Safe"/"Malicious")
                brace_start = stdout.find("{")
                brace_end = stdout.rfind("}") + 1
                if brace_start >= 0 and brace_end > brace_start:
                    actual_output = json.loads(stdout[brace_start:brace_end])
                else:
                    error = f"No JSON object found in stdout: {stdout[:500]}"
        except json.JSONDecodeError as e:
            error = f"JSON parse error: {e}. stdout={proc.stdout[:500]}"

        if proc.returncode == 1 and error is None:
            error = f"SUT error (exit 1): {proc.stderr[:500]}"

        return EvalResult(
            prompt_id=test_case.prompt_id,
            mode=mode,
            actual_output=actual_output,
            exit_code=proc.returncode,
            execution_time_ms=elapsed_ms,
            timestamp=timestamp,
            error=error,
            test_case=_serialize_test_case(test_case),
        )

    except subprocess.TimeoutExpired:
        return EvalResult(
            prompt_id=test_case.prompt_id,
            mode=mode,
            actual_output=None,
            exit_code=-1,
            execution_time_ms=SUT_TIMEOUT_SECONDS * 1000,
            timestamp=timestamp,
            error=f"Timeout after {SUT_TIMEOUT_SECONDS}s",
            test_case=_serialize_test_case(test_case),
        )
    except Exception as e:
        return EvalResult(
            prompt_id=test_case.prompt_id,
            mode=mode,
            actual_output=None,
            exit_code=-1,
            execution_time_ms=0,
            timestamp=timestamp,
            error=str(e),
            test_case=_serialize_test_case(test_case),
        )
    finally:
        if history_path is not None:
            history_path.unlink(missing_ok=True)


def _serialize_test_case(tc: TestCase) -> dict[str, Any]:
    """Serialize a TestCase to a dict for storage in results."""
    return {
        "prompt_id": tc.prompt_id,
        "category": tc.category,
        "subcategory": tc.subcategory,
        "prompt_text": tc.prompt_text,
        "expected": {
            "jailbreak": tc.expected.jailbreak,
            "prompt_injection": tc.expected.prompt_injection,
            "harmful_content": tc.expected.harmful_content,
            "min_confidence": tc.expected.min_confidence,
            "expected_attack_types": tc.expected.expected_attack_types,
            "expected_content_flags": tc.expected.expected_content_flags,
        },
        "is_multi_turn": tc.is_multi_turn,
        "is_malicious": tc.is_malicious,
    }


def run_batch(
    dataset: list[TestCase],
    modes: list[str] | None = None,
    output_dir: Path = RESULTS_DIR,
    progress_callback: Any = None,
) -> list[EvalResult]:
    """Run all test cases through the SUT in all specified modes.

    Saves intermediate results as JSONL for crash recovery.
    """
    if modes is None:
        modes = [MODE_SINGLE]

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    intermediate_path = output_dir / f"eval_intermediate_{timestamp}.jsonl"

    results: list[EvalResult] = []
    total = len(dataset) * len(modes)
    completed = 0

    for mode in modes:
        for test_case in dataset:
            completed += 1
            if progress_callback:
                progress_callback(completed, total, test_case.prompt_id, mode)
            else:
                print(
                    f"  [{completed}/{total}] {mode}: {test_case.prompt_id}",
                    flush=True,
                )

            result = run_single(test_case, mode)
            results.append(result)

            # Append to intermediate file for crash recovery
            with open(intermediate_path, "a") as f:
                f.write(json.dumps(asdict(result)) + "\n")

    # Save final results
    final_path = output_dir / f"eval_run_{timestamp}.json"
    with open(final_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)

    print(f"\nResults saved to {final_path}")
    # Clean up intermediate file
    intermediate_path.unlink(missing_ok=True)

    return results
