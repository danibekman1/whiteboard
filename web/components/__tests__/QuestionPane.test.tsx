import { describe, it, test, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { QuestionPane } from "../QuestionPane"

const Q = {
  slug: "valid-anagram",
  title: "Valid Anagram",
  statement: "Given two strings s and t, return true if t is an anagram of s.",
  difficulty: "easy" as const,
}

test("renders title, difficulty, and statement", () => {
  render(<QuestionPane question={Q} />)
  expect(screen.getByText("Valid Anagram")).toBeInTheDocument()
  expect(screen.getByText(/easy/i)).toBeInTheDocument()
  expect(screen.getByText(/anagram of s/)).toBeInTheDocument()
})

test("collapse toggle hides the statement body", () => {
  render(<QuestionPane question={Q} />)
  const toggle = screen.getByRole("button", { name: /collapse|expand/i })
  fireEvent.click(toggle)
  expect(screen.queryByText(/anagram of s/)).not.toBeInTheDocument()
  // Title still visible.
  expect(screen.getByText("Valid Anagram")).toBeInTheDocument()
})

test("difficulty colors", () => {
  const { container, rerender } = render(<QuestionPane question={{...Q, difficulty: "easy"}} />)
  expect(container.querySelector("[data-difficulty='easy']")).toBeTruthy()
  rerender(<QuestionPane question={{...Q, difficulty: "medium"}} />)
  expect(container.querySelector("[data-difficulty='medium']")).toBeTruthy()
  rerender(<QuestionPane question={{...Q, difficulty: "hard"}} />)
  expect(container.querySelector("[data-difficulty='hard']")).toBeTruthy()
})
