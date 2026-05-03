const STATUS_GLYPH: Record<string, string> = {
  unaided: "✓",
  with_hints: "◐",
  partial: "○",
  skipped: "✗",
  revisit_flagged: "☆",
  unsolved: "○",
  locked: "◌",
}

export function QuestionCard({
  slug,
  title,
  difficulty,
  status,
  starred,
  onStart,
}: {
  slug: string
  title: string
  difficulty: string
  status: string
  starred: boolean
  onStart: (slug: string) => void
}) {
  return (
    <div
      onClick={() => onStart(slug)}
      style={{
        padding: "6px 8px",
        display: "flex",
        alignItems: "center",
        gap: 8,
        cursor: "pointer",
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <span style={{ width: 14, textAlign: "center" }}>{STATUS_GLYPH[status] ?? "○"}</span>
      <span style={{ flex: 1 }}>{title}</span>
      <span style={{ fontSize: 11, color: "#888", textTransform: "capitalize" }}>{difficulty}</span>
      {starred && <span title="revisit">☆</span>}
    </div>
  )
}
