"""Dataset schema, loader, and validator for evaluation test cases."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from safejudge.config import CATEGORIES, CONVERSATIONS_DIR, PROMPTS_DIR


@dataclass
class ExpectedResult:
    """Ground-truth expected classification for a test case."""

    jailbreak: bool
    prompt_injection: bool
    harmful_content: bool
    min_confidence: float = 0.0
    expected_attack_types: list[str] = field(default_factory=list)
    expected_content_flags: list[str] = field(default_factory=list)


@dataclass
class TestCase:
    """A single evaluation test case with ground-truth labels."""

    prompt_id: str
    category: str
    subcategory: str
    prompt_text: str
    expected: ExpectedResult
    conversation_history: list[dict[str, str]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_multi_turn(self) -> bool:
        return self.conversation_history is not None and len(self.conversation_history) > 0

    @property
    def is_malicious(self) -> bool:
        return (
            self.expected.jailbreak
            or self.expected.prompt_injection
            or self.expected.harmful_content
        )


def _parse_expected(data: dict) -> ExpectedResult:
    return ExpectedResult(
        jailbreak=data["jailbreak"],
        prompt_injection=data["prompt_injection"],
        harmful_content=data["harmful_content"],
        min_confidence=data.get("min_confidence", 0.0),
        expected_attack_types=data.get("expected_attack_types", []),
        expected_content_flags=data.get("expected_content_flags", []),
    )


def _parse_test_case(data: dict) -> TestCase:
    return TestCase(
        prompt_id=data["prompt_id"],
        category=data["category"],
        subcategory=data.get("subcategory", ""),
        prompt_text=data["prompt_text"],
        expected=_parse_expected(data["expected"]),
        conversation_history=data.get("conversation_history"),
        metadata=data.get("metadata", {}),
    )


def load_dataset(
    prompts_dir: Path = PROMPTS_DIR,
    conversations_dir: Path = CONVERSATIONS_DIR,
) -> list[TestCase]:
    """Load all test cases from prompt and conversation dataset directories."""
    cases: list[TestCase] = []

    for directory in (prompts_dir, conversations_dir):
        if not directory.exists():
            continue
        for json_file in sorted(directory.glob("*.json")):
            with open(json_file) as f:
                data = json.load(f)
            cases.append(_parse_test_case(data))

    return cases


def validate_dataset(cases: list[TestCase]) -> list[str]:
    """Validate the dataset and return a list of error messages (empty = valid)."""
    errors: list[str] = []

    if not cases:
        errors.append("Dataset is empty")
        return errors

    # Check for duplicate IDs
    ids = [c.prompt_id for c in cases]
    seen: set[str] = set()
    for pid in ids:
        if pid in seen:
            errors.append(f"Duplicate prompt_id: {pid}")
        seen.add(pid)

    # Check category validity
    for case in cases:
        if case.category not in CATEGORIES:
            errors.append(
                f"{case.prompt_id}: unknown category '{case.category}' "
                f"(valid: {CATEGORIES})"
            )

    # Check minimum category coverage
    category_counts: dict[str, int] = {}
    for case in cases:
        category_counts[case.category] = category_counts.get(case.category, 0) + 1
    for cat in CATEGORIES:
        count = category_counts.get(cat, 0)
        if count < 3:
            errors.append(
                f"Category '{cat}' has only {count} examples (minimum 3 recommended)"
            )

    # Validate prompt text is non-empty
    for case in cases:
        if not case.prompt_text.strip():
            errors.append(f"{case.prompt_id}: empty prompt_text")

    return errors


def get_by_category(cases: list[TestCase], category: str) -> list[TestCase]:
    """Filter test cases by category."""
    return [c for c in cases if c.category == category]


def get_summary_stats(cases: list[TestCase]) -> dict[str, Any]:
    """Return summary statistics about the dataset."""
    category_counts: dict[str, int] = {}
    for case in cases:
        category_counts[case.category] = category_counts.get(case.category, 0) + 1

    malicious_count = sum(1 for c in cases if c.is_malicious)
    benign_count = len(cases) - malicious_count
    multi_turn_count = sum(1 for c in cases if c.is_multi_turn)

    return {
        "total": len(cases),
        "malicious": malicious_count,
        "benign": benign_count,
        "multi_turn": multi_turn_count,
        "single_turn": len(cases) - multi_turn_count,
        "by_category": category_counts,
    }
