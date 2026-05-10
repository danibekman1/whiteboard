"use client"
import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Roadmap, type RoadmapData } from "@/components/Roadmap"
import { TopicDetail } from "@/components/TopicDetail"
import { RoadmapTabs } from "@/components/RoadmapTabs"
import { SDList } from "@/components/SDList"
import type { Outcome } from "@/lib/status-colors"

type Topic = RoadmapData["topics"][number]
type SDQuestion = {
  slug: string
  title: string
  difficulty: "easy" | "medium" | "hard"
  scenario_tag: string
  latest_outcome: Outcome | null
}
type RoadmapPayload = RoadmapData & {
  questions: any[]
  sd_questions: SDQuestion[]
  recommendation: any | null
  weakness: any[]
}

export default function Home() {
  const [data, setData] = useState<RoadmapPayload | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const router = useRouter()

  const refresh = useCallback(async (focus?: string) => {
    const url = focus
      ? `/api/roadmap?focus_topic_slug=${encodeURIComponent(focus)}`
      : "/api/roadmap"
    const r = await fetch(url)
    setData(await r.json())
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  function onSelectTopic(slug: string) {
    setSelected(slug)
    refresh(slug)
  }

  async function onStart(questionSlug: string) {
    const res = await fetch("/api/start-question", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ slug: questionSlug }),
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`couldn't start: ${err.error ?? "unknown error"}`)
      return
    }
    const { session_id } = await res.json()
    router.push(`/practice/${session_id}`)
  }

  if (!data) {
    return <main className="p-6 text-text-muted text-sm">loading roadmap…</main>
  }
  const selectedTopic = selected
    ? data.topics.find((t: Topic) => t.slug === selected) ?? null
    : null

  const algosBody = (
    <div className="flex h-full">
      <div className="flex-1 border-r border-line">
        <Roadmap data={data} onSelect={onSelectTopic} selectedSlug={selected} />
      </div>
      <aside className="w-[360px] bg-surface">
        {selectedTopic ? (
          <TopicDetail
            topic={selectedTopic}
            questions={data.questions}
            allTopics={data.topics}
            recommendation={data.recommendation}
            onStart={onStart}
          />
        ) : (
          <div className="p-5 text-text-muted">
            <p className="text-sm">
              Click a topic in the DAG to see questions and recommended next.
            </p>
            {data.recommendation && (
              <div className="mt-4 rounded-xl bg-tint border border-line-accent p-3 shadow-clay-sm">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-primary">
                  Recommended right now
                </div>
                <button
                  onClick={() => onStart(data.recommendation.question_slug)}
                  className="cursor-pointer bg-transparent border-0 p-0 text-sm font-semibold text-text mt-1 hover:text-primary transition-colors"
                >
                  {data.recommendation.question_slug} ({data.recommendation.difficulty}) →
                </button>
                <div className="text-xs italic mt-1 text-text-muted">
                  &quot;{data.recommendation.justification}&quot;
                </div>
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  )

  // Defensive read: if a stale browser tab hits a server that isn't returning
  // sd_questions yet (e.g. mid-deploy), fall back to empty so SDList renders
  // its empty-state instead of crashing on .length.
  const sdBody = <SDList questions={data.sd_questions ?? []} onStart={onStart} />

  return (
    <div className="h-screen">
      <RoadmapTabs algos={algosBody} systemDesign={sdBody} />
    </div>
  )
}
