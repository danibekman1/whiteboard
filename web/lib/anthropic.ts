import Anthropic from "@anthropic-ai/sdk"

let _client: Anthropic | null = null

// Lazy proxy so missing creds fail at first request, not at module load.
// Failing at module load would break `next build` (which imports route
// modules to collect static page data without runtime env).
export const anthropic = new Proxy({} as Anthropic, {
  get(_target, prop, receiver) {
    if (!_client) {
      const apiKey = process.env.ANTHROPIC_API_KEY
      if (!apiKey) throw new Error("ANTHROPIC_API_KEY is not set")
      _client = new Anthropic({ apiKey })
    }
    return Reflect.get(_client, prop, receiver)
  },
})

export const COACH_MODEL = process.env.CLAUDE_COACH_MODEL ?? "claude-opus-4-7"
export const AUX_MODEL = process.env.CLAUDE_AUX_MODEL ?? "claude-haiku-4-5-20251001"

export const MAX_ITERS = 8
