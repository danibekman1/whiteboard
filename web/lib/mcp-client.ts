import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js"

const MCP_URL = process.env.MCP_SERVER_URL ?? "http://localhost:8000/mcp"

let _client: Client | null = null
let _toolCatalogue: any[] | null = null

async function getClient(): Promise<Client> {
  if (_client) return _client
  const transport = new StreamableHTTPClientTransport(new URL(MCP_URL))
  const client = new Client({ name: "whiteboard-web", version: "0.1.0" }, { capabilities: {} })
  await client.connect(transport)
  _client = client
  return client
}

export async function getToolCatalogue(): Promise<any[]> {
  if (_toolCatalogue) return _toolCatalogue
  const c = await getClient()
  const res = await c.listTools()
  // MCP -> Anthropic tool shape: rename inputSchema -> input_schema.
  // Description is omitted when MCP doesn't supply one - sending an empty
  // string tells the model "this tool has been described and the description
  // is empty," which can degrade tool selection.
  _toolCatalogue = res.tools.map((t: any) => {
    const tool: { name: string; description?: string; input_schema: unknown } = {
      name: t.name,
      input_schema: t.inputSchema ?? { type: "object", properties: {} },
    }
    if (t.description) tool.description = t.description
    return tool
  })
  return _toolCatalogue!
}

export async function callTool(name: string, args: any): Promise<any> {
  const c = await getClient()
  const res = await c.callTool({ name, arguments: args })
  // MCP results come back as content blocks; we expect a JSON-text block.
  const content = (res as any).content
  const first = content?.[0]
  if (first?.type === "text") {
    try {
      return JSON.parse(first.text)
    } catch {
      return { text: first.text }
    }
  }
  return res
}
