"use client"
import { statusPillClass } from "@/lib/status-colors"

type Difficulty = "easy" | "medium" | "hard"

type SDQuestion = {
  slug: string
  title: string
  difficulty: Difficulty
  scenario_tag: string
  latest_outcome: string | null
}

const DIFF_ORDER: Difficulty[] = ["easy", "medium", "hard"]
const DIFF_LABEL: Record<Difficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
}

export function SDList({
  questions,
  onStart,
}: {
  questions: SDQuestion[]
  onStart: (slug: string) => void
}) {
  if (questions.length === 0) {
    return (
      <div className="p-8 text-center text-text-muted text-sm">
        No system design questions in the bank yet.
      </div>
    )
  }

  const grouped: Record<Difficulty, SDQuestion[]> = {
    easy: [], medium: [], hard: [],
  }
  for (const q of questions) grouped[q.difficulty].push(q)

  return (
    <div className="p-6 space-y-6">
      {DIFF_ORDER.map((diff) => {
        const rows = grouped[diff]
        if (rows.length === 0) return null
        return (
          <section key={diff}>
            <h3 className="font-heading text-sm font-semibold text-text-muted uppercase tracking-wide mb-2">
              {DIFF_LABEL[diff]}
            </h3>
            <ul className="space-y-1">
              {rows.map((q) => (
                <li key={q.slug}>
                  <button
                    type="button"
                    onClick={() => onStart(q.slug)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-surface border border-line hover:border-primary hover:bg-tint cursor-pointer text-left transition-colors"
                  >
                    <span className="font-medium text-text">{q.title}</span>
                    <span className="inline-flex items-center rounded-full px-2 h-5 text-[10px] font-medium bg-tint text-text-muted border border-line">
                      {q.scenario_tag}
                    </span>
                    <div className="flex-1" />
                    {q.latest_outcome && (
                      <span className={`text-[10px] px-2 h-5 inline-flex items-center rounded-full ${statusPillClass(q.latest_outcome)}`}>
                        {q.latest_outcome}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
