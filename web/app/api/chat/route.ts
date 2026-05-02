import { NextRequest } from "next/server"
import { z } from "zod"
import { anthropic, COACH_MODEL, MAX_ITERS } from "@/lib/anthropic"
import { COACH_SYSTEM_PROMPT } from "@/lib/coach-prompt"
import { callTool, getToolCatalogue } from "@/lib/mcp-client"
import { sseStream } from "@/lib/sse"

export const runtime = "nodejs"

type AMessage = { role: "user" | "assistant"; content: any }

const ChatRequestSchema = z.object({
  message: z.string().min(1).max(4000),
  // Full prior chat history threaded by the browser. v0 does not persist
  // server-side; refresh loses chat (server-side attempts in coach.db survive).
  history: z
    .array(z.object({ role: z.enum(["user", "assistant"]), content: z.any() }))
    .default([]),
})

export async function POST(req: NextRequest) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 })
  }
  const parsed = ChatRequestSchema.safeParse(body)
  if (!parsed.success) {
    return Response.json(
      { error: "invalid_request", issues: parsed.error.issues },
      { status: 400 },
    )
  }
  const { message, history } = parsed.data

  const messages: AMessage[] = [...history, { role: "user", content: message }]
  const stream = sseStream(runLoop(messages))
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  })
}

async function* runLoop(messages: AMessage[]): AsyncGenerator<any> {
  const startedAt = Date.now()
  const tools = await getToolCatalogue()
  let totalToolCalls = 0
  let totalIters = 0

  outer: for (let iter = 0; iter < MAX_ITERS; iter++) {
    totalIters = iter + 1

    const stream = anthropic.messages.stream({
      model: COACH_MODEL,
      system: COACH_SYSTEM_PROMPT,
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
        // Echo the assistant message blocks back so the browser can append
        // them to history for the next turn (preserves user/assistant alternation).
        assistant: collected,
      }
      break outer
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

  if (totalIters >= MAX_ITERS) {
    yield { type: "error", message: "max iterations exceeded" }
  }
}
