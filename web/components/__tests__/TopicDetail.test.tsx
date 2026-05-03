import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TopicDetail } from "../TopicDetail"

const TOPIC = {
  slug: "trees", name: "Trees", status: "in_progress",
  total: 5, solved: 2, mastered: 1, prereqs: ["linked-list"],
}

const ALL_TOPICS = [
  TOPIC,
  { slug: "linked-list", name: "Linked List", status: "mastered",
    total: 3, solved: 3, mastered: 3, prereqs: [] },
  { slug: "stranger", name: "Stranger", status: "locked",
    total: 1, solved: 0, mastered: 0, prereqs: [] },
]

const QUESTIONS = [
  { slug: "invert-tree", title: "Invert Binary Tree", difficulty: "easy",
    topic_slug: "trees", status: "unaided", starred: false },
  { slug: "max-depth", title: "Max Depth", difficulty: "easy",
    topic_slug: "trees", status: "unsolved", starred: false },
  { slug: "reverse-list", title: "Reverse Linked List", difficulty: "easy",
    topic_slug: "linked-list", status: "unaided", starred: false },
]

describe("TopicDetail", () => {
  it("renders only questions for the selected topic", () => {
    render(
      <TopicDetail topic={TOPIC} questions={QUESTIONS} allTopics={ALL_TOPICS}
                   recommendation={null} onStart={() => {}} />,
    )
    expect(screen.getByText("Invert Binary Tree")).toBeInTheDocument()
    expect(screen.getByText("Max Depth")).toBeInTheDocument()
    expect(screen.queryByText("Reverse Linked List")).not.toBeInTheDocument()
  })

  it("renders the prereq Topic with its mastery glyph", () => {
    render(
      <TopicDetail topic={TOPIC} questions={QUESTIONS} allTopics={ALL_TOPICS}
                   recommendation={null} onStart={() => {}} />,
    )
    expect(screen.getByText(/Linked List - 3\/3/)).toBeInTheDocument()
  })

  it("silently filters unknown prereq slugs (forward-compat)", () => {
    const orphanTopic = { ...TOPIC, prereqs: ["linked-list", "ghost-topic"] }
    render(
      <TopicDetail topic={orphanTopic} questions={QUESTIONS} allTopics={ALL_TOPICS}
                   recommendation={null} onStart={() => {}} />,
    )
    expect(screen.getByText(/Linked List/)).toBeInTheDocument()
    expect(screen.queryByText(/ghost-topic/)).not.toBeInTheDocument()
  })

  it("omits the recommendation section when recommendation is null", () => {
    render(
      <TopicDetail topic={TOPIC} questions={QUESTIONS} allTopics={ALL_TOPICS}
                   recommendation={null} onStart={() => {}} />,
    )
    expect(screen.queryByText(/Recommended next/i)).not.toBeInTheDocument()
  })

  it("renders the recommendation and routes click to onStart", () => {
    const onStart = vi.fn()
    const rec = {
      question_slug: "max-depth", topic_slug: "trees",
      difficulty: "easy", justification: "drill recursion",
    }
    render(
      <TopicDetail topic={TOPIC} questions={QUESTIONS} allTopics={ALL_TOPICS}
                   recommendation={rec} onStart={onStart} />,
    )
    expect(screen.getByText(/Recommended next/i)).toBeInTheDocument()
    expect(screen.getByText(/drill recursion/)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/max-depth.*easy/))
    expect(onStart).toHaveBeenCalledWith("max-depth")
  })

  it("renders empty question list without crashing when no questions match", () => {
    const noQs = [{ ...QUESTIONS[2] }]  // only linked-list
    render(
      <TopicDetail topic={TOPIC} questions={noQs} allTopics={ALL_TOPICS}
                   recommendation={null} onStart={() => {}} />,
    )
    expect(screen.queryByText("Invert Binary Tree")).not.toBeInTheDocument()
  })
})
