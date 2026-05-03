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

  it("shows the right glyph per status", () => {
    const { container, rerender } = render(
      <QuestionCard
        slug="x"
        title="X"
        difficulty="easy"
        status="unaided"
        starred={false}
        onStart={() => {}}
      />,
    )
    expect(container.textContent).toContain("✓")
    rerender(
      <QuestionCard
        slug="x"
        title="X"
        difficulty="easy"
        status="with_hints"
        starred={false}
        onStart={() => {}}
      />,
    )
    expect(container.textContent).toContain("◐")
  })
})
