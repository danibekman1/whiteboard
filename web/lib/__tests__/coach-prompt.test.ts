import { describe, it, expect } from "vitest"
import { COACH_SYSTEM_PROMPT } from "../coach-prompt"

describe("COACH_SYSTEM_PROMPT", () => {
  it("forbids revealing canonical steps", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/never reveal/i)
  })
  it("enforces one move per turn", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/one (question|move) per turn/i)
  })
  it("instructs adversarial pushback on flawed reasoning", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/(push back|adversarial|challenge)/i)
  })
  it("references the evaluate_attempt tool", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/evaluate_attempt/)
  })
  it("references get_next_question for first turn", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/get_next_question/)
  })
  it("documents all four suggested_move semantics", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/nudge/)
    expect(COACH_SYSTEM_PROMPT).toMatch(/advance/)
    expect(COACH_SYSTEM_PROMPT).toMatch(/reanchor/)
    expect(COACH_SYSTEM_PROMPT).toMatch(/wrap_up/)
  })
})
