import { describe, test, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { Chat } from "../Chat"

const SD_SESSION = {
  session_id: "sess-sd-1",
  question: {
    type: "system_design",
    slug: "url-shortener",
    title: "URL Shortener",
    statement: "Design a URL shortener like bit.ly...",
    difficulty: "medium",
    scenario_tag: "high read traffic",
  },
  current_step_ordinal: null,
  current_phase: { phase: "clarify", ordinal: 1 },
  attempts_count: 0,
  outcome: null,
}

const ALGO_SESSION = {
  ...SD_SESSION,
  session_id: "sess-algo-1",
  question: {
    type: "algo",
    slug: "two-sum",
    title: "Two Sum",
    statement: "Given nums and target, return indices...",
    difficulty: "easy",
  },
  current_phase: null,
}

function makeFetchMock(sessionPayload: any) {
  // The session GET resolves with the payload; the /api/chat POST returns an
  // empty SSE stream so Chat.send() finishes without error.
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (typeof url === "string" && url.startsWith("/api/session/")) {
      return new Response(JSON.stringify(sessionPayload), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    }
    if (typeof url === "string" && url === "/api/chat") {
      // record the body for assertions below
      ;(makeFetchMock as any).lastChatBody = JSON.parse(String(init?.body))
      // Empty SSE stream - Chat reads the body via getReader.
      const stream = new ReadableStream({ start(c) { c.close() } })
      return new Response(stream, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      })
    }
    throw new Error(`unexpected fetch: ${url}`)
  })
}

beforeEach(() => {
  ;(makeFetchMock as any).lastChatBody = null
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe("Chat /api/chat POST body", () => {
  test("threads question_type='system_design' for SD sessions", async () => {
    const fetchMock = makeFetchMock(SD_SESSION)
    vi.stubGlobal("fetch", fetchMock)

    render(<Chat sessionId="sess-sd-1" />)

    // Wait for session GET to resolve and pane to render.
    await waitFor(() => {
      expect(screen.getByText("URL Shortener")).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/walk me through|reasoning|next step|reach for|message|ask|type/i) as HTMLTextAreaElement | HTMLInputElement
    fireEvent.change(input, { target: { value: "Let me clarify scope first." } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() => {
      expect((makeFetchMock as any).lastChatBody).not.toBeNull()
    })
    const body = (makeFetchMock as any).lastChatBody
    expect(body.message).toBe("Let me clarify scope first.")
    expect(body.session_id).toBe("sess-sd-1")
    expect(body.question_type).toBe("system_design")
  })

  test("threads question_type='algo' for algo sessions", async () => {
    const fetchMock = makeFetchMock(ALGO_SESSION)
    vi.stubGlobal("fetch", fetchMock)

    render(<Chat sessionId="sess-algo-1" />)

    await waitFor(() => {
      expect(screen.getByText("Two Sum")).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/walk me through|reasoning|next step|reach for|message|ask|type/i) as HTMLTextAreaElement | HTMLInputElement
    fireEvent.change(input, { target: { value: "I'd reach for a hash map." } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() => {
      expect((makeFetchMock as any).lastChatBody).not.toBeNull()
    })
    expect((makeFetchMock as any).lastChatBody.question_type).toBe("algo")
  })
})
