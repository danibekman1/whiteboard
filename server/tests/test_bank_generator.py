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


def _make_response(payload: dict):
    response = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_question"
    block.input = payload
    response.content = [block]
    return response


def test_generate_with_retries_retries_on_validation_failure():
    """First call returns a payload missing one hint; second call returns valid."""
    bad = _good_payload()
    bad["steps"][0]["hints"] = [{"level": 1, "text": "only one"}]
    good = _good_payload()
    client = MagicMock()
    client.messages.create.side_effect = [_make_response(bad), _make_response(good)]

    from bank.generator import generate_with_retries
    q = generate_with_retries(
        client=client,
        seed=GenerationInput(slug="two-sum", title="Two Sum", difficulty="easy", topic="arrays-hashing"),
        max_attempts=3,
    )
    assert q.slug == "two-sum"
    assert client.messages.create.call_count == 2
    second_call_msg = client.messages.create.call_args_list[1][1]["messages"][0]["content"]
    assert "hints" in second_call_msg.lower() or "level" in second_call_msg.lower()


def test_generate_with_retries_gives_up_after_max():
    bad = _good_payload()
    bad["steps"] = bad["steps"][:1]  # too few steps - always fails
    client = MagicMock()
    client.messages.create.return_value = _make_response(bad)

    from bank.generator import generate_with_retries, GenerationFailed
    with pytest.raises(GenerationFailed) as ei:
        generate_with_retries(
            client=client,
            seed=GenerationInput(slug="x", title="X", difficulty="easy", topic="t"),
            max_attempts=3,
        )
    assert client.messages.create.call_count == 3
    assert len(ei.value.attempt_errors) == 3


def test_generate_with_retries_bails_on_non_retryable_api_error():
    """Auth / billing / bad-request errors must NOT be retried with feedback;
    the orchestrator needs to stop the whole run, not burn more retries."""
    import anthropic
    client = MagicMock()
    # Build a 400 with the same shape Anthropic raises (it requires response/body args).
    response = MagicMock()
    response.status_code = 400
    err = anthropic.BadRequestError(
        message="credit balance is too low",
        response=response,
        body={"error": {"message": "credit balance is too low"}},
    )
    client.messages.create.side_effect = err

    from bank.generator import generate_with_retries
    with pytest.raises(anthropic.BadRequestError):
        generate_with_retries(
            client=client,
            seed=GenerationInput(slug="x", title="X", difficulty="easy", topic="t"),
            max_attempts=3,
        )
    # Bailed after the first call - did not waste 2 more retries.
    assert client.messages.create.call_count == 1
