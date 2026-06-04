# Quickstart

## Install

MCP-Forge needs **Python 3.10+**.

```bash
git clone https://github.com/Ansarafsar/mcp-forge.git
cd mcp-forge
pip install -e ".[serve]"
```

The `serve` extra installs the `mcp` SDK, needed to *run* a generated server. The
compiler itself has no MCP dependency.

## Your first server in 60 seconds

```bash
# 1. Scaffold a spec (and a matching test file)
mcp-forge init my-weather --template weather

# 2. Compile it
mcp-forge build my-weather.yaml -o server.py

# 3. Run it (speaks MCP over stdio)
python server.py
```

Or skip straight to a live, hot-reloading dev loop:

```bash
mcp-forge dev my-weather.yaml
```

## Use it from Claude Desktop

Add the generated server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

Restart Claude Desktop; the tools appear in the client.
