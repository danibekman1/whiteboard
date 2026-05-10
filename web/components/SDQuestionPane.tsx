"use client"
import { useState } from "react"
import { Markdown } from "./Markdown"

type Difficulty = "easy" | "medium" | "hard"

type SDQuestion = {
  type: "system_design"
  slug: string
  title: string
  statement: string
  difficulty: Difficulty
  scenario_tag: string
}

type Phase = "clarify" | "estimate" | "high_level" | "deep_dive" | "tradeoffs"

type CurrentPhase = { phase: Phase; ordinal: number } | null

const PILL: Record<Difficulty, string> = {
  easy: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  hard: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
}

// Phase order matters: drives the left-to-right tracker layout.
const PHASES: { key: Phase; label: string }[] = [
  { key: "clarify", label: "Clarify" },
  { key: "estimate", label: "Estimate" },
  { key: "high_level", label: "High-level" },
  { key: "deep_dive", label: "Deep dive" },
  { key: "tradeoffs", label: "Tradeoffs" },
]

export function SDQuestionPane({
  question,
  currentPhase,
}: {
  question: SDQuestion
  currentPhase: CurrentPhase
}) {
  const [expanded, setExpanded] = useState(true)
  const currentKey = currentPhase?.phase ?? null
  return (
    <div
      data-difficulty={question.difficulty}
      className="bg-tint border-b border-line-accent px-4 py-3"
    >
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 h-6 text-[11px] font-semibold uppercase tracking-wide ${PILL[question.difficulty]}`}
        >
          {question.difficulty}
        </span>
        <h2 className="font-heading text-base sm:text-lg font-semibold text-text m-0">
          {question.title}
        </h2>
        <span className="inline-flex items-center rounded-full px-2.5 h-6 text-[11px] font-medium bg-surface border border-line text-text-muted">
          {question.scenario_tag}
        </span>
        <div className="flex-1" />
        <button
          type="button"
          aria-label={expanded ? "Collapse statement" : "Expand statement"}
          onClick={() => setExpanded((e) => !e)}
          className="cursor-pointer text-xs text-text-muted hover:text-primary transition-colors flex items-center gap-1"
        >
          {expanded ? (
            <>collapse <span aria-hidden>▴</span></>
          ) : (
            <>expand <span aria-hidden>▾</span></>
          )}
        </button>
      </div>

      <ol className="mt-2 flex flex-wrap items-center gap-1 text-xs">
        {PHASES.map((p, idx) => {
          const isCurrent = p.key === currentKey
          return (
            <li
              key={p.key}
              data-phase={p.key}
              data-current={isCurrent}
              className={`inline-flex items-center gap-1 ${
                isCurrent
                  ? "text-primary font-semibold"
                  : "text-text-muted"
              }`}
            >
              <span>{p.label}</span>
              {idx < PHASES.length - 1 && (
                <span aria-hidden className="text-text-muted/60">→</span>
              )}
            </li>
          )
        })}
      </ol>

      {expanded && (
        <div className="mt-3 text-sm leading-relaxed text-text-body max-w-prose">
          <Markdown>{question.statement}</Markdown>
        </div>
      )}
    </div>
  )
}
