"""End-to-end smoke driver for v0.6 Task 19.

Drives a real Two Sum coaching session via the same /api/chat HTTP path
the browser uses, then verifies record_outcome landed in coach.db.

Flow:
  1. POST /api/start-question { slug: "two-sum" } -> session_id
  2. POST /api/chat with primer-history + 4 user turns walking Two Sum:
       brute force -> hash map insight -> single pass -> done
  3. Watch SSE events for record_outcome tool_call
  4. SQL the coach.db for sessions.outcome / weakness_profile rows

Run:
  python3 scripts/smoke_two_sum.py
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request

BASE = "http://localhost:3000"

USER_TURNS = [
    "Brute force is two nested loops, that's O(n^2). For each i, scan j>i and check if nums[i]+nums[j]==target.",
    "I can use a hash map to remember complements. For each x, I look up (target - x) in O(1).",
    "Single pass: as I iterate, check if (target - x) is already in the map, otherwise insert nums[i] -> i. Time O(n), space O(n).",
    "Got it - I think we're done.",
]


def post_json(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def stream_chat(message: str, history: list[dict]) -> tuple[list[dict], list[dict], str]:
    """POST /api/chat and return (events, assistant_content_for_history, text_so_far)."""
    body = json.dumps({"message": message, "history": history}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/chat",
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    events: list[dict] = []
    assistant: list[dict] = []
    text_buf = ""
    with urllib.request.urlopen(req, timeout=180) as r:
        buf = ""
        while True:
            chunk = r.read1(4096)
            if not chunk:
                break
            buf += chunk.decode()
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                raw = raw.strip()
                if not raw.startswith("data:"):
                    continue
                ev = json.loads(raw[5:].strip())
                events.append(ev)
                if ev.get("type") == "text":
                    text_buf += ev.get("delta", "")
                elif ev.get("type") == "done":
                    assistant = ev.get("assistant", [])
    return events, assistant, text_buf


def main() -> int:
    print(">>> Starting Two Sum session via /api/start-question")
    out = post_json("/api/start-question", {"slug": "two-sum"})
    session_id = out["session_id"]
    print(f"    session_id = {session_id}")

    # Primer history matches what Chat.tsx seeds when sessionId is set.
    history: list[dict] = [
        {
            "role": "user",
            "content": (
                f"(Continue whiteboard session {session_id} - call evaluate_attempt "
                f"with this session_id when I respond next.)"
            ),
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Picking up where you left off. Walk me through your latest thought."}
            ],
        },
    ]

    record_outcome_seen = False
    record_outcome_input: dict | None = None
    final_text = ""

    for i, turn in enumerate(USER_TURNS, 1):
        print(f"\n>>> Turn {i}: USER: {turn}")
        events, assistant, text = stream_chat(turn, history)
        final_text = text
        print(f"    AGENT TEXT (truncated 240): {text[:240]!r}")
        for ev in events:
            if ev.get("type") == "tool_call":
                name = ev.get("name")
                inp = ev.get("input", {})
                print(f"    TOOL_CALL: {name}({inp})")
                if name == "record_outcome":
                    record_outcome_seen = True
                    record_outcome_input = inp
        # Append the user+assistant pair to history for the next turn.
        if assistant:
            history.append({"role": "user", "content": turn})
            history.append({"role": "assistant", "content": assistant})
        else:
            print("    !! agent emitted no done event for this turn", file=sys.stderr)
            break
        if record_outcome_seen:
            print(">>> record_outcome called - stopping here")
            break

    print("\n=== SUMMARY ===")
    print(f"session_id: {session_id}")
    print(f"record_outcome called: {record_outcome_seen}")
    if record_outcome_input:
        print(f"record_outcome input: {json.dumps(record_outcome_input, indent=2)}")
    return 0 if record_outcome_seen else 1


if __name__ == "__main__":
    sys.exit(main())
