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
  const colors: Record<string, string> = {
    mastered: "#16a34a",
    solved: "#eab308",
    empty: "#d1d5db",
  }
  return (
    <div style={{ display: "inline-flex", gap: 4 }}>
      {states.map((s, i) => (
        <div
          key={i}
          data-state={s}
          style={{ width: 10, height: 10, borderRadius: 5, background: colors[s] }}
        />
      ))}
    </div>
  )
}
