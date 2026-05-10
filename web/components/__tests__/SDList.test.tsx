import { test, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { SDList } from "../SDList"

const SD_QUESTIONS = [
  { slug: "parking-lot", title: "Parking Lot", difficulty: "easy" as const,
    scenario_tag: "OO design + capacity", latest_outcome: null },
  { slug: "url-shortener", title: "URL Shortener", difficulty: "medium" as const,
    scenario_tag: "high read traffic", latest_outcome: "unaided" as const },
  { slug: "rate-limiter", title: "Rate Limiter", difficulty: "medium" as const,
    scenario_tag: "token bucket vs sliding window", latest_outcome: null },
]

test("renders three difficulty groups when all present", () => {
  render(<SDList questions={SD_QUESTIONS} onStart={() => {}} />)
  expect(screen.getByText(/^Easy$/)).toBeInTheDocument()
  expect(screen.getByText(/^Medium$/)).toBeInTheDocument()
  // No 'Hard' SDs in fixture - the section is hidden when empty.
  expect(screen.queryByText(/^Hard$/)).not.toBeInTheDocument()
})

test("renders one row per question with title + scenario_tag", () => {
  render(<SDList questions={SD_QUESTIONS} onStart={() => {}} />)
  expect(screen.getByText("URL Shortener")).toBeInTheDocument()
  expect(screen.getByText("high read traffic")).toBeInTheDocument()
  expect(screen.getByText("Parking Lot")).toBeInTheDocument()
})

test("click row calls onStart with the question slug", () => {
  const onStart = vi.fn()
  render(<SDList questions={SD_QUESTIONS} onStart={onStart} />)
  fireEvent.click(screen.getByText("URL Shortener"))
  expect(onStart).toHaveBeenCalledWith("url-shortener")
})

test("renders empty state when no SD questions", () => {
  render(<SDList questions={[]} onStart={() => {}} />)
  expect(screen.getByText(/no system design questions/i)).toBeInTheDocument()
})

test("renders the latest_outcome pill with the matching pill class", () => {
  render(<SDList questions={SD_QUESTIONS} onStart={() => {}} />)
  // Row with outcome='unaided' (URL Shortener) shows the outcome text inside
  // a pill that uses the green statusPillClass for 'unaided'.
  const pill = screen.getByText("unaided")
  expect(pill).toBeInTheDocument()
  // Sanity: the green class for 'unaided' is on the pill element.
  expect(pill.className).toMatch(/bg-green-100/)
  // Rows without an outcome (Parking Lot, Rate Limiter) have no pill.
  expect(screen.queryByText("partial")).not.toBeInTheDocument()
  expect(screen.queryByText("with_hints")).not.toBeInTheDocument()
})
