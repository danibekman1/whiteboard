import { query } from "@anthropic-ai/claude-agent-sdk"
import { anthropic } from "./anthropic"
import { callTool, getToolCatalogue } from "./mcp-client"
import type { WireMessage } from "./types"

const MCP_PREFIX = "mcp__whiteboard__"

function stripPrefix(name: string): string {
  return name.startsWith(MCP_PREFIX) ? name.slice(MCP_PREFIX.length) : name
}

function synthesizePrompt(messages: WireMessage[]): string {
  if (messages.length === 0) return ""
  const prior = messages.slice(0, -1)
  const last = messages[messages.length - 1]
  const lastText = typeof last.content === "string" ? last.content : JSON.stringify(last.content)
  if (prior.length === 0) return lastText
  const lines = prior.map((m) => {
    const text = typeof m.content === "string" ? m.content : JSON.stringify(m.content)
    return `${m.role === "user" ? "USER" : "ASSISTANT"}: ${text}`
  })
  return `${lines.join("\n\n")}\n\nUSER: ${lastText}`
}

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

async function* streamAgentSdk({
  system, messages, model,
}: StreamCoachInput): AsyncGenerator<CoachEvent> {
  const startedAt = Date.now()
  const mcpUrl = process.env.MCP_SERVER_URL
  if (!mcpUrl) throw new Error("MCP_SERVER_URL is not set (agent_sdk backend)")

  // Per content_block index, accumulate input_json_delta until content_block_stop.
  // Then emit one tool_call with the parsed input. The SDK auto-executes tools
  // via the MCP server; we never see tool_result events on this path.
  const toolUseInProgress: Record<number, { id: string; name: string; jsonBuf: string }> = {}
  let toolCalls = 0

  for await (const msg of (query as any)({
    prompt: synthesizePrompt(messages),
    options: {
      model,
      systemPrompt: system,
      mcpServers: { whiteboard: { type: "sse", url: mcpUrl } },
      // tools: [] disables all built-in Claude Code tools (Bash, Read,
      // ToolSearch, etc.). Without it, the SDK ships those by default
      // and the coach gets shell access inside the container - we only
      // want the MCP whiteboard tools.
      tools: [],
      allowedTools: [`${MCP_PREFIX}*`],
      includePartialMessages: true,
      permissionMode: "bypassPermissions",
    },
  })) {
    if (msg.type !== "stream_event") continue
    const ev = msg.event
    if (ev?.type === "content_block_delta" && ev.delta?.type === "text_delta") {
      yield { type: "text", delta: ev.delta.text as string }
      continue
    }
    if (ev?.type === "content_block_start" && ev.content_block?.type === "tool_use") {
      toolUseInProgress[ev.index] = {
        id: ev.content_block.id,
        name: stripPrefix(ev.content_block.name),
        jsonBuf: "",
      }
      continue
    }
    if (ev?.type === "content_block_delta" && ev.delta?.type === "input_json_delta") {
      const slot = toolUseInProgress[ev.index]
      if (slot) slot.jsonBuf += ev.delta.partial_json ?? ""
      continue
    }
    if (ev?.type === "content_block_stop") {
      const slot = toolUseInProgress[ev.index]
      if (slot) {
        let input: unknown = {}
        try { input = JSON.parse(slot.jsonBuf || "{}") } catch { input = { _raw: slot.jsonBuf } }
        toolCalls++
        yield { type: "tool_call", id: slot.id, name: slot.name, input }
        delete toolUseInProgress[ev.index]
      }
    }
  }

  yield {
    type: "done",
    assistant: [],
    iters: 1,
    total_ms: Date.now() - startedAt,
    tool_calls: toolCalls,
  }
}
