export function ToolCallPill({
  name,
  input,
  result,
}: {
  name: string
  input: any
  result?: any
}) {
  return (
    <details
      style={{
        margin: "6px 0",
        padding: 8,
        background: "#f4f4f4",
        borderRadius: 6,
        fontSize: 12,
      }}
    >
      <summary style={{ cursor: "pointer" }}>
        🔧 <code>{name}</code> {result?.error ? "❌" : "✓"}
      </summary>
      <pre style={{ overflow: "auto", margin: "6px 0 0 0" }}>
        {JSON.stringify({ input, result }, null, 2)}
      </pre>
    </details>
  )
}
