# Testing

MCP-Forge ships a mock MCP client and a snapshot test harness, so you can verify a
generated server **without** an LLM or any real client.

## How it works

`mcp-forge test` finds `*.test.yaml` files, builds the referenced spec to a
temporary server, launches it as a subprocess, and drives it with
`MockMCPClient` — a dependency-free client that speaks MCP's newline-delimited
JSON-RPC over stdio. Each case's result is compared to its expectation.

## Test file format

A `*.test.yaml` sits next to its spec:

```yaml
spec: weather.yaml          # defaults to the same name without `.test`
env:                        # optional env vars for the server process
  MCP_API_KEY: secret
cases:
  - name: celsius           # optional label
    tool: get_weather       # call a tool...
    args: { city: London, units: celsius }
    expect: "Weather in London: 22 degrees C, clear skies."

  - resource: notes://all   # ...or read a resource
    expect: "(no notes yet)"

  - prompt: summarize_note   # ...or render a prompt
    args: { body: hello }
    expect_contains: "Summarize"
```

### Matchers

| Key | Meaning |
|---|---|
| `expect` | Exact string match (whitespace-trimmed). |
| `expect_contains` | Substring must appear in the result. |
| `expect_error` | The call is expected to raise (e.g. auth or rate-limit rejection). |

## Running

```bash
mcp-forge test examples/            # all *.test.yaml under a directory
mcp-forge test examples/weather.test.yaml
```

The command exits non-zero on any failure and prints a colored diff pointing at
the exact line that changed — wire it straight into CI.
