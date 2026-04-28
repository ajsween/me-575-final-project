"""Tests for the metrics module."""

import pytest

from safejudge.metrics import (
    BinaryMetrics,
    compute_binary_metrics,
    compute_overall_accuracy,
    compute_benign_fpr,
    compute_confidence_calibration,
    compute_cross_model_consistency,
    compute_all_metrics,
    compute_judge_summary,
)
from safejudge.runner import EvalResult
from safejudge.judge import JudgeScore


def _make_result(
    prompt_id: str,
    expected_jailbreak: bool,
    actual_jailbreak: bool,
    expected_injection: bool = False,
    actual_injection: bool = False,
    expected_harmful: bool = False,
    actual_harmful: bool = False,
    confidence: float = 0.9,
    mode: str = "single",
    is_malicious: bool | None = None,
    category: str = "safe",
) -> EvalResult:
    if is_malicious is None:
        is_malicious = expected_jailbreak or expected_injection or expected_harmful
    return EvalResult(
        prompt_id=prompt_id,
        mode=mode,
        actual_output={
            "jailbreak": actual_jailbreak,
            "prompt_injection": actual_injection,
            "harmful_content": actual_harmful,
            "confidence": confidence,
        },
        exit_code=0,
        execution_time_ms=100,
        timestamp="2026-04-27T00:00:00Z",
        test_case={
            "prompt_id": prompt_id,
            "category": category,
            "subcategory": "test",
            "prompt_text": "test",
            "expected": {
                "jailbreak": expected_jailbreak,
                "prompt_injection": expected_injection,
                "harmful_content": expected_harmful,
            },
            "is_malicious": is_malicious,
        },
    )


class TestBinaryMetrics:
    def test_perfect_accuracy(self):
        m = BinaryMetrics("test", true_positives=5, true_negatives=5)
        assert m.accuracy == 1.0
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0

    def test_all_false_positives(self):
        m = BinaryMetrics("test", false_positives=5, true_negatives=5)
        assert m.accuracy == 0.5
        assert m.precision == 0.0

    def test_all_false_negatives(self):
        m = BinaryMetrics("test", true_positives=0, false_negatives=5, true_negatives=5)
        assert m.recall == 0.0

    def test_empty(self):
        m = BinaryMetrics("test")
        assert m.accuracy == 0.0
        assert m.f1 == 0.0


class TestComputeMetrics:
    def test_compute_binary_metrics(self):
        results = [
            _make_result("p1", expected_jailbreak=True, actual_jailbreak=True),   # TP
            _make_result("p2", expected_jailbreak=True, actual_jailbreak=False),  # FN
            _make_result("p3", expected_jailbreak=False, actual_jailbreak=False), # TN
            _make_result("p4", expected_jailbreak=False, actual_jailbreak=True),  # FP
        ]
        m = compute_binary_metrics(results, "jailbreak")
        assert m.true_positives == 1
        assert m.false_negatives == 1
        assert m.true_negatives == 1
        assert m.false_positives == 1
        assert m.accuracy == 0.5
        assert m.precision == 0.5
        assert m.recall == 0.5

    def test_overall_accuracy_all_correct(self):
        results = [
            _make_result("p1", True, True, True, True, True, True),
            _make_result("p2", False, False, False, False, False, False),
        ]
        assert compute_overall_accuracy(results) == 1.0

    def test_overall_accuracy_partial(self):
        results = [
            _make_result("p1", True, True, True, True, True, True),
            _make_result("p2", False, False, False, False, False, False),
            _make_result("p3", True, False, False, False, False, False),  # jailbreak wrong
        ]
        assert compute_overall_accuracy(results) == pytest.approx(2 / 3, rel=1e-2)

    def test_benign_fpr(self):
        results = [
            _make_result("safe1", False, False, category="safe", is_malicious=False),
            _make_result("safe2", False, True, category="safe", is_malicious=False),  # FP
            _make_result("mal1", True, True, category="jailbreak", is_malicious=True),
        ]
        assert compute_benign_fpr(results) == 0.5

    def test_confidence_calibration(self):
        results = [
            _make_result("p1", False, False, confidence=0.1),
            _make_result("p2", True, True, confidence=0.9),
        ]
        cal = compute_confidence_calibration(results, n_bins=5)
        assert len(cal) == 5
        assert all("avg_confidence" in c for c in cal)

    def test_cross_model_consistency_perfect(self):
        results = [
            _make_result("p1", True, True, mode="single"),
            _make_result("p1", True, True, mode="ensemble"),
        ]
        assert compute_cross_model_consistency(results) == 1.0

    def test_cross_model_consistency_disagreement(self):
        results = [
            _make_result("p1", True, True, mode="single"),
            _make_result("p1", True, False, mode="ensemble"),
        ]
        assert compute_cross_model_consistency(results) == 0.0


class TestComputeAllMetrics:
    def test_produces_report(self):
        results = [
            _make_result("p1", True, True, True, True, True, True, category="jailbreak", is_malicious=True),
            _make_result("p2", False, False, False, False, False, False, category="safe", is_malicious=False),
        ]
        report = compute_all_metrics(results)
        assert report.total_evaluated == 2
        assert report.overall_accuracy == 1.0
        d = report.to_dict()
        assert "jailbreak" in d
        assert "overall_accuracy" in d


class TestJudgeSummary:
    def test_summary_with_scores(self):
        scores = [
            JudgeScore("p1", "single", 5, 4, 3, 5, 4, "good"),
            JudgeScore("p2", "single", 3, 3, 2, 4, 3, "ok"),
        ]
        summary = compute_judge_summary(scores)
        assert summary["valid"] == 2
        assert summary["correctness_score"]["mean"] == 4.0
        assert summary["overall_score"]["mean"] == 3.5

    def test_summary_with_errors(self):
        scores = [
            JudgeScore("p1", "single", 0, 0, 0, 0, 0, "", judge_error="fail"),
        ]
        summary = compute_judge_summary(scores)
        assert summary["valid"] == 0
        assert summary["error_count"] == 1
