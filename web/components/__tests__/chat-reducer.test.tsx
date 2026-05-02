import { describe, it, expect } from "vitest"
import { applyEvent } from "../Chat"

type ChatBlock =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; id: string; name: string; input: unknown; result?: unknown }

type ChatMessage = { role: "user" | "assistant"; blocks: ChatBlock[] }

function seed(): ChatMessage[] {
  return [
    { role: "user", blocks: [{ kind: "text", text: "hi" }] },
    { role: "assistant", blocks: [{ kind: "text", text: "" }] },
  ]
}

describe("applyEvent", () => {
  it("appends text deltas to the trailing text block", () => {
    let msgs = seed()
    msgs = applyEvent(msgs, { type: "text", delta: "Hello" })
    msgs = applyEvent(msgs, { type: "text", delta: " world" })
    const tail = msgs[1].blocks[0]
    expect(tail.kind).toBe("text")
    if (tail.kind === "text") expect(tail.text).toBe("Hello world")
  })

  it("does not mutate the original block reference (immutable update)", () => {
    const before = seed()
    const beforeBlock = before[1].blocks[0] as { kind: "text"; text: string }
    const after = applyEvent(before, { type: "text", delta: "x" })
    // The pre-event block reference must be unchanged.
    expect(beforeBlock.text).toBe("")
    // The post-event block must be a different reference.
    expect(after[1].blocks[0]).not.toBe(beforeBlock)
  })

  it("starts a fresh text block after a tool_call", () => {
    let msgs = seed()
    msgs = applyEvent(msgs, { type: "text", delta: "thinking..." })
    msgs = applyEvent(msgs, {
      type: "tool_call",
      id: "t1",
      name: "get_next_question",
      input: { slug: "two-sum" },
    })
    msgs = applyEvent(msgs, { type: "text", delta: "got it" })
    const blocks = msgs[1].blocks
    expect(blocks).toHaveLength(3)
    expect(blocks[0]).toMatchObject({ kind: "text", text: "thinking..." })
    expect(blocks[1]).toMatchObject({ kind: "tool_call", id: "t1" })
    expect(blocks[2]).toMatchObject({ kind: "text", text: "got it" })
  })

  it("attaches a tool_result to the matching tool_call by id", () => {
    let msgs = seed()
    msgs = applyEvent(msgs, {
      type: "tool_call",
      id: "t1",
      name: "evaluate_attempt",
      input: { session_id: "s1", user_text: "hi" },
    })
    msgs = applyEvent(msgs, {
      type: "tool_result",
      tool_use_id: "t1",
      result: { step_ordinal: 1, correct: true },
    })
    const tc = msgs[1].blocks.find((b) => b.kind === "tool_call") as any
    expect(tc.result).toEqual({ step_ordinal: 1, correct: true })
  })

  it("ignores tool_result when no matching tool_call id exists", () => {
    const before = seed()
    const after = applyEvent(before, {
      type: "tool_result",
      tool_use_id: "missing",
      result: { x: 1 },
    })
    // Last assistant message untouched.
    expect(after[after.length - 1].blocks).toEqual(before[before.length - 1].blocks)
  })

  it("returns msgs unchanged if there's no trailing assistant message", () => {
    const onlyUser: ChatMessage[] = [{ role: "user", blocks: [{ kind: "text", text: "hi" }] }]
    const after = applyEvent(onlyUser, { type: "text", delta: "x" })
    expect(after).toBe(onlyUser)
  })

  it("ignores unknown event types", () => {
    const before = seed()
    const after = applyEvent(before, { type: "weird-event", payload: 42 })
    expect(after[1].blocks).toEqual(before[1].blocks)
  })
})
