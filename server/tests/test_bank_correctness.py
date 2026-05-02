import pytest

from bank.correctness import check, FunctionNotFound, ExecutionTimeout
from bank.schemas import CanonicalSolution, TestCase


def test_correct_solution_passes():
    sol = CanonicalSolution(
        language="python",
        code="def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen: return [seen[target-x], i]\n        seen[x] = i\n",
        time="O(n)", space="O(n)",
    )
    cases = [
        TestCase(input=[[2, 7, 11, 15], 9], expected=[0, 1]),
        TestCase(input=[[3, 2, 4], 6], expected=[1, 2]),
        TestCase(input=[[3, 3], 6], expected=[0, 1]),
    ]
    out = check(slug="two-sum", solution=sol, test_cases=cases)
    assert out.all_passed
    assert out.failures == []


def test_wrong_solution_fails():
    sol = CanonicalSolution(
        language="python",
        code="def two_sum(nums, target):\n    return [0, 0]\n",
        time="O(1)", space="O(1)",
    )
    cases = [TestCase(input=[[2, 7, 11, 15], 9], expected=[0, 1])]
    out = check(slug="two-sum", solution=sol, test_cases=cases)
    assert not out.all_passed
    assert "expected" in out.failures[0]


def test_function_name_mismatch_raises():
    sol = CanonicalSolution(
        language="python", code="def wrong(): pass\n", time="O(1)", space="O(1)",
    )
    with pytest.raises(FunctionNotFound):
        check(slug="two-sum", solution=sol, test_cases=[TestCase(input=[], expected=None)])


def test_infinite_loop_times_out():
    sol = CanonicalSolution(
        language="python", code="def two_sum(nums, target):\n    while True: pass\n",
        time="O(1)", space="O(1)",
    )
    with pytest.raises(ExecutionTimeout):
        check(slug="two-sum", solution=sol, test_cases=[
            TestCase(input=[[1, 2], 3], expected=[0, 1])
        ], timeout_s=2)


def test_set_equality_for_unordered_returns():
    """Some problems return order-insensitive results. v0.5a default is strict
    list equality - ordering issues surface as test_case fixes (re-author the
    expected) rather than special-casing here."""
    sol = CanonicalSolution(
        language="python", code="def two_sum(nums, target):\n    return [1, 0]\n",
        time="O(1)", space="O(1)",
    )
    cases = [TestCase(input=[[2, 7], 9], expected=[0, 1])]
    out = check(slug="two-sum", solution=sol, test_cases=cases)
    assert not out.all_passed  # strict equality - good signal of bad output
