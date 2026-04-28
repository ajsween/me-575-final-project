"""Release gate logic — pass/fail decisions based on evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safejudge.config import EVIDENCE_DIR, GATE_THRESHOLDS
from safejudge.metrics import MetricReport


@dataclass
class GateDecision:
    """Result of evaluating a single release gate."""

    gate_name: str
    metric_value: float
    threshold: float
    passed: bool
    action: str  # "block" or "flag"
    severity: str  # PASS, FLAG_FOR_REVIEW, BLOCK_RELEASE


@dataclass
class GateResult:
    """Aggregate result of all release gates."""

    decisions: list[GateDecision] = field(default_factory=list)
    overall_verdict: str = "PASS"  # PASS, FLAG_FOR_REVIEW, BLOCK_RELEASE
    timestamp: str = ""

    @property
    def all_passed(self) -> bool:
        return self.overall_verdict == "PASS"

    @property
    def blocked(self) -> bool:
        return self.overall_verdict == "BLOCK_RELEASE"


def _check_gate(
    name: str,
    value: float,
    threshold: float,
    action: str,
    direction: str = "gte",
) -> GateDecision:
    """Evaluate a single gate threshold."""
    if direction == "lte":
        passed = value <= threshold
    else:
        passed = value >= threshold

    if passed:
        severity = "PASS"
    elif action == "block":
        severity = "BLOCK_RELEASE"
    else:
        severity = "FLAG_FOR_REVIEW"

    return GateDecision(
        gate_name=name,
        metric_value=round(value, 4),
        threshold=threshold,
        passed=passed,
        action=action,
        severity=severity,
    )


def evaluate_gates(metric_report: MetricReport) -> GateResult:
    """Evaluate all release gates against the metric report."""
    decisions: list[GateDecision] = []

    # Map gate names to actual metric values
    metric_map = {
        "overall_accuracy": metric_report.overall_accuracy,
        "jailbreak_recall": metric_report.jailbreak.recall,
        "harmful_content_recall": metric_report.harmful_content.recall,
        "false_positive_rate": metric_report.benign_false_positive_rate,
        "obfuscation_detection_rate": (
            sum(metric_report.obfuscation_breakdown.values())
            / len(metric_report.obfuscation_breakdown)
            if metric_report.obfuscation_breakdown
            else 0.0
        ),
        "cross_model_consistency": metric_report.cross_model_consistency,
    }

    for gate_name, gate_config in GATE_THRESHOLDS.items():
        value = metric_map.get(gate_name, 0.0)
        direction = gate_config.get("direction", "gte")
        decision = _check_gate(
            name=gate_name,
            value=value,
            threshold=gate_config["value"],
            action=gate_config["action"],
            direction=direction,
        )
        decisions.append(decision)

    # Determine overall verdict
    has_block = any(d.severity == "BLOCK_RELEASE" for d in decisions)
    has_flag = any(d.severity == "FLAG_FOR_REVIEW" for d in decisions)

    if has_block:
        overall = "BLOCK_RELEASE"
    elif has_flag:
        overall = "FLAG_FOR_REVIEW"
    else:
        overall = "PASS"

    return GateResult(
        decisions=decisions,
        overall_verdict=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def generate_gate_report(
    gate_result: GateResult,
    output_dir: Path = EVIDENCE_DIR,
) -> Path:
    """Write the release gate decision log as markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)

    verdict_emoji = {
        "PASS": "PASS",
        "FLAG_FOR_REVIEW": "FLAG FOR REVIEW",
        "BLOCK_RELEASE": "BLOCK RELEASE",
    }

    lines = [
        "# Release Gate Decision Log\n",
        f"**Timestamp:** {gate_result.timestamp}  ",
        f"**Overall Verdict:** {verdict_emoji.get(gate_result.overall_verdict, gate_result.overall_verdict)}\n",
        "## Gate Results\n",
        "| Gate | Metric Value | Threshold | Direction | Passed | Action |",
        "|------|-------------|-----------|-----------|--------|--------|",
    ]

    for d in gate_result.decisions:
        direction = "lte" if GATE_THRESHOLDS.get(d.gate_name, {}).get("direction") == "lte" else "gte"
        dir_symbol = "<=" if direction == "lte" else ">="
        passed_str = "Yes" if d.passed else "No"
        lines.append(
            f"| {d.gate_name} | {d.metric_value:.1%} | {dir_symbol} {d.threshold:.0%} "
            f"| {dir_symbol} | {passed_str} | {d.severity} |"
        )

    # Summary
    passed_count = sum(1 for d in gate_result.decisions if d.passed)
    total_count = len(gate_result.decisions)
    lines.append(f"\n**Gates Passed:** {passed_count}/{total_count}")

    if gate_result.blocked:
        blocked_gates = [d.gate_name for d in gate_result.decisions if d.severity == "BLOCK_RELEASE"]
        lines.append(f"\n**Blocking Gates:** {', '.join(blocked_gates)}")
        lines.append("\n> Release is BLOCKED. The above gates must pass before deployment.")

    flagged = [d.gate_name for d in gate_result.decisions if d.severity == "FLAG_FOR_REVIEW"]
    if flagged:
        lines.append(f"\n**Flagged for Review:** {', '.join(flagged)}")
        lines.append("\n> These gates require human review before proceeding.")

    if gate_result.all_passed:
        lines.append("\n> All gates passed. Release may proceed.")

    out_path = output_dir / "release_gate_decision.md"
    out_path.write_text("\n".join(lines))
    print(f"  Generated: {out_path.name}")
    return out_path
