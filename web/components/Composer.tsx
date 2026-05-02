"use client"
import { useState, FormEvent, KeyboardEvent } from "react"

export function Composer({
  onSend,
  busy,
}: {
  onSend: (text: string) => void
  busy: boolean
}) {
  const [text, setText] = useState("")
  function submit(e: FormEvent | KeyboardEvent) {
    e.preventDefault()
    const t = text.trim()
    if (!t || busy) return
    onSend(t)
    setText("")
  }
  return (
    <form
      onSubmit={submit}
      style={{ display: "flex", gap: 8, padding: 12, borderTop: "1px solid #ddd" }}
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) submit(e)
        }}
        rows={2}
        placeholder={busy ? "thinking…" : "your reasoning…"}
        disabled={busy}
        style={{ flex: 1, padding: 8, fontFamily: "inherit", resize: "vertical" }}
      />
      <button type="submit" disabled={busy || !text.trim()} style={{ padding: "0 16px" }}>
        ↑
      </button>
    </form>
  )
}
