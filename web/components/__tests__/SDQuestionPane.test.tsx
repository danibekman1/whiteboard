import { test, expect } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { SDQuestionPane } from "../SDQuestionPane"

const Q = {
  type: "system_design" as const,
  slug: "url-shortener",
  title: "URL Shortener",
  statement: "Design a URL shortener service like bit.ly...",
  difficulty: "medium" as const,
  scenario_tag: "high read traffic",
}

test("renders title, difficulty pill, scenario tag, and statement", () => {
  render(<SDQuestionPane question={Q} currentPhase={null} />)
  expect(screen.getByText("URL Shortener")).toBeInTheDocument()
  expect(screen.getByText(/medium/i)).toBeInTheDocument()
  expect(screen.getByText("high read traffic")).toBeInTheDocument()
  expect(screen.getByText(/bit\.ly/)).toBeInTheDocument()
})

test("renders all 5 phases in the tracker", () => {
  const { container } = render(<SDQuestionPane question={Q} currentPhase={null} />)
  // Scope to phase tracker via the data-phase attributes to avoid collisions
  // with the scenario_tag text (e.g. "high read traffic" vs "High-level").
  const tracker = container.querySelector("ol")!
  const utils = within(tracker)
  for (const label of ["Clarify", "Estimate", "High", "Deep", "Tradeoffs"]) {
    expect(utils.getByText(new RegExp(label, "i"))).toBeInTheDocument()
  }
})

test("highlights current phase when provided", () => {
  const { container } = render(
    <SDQuestionPane question={Q} currentPhase={{ phase: "estimate", ordinal: 2 }} />,
  )
  const current = container.querySelector("[data-phase='estimate']")
  expect(current?.getAttribute("data-current")).toBe("true")
  const clarify = container.querySelector("[data-phase='clarify']")
  expect(clarify?.getAttribute("data-current")).toBe("false")
})

test("no phase highlighted when currentPhase is null", () => {
  const { container } = render(<SDQuestionPane question={Q} currentPhase={null} />)
  const phases = container.querySelectorAll("[data-phase]")
  expect(phases.length).toBe(5)
  for (const ph of Array.from(phases)) {
    expect(ph.getAttribute("data-current")).toBe("false")
  }
})

test("collapse toggle hides the statement body but keeps phase tracker visible", () => {
  render(<SDQuestionPane question={Q} currentPhase={{ phase: "clarify", ordinal: 1 }} />)
  const toggle = screen.getByRole("button", { name: /collapse|expand/i })
  fireEvent.click(toggle)
  expect(screen.queryByText(/bit\.ly/)).not.toBeInTheDocument()
  expect(screen.getByText("URL Shortener")).toBeInTheDocument()
  expect(screen.getByText("high read traffic")).toBeInTheDocument()
  expect(screen.getByText(/clarify/i)).toBeInTheDocument()
})

test("difficulty colors via data-difficulty attribute", () => {
  const { container, rerender } = render(
    <SDQuestionPane question={{ ...Q, difficulty: "easy" }} currentPhase={null} />,
  )
  expect(container.querySelector("[data-difficulty='easy']")).toBeTruthy()
  rerender(<SDQuestionPane question={{ ...Q, difficulty: "hard" }} currentPhase={null} />)
  expect(container.querySelector("[data-difficulty='hard']")).toBeTruthy()
})
