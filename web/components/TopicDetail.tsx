"use client"
import { ProgressDots } from "./ProgressDots"
import { QuestionCard } from "./QuestionCard"

type Topic = {
  slug: string
  name: string
  status: string
  total: number
  solved: number
  mastered: number
  prereqs: string[]
}
type Question = {
  slug: string
  title: string
  difficulty: string
  topic_slug: string | null
  status: string
  starred: boolean
}
type Recommendation = {
  question_slug: string
  topic_slug: string
  difficulty: string
  justification: string
} | null

export function TopicDetail({
  topic,
  questions,
  allTopics,
  recommendation,
  onStart,
}: {
  topic: Topic
  questions: Question[]
  allTopics: Topic[]
  recommendation: Recommendation
  onStart: (slug: string) => void
}) {
  const inTopic = questions.filter((q) => q.topic_slug === topic.slug)
  const prereqDetails = topic.prereqs
    .map((p) => allTopics.find((t) => t.slug === p))
    .filter(Boolean) as Topic[]
  return (
    <div style={{ padding: 16, height: "100%", overflow: "auto" }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}
      >
        <h2 style={{ margin: 0 }}>{topic.name}</h2>
        <span style={{ fontSize: 14, color: "#666" }}>
          {topic.solved}/{topic.total} {topic.status}
        </span>
      </div>
      <div style={{ marginTop: 8 }}>
        <ProgressDots solved={topic.solved} mastered={topic.mastered} total={topic.total} />
      </div>

      {prereqDetails.length > 0 && (
        <section style={{ marginTop: 16 }}>
          <h4
            style={{
              margin: "0 0 6px 0",
              fontSize: 12,
              color: "#666",
              textTransform: "uppercase",
            }}
          >
            Prerequisites
          </h4>
          {prereqDetails.map((p) => (
            <div key={p.slug} style={{ fontSize: 13, padding: "2px 0" }}>
              <span
                style={{
                  display: "inline-block",
                  width: 12,
                  height: 12,
                  borderRadius: 6,
                  background: p.status === "mastered" ? "#16a34a" : "#d1d5db",
                  marginRight: 8,
                  verticalAlign: "middle",
                }}
              />
              {p.name} - {p.solved}/{p.total} {p.status === "mastered" && "✓"}
            </div>
          ))}
        </section>
      )}

      {recommendation && (
        <section
          style={{ marginTop: 16, padding: 12, background: "#fef3c7", borderRadius: 6 }}
        >
          <div
            style={{
              fontSize: 11,
              color: "#92400e",
              textTransform: "uppercase",
              marginBottom: 4,
            }}
          >
            Recommended next
          </div>
          <button
            onClick={() => onStart(recommendation.question_slug)}
            style={{
              background: "transparent",
              border: "none",
              padding: 0,
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 600,
              textAlign: "left",
            }}
          >
            {recommendation.question_slug} ({recommendation.difficulty}) →
          </button>
          <div
            style={{
              fontSize: 12,
              color: "#92400e",
              fontStyle: "italic",
              marginTop: 4,
            }}
          >
            &quot;{recommendation.justification}&quot;
          </div>
        </section>
      )}

      <section style={{ marginTop: 16 }}>
        <h4
          style={{
            margin: "0 0 6px 0",
            fontSize: 12,
            color: "#666",
            textTransform: "uppercase",
          }}
        >
          Questions
        </h4>
        {inTopic.map((q) => (
          <QuestionCard key={q.slug} {...q} onStart={onStart} />
        ))}
      </section>
    </div>
  )
}
