// Topic status enum used by the Roadmap DAG and TopicDetail. The visual
// mapping (border colors, fill tints) lives next to each component now -
// see Roadmap's STATUS_RING / STATUS_BG_SELECTED maps and the design tokens
// in app/globals.css. Kept as a separate module so types and visuals can
// evolve independently.

export type TopicStatus = "mastered" | "in_progress" | "unlocked" | "locked"

// Outcome pill classes for question rows (SDList; future: AlgoList). Mirrors
// QuestionCard's STATUS_GLYPH_COLOR semantics (ok/warn/err) but as filled
// pills since the SD list uses pills instead of inline glyphs.
const OUTCOME_PILL: Record<string, string> = {
  unaided: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  with_hints: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  partial: "bg-tint text-text-muted border border-line",
  skipped: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  revisit_flagged: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
}

export function statusPillClass(outcome: string): string {
  return OUTCOME_PILL[outcome] ?? "bg-tint text-text-muted border border-line"
}
