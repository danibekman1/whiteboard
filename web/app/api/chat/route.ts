import { NextRequest } from "next/server"
import { z } from "zod"
import { anthropic, COACH_MODEL, MAX_ITERS } from "@/lib/anthropic"
import { COACH_SYSTEM_PROMPT } from "@/lib/coach-prompt"
import { callTool, getToolCatalogue } from "@/lib/mcp-client"
import { sseStream } from "@/lib/sse"
import { WireMessage } from "@/lib/types"

export const runtime = "nodejs"

const ChatRequestSchema = z.object({
  message: z.string().min(1).max(4000),
  // Full prior chat history threaded by the browser. v0 does not persist
  // server-side; refresh loses chat (server-side attempts in coach.db survive).
  history: z
    .array(z.object({ role: z.enum(["user", "assistant"]), content: z.any() }))
    .default([]),
  // When the chat is mounted on /practice/[id], the browser passes the active
  // session_id so we can pin it into the system prompt - no synthetic user
  // primer needed. Optional: the homepage chat starts without a session.
  session_id: z.string().optional(),
  // Browser pulls this from /api/session/[id] and threads it through so the
  // coach prompt can dispatch to the right evaluator (evaluate_attempt for
  // algo, evaluate_sd_attempt for system_design) without an extra
  // get_session round-trip per turn. Optional for the upgrade window when
  // old browser tabs may be open.
  question_type: z.enum(["algo", "system_design"]).optional(),
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
  const { message, history, session_id, question_type } = parsed.data

  const messages: WireMessage[] = [...history, { role: "user", content: message }]
  const stream = sseStream(runLoop(messages, session_id, question_type))
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  })
}

// Pure system-prompt builder. Kept separate so the per-turn injection
// (session_id + question_type pin) can be unit-tested without spinning up
// the full route + SDK.
export function buildSystemPrompt(
  sessionId?: string,
  questionType?: "algo" | "system_design",
): string {
  // System prompt = coach base + session pin + type pin (when active). The
  // base prompt contains type-dispatch instructions; the per-turn injection
  // just states which branch to take. Keeping all three in the system position
  // (not user) avoids a fake user turn and remains visible every iteration.
  let system = COACH_SYSTEM_PROMPT
  if (sessionId) {
    system += `\n\nCurrent session_id: ${sessionId}`
    if (questionType) {
      system += `\nCurrent question_type: ${questionType}`
    }
    system += `\nWhen calling tools that take session_id, pass it verbatim. Do NOT call get_next_question - the candidate is already in a session.`
  }
  return system
}

async function* runLoop(
  messages: WireMessage[],
  sessionId?: string,
  questionType?: "algo" | "system_design",
): AsyncGenerator<any> {
  const startedAt = Date.now()
  const tools = await getToolCatalogue()
  let totalToolCalls = 0
  let cleanExit = false

  const system = buildSystemPrompt(sessionId, questionType)

  for (let iter = 0; iter < MAX_ITERS; iter++) {
    const stream = anthropic.messages.stream({
      model: COACH_MODEL,
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
        // Echo the assistant message blocks back so the browser can append
        // them to history for the next turn (preserves user/assistant alternation).
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

  // Only emit the cap error if we ran out of iterations without a clean done.
  if (!cleanExit) {
    yield { type: "error", message: "max iterations exceeded" }
  }
}
