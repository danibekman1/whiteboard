import { NextRequest } from "next/server"
import { callTool } from "@/lib/mcp-client"

export const runtime = "nodejs"

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const out = await callTool("get_session", { session_id: id })
  if (out?.error === "not_found") {
    return Response.json(out, { status: 404 })
  }
  if (out?.error) {
    return Response.json(out, { status: 500 })
  }
  return Response.json(out)
}
