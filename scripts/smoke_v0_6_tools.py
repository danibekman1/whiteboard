"""Degraded end-to-end smoke for v0.6 (no Anthropic API required).

Why degraded: the outer-coach agent loop in /api/chat calls Anthropic via
the SDK, and we have no valid ANTHROPIC_API_KEY. So this smoke skips the
agent and exercises every other layer:

  1. /api/roadmap returns the full DAG payload with correct statuses.
  2. /api/start-question creates a real session row.
  3. We inject fake `attempts` rows (mimicking what evaluate_attempt would
     have written if Opus had run) directly via docker exec.
  4. record_outcome is invoked via docker exec on the live container's DB,
     proving session state + weakness_profile bumping work end-to-end on
     the deployed code path.
  5. /api/roadmap is hit again, verifying topic status + question status
     reflect the recorded outcome.
  6. A second session is created and recorded as 'partial' (the leave-session
     equivalent). Roadmap reflects.

What this smoke does NOT prove (requires a valid API key):
  - The coach prompt actually triggers record_outcome at wrap_up.
  - The Anthropic SDK + tool catalogue + MCP handshake on /api/chat path.

Run from the host, after docker compose up:
    python3 scripts/smoke_v0_6_tools.py
"""
from __future__ import annotations
import json
import subprocess
import sys
import urllib.request

BASE = "http://localhost:3000"


def http_get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as r:
        return json.loads(r.read().decode())


