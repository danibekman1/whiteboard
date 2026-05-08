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
      className="flex items-end gap-2 p-3 border-t border-line bg-surface"
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
        className="flex-1 rounded-xl border border-line bg-surface text-text-body px-3 py-2 leading-relaxed resize-y min-h-12 max-h-40 placeholder:text-text-muted focus:outline-none focus:border-primary focus:shadow-[var(--shadow-focus)] disabled:opacity-60 transition-shadow"
      />
      <button
        type="submit"
        disabled={busy || !text.trim()}
        aria-label="Send"
        className="cursor-pointer h-10 px-4 rounded-xl bg-primary text-white font-semibold shadow-clay-sm hover:bg-primary-hover active:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)] transition-[background,transform] duration-150"
      >
        ↑
      </button>
    </form>
  )
}
