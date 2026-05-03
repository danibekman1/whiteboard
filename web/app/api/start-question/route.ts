import { NextRequest } from "next/server"
import { callTool } from "@/lib/mcp-client"

export const runtime = "nodejs"

export async function POST(req: NextRequest) {
  let body: any
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 })
  }
  const slug = body?.slug
  if (!slug || typeof slug !== "string") {
    return Response.json({ error: "slug required" }, { status: 400 })
  }
  const out = await callTool("get_next_question", { slug })
  if (out?.error) return Response.json(out, { status: 404 })
  return Response.json({ session_id: out.session_id })
}
