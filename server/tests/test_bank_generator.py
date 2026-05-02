from unittest.mock import MagicMock
import pytest
from bank.generator import generate, GenerationInput
from bank.schemas import QuestionJSON


def _good_payload():
    return {
        "slug": "two-sum",
        "title": "Two Sum",
        "statement": "Given an array of integers nums and a target, return indices summing to target.",
        "difficulty": "easy",
        "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {
            "language": "python",
            "code": "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen: return [seen[target-x], i]\n        seen[x] = i",
            "time": "O(n)", "space": "O(n)",
        },
        "test_cases": [
            {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"input": [[3, 2, 4], 6], "expected": [1, 2]},
            {"input": [[3, 3], 6], "expected": [0, 1]},
        ],
        "steps": [
            {"ordinal": i, "description": f"some descriptive step {i} text", "pattern_tags": ["x"], "hints": [
                {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"},
            ]} for i in range(1, 4)
        ],
    }


def _fake_client(payload: dict):
    client = MagicMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_question"
    block.input = payload
    response.content = [block]
    client.messages.create.return_value = response
    return client


def test_generate_returns_validated_question():
    client = _fake_client(_good_payload())
    q = generate(
        client=client,
        seed=GenerationInput(
            slug="two-sum", title="Two Sum", difficulty="easy",
            topic="arrays-hashing", leetcode_id=1,
            optimal_time="O(n)", optimal_space="O(n)",
        ),
    )
    assert isinstance(q, QuestionJSON)
    assert q.slug == "two-sum"


def test_generate_raises_on_no_tool_use():
    client = MagicMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "oops"
    response.content = [block]
    client.messages.create.return_value = response
    with pytest.raises(ValueError, match="no tool_use"):
        generate(
            client=client,
            seed=GenerationInput(slug="x", title="X", difficulty="easy", topic="t"),
        )
