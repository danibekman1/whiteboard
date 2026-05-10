import { describe, test, expect, vi, beforeEach } from "vitest"
import type { CoachEvent } from "../coach-backend"

// vi.mock must be hoisted; the factory returns the mock module shape.
vi.mock("@anthropic-ai/claude-agent-sdk", () => {
  return {
    query: vi.fn(),
  }
})

// Re-import after the mock is registered.
import { query } from "@anthropic-ai/claude-agent-sdk"
import { streamCoach } from "../coach-backend"

const ENV_BACKUP = { ...process.env }
beforeEach(() => {
  process.env = { ...ENV_BACKUP, CHAT_BACKEND: "agent_sdk", MCP_SERVER_URL: "http://test/mcp" }
  vi.clearAllMocks()
})

async function collect(gen: AsyncGenerator<CoachEvent>): Promise<CoachEvent[]> {
  const out: CoachEvent[] = []
  for await (const ev of gen) out.push(ev)
  return out
}

function fakeStream(events: any[]) {
  // Yield each fixture event wrapped in the {type:"stream_event", event} envelope.
  return (async function* () {
    for (const e of events) yield { type: "stream_event", event: e }
    yield { type: "result", subtype: "success" }
  })()
}

describe("streamCoach (agent_sdk backend)", () => {
  test("translates text_delta events into {type: 'text'} CoachEvents", async () => {
    ;(query as any).mockReturnValue(
      fakeStream([
        { type: "content_block_delta", delta: { type: "text_delta", text: "Hello" } },
        { type: "content_block_delta", delta: { type: "text_delta", text: " world" } },
      ]),
    )
    const events = await collect(streamCoach({
      system: "S", messages: [{ role: "user", content: "hi" }],
      model: "claude-opus-4-7", maxIters: 8,
    }))
    const texts = events.filter(e => e.type === "text").map(e => (e as any).delta)
    expect(texts).toEqual(["Hello", " world"])
  })

  test("emits tool_call with the prefix-stripped name", async () => {
    ;(query as any).mockReturnValue(
      fakeStream([
        {
          type: "content_block_start",
          index: 0,
          content_block: {
            type: "tool_use",
            id: "tu_1",
            name: "mcp__whiteboard__evaluate_sd_attempt",
            input: {},
          },
        },
        {
          type: "content_block_delta",
          index: 0,
          delta: { type: "input_json_delta", partial_json: "{\"session_id\":\"s1\"}" },
        },
        { type: "content_block_stop", index: 0 },
      ]),
    )
    const events = await collect(streamCoach({
      system: "S", messages: [{ role: "user", content: "go" }],
      model: "claude-opus-4-7", maxIters: 8,
    }))
    const calls = events.filter(e => e.type === "tool_call")
    expect(calls).toHaveLength(1)
    expect((calls[0] as any).name).toBe("evaluate_sd_attempt")  // prefix stripped
    expect((calls[0] as any).id).toBe("tu_1")
    expect((calls[0] as any).input).toEqual({ session_id: "s1" })
  })

  test("registers the MCP server in query() options", async () => {
    ;(query as any).mockReturnValue(fakeStream([]))
    await collect(streamCoach({
      system: "S", messages: [{ role: "user", content: "x" }],
      model: "claude-opus-4-7", maxIters: 8,
    }))
    const callArgs = (query as any).mock.calls[0][0]
    expect(callArgs.options.mcpServers.whiteboard).toMatchObject({
      type: "sse",
      url: "http://test/mcp",
    })
    expect(callArgs.options.allowedTools).toEqual(["mcp__whiteboard__*"])
    expect(callArgs.options.systemPrompt).toBe("S")
    expect(callArgs.options.model).toBe("claude-opus-4-7")
  })

  test("emits a done event after the stream closes", async () => {
    ;(query as any).mockReturnValue(fakeStream([]))
    const events = await collect(streamCoach({
      system: "S", messages: [{ role: "user", content: "x" }],
      model: "claude-opus-4-7", maxIters: 8,
    }))
    const done = events.find(e => e.type === "done")
    expect(done).toBeDefined()
  })

  test("synthesizes USER:/ASSISTANT: history prefix on multi-turn messages", async () => {
    ;(query as any).mockReturnValue(fakeStream([]))
    await collect(streamCoach({
      system: "S",
      messages: [
        { role: "user", content: "hello" },
        { role: "assistant", content: "hi back" },
        { role: "user", content: "second turn" },
      ],
      model: "claude-opus-4-7", maxIters: 8,
    }))
    const callArgs = (query as any).mock.calls[0][0]
    expect(callArgs.prompt).toContain("USER: hello")
    expect(callArgs.prompt).toContain("ASSISTANT: hi back")
    expect(callArgs.prompt).toContain("USER: second turn")
    // The latest user turn appears last.
    const lastUserIdx = callArgs.prompt.lastIndexOf("USER: second turn")
    const assistantIdx = callArgs.prompt.lastIndexOf("ASSISTANT: hi back")
    expect(lastUserIdx).toBeGreaterThan(assistantIdx)
  })
})
