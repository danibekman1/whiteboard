"use client"
import { useEffect, useRef, useState } from "react"
import { Composer } from "./Composer"
import { Message } from "./Message"
import { QuestionPane } from "./QuestionPane"
import { ChatBlock, WireMessage } from "@/lib/types"

type ChatMessage = { role: "user" | "assistant"; blocks: ChatBlock[] }

type SessionMeta = {
  session_id: string
  question: { slug: string; title: string; statement: string; difficulty: "easy" | "medium" | "hard" }
  current_step_ordinal: number | null
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
        body: JSON.stringify({ message: text, history, session_id: sessionId }),
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
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {sessionId && (
        <div
          style={{
            padding: 8,
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <a href="/" style={{ fontSize: 12 }}>
            ← Roadmap
          </a>
          <button
            type="button"
            onClick={() => send("(I'm leaving this session)")}
            disabled={busy || ended}
            aria-label="Leave session and return to roadmap"
            style={{ fontSize: 12, padding: "2px 8px" }}
          >
            Leave session
          </button>
        </div>
      )}
      {session && <QuestionPane question={session.question} />}
      {sessionError && (
        <div style={{ padding: 12, color: "#b91c1c", background: "#fee2e2", fontSize: 13 }}>
          {sessionError}
        </div>
      )}
      <div style={{ flex: 1, overflow: "auto" }}>
        {msgs.length === 0 && !sessionId && (
          <div style={{ padding: 24, color: "#666" }}>
            Type a question (e.g. &quot;give me Two Sum&quot;) to start.
          </div>
        )}
        {msgs.length === 0 && sessionId && session && (
          <div style={{ padding: 24, color: "#666" }}>
            Walk me through your reasoning. What&apos;s the first thing you reach for?
          </div>
        )}
        {msgs.map((m, i) => (
          <Message key={i} role={m.role} blocks={m.blocks} />
        ))}
      </div>
      {ended && (
        <div
          style={{
            padding: 8,
            background: "#dcfce7",
            textAlign: "center",
            fontSize: 13,
          }}
        >
          Session complete. <a href="/">Back to roadmap →</a>
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
