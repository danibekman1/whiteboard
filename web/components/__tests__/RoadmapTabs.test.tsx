import { test, expect, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { RoadmapTabs } from "../RoadmapTabs"

beforeEach(() => {
  localStorage.clear()
})

test("renders both tab labels", () => {
  render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  expect(screen.getByRole("tab", { name: /algos/i })).toBeInTheDocument()
  expect(screen.getByRole("tab", { name: /system design/i })).toBeInTheDocument()
})

test("default tab is algos", () => {
  render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  expect(screen.getByText("ALGO_BODY")).toBeInTheDocument()
  expect(screen.queryByText("SD_BODY")).not.toBeInTheDocument()
})

test("clicking System Design tab switches body", () => {
  render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  fireEvent.click(screen.getByRole("tab", { name: /system design/i }))
  expect(screen.getByText("SD_BODY")).toBeInTheDocument()
  expect(screen.queryByText("ALGO_BODY")).not.toBeInTheDocument()
})

test("selection persists in localStorage", () => {
  const { unmount } = render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  fireEvent.click(screen.getByRole("tab", { name: /system design/i }))
  expect(localStorage.getItem("whiteboard-roadmap-tab")).toBe("system_design")
  unmount()

  // Re-mount: should restore SD tab.
  render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  expect(screen.getByText("SD_BODY")).toBeInTheDocument()
})

test("ignores unknown localStorage value and falls back to algos", () => {
  localStorage.setItem("whiteboard-roadmap-tab", "garbage")
  render(
    <RoadmapTabs
      algos={<div>ALGO_BODY</div>}
      systemDesign={<div>SD_BODY</div>}
    />,
  )
  expect(screen.getByText("ALGO_BODY")).toBeInTheDocument()
})
