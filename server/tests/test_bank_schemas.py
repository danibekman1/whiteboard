import pytest
from pydantic import ValidationError
from bank.schemas import QuestionJSON


def _good_question_dict() -> dict:
    return {
        "slug": "two-sum",
        "title": "Two Sum",
        "statement": "Given an array of integers nums and an integer target, return indices that sum to target.",
        "difficulty": "easy",
        "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {
            "language": "python",
            "code": "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen: return [seen[target-x], i]\n        seen[x] = i",
            "time": "O(n)",
            "space": "O(n)",
        },
        "test_cases": [
            {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"input": [[3, 2, 4], 6], "expected": [1, 2]},
            {"input": [[3, 3], 6], "expected": [0, 1]},
        ],
        "steps": [
            {"ordinal": i, "description": f"step {i} description text", "pattern_tags": ["x"], "hints": [
                {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"},
            ]} for i in range(1, 4)
        ],
    }


def test_good_question_validates():
    q = QuestionJSON.model_validate(_good_question_dict())
    assert q.slug == "two-sum"
    assert len(q.steps) == 3


def test_step_count_too_few_rejected():
    d = _good_question_dict()
    d["steps"] = d["steps"][:2]
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)


def test_step_count_too_many_rejected():
    d = _good_question_dict()
    d["steps"] = [{"ordinal": i, "description": "step description here", "pattern_tags": [], "hints": [
        {"level": 1, "text": "h"}, {"level": 2, "text": "h"}, {"level": 3, "text": "h"},
    ]} for i in range(1, 12)]
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)


def test_step_ordinal_must_start_at_1_and_be_dense():
    d = _good_question_dict()
    d["steps"][0]["ordinal"] = 2  # gap
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)


def test_each_step_must_have_three_hints_at_levels_1_2_3():
    d = _good_question_dict()
    d["steps"][0]["hints"] = [{"level": 1, "text": "only one"}]
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)

    d = _good_question_dict()
    d["steps"][0]["hints"] = [
        {"level": 1, "text": "a"},
        {"level": 1, "text": "dup"},
        {"level": 3, "text": "c"},
    ]
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)


def test_unknown_difficulty_rejected():
    d = _good_question_dict()
    d["difficulty"] = "trivial"
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)


def test_min_three_test_cases():
    d = _good_question_dict()
    d["test_cases"] = d["test_cases"][:2]
    with pytest.raises(ValidationError):
        QuestionJSON.model_validate(d)
