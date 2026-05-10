import { describe, test, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { Chat } from "../Chat"

// Repro for the PR 5.1 bug: after PR 5, Chat.tsx fetched session metadata
// once at mount and never refreshed `current_phase` afterwards. The phase
// tracker stayed stuck on whatever was current at page load (or null for
// fresh sessions) until the user F5'd. The fix piggybacks on the existing
// SSE consumer: when an SD evaluator tool_result lands carrying a `phase`
// field, sync session.current_phase from it.

const SD_SESSION_FRESH = {
  session_id: "sid",
  question: {
    type: "system_design",
    slug: "url-shortener",
    title: "URL Shortener",
    statement: "Design a URL shortener.",
    difficulty: "medium",
    scenario_tag: "high read traffic",
  },
  current_step_ordinal: null,
  current_phase: null,
  attempts_count: 0,
  outcome: null,
}

const ALGO_SESSION = {
  session_id: "sid-algo",
  question: {
    type: "algo",
    slug: "two-sum",
    title: "Two Sum",
    statement: "Given nums and target...",
    difficulty: "easy",
  },
  current_step_ordinal: null,
  current_phase: null,
  attempts_count: 0,
  outcome: null,
}

function sseEncode(events: unknown[]): Uint8Array[] {
  const enc = new TextEncoder()
  return events.map((ev) => enc.encode(`data: ${JSON.stringify(ev)}\n\n`))
}

// Build a fetch mock whose /api/chat response streams the supplied SSE events.
function makeFetchMock(sessionPayload: any, sseEvents: unknown[]) {
  return vi.fn(async (url: string) => {
    if (typeof url === "string" && url.startsWith("/api/session/")) {
      return new Response(JSON.stringify(sessionPayload), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    }
    if (typeof url === "string" && url === "/api/chat") {
      const chunks = sseEncode(sseEvents)
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          for (const c of chunks) controller.enqueue(c)
          controller.close()
        },
      })
      return new Response(stream, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      })
    }
    throw new Error(`unexpected fetch: ${url}`)
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("Chat phase tracker sync", () => {
  test("phase tracker updates after SD tool_result without page reload", async () => {
    const sse = [
      {
        type: "tool_call",
        id: "x1",
        name: "evaluate_sd_attempt",
        input: { session_id: "sid", user_text: "100M URLs/year" },
      },
      {
        type: "tool_result",
        tool_use_id: "x1",
        result: {
          phase: "estimate",
          checklist_covered: [],
          checklist_missing_required: [],
          pushback_triggered: null,
          suggested_move: "press_on_missing",
        },
      },
      { type: "done", assistant: [{ type: "text", text: "ok" }] },
    ]
    const fetchMock = makeFetchMock(SD_SESSION_FRESH, sse)
    vi.stubGlobal("fetch", fetchMock)

    render(<Chat sessionId="sid" />)

    await waitFor(() => {
      expect(screen.getByText("URL Shortener")).toBeInTheDocument()
    })

    // Pre-state: no phase highlighted (data-current="false" on every phase chip).
    const estimateBefore = document.querySelector("[data-phase='estimate']")
    expect(estimateBefore?.getAttribute("data-current")).toBe("false")
    const clarifyBefore = document.querySelector("[data-phase='clarify']")
    expect(clarifyBefore?.getAttribute("data-current")).toBe("false")

    // Drive a turn through the Composer.
    const input = screen.getByPlaceholderText(/your reasoning|thinking/i) as HTMLTextAreaElement
    fireEvent.change(input, { target: { value: "100M URLs/year" } })
    fireEvent.submit(input.closest("form")!)

    // Wait for tracker to reflect the new phase from tool_result.
    await waitFor(() => {
      const estimate = document.querySelector("[data-phase='estimate']")
      expect(estimate?.getAttribute("data-current")).toBe("true")
    })

    // Other phases should remain not-current.
    const clarifyAfter = document.querySelector("[data-phase='clarify']")
    expect(clarifyAfter?.getAttribute("data-current")).toBe("false")
  })

  test("algo tool_result does NOT render a phase tracker (and does not crash)", async () => {
    // Algo evaluator returns a step_ordinal-shaped result; no phase field.
    const sse = [
      {
        type: "tool_call",
        id: "a1",
        name: "evaluate_attempt",
        input: { session_id: "sid-algo", user_text: "hash map" },
      },
      {
        type: "tool_result",
        tool_use_id: "a1",
        result: { step_ordinal: 1, correct: true },
      },
      { type: "done", assistant: [{ type: "text", text: "ok" }] },
    ]
    const fetchMock = makeFetchMock(ALGO_SESSION, sse)
    vi.stubGlobal("fetch", fetchMock)

    render(<Chat sessionId="sid-algo" />)

    await waitFor(() => {
      expect(screen.getByText("Two Sum")).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/your reasoning|thinking/i) as HTMLTextAreaElement
    fireEvent.change(input, { target: { value: "hash map" } })
    fireEvent.submit(input.closest("form")!)

    // Algo path renders AlgoQuestionPane - no phase chips at all.
    await waitFor(() => {
      // Wait long enough for SSE stream to drain by waiting for textarea to re-enable.
      expect((input as HTMLTextAreaElement).disabled).toBe(false)
    })
    expect(document.querySelector("[data-phase]")).toBeNull()
  })
})
