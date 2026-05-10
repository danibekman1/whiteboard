"use client"
import { useEffect, useRef, useState } from "react"
import { Composer } from "./Composer"
import { Message } from "./Message"
import { QuestionPane, type QuestionMeta, type CurrentPhase } from "./QuestionPane"
import { ChatBlock, WireMessage } from "@/lib/types"

type ChatMessage = { role: "user" | "assistant"; blocks: ChatBlock[] }

type SessionMeta = {
  session_id: string
  question: QuestionMeta
  current_step_ordinal: number | null
  current_phase: CurrentPhase
  attempts_count: number
  outcome: string | null
}

export function Chat({ sessionId }: { sessionId?: string } = {}) {
  const [msgs, setMsgs] = useState<ChatMessage[]>([])
  const [history, setHistory] = useState<WireMessage[]>([])
  const [busy, setBusy] = useState(false)
  const [ended, setEnded] = useState(false)
  const [session, setSession] = useState<SessionMeta | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  // Guard against React Strict Mode double-invocation.
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (!sessionId || fetchedRef.current) return
    fetchedRef.current = true
    fetch(`/api/session/${encodeURIComponent(sessionId)}`)
      .then(async (r) => {
        if (!r.ok) {
          setSessionError(`Couldn't load session (${r.status})`)
          return null
        }
        return r.json() as Promise<SessionMeta>
      })
      .then((data) => {
        if (!data) return
        setSession(data)
        if (data.outcome) setEnded(true)
      })
      .catch((e) => setSessionError(String(e)))
  }, [sessionId])

  async function send(text: string) {
    setBusy(true)
    const userMsg: ChatMessage = { role: "user", blocks: [{ kind: "text", text }] }
    const assistantMsg: ChatMessage = {
      role: "assistant",
      blocks: [{ kind: "text", text: "" }],
    }
    setMsgs((m) => [...m, userMsg, assistantMsg])

    let assistantCollected: unknown = null

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: text,
          history,
          session_id: sessionId,
          question_type: session?.question.type,
        }),
      })
      if (!res.body) throw new Error("no body")
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const chunk = buffer.slice(0, idx).trim()
          buffer = buffer.slice(idx + 2)
          if (!chunk.startsWith("data:")) continue
          const ev = JSON.parse(chunk.slice(5).trim())
          setMsgs((m) => applyEvent(m, ev))
          if (ev.type === "done") assistantCollected = ev.assistant
          // Detect record_outcome tool calls -> session ended.
          if (ev.type === "tool_call" && ev.name === "record_outcome") {
            setEnded(true)
          }
        }
      }
    } catch (err) {
      console.error(err)
    } finally {
      setBusy(false)
    }

    // Update history atomically: only push the user+assistant pair when we
    // actually have an assistant turn to push. Half-updating (user only)
    // would leave history ending in a user message and break alternation
    // on the next turn.
    if (assistantCollected) {
      setHistory((h) => [
        ...h,
        { role: "user", content: text },
        { role: "assistant", content: assistantCollected },
      ])
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {sessionId && (
        <header className="sticky top-0 z-10 h-12 px-4 flex items-center justify-between border-b border-line bg-surface/85 backdrop-blur">
          <a
            href="/"
            className="text-sm text-text-muted hover:text-primary transition-colors"
          >
            ← Roadmap
          </a>
          <button
            type="button"
            onClick={() => send("(I'm leaving this session)")}
            disabled={busy || ended}
            aria-label="Leave session and return to roadmap"
            className="cursor-pointer text-sm text-text-muted hover:text-err disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Leave session
          </button>
        </header>
      )}
      {session && (
        <QuestionPane
          question={session.question}
          currentPhase={session.current_phase}
        />
      )}
      {sessionError && (
        <div className="bg-red-50 dark:bg-red-950/40 border-b border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm px-4 py-3">
          {sessionError}
        </div>
      )}
      <div className="flex-1 overflow-y-auto py-2">
        {msgs.length === 0 && !sessionId && (
          <div className="px-4 py-12 text-center text-text-muted text-sm">
            Type a question (e.g. &quot;give me Two Sum&quot;) to start.
          </div>
        )}
        {msgs.length === 0 && sessionId && session && (
          <div className="px-4 py-12 text-center text-text-muted text-sm">
            Walk me through your reasoning. What&apos;s the first thing you reach for?
          </div>
        )}
        {msgs.map((m, i) => (
          <Message key={i} role={m.role} blocks={m.blocks} />
        ))}
      </div>
      {ended && (
        <div className="bg-green-50 dark:bg-green-950/40 border-t border-green-200 dark:border-green-900 text-green-800 dark:text-green-300 text-sm py-2 px-4 text-center">
          Session complete.{" "}
          <a href="/" className="font-semibold hover:underline">
            Back to roadmap →
          </a>
        </div>
      )}
      <Composer onSend={send} busy={busy || ended} />
    </div>
  )
}

// Pure reducer: produces a new ChatMessage array without mutating any block
// reference from the input. Tested separately in __tests__/chat-reducer.test.ts.
export function applyEvent(msgs: ChatMessage[], ev: any): ChatMessage[] {
  const last = msgs[msgs.length - 1]
  if (!last || last.role !== "assistant") return msgs
  const blocks = [...last.blocks]

  if (ev.type === "text") {
    const tailIdx = blocks.length - 1
    const tail = blocks[tailIdx]
    if (tail?.kind === "text") {
      // Replace the tail block with a fresh object instead of mutating
      // the reference shared with the prior msgs[i].blocks[i].
      blocks[tailIdx] = { kind: "text", text: tail.text + ev.delta }
    } else {
      blocks.push({ kind: "text", text: ev.delta })
    }
  } else if (ev.type === "tool_call") {
    blocks.push({
      kind: "tool_call",
      id: ev.id,
      name: ev.name,
      input: ev.input,
    })
  } else if (ev.type === "tool_result") {
    const targetIdx = blocks.findIndex(
      (b) => b.kind === "tool_call" && b.id === ev.tool_use_id,
    )
    if (targetIdx >= 0) {
      const target = blocks[targetIdx] as Extract<ChatBlock, { kind: "tool_call" }>
      blocks[targetIdx] = { ...target, result: ev.result }
    }
  }

  return [...msgs.slice(0, -1), { ...last, blocks }]
}
