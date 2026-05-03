"use client"
import { useEffect, useRef, useState } from "react"
import { Composer } from "./Composer"
import { Message } from "./Message"
import { ChatBlock, WireMessage } from "@/lib/types"

type ChatMessage = { role: "user" | "assistant"; blocks: ChatBlock[] }

export function Chat({ sessionId }: { sessionId?: string } = {}) {
  const [msgs, setMsgs] = useState<ChatMessage[]>([])
  const [history, setHistory] = useState<WireMessage[]>([])
  const [busy, setBusy] = useState(false)
  // Guard against React Strict Mode double-invocation: only seed once per
  // mounted component instance, even though the effect fires twice in dev.
  const seededRef = useRef(false)

  useEffect(() => {
    if (!sessionId || seededRef.current) return
    seededRef.current = true
    // Seed history (not msgs) with a primer pair so the next real user turn
    // arrives with context: the agent sees a fake "continue session X" user
    // turn and a fake assistant ack, then the user's actual message. The
    // coach prompt instructs the agent to call evaluate_attempt with that
    // session_id. We don't display the fake user msg in the UI; we do show
    // the assistant ack as the chat opener.
    setHistory([
      { role: "user", content: `(Continue whiteboard session ${sessionId} - call evaluate_attempt with this session_id when I respond next.)` },
      { role: "assistant", content: [{ type: "text", text: "Picking up where you left off. Walk me through your latest thought." }] },
    ])
    setMsgs([
      {
        role: "assistant",
        blocks: [{ kind: "text", text: "Picking up where you left off. Walk me through your latest thought." }],
      },
    ])
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
        body: JSON.stringify({ message: text, history }),
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
      <div style={{ flex: 1, overflow: "auto" }}>
        {msgs.length === 0 && (
          <div style={{ padding: 24, color: "#666" }}>
            Type a question (e.g. &quot;give me Two Sum&quot;) to start.
          </div>
        )}
        {msgs.map((m, i) => (
          <Message key={i} role={m.role} blocks={m.blocks} />
        ))}
      </div>
      <Composer onSend={send} busy={busy} />
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
