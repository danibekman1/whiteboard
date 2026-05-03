"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Roadmap, type RoadmapData } from "@/components/Roadmap"
import { TopicDetail } from "@/components/TopicDetail"

type Topic = RoadmapData["topics"][number]
type RoadmapPayload = RoadmapData & {
  questions: any[]
  recommendation: any | null
  weakness: any[]
}

export default function Home() {
  const [data, setData] = useState<RoadmapPayload | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    refresh()
  }, [])

  async function refresh(focus?: string) {
    const url = focus
      ? `/api/roadmap?focus_topic_slug=${encodeURIComponent(focus)}`
      : "/api/roadmap"
    const r = await fetch(url)
    setData(await r.json())
  }

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

  if (!data) return <main style={{ padding: 24 }}>loading roadmap…</main>
  const selectedTopic = selected
    ? data.topics.find((t: Topic) => t.slug === selected) ?? null
    : null

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <div style={{ flex: 1, borderRight: "1px solid #e5e7eb" }}>
        <Roadmap data={data} onSelect={onSelectTopic} selectedSlug={selected} />
      </div>
      <div style={{ width: 360 }}>
        {selectedTopic ? (
          <TopicDetail
            topic={selectedTopic}
            questions={data.questions}
            allTopics={data.topics}
            recommendation={data.recommendation}
            onStart={onStart}
          />
        ) : (
          <div style={{ padding: 24, color: "#666" }}>
            <p>Click a topic in the DAG to see questions and recommended next.</p>
            {data.recommendation && (
              <div
                style={{
                  marginTop: 16,
                  padding: 12,
                  background: "#fef3c7",
                  borderRadius: 6,
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: "#92400e",
                    textTransform: "uppercase",
                  }}
                >
                  Recommended right now
                </div>
                <button
                  onClick={() => onStart(data.recommendation.question_slug)}
                  style={{
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {data.recommendation.question_slug} ({data.recommendation.difficulty}) →
                </button>
                <div
                  style={{ fontSize: 12, fontStyle: "italic", marginTop: 4 }}
                >
                  &quot;{data.recommendation.justification}&quot;
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
