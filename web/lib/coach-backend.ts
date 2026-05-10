import { anthropic } from "./anthropic"
import { callTool, getToolCatalogue } from "./mcp-client"
import type { WireMessage } from "./types"

export type CoachEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; id: string; name: string; input: unknown }
  | { type: "tool_result"; tool_use_id: string; result: unknown; ms: number }
  | { type: "done"; assistant: any[]; iters: number; total_ms: number; tool_calls: number }
  | { type: "error"; message: string }

export type StreamCoachInput = {
  system: string
  messages: WireMessage[]
  model: string
  maxIters: number
}

// Single entry point; route.ts only knows about this. The factory inside
// dispatches on CHAT_BACKEND. Adding more backends later means new branches
// here only.
export async function* streamCoach(
  input: StreamCoachInput,
): AsyncGenerator<CoachEvent> {
  const backend = process.env.CHAT_BACKEND ?? "api"
  if (backend === "agent_sdk") {
    yield* streamAgentSdk(input)
    return
  }
  yield* streamMeteredApi(input)
}

async function* streamMeteredApi({
  system, messages, model, maxIters,
}: StreamCoachInput): AsyncGenerator<CoachEvent> {
  const startedAt = Date.now()
  const tools = await getToolCatalogue()
  let totalToolCalls = 0
  let cleanExit = false

  for (let iter = 0; iter < maxIters; iter++) {
    const stream = anthropic.messages.stream({
      model,
      system,
      tools,
      messages,
      max_tokens: 1024,
    })

    for await (const event of stream) {
      if (
        event.type === "content_block_delta" &&
        (event.delta as any).type === "text_delta"
      ) {
        yield { type: "text", delta: (event.delta as any).text }
      }
    }
    const final = await stream.finalMessage()
    const collected: any[] = [...final.content]
    messages.push({ role: "assistant", content: collected })

    const toolUses = collected.filter((b: any) => b.type === "tool_use")
    for (const tu of toolUses as any[]) {
      yield { type: "tool_call", id: tu.id, name: tu.name, input: tu.input }
    }

    if (toolUses.length === 0) {
      yield {
        type: "done",
        total_ms: Date.now() - startedAt,
        iters: iter + 1,
        tool_calls: totalToolCalls,
        assistant: collected,
      }
      cleanExit = true
      break
    }

    const results: any[] = []
    for (const tu of toolUses as any[]) {
      let result: any
      const t0 = Date.now()
      try {
        result = await callTool(tu.name, tu.input)
      } catch (err: any) {
        result = { error: "internal_error", message: String(err) }
      }
      totalToolCalls++
      const isError = Boolean(result?.error)
      yield { type: "tool_result", tool_use_id: tu.id, result, ms: Date.now() - t0 }
      results.push({
        type: "tool_result",
        tool_use_id: tu.id,
        content: JSON.stringify(result),
        is_error: isError,
      })
    }
    messages.push({ role: "user", content: results })
  }

  if (!cleanExit) {
    yield { type: "error", message: "max iterations exceeded" }
  }
}

// Stub - implemented in Task 3.
async function* streamAgentSdk(
  _input: StreamCoachInput,
): AsyncGenerator<CoachEvent> {
  throw new Error("agent_sdk backend not yet implemented")
  yield {} as CoachEvent
}
