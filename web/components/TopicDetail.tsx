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
    <div className="p-5 h-full overflow-y-auto">
      <div className="flex justify-between items-baseline">
        <h2 className="font-heading text-xl font-semibold text-text m-0">
          {topic.name}
        </h2>
        <span className="text-sm text-text-muted">
          {topic.solved}/{topic.total} {topic.status}
        </span>
      </div>
      <div className="mt-2">
        <ProgressDots
          solved={topic.solved}
          mastered={topic.mastered}
          total={topic.total}
        />
      </div>

      {prereqDetails.length > 0 && (
        <section className="mt-5">
          <h4 className="text-[11px] font-semibold uppercase tracking-wide text-text-muted m-0 mb-1.5">
            Prerequisites
          </h4>
          {prereqDetails.map((p) => (
            <div
              key={p.slug}
              className="text-sm py-0.5 flex items-center gap-2 text-text-body"
            >
              <span
                className={`inline-block w-3 h-3 rounded-full ${
                  p.status === "mastered" ? "bg-green-500" : "bg-zinc-300 dark:bg-zinc-600"
                }`}
              />
              <span>
                {p.name} - {p.solved}/{p.total} {p.status === "mastered" && "✓"}
              </span>
            </div>
          ))}
        </section>
      )}

      {recommendation && (
        <section className="mt-5 rounded-xl bg-tint border border-line-accent p-3 shadow-clay-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-primary mb-1">
            Recommended next
          </div>
          <button
            onClick={() => onStart(recommendation.question_slug)}
            className="cursor-pointer bg-transparent border-0 p-0 text-sm font-semibold text-text text-left hover:text-primary transition-colors"
          >
            {recommendation.question_slug} ({recommendation.difficulty}) →
          </button>
          <div className="text-xs text-text-muted italic mt-1">
            &quot;{recommendation.justification}&quot;
          </div>
        </section>
      )}

      <section className="mt-5">
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-text-muted m-0 mb-1.5">
          Questions
        </h4>
        {inTopic.map((q) => (
          <QuestionCard key={q.slug} {...q} onStart={onStart} />
        ))}
      </section>
    </div>
  )
}
