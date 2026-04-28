"""Tests for the LLM judge module."""

import json
from unittest.mock import patch, MagicMock

import pytest

from safejudge.judge import (
    JudgeScore,
    _build_judge_input,
    _parse_judge_response,
    judge_single,
)
from safejudge.runner import EvalResult


def _make_eval_result(
    prompt_id: str = "test_001",
    jailbreak: bool = False,
    confidence: float = 0.9,
    succeeded: bool = True,
) -> EvalResult:
    if succeeded:
        actual = {
            "jailbreak": jailbreak,
            "prompt_injection": False,
            "harmful_content": False,
            "confidence": confidence,
            "reasoning": "Test reasoning",
            "attack_types": [],
            "content_flags": [],
        }
        error = None
    else:
        actual = None
        error = "SUT failed"

    return EvalResult(
        prompt_id=prompt_id,
        mode="single",
        actual_output=actual,
        exit_code=0 if succeeded else 1,
        execution_time_ms=100,
        timestamp="2026-04-27T00:00:00Z",
        error=error,
        test_case={
            "prompt_id": prompt_id,
            "prompt_text": "test prompt",
            "expected": {
                "jailbreak": jailbreak,
                "prompt_injection": False,
                "harmful_content": False,
                "expected_attack_types": [],
                "expected_content_flags": [],
            },
        },
    )


class TestParseJudgeResponse:
    def test_valid_response(self):
        raw = json.dumps({
            "correctness_score": 5,
            "reasoning_quality": 4,
            "confidence_calibration": 3,
            "content_flag_completeness": 5,
            "overall_score": 4,
            "justification": "Good classification",
            "errors_found": [],
        })
        score = _parse_judge_response(raw, "p1", "single")
        assert score.correctness_score == 5
        assert score.overall_score == 4
        assert score.judge_error is None

    def test_invalid_json(self):
        score = _parse_judge_response("not json", "p1", "single")
        assert score.judge_error is not None
        assert score.overall_score == 0

    def test_missing_fields(self):
        raw = json.dumps({"correctness_score": 3})
        score = _parse_judge_response(raw, "p1", "single")
        assert score.correctness_score == 3
        assert score.reasoning_quality == 0  # defaults to 0


class TestBuildJudgeInput:
    def test_builds_valid_json(self):
        result = _make_eval_result()
        input_str = _build_judge_input(result)
        parsed = json.loads(input_str)
        assert "prompt" in parsed
        assert "expected" in parsed
        assert "actual" in parsed


class TestJudgeSingle:
    def test_failed_eval_result(self):
        result = _make_eval_result(succeeded=False)
        score = judge_single(result)
        assert score.overall_score == 0
        assert "SUT failed" in score.justification

    @patch("safejudge.judge.OpenAI")
    def test_successful_judge_call(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps({
                "correctness_score": 5,
                "reasoning_quality": 4,
                "confidence_calibration": 4,
                "content_flag_completeness": 5,
                "overall_score": 5,
                "justification": "Perfect",
                "errors_found": [],
            })))]
        )
        result = _make_eval_result()
        score = judge_single(result)
        assert score.correctness_score == 5
        assert score.judge_error is None

    @patch("safejudge.judge.OpenAI")
    def test_judge_api_error(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")
        result = _make_eval_result()
        score = judge_single(result)
        assert score.judge_error is not None
        assert "Connection refused" in score.judge_error
