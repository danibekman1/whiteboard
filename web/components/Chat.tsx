"use client"
import { useState } from "react"
import { Composer } from "./Composer"
import { Message, Block } from "./Message"

type ChatMessage = { role: "user" | "assistant"; blocks: Block[] }

// Anthropic-format history is what the API expects; we keep both shapes side
// by side: ChatMessage drives rendering, AMessage is the wire format.
type AMessage = { role: "user" | "assistant"; content: any }

export function Chat() {
  const [msgs, setMsgs] = useState<ChatMessage[]>([])
  const [history, setHistory] = useState<AMessage[]>([])
  const [busy, setBusy] = useState(false)

  async function send(text: string) {
    setBusy(true)
    const userMsg: ChatMessage = { role: "user", blocks: [{ kind: "text", text }] }
    const assistantMsg: ChatMessage = {
      role: "assistant",
      blocks: [{ kind: "text", text: "" }],
    }
    setMsgs((m) => [...m, userMsg, assistantMsg])

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
      let assistantCollected: any | null = null

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
      // Update Anthropic-format history for the next turn.
      setHistory((h) => {
        const next: AMessage[] = [...h, { role: "user", content: text }]
        if (assistantCollected) next.push({ role: "assistant", content: assistantCollected })
        return next
      })
    } catch (err) {
      console.error(err)
    } finally {
      setBusy(false)
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

function applyEvent(msgs: ChatMessage[], ev: any): ChatMessage[] {
  const last = msgs[msgs.length - 1]
  if (!last || last.role !== "assistant") return msgs
  const blocks = [...last.blocks]
  if (ev.type === "text") {
    const tail = blocks[blocks.length - 1]
    if (tail?.kind === "text") tail.text += ev.delta
    else blocks.push({ kind: "text", text: ev.delta })
  } else if (ev.type === "tool_call") {
    blocks.push({ kind: "tool_call", id: ev.id, name: ev.name, input: ev.input })
  } else if (ev.type === "tool_result") {
    const target = blocks.find(
      (b) => b.kind === "tool_call" && b.id === ev.tool_use_id,
    ) as any
    if (target) target.result = ev.result
  }
  return [...msgs.slice(0, -1), { ...last, blocks }]
}
