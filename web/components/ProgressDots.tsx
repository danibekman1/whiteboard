const COLOR_CLASS = {
  mastered: "bg-green-500",
  solved: "bg-amber-500",
  empty: "bg-zinc-200 dark:bg-zinc-700",
} as const

type DotState = keyof typeof COLOR_CLASS

export function ProgressDots({
  solved,
  total,
  mastered,
}: {
  solved: number
  total: number
  mastered: number
}) {
  const states: DotState[] = Array.from({ length: total }, (_, i) =>
    i < mastered ? "mastered" : i < solved ? "solved" : "empty",
  )
  return (
    <div className="inline-flex gap-1">
      {states.map((s, i) => (
        <div
          key={i}
          data-state={s}
          className={`w-2.5 h-2.5 rounded-full ${COLOR_CLASS[s]}`}
        />
      ))}
    </div>
  )
}
