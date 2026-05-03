import { NextRequest } from "next/server"
import { callTool } from "@/lib/mcp-client"

export const runtime = "nodejs"

export async function GET(req: NextRequest) {
  const focus = new URL(req.url).searchParams.get("focus_topic_slug") ?? undefined
  const result = await callTool("get_roadmap", focus ? { focus_topic_slug: focus } : {})
  return Response.json(result)
}
