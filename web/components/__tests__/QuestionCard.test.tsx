import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { QuestionCard } from "../QuestionCard"

describe("QuestionCard", () => {
  it("renders title and difficulty", () => {
    render(
      <QuestionCard
        slug="two-sum"
        title="Two Sum"
        difficulty="easy"
        status="unsolved"
        starred={false}
        onStart={() => {}}
      />,
    )
    expect(screen.getByText("Two Sum")).toBeInTheDocument()
    expect(screen.getByText(/easy/i)).toBeInTheDocument()
  })

  it("calls onStart with slug when clicked", () => {
    const onStart = vi.fn()
    render(
      <QuestionCard
        slug="two-sum"
        title="Two Sum"
        difficulty="easy"
        status="unsolved"
        starred={false}
        onStart={onStart}
      />,
    )
    fireEvent.click(screen.getByText("Two Sum"))
    expect(onStart).toHaveBeenCalledWith("two-sum")
  })

  it("shows revisit star when starred", () => {
    render(
      <QuestionCard
        slug="x"
        title="X"
        difficulty="easy"
        status="revisit_flagged"
        starred={true}
        onStart={() => {}}
      />,
    )
    expect(screen.getByTitle("revisit")).toBeInTheDocument()
  })

  it.each([
    ["unaided", "✓"],
    ["with_hints", "◐"],
    ["partial", "○"],
    ["skipped", "✗"],
    ["revisit_flagged", "☆"],
    ["unsolved", "○"],
    ["locked", "◌"],
  ])("renders glyph %s for status %s", (status, glyph) => {
    const { container } = render(
      <QuestionCard
        slug="x"
        title="X"
        difficulty="easy"
        status={status}
        starred={false}
        onStart={() => {}}
      />,
    )
    expect(container.textContent).toContain(glyph)
  })

  it("falls back to ○ glyph for unknown status", () => {
    const { container } = render(
      <QuestionCard
        slug="x"
        title="X"
        difficulty="easy"
        status="something-new"
        starred={false}
        onStart={() => {}}
      />,
    )
    expect(container.textContent).toContain("○")
  })
})
