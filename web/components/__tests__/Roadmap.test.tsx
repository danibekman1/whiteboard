import { describe, it, expect } from "vitest"
import { layoutRoadmap, type RoadmapData } from "../Roadmap"

// react-flow's internals (ResizeObserver, getBoundingClientRect math) don't
// render reliably under jsdom. Per phase note in the v0.6 plan, we test the
// layout/prop-derivation logic directly rather than DOM rendering.

const FIXTURE: RoadmapData = {
  topics: [
    { slug: "a", name: "A", status: "mastered", total: 5, solved: 5, mastered: 5, prereqs: [] },
    { slug: "b", name: "B", status: "unlocked", total: 4, solved: 0, mastered: 0, prereqs: ["a"] },
    { slug: "c", name: "C", status: "locked", total: 3, solved: 0, mastered: 0, prereqs: ["b"] },
    { slug: "d", name: "D", status: "locked", total: 2, solved: 0, mastered: 0, prereqs: ["a"] },
  ],
  edges: [
    { from: "a", to: "b" },
    { from: "b", to: "c" },
    { from: "a", to: "d" },
  ],
}

describe("layoutRoadmap", () => {
  it("derives one node per topic", () => {
    const nodes = layoutRoadmap(FIXTURE.topics, FIXTURE.edges)
    expect(nodes).toHaveLength(4)
    expect(nodes.map((n) => n.id).sort()).toEqual(["a", "b", "c", "d"])
  })

  it("places no-prereq topics at depth 0 (y=0)", () => {
    const nodes = layoutRoadmap(FIXTURE.topics, FIXTURE.edges)
    const a = nodes.find((n) => n.id === "a")!
    expect(a.position.y).toBe(0)
  })

  it("places topics at depth = 1 + max(prereq depth)", () => {
    const nodes = layoutRoadmap(FIXTURE.topics, FIXTURE.edges)
    const b = nodes.find((n) => n.id === "b")!
    const c = nodes.find((n) => n.id === "c")!
    const d = nodes.find((n) => n.id === "d")!
    // b depth = 1 (prereq a is depth 0)
    expect(b.position.y).toBe(110)
    // d depth = 1 (prereq a is depth 0)
    expect(d.position.y).toBe(110)
    // c depth = 2 (prereq b is depth 1)
    expect(c.position.y).toBe(220)
  })

  it("attaches the topic data (slug, status, counts) on each node", () => {
    const nodes = layoutRoadmap(FIXTURE.topics, FIXTURE.edges)
    const a = nodes.find((n) => n.id === "a")!
    expect((a.data as any).slug).toBe("a")
    expect((a.data as any).status).toBe("mastered")
    expect((a.data as any).total).toBe(5)
  })

  it("uses the topic node type", () => {
    const nodes = layoutRoadmap(FIXTURE.topics, FIXTURE.edges)
    expect(nodes.every((n) => n.type === "topic")).toBe(true)
  })

  it("returns no nodes for an empty roadmap", () => {
    expect(layoutRoadmap([], [])).toEqual([])
  })

  it("places a single isolated topic at depth 0", () => {
    const nodes = layoutRoadmap(
      [
        {
          slug: "lone",
          name: "Lone",
          status: "unlocked",
          total: 1,
          solved: 0,
          mastered: 0,
          prereqs: [],
        },
      ],
      [],
    )
    expect(nodes).toHaveLength(1)
    expect(nodes[0].position).toEqual({ x: 0, y: 0 })
  })
})
