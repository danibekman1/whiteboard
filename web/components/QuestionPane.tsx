"use client"
import { useState } from "react"

type Question = {
  slug: string
  title: string
  statement: string
  difficulty: "easy" | "medium" | "hard"
}

const DIFFICULTY_COLOR: Record<Question["difficulty"], string> = {
  easy:   "#16a34a",
  medium: "#eab308",
  hard:   "#dc2626",
}

export function QuestionPane({ question }: { question: Question }) {
  const [expanded, setExpanded] = useState(true)
  const color = DIFFICULTY_COLOR[question.difficulty]
  return (
    <div
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid #e5e7eb",
        background: "#fafafa",
      }}
      data-difficulty={question.difficulty}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span
          style={{
            fontSize: 11,
            padding: "2px 8px",
            borderRadius: 12,
            background: color + "22",
            color,
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          {question.difficulty}
        </span>
        <h2 style={{ margin: 0, fontSize: 16, flex: 1 }}>{question.title}</h2>
        <button
          type="button"
          aria-label={expanded ? "Collapse statement" : "Expand statement"}
          onClick={() => setExpanded((e) => !e)}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            fontSize: 12,
            color: "#666",
          }}
        >
          {expanded ? "collapse ▴" : "expand ▾"}
        </button>
      </div>
      {expanded && (
        <div
          style={{
            marginTop: 8,
            fontSize: 13,
            lineHeight: 1.5,
            whiteSpace: "pre-wrap",
            color: "#333",
          }}
        >
          {question.statement}
        </div>
      )}
    </div>
  )
}
