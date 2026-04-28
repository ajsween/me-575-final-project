"""Tests for the evaluation runner module."""

import json
from unittest.mock import patch, MagicMock

import pytest

from safejudge.dataset import TestCase, ExpectedResult
from safejudge.runner import run_single, _build_command, EvalResult


def _make_test_case(
    prompt_id: str = "test_001",
    prompt_text: str = "test prompt",
    category: str = "safe",
    malicious: bool = False,
    conversation_history: list | None = None,
) -> TestCase:
    return TestCase(
        prompt_id=prompt_id,
        category=category,
        subcategory="test",
        prompt_text=prompt_text,
        expected=ExpectedResult(
            jailbreak=malicious,
            prompt_injection=malicious,
            harmful_content=malicious,
        ),
        conversation_history=conversation_history,
    )


class TestBuildCommand:
    def test_single_mode(self):
        tc = _make_test_case()
        cmd = _build_command(tc, "single")
        assert "--prompt" in cmd
        assert "test prompt" in cmd
        assert "--ensemble" not in cmd
        assert "--use-safety-classifier" not in cmd

    def test_ensemble_mode(self):
        tc = _make_test_case()
        cmd = _build_command(tc, "ensemble")
        assert "--ensemble" in cmd
        assert "--secondary-model" in cmd

    def test_safety_mode(self):
        tc = _make_test_case()
        cmd = _build_command(tc, "safety_classifier")
        assert "--use-safety-classifier" in cmd
        assert "--safety-model" in cmd

    def test_with_history(self, tmp_path):
        tc = _make_test_case()
        history_path = tmp_path / "hist.jsonl"
        history_path.touch()
        cmd = _build_command(tc, "single", history_path)
        assert "--history" in cmd
        assert str(history_path) in cmd


class TestRunSingle:
    @patch("safejudge.runner.subprocess.run")
    def test_successful_run(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='{"jailbreak": false, "prompt_injection": false, "harmful_content": false, "confidence": 0.9}',
            stderr="",
            returncode=0,
        )
        tc = _make_test_case()
        result = run_single(tc, "single")
        assert result.succeeded
        assert result.actual_output["jailbreak"] is False
        assert result.exit_code == 0
        assert result.error is None

    @patch("safejudge.runner.subprocess.run")
    def test_malicious_detection(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='{"jailbreak": true, "prompt_injection": true, "harmful_content": false, "confidence": 0.95}',
            stderr="",
            returncode=2,
        )
        tc = _make_test_case(malicious=True)
        result = run_single(tc, "single")
        assert result.succeeded
        assert result.actual_output["jailbreak"] is True
        assert result.exit_code == 2

    @patch("safejudge.runner.subprocess.run")
    def test_invalid_json_output(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="not valid json",
            stderr="",
            returncode=0,
        )
        tc = _make_test_case()
        result = run_single(tc, "single")
        assert not result.succeeded
        assert "JSON parse error" in result.error

    @patch("safejudge.runner.subprocess.run")
    def test_sut_error(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Model not found",
            returncode=1,
        )
        tc = _make_test_case()
        result = run_single(tc, "single")
        assert not result.succeeded
        assert "SUT error" in result.error

    @patch("safejudge.runner.subprocess.run")
    def test_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=120)
        tc = _make_test_case()
        result = run_single(tc, "single")
        assert not result.succeeded
        assert "Timeout" in result.error
        assert result.exit_code == -1

    @patch("safejudge.runner.subprocess.run")
    def test_result_contains_test_case(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='{"jailbreak": false}',
            stderr="",
            returncode=0,
        )
        tc = _make_test_case(prompt_id="tc_check")
        result = run_single(tc, "single")
        assert result.test_case["prompt_id"] == "tc_check"
        assert result.mode == "single"
