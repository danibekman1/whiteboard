// Wire format the /api/chat route accepts and produces. Mirrors Anthropic's
// MessageParam: `content` is `string | ContentBlockParam[]`. We type it as
// `any` here because Anthropic's union of block types is wide and we just
// pass them straight through to the SDK.
export type WireMessage = {
  role: "user" | "assistant"
  content: any
}

// UI-shape block for the chat renderer. The browser converts SSE events
// into these blocks via `applyEvent`.
export type ChatBlock =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; id: string; name: string; input: unknown; result?: unknown }
