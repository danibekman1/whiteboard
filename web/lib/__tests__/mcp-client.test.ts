import { describe, it, expect, vi, beforeEach } from "vitest"

const mockListTools = vi.fn()
const mockConnect = vi.fn()

vi.mock("@modelcontextprotocol/sdk/client/index.js", () => {
  return {
    Client: class {
      connect = mockConnect
      listTools = mockListTools
    },
  }
})

vi.mock("@modelcontextprotocol/sdk/client/streamableHttp.js", () => ({
  StreamableHTTPClientTransport: class {},
}))

describe("getToolCatalogue", () => {
  beforeEach(() => {
    vi.resetModules()
    mockListTools.mockReset()
    mockConnect.mockReset()
  })

  it("renames inputSchema -> input_schema", async () => {
    mockListTools.mockResolvedValue({
      tools: [
        {
          name: "get_next_question",
          description: "fetch a question",
          inputSchema: { type: "object", properties: { slug: { type: "string" } } },
        },
      ],
    })
    const { getToolCatalogue } = await import("../mcp-client")
    const cat = await getToolCatalogue()
    expect(cat).toHaveLength(1)
    expect(cat[0]).toEqual({
      name: "get_next_question",
      description: "fetch a question",
      input_schema: { type: "object", properties: { slug: { type: "string" } } },
    })
    expect("inputSchema" in cat[0]).toBe(false)
  })

  it("omits description when MCP tool has none", async () => {
    mockListTools.mockResolvedValue({
      tools: [{ name: "no_desc", inputSchema: { type: "object" } }],
    })
    const { getToolCatalogue } = await import("../mcp-client")
    const cat = await getToolCatalogue()
    expect(cat[0]).not.toHaveProperty("description")
  })

  it("falls back to an empty object schema when inputSchema is missing", async () => {
    mockListTools.mockResolvedValue({
      tools: [{ name: "no_schema", description: "x" }],
    })
    const { getToolCatalogue } = await import("../mcp-client")
    const cat = await getToolCatalogue()
    expect(cat[0].input_schema).toEqual({ type: "object", properties: {} })
  })
})
