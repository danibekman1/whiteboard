"use client"
import { AlgoQuestionPane } from "./AlgoQuestionPane"
import { SDQuestionPane } from "./SDQuestionPane"

type Difficulty = "easy" | "medium" | "hard"

type Phase = "clarify" | "estimate" | "high_level" | "deep_dive" | "tradeoffs"

export type AlgoQuestion = {
  type: "algo"
  slug: string
  title: string
  statement: string
  difficulty: Difficulty
}

export type SDQuestion = {
  type: "system_design"
  slug: string
  title: string
  statement: string
  difficulty: Difficulty
  scenario_tag: string
}

export type QuestionMeta = AlgoQuestion | SDQuestion
export type CurrentPhase = { phase: Phase; ordinal: number } | null

// Wrapper that picks the variant pane based on question.type. Localizes the
// discriminated-union knowledge so callers (Chat.tsx) just hand over the
// session payload's question + current_phase. SD-only fields like
// scenario_tag and current_phase are typed-checked here, not in the caller.
export function QuestionPane({
  question,
  currentPhase,
}: {
  question: QuestionMeta
  currentPhase: CurrentPhase
}) {
  if (question.type === "system_design") {
    return <SDQuestionPane question={question} currentPhase={currentPhase} />
  }
  return <AlgoQuestionPane question={question} />
}
