# Bank question generator — sub-agent prompt template

> **Use this when**: developer has no Anthropic API credits but wants to populate
> the bank locally. The orchestrating Claude Code session dispatches one
> sub-agent per slug; each sub-agent writes its JSON to disk via the Write tool,
> billed against the developer's Claude Code subscription.
>
> **Production path (`bank/generator.py` via Anthropic SDK) is unchanged and
> remains the supported flow** for CI / users with API credits.

---

## Per-agent prompt (substitute the bracketed slots)

You are an expert software-engineering interview question author.

Your task: produce ONE complete question record for the LeetCode-style problem
described below, and write it to disk as a JSON file. You are running as a
Claude Code sub-agent and must call the Write tool to produce the output.

### Seed

- slug: `[SLUG]`
- title: `[TITLE]`
- difficulty: `[easy|medium|hard]`
- primary topic (must be first in `topics`, copied verbatim): `[TOPIC_SLUG]`
- leetcode_id: `[N or null]`
- optimal time: `[O(...) or unknown]`
- optimal space: `[O(...) or unknown]`

### Output

Write the JSON to: `/home/frtlx/whiteboard/server/bank/generated/[SLUG].json`

### JSON shape (strict — matches `server/bank/schemas.py`)

```jsonc
{
  "slug": "[SLUG]",                           // must equal seed slug exactly
  "title": "...",                             // 1+ chars
  "statement": "...",                         // 20+ chars, LeetCode-style with constraints
  "difficulty": "easy" | "medium" | "hard",
  "leetcode_id": <int or null>,
  "topics": ["[TOPIC_SLUG]", "...", ...],     // FIRST entry MUST equal seed primary topic VERBATIM
  "canonical_solution": {
    "language": "python",
    "code": "...",                            // top-level def, NOT a Solution class
    "time": "O(...)",                         // must match seed optimal
    "space": "O(...)"                         // must match seed optimal
  },
  "test_cases": [                             // >= 3 cases, include edges
    {"input": [arg1, arg2, ...], "expected": <value>},
    ...
  ],
  "steps": [                                  // 3-10 dense, 1-based ordinals
    {
      "ordinal": 1,
      "description": "...",                   // 10+ chars; SOCRATIC THOUGHT, not code
      "pattern_tags": ["..."],                // short lowercase identifiers
      "hints": [                              // exactly 3, levels 1/2/3 escalating
        {"level": 1, "text": "..."},
        {"level": 2, "text": "..."},
        {"level": 3, "text": "..."}
      ]
    },
    ...
  ]
}
```

### Hard requirements

- **`canonical_solution.code`** is a TOP-LEVEL `def`, named after the slug with
  hyphens replaced by underscores (`two-sum` -> `two_sum`). Do **not** wrap in
  a `Solution` class. The runner looks up the function by name in module
  globals; methods on a class will fail with `function_not_found`.
- For **linked-list** problems, use the class name `ListNode` directly (`val`,
  `next`); for **binary-tree** problems use `TreeNode` (`val`, `left`,
  `right`). Do NOT redefine these classes — the runner injects them.
- For **class-based problems** (e.g., trie / data-stream APIs that need
  multiple methods on a stateful object), define the class AND a top-level
  function with the slug-derived name; have the function accept a sequence of
  `(operation, args)` pairs and return a sequence of results. Test cases
  drive the top-level function.
- **Linked-list test cases** use `{"__linked_list__": [v1, v2, v3]}` for both
  inputs and expecteds. `{"__linked_list__": []}` decodes to `None`.
- **Tree test cases** use `{"__tree__": [1, 2, 3, null, 4]}` (LeetCode BFS).
  `{"__tree__": []}` decodes to `None`.
- **Steps are Socratic thoughts**, not code. Each step is what the candidate
  *thinks* at the whiteboard. End with an explicit complexity-statement step.
- **Hints escalate**: level 1 is a gentle prompt, level 2 is directional,
  level 3 reveals the step.

### Validation step (do this AFTER writing)

Run from the server directory:

```bash
cd /home/frtlx/whiteboard/server && \
  uv run python -c "
from pathlib import Path
from bank.validator import validate_one
r = validate_one(
    Path('bank/generated/[SLUG].json'),
    optimal_csv=Path('bank/seed/optimal_complexity.csv'),
)
print('OK' if r.ok else 'FAIL: ' + '; '.join(r.failures))
"
```

If output is `OK`, you're done. If `FAIL`, fix the issues in the JSON and
re-write. Up to 2 fix attempts. Then report back.

### Report format

Reply with **exactly one short line**, nothing else:

- On success: `OK [SLUG]`
- On failure: `FAIL [SLUG]: <one-line reason>`

Do not summarize the question contents. The orchestrator just needs the
status.
