"""Tests for the release gate module."""

import pytest

from safejudge.gates import evaluate_gates, GateResult
from safejudge.metrics import BinaryMetrics, MetricReport


def _make_report(
    overall_acc: float = 0.95,
    jailbreak_recall: float = 0.92,
    harmful_recall: float = 0.97,
    benign_fpr: float = 0.05,
    obfuscation: dict | None = None,
    cross_model: float = 0.90,
) -> MetricReport:
    jailbreak = BinaryMetrics("jailbreak")
    # Set TP/FN to achieve desired recall
    jailbreak.true_positives = int(jailbreak_recall * 100)
    jailbreak.false_negatives = 100 - jailbreak.true_positives

    harmful = BinaryMetrics("harmful_content")
    harmful.true_positives = int(harmful_recall * 100)
    harmful.false_negatives = 100 - harmful.true_positives

    return MetricReport(
        jailbreak=jailbreak,
        harmful_content=harmful,
        overall_accuracy=overall_acc,
        benign_false_positive_rate=benign_fpr,
        obfuscation_breakdown=obfuscation or {"base64": 0.85, "rot13": 0.80},
        cross_model_consistency=cross_model,
        total_evaluated=100,
    )


class TestEvaluateGates:
    def test_all_pass(self):
        report = _make_report()
        result = evaluate_gates(report)
        assert result.all_passed
        assert result.overall_verdict == "PASS"
        assert all(d.passed for d in result.decisions)

    def test_accuracy_block(self):
        report = _make_report(overall_acc=0.85)
        result = evaluate_gates(report)
        assert result.blocked
        assert result.overall_verdict == "BLOCK_RELEASE"
        acc_gate = next(d for d in result.decisions if d.gate_name == "overall_accuracy")
        assert not acc_gate.passed
        assert acc_gate.severity == "BLOCK_RELEASE"

    def test_jailbreak_recall_block(self):
        report = _make_report(jailbreak_recall=0.80)
        result = evaluate_gates(report)
        assert result.blocked

    def test_harmful_recall_block(self):
        report = _make_report(harmful_recall=0.90)
        result = evaluate_gates(report)
        assert result.blocked

    def test_fpr_block(self):
        report = _make_report(benign_fpr=0.15)
        result = evaluate_gates(report)
        assert result.blocked

    def test_obfuscation_flag(self):
        report = _make_report(obfuscation={"base64": 0.70, "rot13": 0.60})
        result = evaluate_gates(report)
        # Obfuscation is a flag, not a block
        assert not result.blocked
        assert result.overall_verdict == "FLAG_FOR_REVIEW"
        obf_gate = next(d for d in result.decisions if d.gate_name == "obfuscation_detection_rate")
        assert not obf_gate.passed
        assert obf_gate.severity == "FLAG_FOR_REVIEW"

    def test_cross_model_flag(self):
        report = _make_report(cross_model=0.80)
        result = evaluate_gates(report)
        assert not result.blocked
        assert result.overall_verdict == "FLAG_FOR_REVIEW"

    def test_multiple_failures(self):
        report = _make_report(overall_acc=0.80, jailbreak_recall=0.70, benign_fpr=0.20)
        result = evaluate_gates(report)
        assert result.blocked
        failed = [d for d in result.decisions if not d.passed]
        assert len(failed) >= 3
