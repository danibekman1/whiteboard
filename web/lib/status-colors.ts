// Topic status enum used by the Roadmap DAG and TopicDetail. The visual
// mapping (border colors, fill tints) lives next to each component now -
// see Roadmap's STATUS_RING / STATUS_BG_SELECTED maps and the design tokens
// in app/globals.css. Kept as a separate module so types and visuals can
// evolve independently.

export type TopicStatus = "mastered" | "in_progress" | "unlocked" | "locked"
