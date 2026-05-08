import { ChatBlock } from "@/lib/types"
import { ToolCallPill } from "./ToolCallPill"
import { Markdown } from "./Markdown"

export function Message({
  role,
  blocks,
}: {
  role: "user" | "assistant"
  blocks: ChatBlock[]
}) {
  const isUser = role === "user"
  return (
    <div className={`flex px-4 py-1.5 ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`
          max-w-[42rem] px-4 py-2.5 rounded-2xl shadow-clay-sm
          ${isUser
            ? "bg-primary text-white rounded-br-md"
            : "bg-surface border border-line-accent text-text-body rounded-bl-md"}
        `}
      >
        {blocks.map((b, i) => {
          if (b.kind === "text") {
            // User messages stay plain - they're typed prose, not markdown,
            // and the indigo background would clash with the Markdown
            // component's inline-code chip styling.
            if (isUser) {
              return (
                <div key={i} className="whitespace-pre-wrap leading-relaxed">
                  {b.text}
                </div>
              )
            }
            return (
              <div key={i} className="text-sm">
                <Markdown>{b.text}</Markdown>
              </div>
            )
          }
          return <ToolCallPill key={i} name={b.name} input={b.input} result={b.result} />
        })}
      </div>
    </div>
  )
}
