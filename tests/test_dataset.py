"""Tests for the dataset module."""

import json
import tempfile
from pathlib import Path

import pytest

from safejudge.dataset import (
    TestCase,
    load_dataset,
    validate_dataset,
    get_by_category,
    get_summary_stats,
)


def _make_case(prompt_id: str, category: str = "safe", malicious: bool = False) -> dict:
    return {
        "prompt_id": prompt_id,
        "category": category,
        "subcategory": "test",
        "prompt_text": f"Test prompt for {prompt_id}",
        "expected": {
            "jailbreak": malicious,
            "prompt_injection": malicious,
            "harmful_content": malicious,
            "min_confidence": 0.8,
            "expected_attack_types": [],
            "expected_content_flags": [],
        },
        "metadata": {"source": "test"},
    }


@pytest.fixture
def dataset_dir(tmp_path):
    prompts = tmp_path / "prompts"
    convos = tmp_path / "conversations"
    prompts.mkdir()
    convos.mkdir()
    return tmp_path


def test_load_empty_dataset(dataset_dir):
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    assert cases == []


def test_load_single_prompt(dataset_dir):
    case_data = _make_case("test_001")
    (dataset_dir / "prompts" / "test_001.json").write_text(json.dumps(case_data))
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    assert len(cases) == 1
    assert cases[0].prompt_id == "test_001"
    assert cases[0].category == "safe"


def test_load_with_conversation_history(dataset_dir):
    case_data = _make_case("conv_001", category="multi_turn", malicious=True)
    case_data["conversation_history"] = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    (dataset_dir / "conversations" / "conv_001.json").write_text(json.dumps(case_data))
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    assert len(cases) == 1
    assert cases[0].is_multi_turn is True
    assert cases[0].is_malicious is True


def test_validate_detects_duplicates(dataset_dir):
    for i in range(2):
        (dataset_dir / "prompts" / f"dup_{i}.json").write_text(
            json.dumps(_make_case("same_id"))
        )
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    errors = validate_dataset(cases)
    assert any("Duplicate" in e for e in errors)


def test_validate_detects_unknown_category(dataset_dir):
    case_data = _make_case("bad_cat", category="nonexistent")
    (dataset_dir / "prompts" / "bad_cat.json").write_text(json.dumps(case_data))
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    errors = validate_dataset(cases)
    assert any("unknown category" in e for e in errors)


def test_validate_detects_empty_prompt(dataset_dir):
    case_data = _make_case("empty_prompt")
    case_data["prompt_text"] = ""
    (dataset_dir / "prompts" / "empty.json").write_text(json.dumps(case_data))
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    errors = validate_dataset(cases)
    assert any("empty prompt_text" in e for e in errors)


def test_get_by_category(dataset_dir):
    for i, cat in enumerate(("safe", "safe", "jailbreak")):
        pid = f"{cat}_{i}"
        (dataset_dir / "prompts" / f"{pid}.json").write_text(
            json.dumps(_make_case(pid, category=cat))
        )
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    safe = get_by_category(cases, "safe")
    assert len(safe) == 2


def test_get_summary_stats(dataset_dir):
    for i, cat in enumerate(["safe", "safe", "jailbreak", "harmful"]):
        case = _make_case(f"stat_{i}", category=cat, malicious=(cat != "safe"))
        (dataset_dir / "prompts" / f"stat_{i}.json").write_text(json.dumps(case))
    cases = load_dataset(dataset_dir / "prompts", dataset_dir / "conversations")
    stats = get_summary_stats(cases)
    assert stats["total"] == 4
    assert stats["malicious"] == 2
    assert stats["benign"] == 2


def test_real_dataset():
    """Validate the actual generated dataset."""
    real_prompts = Path("datasets/prompts")
    real_convos = Path("datasets/conversations")
    if not real_prompts.exists():
        pytest.skip("Dataset not generated yet")
    cases = load_dataset(real_prompts, real_convos)
    assert len(cases) >= 90, f"Expected >=90 cases, got {len(cases)}"
    errors = validate_dataset(cases)
    # Filter to only critical errors (not category coverage warnings)
    critical = [e for e in errors if "Duplicate" in e or "empty prompt_text" in e or "unknown category" in e]
    assert not critical, f"Dataset validation errors: {critical}"
