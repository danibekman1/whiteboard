// Single source of truth for the status palette used across Roadmap,
// ProgressDots, TopicDetail, and the home page recommendation card.

export type TopicStatus = "mastered" | "in_progress" | "unlocked" | "locked"

export const STATUS_COLORS: Record<TopicStatus, string> = {
  mastered: "#16a34a",     // green
  in_progress: "#eab308",  // amber
  unlocked: "#3b82f6",     // blue
  locked: "#9ca3af",       // gray
}

export const PROGRESS_DOT_COLORS = {
  mastered: STATUS_COLORS.mastered,
  solved: STATUS_COLORS.in_progress,
  empty: "#d1d5db",
}

// "Recommended next" highlight - amber-ish to draw the eye without alarming.
export const RECOMMENDATION_BG = "#fef3c7"
export const RECOMMENDATION_FG = "#92400e"
