import { ChatBlock } from "@/lib/types"
import { ToolCallPill } from "./ToolCallPill"

export function Message({
  role,
  blocks,
}: {
  role: "user" | "assistant"
  blocks: ChatBlock[]
}) {
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid #f0f0f0" }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{role}</div>
      {blocks.map((b, i) => {
        if (b.kind === "text")
          return (
            <div key={i} style={{ whiteSpace: "pre-wrap" }}>
              {b.text}
            </div>
          )
        return <ToolCallPill key={i} name={b.name} input={b.input} result={b.result} />
      })}
    </div>
  )
}
