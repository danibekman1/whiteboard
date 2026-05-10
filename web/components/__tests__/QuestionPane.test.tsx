import { test, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { QuestionPane } from "../QuestionPane"

const ALGO = {
  type: "algo" as const,
  slug: "valid-anagram",
  title: "Valid Anagram",
  statement: "Given two strings s and t, return true if t is an anagram of s.",
  difficulty: "easy" as const,
}

const SD = {
  type: "system_design" as const,
  slug: "url-shortener",
  title: "URL Shortener",
  statement: "Design a URL shortener like bit.ly...",
  difficulty: "medium" as const,
  scenario_tag: "high read traffic",
}

test("renders AlgoQuestionPane for algo question (no scenario_tag, no phase tracker)", () => {
  const { container } = render(<QuestionPane question={ALGO} currentPhase={null} />)
  expect(screen.getByText("Valid Anagram")).toBeInTheDocument()
  // Phase tracker is SD-only; algo path has no [data-phase] elements.
  expect(container.querySelectorAll("[data-phase]").length).toBe(0)
})

test("renders SDQuestionPane for system_design question (scenario_tag + 5-phase tracker)", () => {
  const { container } = render(
    <QuestionPane
      question={SD}
      currentPhase={{ phase: "clarify", ordinal: 1 }}
    />,
  )
  expect(screen.getByText("URL Shortener")).toBeInTheDocument()
  expect(screen.getByText("high read traffic")).toBeInTheDocument()
  expect(container.querySelectorAll("[data-phase]").length).toBe(5)
  expect(
    container.querySelector("[data-phase='clarify']")?.getAttribute("data-current"),
  ).toBe("true")
})
