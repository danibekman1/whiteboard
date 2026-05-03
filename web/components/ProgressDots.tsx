import { PROGRESS_DOT_COLORS } from "@/lib/status-colors"

export function ProgressDots({
  solved,
  total,
  mastered,
}: {
  solved: number
  total: number
  mastered: number
}) {
  const states = Array.from({ length: total }, (_, i) =>
    i < mastered ? "mastered" : i < solved ? "solved" : "empty",
  )
  return (
    <div style={{ display: "inline-flex", gap: 4 }}>
      {states.map((s, i) => (
        <div
          key={i}
          data-state={s}
          style={{
            width: 10,
            height: 10,
            borderRadius: 5,
            background: PROGRESS_DOT_COLORS[s as keyof typeof PROGRESS_DOT_COLORS],
          }}
        />
      ))}
    </div>
  )
}
