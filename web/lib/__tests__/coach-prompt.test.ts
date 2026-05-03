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
  it("references the get_hint tool", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/get_hint/)
  })
  it("teaches the hint ladder discipline", () => {
    // [\s\S] = any char incl. newlines without needing the /s flag (which
    // requires ES2018 target).
    expect(COACH_SYSTEM_PROMPT).toMatch(/level\s*1[\s\S]*level\s*2[\s\S]*level\s*3/i)
  })
  it("escalates only on explicit ask or repeated stuck turns", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/(stuck|asks|ask)/i)
  })
  it("references the record_outcome tool", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/record_outcome/)
  })
  it("ties wrap_up to a record_outcome call", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/wrap_up[\s\S]*record_outcome/i)
  })
  it("explains the outcome enum values", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/unaided/)
    expect(COACH_SYSTEM_PROMPT).toMatch(/with_hints/)
    expect(COACH_SYSTEM_PROMPT).toMatch(/partial/)
  })
  it("instructs partial outcome on user abandon", () => {
    expect(COACH_SYSTEM_PROMPT).toMatch(/(abandon|leav|done|quit)[\s\S]*partial/i)
  })
})
