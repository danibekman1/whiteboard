"use client"
import { useEffect, useState, type ReactNode } from "react"

type Tab = "algos" | "system_design"
const STORAGE_KEY = "whiteboard-roadmap-tab"
const VALID: Tab[] = ["algos", "system_design"]

function loadInitialTab(): Tab {
  if (typeof window === "undefined") return "algos"
  const v = window.localStorage.getItem(STORAGE_KEY)
  return VALID.includes(v as Tab) ? (v as Tab) : "algos"
}

export function RoadmapTabs({
  algos,
  systemDesign,
}: {
  algos: ReactNode
  systemDesign: ReactNode
}) {
  // Initialize lazily to avoid SSR mismatch (server has no localStorage).
  // Two-pass pattern: render with default on first paint, sync to
  // localStorage value on mount.
  const [tab, setTab] = useState<Tab>("algos")
  useEffect(() => {
    setTab(loadInitialTab())
  }, [])

  function pick(next: Tab) {
    setTab(next)
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div role="tablist" className="flex gap-1 px-4 pt-3 border-b border-line">
        <TabButton label="Algos" selected={tab === "algos"} onClick={() => pick("algos")} />
        <TabButton
          label="System Design"
          selected={tab === "system_design"}
          onClick={() => pick("system_design")}
        />
      </div>
      <div className="flex-1 min-h-0">
        {tab === "algos" ? algos : systemDesign}
      </div>
    </div>
  )
}

function TabButton({
  label,
  selected,
  onClick,
}: {
  label: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      role="tab"
      aria-selected={selected}
      onClick={onClick}
      className={`cursor-pointer px-3 py-2 -mb-px border-b-2 text-sm font-medium transition-colors ${
        selected
          ? "border-primary text-primary"
          : "border-transparent text-text-muted hover:text-text"
      }`}
    >
      {label}
    </button>
  )
}
