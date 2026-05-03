"use client"
import { useEffect, useState } from "react"

export default function Home() {
  const [data, setData] = useState<any>(null)
  useEffect(() => {
    fetch("/api/roadmap").then(r => r.json()).then(setData)
  }, [])
  if (!data) return <main style={{ padding: 24 }}>loading roadmap…</main>
  return (
    <main style={{ padding: 24 }}>
      <h1>whiteboard</h1>
      <p>{data.topics?.length ?? 0} topics, {data.questions?.length ?? 0} questions</p>
      <pre style={{ fontSize: 11, background: "#f4f4f4", padding: 8, overflow: "auto", maxHeight: 400 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </main>
  )
}
