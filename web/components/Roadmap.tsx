"use client"
import "reactflow/dist/style.css"
import ReactFlow, { Background, Controls, Node, Edge, NodeProps, Position } from "reactflow"
import { useMemo } from "react"
import { STATUS_COLORS, type TopicStatus } from "@/lib/status-colors"

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

function TopicNode({ data, selected }: NodeProps<Topic & { selected: boolean }>) {
  const color = STATUS_COLORS[data.status]
  return (
    <div
      data-testid={`topic-node-${data.slug}`}
      style={{
        padding: "8px 12px",
        borderRadius: 8,
        border: `2px solid ${color}`,
        background: selected ? color + "33" : "white",
        minWidth: 110,
        textAlign: "center",
        cursor: "pointer",
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600 }}>{data.name}</div>
      <div style={{ color: "#666", marginTop: 2 }}>
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
    <div style={{ width: "100%", height: "100%" }}>
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
