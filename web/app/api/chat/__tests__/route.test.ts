import { describe, it, expect } from "vitest"
import { buildSystemPrompt } from "../route"
import { COACH_SYSTEM_PROMPT } from "@/lib/coach-prompt"

// The base coach prompt itself describes the injection format ("Current
// session_id: <id>"), so simple substring checks would false-match the
// docs. These tests assert what's *appended* by the per-turn builder.
function appendedSuffix(out: string): string {
  expect(out.startsWith(COACH_SYSTEM_PROMPT)).toBe(true)
  return out.slice(COACH_SYSTEM_PROMPT.length)
}

describe("buildSystemPrompt", () => {
  it("returns the bare coach prompt when no session is active", () => {
    expect(buildSystemPrompt()).toBe(COACH_SYSTEM_PROMPT)
  })

  it("appends only the session_id line when questionType is omitted", () => {
    const suffix = appendedSuffix(buildSystemPrompt("sess-abc"))
    expect(suffix).toContain("\n\nCurrent session_id: sess-abc\n")
    expect(suffix).not.toContain("Current question_type:")
  })

  it("appends both session_id and question_type lines for an SD session", () => {
    const suffix = appendedSuffix(buildSystemPrompt("sess-xyz", "system_design"))
    expect(suffix).toContain("Current session_id: sess-xyz")
    expect(suffix).toContain("Current question_type: system_design")
  })

  it("appends question_type=algo when an algo session is active", () => {
    const suffix = appendedSuffix(buildSystemPrompt("sess-1", "algo"))
    expect(suffix).toContain("Current session_id: sess-1")
    expect(suffix).toContain("Current question_type: algo")
  })

  it("orders lines: session_id then question_type then do-not-call hint", () => {
    const suffix = appendedSuffix(buildSystemPrompt("sess-1", "system_design"))
    const sIdx = suffix.indexOf("Current session_id:")
    const tIdx = suffix.indexOf("Current question_type:")
    const dIdx = suffix.indexOf("Do NOT call get_next_question")
    expect(sIdx).toBeGreaterThanOrEqual(0)
    expect(tIdx).toBeGreaterThan(sIdx)
    expect(dIdx).toBeGreaterThan(tIdx)
  })
})
