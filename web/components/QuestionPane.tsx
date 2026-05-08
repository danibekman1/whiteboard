"use client"
import { useState } from "react"
import { Markdown } from "./Markdown"

type Difficulty = "easy" | "medium" | "hard"

type Question = {
  slug: string
  title: string
  statement: string
  difficulty: Difficulty
}

const PILL: Record<Difficulty, string> = {
  easy: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  hard: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
}

export function QuestionPane({ question }: { question: Question }) {
  const [expanded, setExpanded] = useState(true)
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
        <h2 className="font-heading flex-1 text-base sm:text-lg font-semibold text-text m-0">
          {question.title}
        </h2>
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
      {expanded && (
        <div className="mt-2 text-sm leading-relaxed text-text-body max-w-prose">
          <Markdown>{question.statement}</Markdown>
        </div>
      )}
    </div>
  )
}
