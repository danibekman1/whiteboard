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
    # Input value here is irrelevant - the runner exits before reaching cases.
    with pytest.raises(FunctionNotFound):
        check(slug="two-sum", solution=sol, test_cases=[TestCase(input=[1], expected=None)])


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


def test_boolean_and_none_values_pass_through_runner():
    """Regression: cases were embedded as Python source, so JSON True
    became the undefined identifier `true`. They're now JSON-parsed at
    runtime."""
    sol = CanonicalSolution(
        language="python",
        code="def valid_anagram(s, t):\n    return sorted(s) == sorted(t)\n",
        time="O(n log n)", space="O(1)",
    )
    cases = [
        TestCase(input=["anagram", "nagaram"], expected=True),
        TestCase(input=["rat", "car"], expected=False),
        TestCase(input=["a", "a"], expected=True),
    ]
    out = check(slug="valid-anagram", solution=sol, test_cases=cases)
    assert out.all_passed, out.failures


def test_linked_list_marker_decodes_and_compares():
    """reverse-linked-list-style: __linked_list__ markers decode to real
    ListNode chains; canonical code uses ListNode by name."""
    code = (
        "def reverse_linked_list(head):\n"
        "    prev = None\n"
        "    curr = head\n"
        "    while curr is not None:\n"
        "        nxt = curr.next\n"
        "        curr.next = prev\n"
        "        prev = curr\n"
        "        curr = nxt\n"
        "    return prev\n"
    )
    sol = CanonicalSolution(language="python", code=code, time="O(n)", space="O(1)")
    cases = [
        TestCase(
            input=[{"__linked_list__": [1, 2, 3, 4, 5]}],
            expected={"__linked_list__": [5, 4, 3, 2, 1]},
        ),
        TestCase(
            input=[{"__linked_list__": []}],
            expected={"__linked_list__": []},
        ),
        TestCase(
            input=[{"__linked_list__": [42]}],
            expected={"__linked_list__": [42]},
        ),
    ]
    out = check(slug="reverse-linked-list", solution=sol, test_cases=cases)
    assert out.all_passed, out.failures


def test_runner_nonzero_exit_surfaces_as_failure():
    """Candidate code with a true syntax error (parse-time crash) exits the
    runner with a non-zero, non-2 returncode. This must surface as a
    CheckResult failure (not raise FunctionNotFound or ExecutionTimeout)
    so the validator reports a useful triage message instead of crashing
    the run."""
    sol = CanonicalSolution(
        language="python",
        # Genuine SyntaxError - parser rejects this at compile time.
        code="def two_sum(nums, target:\n    return [0, 1]\n",
        time="O(1)", space="O(1)",
    )
    out = check(
        slug="two-sum", solution=sol,
        test_cases=[TestCase(input=[[1, 2], 3], expected=[0, 1])],
    )
    assert not out.all_passed
    assert any("runner exit=" in f for f in out.failures)


def test_tree_marker_decodes_and_compares():
    """invert-binary-tree-style: __tree__ markers in LeetCode BFS form."""
    code = (
        "def invert_binary_tree(root):\n"
        "    if root is None: return None\n"
        "    root.left, root.right = invert_binary_tree(root.right), invert_binary_tree(root.left)\n"
        "    return root\n"
    )
    sol = CanonicalSolution(language="python", code=code, time="O(n)", space="O(n)")
    cases = [
        TestCase(
            input=[{"__tree__": [4, 2, 7, 1, 3, 6, 9]}],
            expected={"__tree__": [4, 7, 2, 9, 6, 3, 1]},
        ),
        TestCase(
            input=[{"__tree__": []}],
            expected={"__tree__": []},
        ),
    ]
    out = check(slug="invert-binary-tree", solution=sol, test_cases=cases)
    assert out.all_passed, out.failures
