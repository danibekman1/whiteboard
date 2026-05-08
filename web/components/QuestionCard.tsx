const STATUS_GLYPH: Record<string, string> = {
  unaided: "✓",
  with_hints: "◐",
  partial: "○",
  skipped: "✗",
  revisit_flagged: "☆",
  unsolved: "○",
  locked: "◌",
}

const STATUS_GLYPH_COLOR: Record<string, string> = {
  unaided: "text-ok",
  with_hints: "text-warn",
  skipped: "text-err",
  revisit_flagged: "text-warn",
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
  const glyph = STATUS_GLYPH[status] ?? "○"
  const glyphColor = STATUS_GLYPH_COLOR[status] ?? "text-text-muted"
  return (
    <button
      type="button"
      onClick={() => onStart(slug)}
      aria-label={`Start ${title} (${difficulty}, ${status})`}
      className="cursor-pointer flex items-center gap-3 w-full text-left px-2 py-2 rounded-lg hover:bg-tint focus-visible:outline-none focus-visible:bg-tint focus-visible:shadow-[var(--shadow-focus)] transition-colors"
    >
      <span aria-hidden className={`w-4 text-center font-mono ${glyphColor}`}>
        {glyph}
      </span>
      <span className="flex-1 text-sm text-text-body">{title}</span>
      <span className="text-xs text-text-muted capitalize">{difficulty}</span>
      {starred && (
        <span title="revisit" className="text-warn">
          ☆
        </span>
      )}
    </button>
  )
}