def http_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def docker_py(code: str) -> str:
    """Run Python inside the server container (has access to coach.db)."""
    out = subprocess.run(
        ["docker", "exec", "whiteboard-server", "python", "-c", code],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def main() -> int:
    section("1. /api/roadmap baseline (before any progress)")
    rm0 = http_get("/api/roadmap")
    print(f"  topics: {len(rm0['topics'])}")
    print(f"  edges:  {len(rm0['edges'])}")
    print(f"  questions: {len(rm0['questions'])}")
    print(f"  recommendation: {rm0['recommendation']}")
    ah = next(t for t in rm0["topics"] if t["slug"] == "arrays-hashing")
    tp = next(t for t in rm0["topics"] if t["slug"] == "two-pointers")
    print(f"  arrays-hashing status: {ah['status']} (expect: unlocked)")
    print(f"  two-pointers status:   {tp['status']} (expect: locked)")
    assert ah["status"] == "unlocked", f"FAIL: arrays-hashing should be unlocked, got {ah['status']}"
    assert tp["status"] == "locked",   f"FAIL: two-pointers should be locked, got {tp['status']}"

    section("2. Start a Two Sum session via /api/start-question")
    start = http_post("/api/start-question", {"slug": "two-sum"})
    sid = start["session_id"]
    print(f"  session_id: {sid}")

    section("3. Inject 5 attempts for that session (no Anthropic, just SQL)")
    # Mimics what evaluate_attempt would have stored after a 3-step Two Sum walk
    # where the user missed step 2 once before nailing it.
    attempts_code = f"""
import json
from whiteboard_mcp.db import connect
conn = connect('/app/data/coach.db')
fake = [
    (1, 'Brute force two nested loops O(n^2)',
        {{'step_ordinal': 1, 'correct': True, 'missing': [], 'suggested_move': 'advance'}}),
    (2, 'maybe sort first then binary search',
        {{'step_ordinal': 2, 'correct': False, 'missing': ['hashing insight'], 'suggested_move': 'nudge'}}),
    (3, 'use a hash map to look up complement in O(1)',
        {{'step_ordinal': 2, 'correct': True, 'missing': [], 'suggested_move': 'advance'}}),
    (4, 'single pass: check then insert; O(n) time, O(n) space',
        {{'step_ordinal': 3, 'correct': True, 'missing': [], 'suggested_move': 'wrap_up'}}),
    (5, 'wrap up the session please',
        {{'step_ordinal': 3, 'correct': True, 'missing': [], 'suggested_move': 'wrap_up'}}),
]
for ord_, txt, ev in fake:
    conn.execute(
        'INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) VALUES (?,?,?,?)',
        ('{sid}', ord_, txt, json.dumps(ev)),
    )
conn.commit()
n = conn.execute('SELECT COUNT(*) FROM attempts WHERE session_id=?', ('{sid}',)).fetchone()[0]
print(f'attempts inserted: {{n}}')
conn.close()
"""
    print(docker_py(attempts_code).strip())

    section("4. Call record_outcome(with_hints) via the MCP tool function")
    rec_code = f"""
import json
from whiteboard_mcp.db import connect
from whiteboard_mcp.tools.record_outcome import record_outcome
conn = connect('/app/data/coach.db')
res = record_outcome(
    conn, session_id='{sid}', outcome='with_hints',
    hints_used=[{{'step_ordinal': 2, 'level': 1}}],
)
print(json.dumps(res, indent=2))
conn.close()
"""
    print(docker_py(rec_code).strip())

    section("5. Verify sessions row was updated")
    sess_code = f"""
import json
from whiteboard_mcp.db import connect
conn = connect('/app/data/coach.db')
row = conn.execute(
    'SELECT outcome, ended_at, hints_used_json FROM sessions WHERE id=?',
    ('{sid}',),
).fetchone()
print(json.dumps(dict(row), indent=2))
conn.close()
"""
    sess_out = docker_py(sess_code).strip()
    print(sess_out)
    sess_dict = json.loads(sess_out)
    assert sess_dict["outcome"] == "with_hints", f"FAIL: outcome should be with_hints, got {sess_dict['outcome']}"
    assert sess_dict["ended_at"] is not None, "FAIL: ended_at should be set"
    assert json.loads(sess_dict["hints_used_json"]) == [{"step_ordinal": 2, "level": 1}], \
        "FAIL: hints_used_json round-trip"

    section("6. Verify weakness_profile rows were bumped")
    weak_code = """
import json
from whiteboard_mcp.db import connect
conn = connect('/app/data/coach.db')
rows = conn.execute(
    'SELECT pattern_tag, miss_count, total_count, last_seen_session FROM weakness_profile ORDER BY pattern_tag'
).fetchall()
for r in rows:
    print(json.dumps(dict(r)))
conn.close()
"""
    print(docker_py(weak_code).strip())

    section("7. Reload /api/roadmap - verify status reflects the recorded session")
    rm1 = http_get("/api/roadmap")
    ts = next(q for q in rm1["questions"] if q["slug"] == "two-sum")
    ah1 = next(t for t in rm1["topics"] if t["slug"] == "arrays-hashing")
    print(f"  two-sum question status: {ts['status']} (expect: with_hints)")
    print(f"  arrays-hashing topic:    {ah1}")
    print(f"  weakness top 5:          {rm1['weakness']}")
    assert ts["status"] == "with_hints", f"FAIL: two-sum should be with_hints, got {ts['status']}"
    assert ah1["solved"] == 1, f"FAIL: arrays-hashing solved should be 1, got {ah1['solved']}"
    assert ah1["mastered"] == 1, f"FAIL: arrays-hashing mastered should be 1, got {ah1['mastered']}"
    assert ah1["status"] == "in_progress", f"FAIL: arrays-hashing status should be in_progress, got {ah1['status']}"
    assert len(rm1["weakness"]) >= 1, "FAIL: weakness should have at least one entry"

    section("8. Idempotency: call record_outcome again, expect no double-bump")
    again = docker_py(rec_code).strip()
    again_dict = json.loads(again)
    print(f"  second call ok: {again_dict['ok']}")
    print(f"  weakness_updates len (expect 0): {len(again_dict.get('weakness_updates', []))}")
    assert again_dict.get("ok") is True
    assert len(again_dict.get("weakness_updates", [])) == 0, \
        "FAIL: idempotency broken - second record_outcome bumped weakness again"

    section("9. Leave-session flow: new session, record outcome=partial")
    start2 = http_post("/api/start-question", {"slug": "valid-anagram"})
    sid2 = start2["session_id"]
    print(f"  session_id: {sid2}")
    rec_partial = f"""
import json
from whiteboard_mcp.db import connect
from whiteboard_mcp.tools.record_outcome import record_outcome
conn = connect('/app/data/coach.db')
res = record_outcome(conn, session_id='{sid2}', outcome='partial', hints_used=[])
print(json.dumps(res, indent=2))
"""
    print(docker_py(rec_partial).strip())

    rm2 = http_get("/api/roadmap")
    va = next(q for q in rm2["questions"] if q["slug"] == "valid-anagram")
    print(f"  valid-anagram question status: {va['status']} (expect: partial)")
    assert va["status"] == "partial", f"FAIL: valid-anagram should be partial, got {va['status']}"

    section("ALL ASSERTIONS PASSED")
    print("v0.6 MCP tool plumbing works end-to-end through the live containers.")
    print("Not verified (requires valid ANTHROPIC_API_KEY):")
    print("  - the coach prompt actually triggers record_outcome at wrap_up")
    print("  - the Anthropic SDK loop on /api/chat")
    print("Manual flow when an API key is available:")
    print("  1. open http://localhost:3000, click two-sum recommendation")
    print("  2. work through Two Sum to wrap_up; agent should call record_outcome")
    print("  3. reload /, verify two-sum shows the right glyph and arrays-hashing progresses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
