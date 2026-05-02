"""Sandboxed correctness checker.

Spawns a subprocess to run the candidate solution against test cases. NOT a
strict security sandbox - assumes generated code is from our own Opus and run
on our own machine. Timeouts protect against infinite loops; subprocess
isolation protects against accidental import-time side effects. That's the
trust boundary for v0.5a. Tighten when we ship hosted.

The runner injects standard ListNode/TreeNode classes plus a marker codec:
  {"__linked_list__": [1,2,3]}        <-> ListNode(1)->ListNode(2)->ListNode(3)
  {"__tree__": [1, 2, 3, null, 4]}    <-> LeetCode BFS array form
Inputs and expecteds are decoded before calling the function; the actual
return value is compared to the expected with a structural equality that
walks ListNode/TreeNode chains. This lets us compare canonical solutions
written in natural LeetCode style against JSON-encoded test_cases."""
from __future__ import annotations
import json
import subprocess
import sys
from dataclasses import dataclass

from bank.schemas import CanonicalSolution, TestCase


class FunctionNotFound(Exception):
    ...


class ExecutionTimeout(Exception):
    ...


@dataclass
class CheckResult:
    all_passed: bool
    failures: list[str]


def _func_name_from_slug(slug: str) -> str:
    return slug.replace("-", "_")


# Prelude defines ListNode/TreeNode and a marker codec. The candidate code is
# then injected after; canonical solutions reference ListNode/TreeNode by
# name without redefining them. Cases are passed as a JSON string and
# parsed at runtime to keep Python-vs-JSON literal differences (true/True,
# null/None) out of the source-injection path.
_RUNNER_PRELUDE = '''
import json, sys


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def _decode(v):
    if isinstance(v, dict) and len(v) == 1:
        if "__linked_list__" in v:
            arr = v["__linked_list__"]
            head = None
            for x in reversed(arr):
                head = ListNode(_decode(x), head)
            return head
        if "__tree__" in v:
            arr = v["__tree__"]
            if not arr:
                return None
            it = iter(arr)
            root = TreeNode(_decode(next(it)))
            q = [root]
            i = 0
            while i < len(q):
                node = q[i]
                i += 1
                try:
                    lv = next(it)
                except StopIteration:
                    break
                if lv is not None:
                    node.left = TreeNode(_decode(lv))
                    q.append(node.left)
                try:
                    rv = next(it)
                except StopIteration:
                    break
                if rv is not None:
                    node.right = TreeNode(_decode(rv))
                    q.append(node.right)
            return root
    if isinstance(v, list):
        return [_decode(x) for x in v]
    return v


def _eq(a, b):
    if isinstance(a, ListNode) or isinstance(b, ListNode):
        while True:
            if a is None and b is None:
                return True
            if a is None or b is None:
                return False
            if not isinstance(a, ListNode) or not isinstance(b, ListNode):
                return False
            if a.val != b.val:
                return False
            a, b = a.next, b.next
    if isinstance(a, TreeNode) or isinstance(b, TreeNode):
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if not isinstance(a, TreeNode) or not isinstance(b, TreeNode):
            return False
        return a.val == b.val and _eq(a.left, b.left) and _eq(a.right, b.right)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    return a == b


def _encode(v):
    """Best-effort reserialize for failure-message display only."""
    if isinstance(v, ListNode):
        out = []
        cur = v
        seen = set()
        while cur is not None:
            if id(cur) in seen:
                out.append("...cycle...")
                break
            seen.add(id(cur))
            out.append(_encode(cur.val))
            cur = cur.next
        return {"__linked_list__": out}
    if isinstance(v, TreeNode):
        out = []
        q = [v]
        while q:
            node = q.pop(0)
            if node is None:
                out.append(None)
            else:
                out.append(_encode(node.val))
                q.append(node.left)
                q.append(node.right)
        while out and out[-1] is None:
            out.pop()
        return {"__tree__": out}
    if isinstance(v, list):
        return [_encode(x) for x in v]
    if isinstance(v, tuple):
        return [_encode(x) for x in v]
    if isinstance(v, dict):
        return {k: _encode(x) for k, x in v.items()}
    return v
'''


_RUNNER_EPILOGUE = '''
fn = globals().get(__FN_NAME__)
if fn is None:
    print(json.dumps({"error": "function_not_found", "expected": __FN_NAME__}))
    sys.exit(2)
cases = json.loads(__CASES_JSON__)
results = []
for i, c in enumerate(cases):
    try:
        decoded_input = [_decode(x) for x in c["input"]]
        decoded_expected = _decode(c["expected"])
        actual = fn(*decoded_input)
        ok = _eq(actual, decoded_expected)
        results.append({
            "i": i,
            "ok": ok,
            "actual": _encode(actual),
            "expected": c["expected"],
        })
    except Exception as e:
        results.append({
            "i": i,
            "ok": False,
            "exception": repr(e),
            "expected": c["expected"],
        })
print(json.dumps(results))
'''


def _build_runner(code: str, fn_name: str, cases_json: str) -> str:
    epilogue = _RUNNER_EPILOGUE.replace("__FN_NAME__", json.dumps(fn_name))
    epilogue = epilogue.replace("__CASES_JSON__", json.dumps(cases_json))
    return _RUNNER_PRELUDE + "\n" + code + "\n" + epilogue


def check(
    *,
    slug: str,
    solution: CanonicalSolution,
    test_cases: list[TestCase],
    timeout_s: float = 10.0,
) -> CheckResult:
    fn = _func_name_from_slug(slug)
    cases_json = json.dumps([{"input": c.input, "expected": c.expected} for c in test_cases])
    runner = _build_runner(solution.code, fn, cases_json)
    try:
        cp = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise ExecutionTimeout(f"{slug} exceeded {timeout_s}s") from e

    if cp.returncode == 2:
        raise FunctionNotFound(f"{fn!r} not defined in {slug} solution")
    if cp.returncode != 0:
        return CheckResult(all_passed=False, failures=[f"runner exit={cp.returncode}: {cp.stderr.strip()}"])

    results = json.loads(cp.stdout.strip().splitlines()[-1])
    failures = [
        f"case {r['i']}: actual={r.get('actual')!r}, expected={r['expected']!r}"
        + (f" (exception: {r['exception']})" if "exception" in r else "")
        for r in results if not r["ok"]
    ]
    return CheckResult(all_passed=not failures, failures=failures)
