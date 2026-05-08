export function ToolCallPill({
  name,
  input,
  result,
}: {
  name: string
  input: any
  result?: any
}) {
  const errored = !!result?.error
  return (
    <details className="my-1.5 rounded-lg bg-tint border border-line-accent text-xs overflow-hidden">
      <summary className="cursor-pointer list-none px-3 py-2 flex items-center gap-2 select-none hover:bg-surface-muted transition-colors">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          tool
        </span>
        <code className="font-mono text-text-body">{name}</code>
        <span
          aria-label={errored ? "error" : "ok"}
          className={errored ? "text-err" : "text-ok"}
        >
          {errored ? "✗" : "✓"}
        </span>
      </summary>
      <pre className="px-3 pb-3 pt-0 overflow-auto font-mono text-[11px] text-text-muted whitespace-pre-wrap break-words">
        {JSON.stringify({ input, result }, null, 2)}
      </pre>
    </details>
  )
}
