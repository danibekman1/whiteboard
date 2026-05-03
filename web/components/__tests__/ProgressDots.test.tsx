import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { ProgressDots } from "../ProgressDots"

describe("ProgressDots", () => {
  it("renders mastered for first n dots, then solved, then empty", () => {
    const { container } = render(<ProgressDots solved={3} total={7} mastered={2} />)
    const dots = container.querySelectorAll("[data-state]")
    expect(dots).toHaveLength(7)
    expect(dots[0].getAttribute("data-state")).toBe("mastered")
    expect(dots[1].getAttribute("data-state")).toBe("mastered")
    expect(dots[2].getAttribute("data-state")).toBe("solved")
    expect(dots[6].getAttribute("data-state")).toBe("empty")
  })

  it("renders zero dots for total=0", () => {
    const { container } = render(<ProgressDots solved={0} total={0} mastered={0} />)
    expect(container.querySelectorAll("[data-state]")).toHaveLength(0)
  })

  it("renders all-mastered when mastered=total", () => {
    const { container } = render(<ProgressDots solved={5} total={5} mastered={5} />)
    const dots = container.querySelectorAll("[data-state]")
    expect(Array.from(dots).every((d) => d.getAttribute("data-state") === "mastered")).toBe(true)
  })
})
