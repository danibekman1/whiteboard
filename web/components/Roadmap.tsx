"use client"
import "reactflow/dist/style.css"
import ReactFlow, { Background, Controls, Node, Edge, NodeProps, Position } from "reactflow"
import { useMemo } from "react"
import { type TopicStatus } from "@/lib/status-colors"

export type Topic = {
  slug: string
  name: string
  status: TopicStatus
  total: number
  solved: number
  mastered: number
  prereqs: string[]
}
export type RoadmapEdge = { from: string; to: string }
export type RoadmapData = { topics: Topic[]; edges: RoadmapEdge[] }

const STATUS_RING: Record<TopicStatus, string> = {
  mastered: "border-green-500",
  in_progress: "border-amber-500",
  unlocked: "border-primary",
  locked: "border-slate-400",
}

const STATUS_BG_SELECTED: Record<TopicStatus, string> = {
  mastered: "bg-green-50 dark:bg-green-950/40",
  in_progress: "bg-amber-50 dark:bg-amber-950/40",
  unlocked: "bg-tint",
  locked: "bg-slate-100 dark:bg-slate-800/40",
}

function TopicNode({ data, selected }: NodeProps<Topic & { selected: boolean }>) {
  return (
    <div
      data-testid={`topic-node-${data.slug}`}
      className={`
        cursor-pointer rounded-xl border-2 px-3 py-2 min-w-[110px] text-center text-xs
        ${STATUS_RING[data.status]}
        ${data.selected ? STATUS_BG_SELECTED[data.status] : "bg-surface"}
        shadow-clay-sm hover:shadow-clay transition-shadow
      `}
    >
      <div className="font-heading font-semibold text-text">{data.name}</div>
      <div className="text-text-muted mt-0.5">
        {data.solved}/{data.total} {data.status}
      </div>
    </div>
  )
}

const NODE_TYPES = { topic: TopicNode }

// Naive vertical layered layout based on prereq depth. Good enough for ~18 nodes.
// Exported for unit testing — react-flow itself doesn't render reliably under jsdom,
// so we test the layout derivation directly rather than the rendered DOM.
export function layoutRoadmap(topics: Topic[], edges: RoadmapEdge[]): Node[] {
  const depth: Record<string, number> = {}
  const byTo: Record<string, string[]> = {}
  for (const e of edges) (byTo[e.to] ??= []).push(e.from)

  function d(slug: string, seen = new Set<string>()): number {
    if (slug in depth) return depth[slug]
    if (seen.has(slug)) return 0  // cycle guard, defensive
    seen.add(slug)
    const ps = byTo[slug] ?? []
    return (depth[slug] = ps.length === 0 ? 0 : 1 + Math.max(...ps.map((p) => d(p, seen))))
  }
  topics.forEach((t) => d(t.slug))

  const byDepth: Record<number, Topic[]> = {}
  topics.forEach((t) => ((byDepth[depth[t.slug]] ??= []).push(t)))
  const X = 180
  const Y = 110

  return topics.map((t) => {
    const layer = byDepth[depth[t.slug]]
    const idx = layer.indexOf(t)
    return {
      id: t.slug,
      type: "topic",
      data: { ...t, selected: false },
      position: { x: idx * X, y: depth[t.slug] * Y },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }
  })
}

export function Roadmap({
  data,
  onSelect,
  selectedSlug,
}: {
  data: RoadmapData
  onSelect: (slug: string) => void
  selectedSlug: string | null
}) {
  const nodes = useMemo(() => {
    const ns = layoutRoadmap(data.topics, data.edges)
    return ns.map((n) => ({
      ...n,
      data: { ...(n.data as any), selected: n.id === selectedSlug },
    }))
  }, [data, selectedSlug])
  const edges: Edge[] = useMemo(
    () =>
      data.edges.map((e) => ({
        id: `${e.from}->${e.to}`,
        source: e.from,
        target: e.to,
        animated: false,
      })),
    [data],
  )
  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodeClick={(_, n) => onSelect(n.id)}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}
