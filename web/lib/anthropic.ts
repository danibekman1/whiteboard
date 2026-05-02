import Anthropic from "@anthropic-ai/sdk"

const apiKey = process.env.ANTHROPIC_API_KEY
if (!apiKey) {
  // Fail fast at module load so missing creds surface as a clear startup
  // error rather than an opaque 401 from Anthropic at request time.
  throw new Error("ANTHROPIC_API_KEY is not set")
}

export const anthropic = new Anthropic({ apiKey })

export const COACH_MODEL = process.env.CLAUDE_COACH_MODEL ?? "claude-opus-4-7"
export const AUX_MODEL = process.env.CLAUDE_AUX_MODEL ?? "claude-haiku-4-5-20251001"

export const MAX_ITERS = 8
