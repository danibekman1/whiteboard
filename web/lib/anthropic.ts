import Anthropic from "@anthropic-ai/sdk"

export const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY ?? "",
})

export const COACH_MODEL = process.env.CLAUDE_COACH_MODEL ?? "claude-opus-4-7"
export const AUX_MODEL = process.env.CLAUDE_AUX_MODEL ?? "claude-haiku-4-5-20251001"

export const MAX_ITERS = 8
