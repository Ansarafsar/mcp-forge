# MCP-Forge

> Compile a single **YAML** spec into a runnable **Model Context Protocol** server.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built for MCP](https://img.shields.io/badge/protocol-MCP-8A2BE2.svg)](https://modelcontextprotocol.io)

MCP-Forge turns a short, declarative spec into a complete Python server built on the
official [`mcp`](https://pypi.org/project/mcp/) SDK — eliminating the boilerplate you
otherwise rewrite for every server. Describe your **tools**, **resources**, and
**prompts** once; MCP-Forge generates correct type hints, JSON schemas, and the
server wiring for you.

```yaml
# weather.yaml
name: weather
tools:
  - name: get_weather
    description: Get the current weather for a city.
    params:
      - name: city
        type: str
      - name: units
        type: enum
        choices: [celsius, fahrenheit]
        default: celsius
    returns: str
    body: |
      symbol = "C" if units == "celsius" else "F"
      return f"Weather in {city}: 22 degrees {symbol}, clear skies."
```

```console
$ mcp-forge build weather.yaml
OK wrote server.py from weather.yaml
  run it with: python server.py
```

---

## Table of contents

- [Why](#why)
- [Install](#install)
- [60-second quickstart](#60-second-quickstart)
- [CLI reference](#cli-reference)
- [Spec reference](#spec-reference)
- [Use a generated server with Claude Desktop](#use-a-generated-server-with-claude-desktop)
- [Examples & starter templates](#examples--starter-templates)
- [Project layout](#project-layout)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why

Writing an MCP server by hand means repeating the same scaffolding every time:
constructing the server, registering each tool, hand-writing JSON schemas, wiring
stdio transport. MCP-Forge collapses that into one spec file:

- **One source of truth** — a YAML file fully describes the server.
- **Real, runnable output** — generates Python on the official `mcp` SDK, not a wrapper.
- **Type-safe by construction** — friendly YAML types become Python annotations, and
  the SDK derives JSON schemas from them.
- **All three MCP primitives** — tools, resources, and prompts.
- **Validated builds** — specs are checked against a strict schema, and generated code
  is byte-compiled so syntax errors never reach you.

## Install

MCP-Forge needs **Python 3.10+**.

### From source (recommended while pre-release)

```bash
git clone https://github.com/Ansarafsar/mcp-forge.git
cd mcp-forge
pip install -e ".[serve]"
```

The `serve` extra pulls in the `mcp` SDK, which is needed to *run* a generated server.
The compiler itself (building specs) has no MCP dependency.

### Just the compiler

```bash
pip install -e .          # build specs only
pip install -e ".[dev]"   # + pytest and the mcp SDK, for contributors
```

> Once published to PyPI, this becomes `pip install "mcp-forge[serve]"`.

## 60-second quickstart

```bash
# 1. Scaffold a spec from a starter template
mcp-forge new my-weather --template weather

# 2. Compile it to a runnable server
mcp-forge build my-weather.yaml -o server.py

# 3. Run it (speaks MCP over stdio)
python server.py
```

That's a working MCP server. Point any MCP client at `python server.py` and it will see
the `get_weather` and `forecast` tools.

## CLI reference

| Command | What it does |
|---|---|
| `mcp-forge new <name> [-t TEMPLATE]` | Scaffold a new spec from a starter template. |
| `mcp-forge build <spec.yaml> [-o OUT]` | Compile a spec into a Python server (default `server.py`). |
| `mcp-forge validate <spec.yaml>` | Validate a spec without generating code. |
| `mcp-forge templates` | List the bundled starter templates. |
| `mcp-forge version` | Print the installed version. |

Useful flags:

- `build --no-check` — skip byte-compiling the generated file.
- `new --force` — overwrite an existing spec file.

Run `mcp-forge --help` or `mcp-forge <command> --help` for details.

## Spec reference

A spec is one YAML file describing one server.

### Top level

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Server name (shown to MCP clients). |
| `version` | string | no | Defaults to `0.1.0`. |
| `description` | string | no | Free-text summary, used in the file header. |
| `mcp_version` | string | no | Protocol version to pin in the output (e.g. `"2025-06-18"`). |
| `prelude` | string | no | Raw Python inserted at module level (imports, shared state, helpers). |
| `tools` | list | * | MCP tools. |
| `resources` | list | * | MCP resources. |
| `prompts` | list | * | MCP prompts. |

\* At least one of `tools`, `resources`, or `prompts` must be present.

### Tools

```yaml
tools:
  - name: get_weather            # valid Python identifier
    description: Get weather.    # becomes the tool docstring
    params: [ ... ]              # see Parameters below
    returns: str                 # return type annotation (default: str)
    body: |                      # inline Python. Omit for a NotImplementedError stub.
      return "..."
```

### Resources

```yaml
resources:
  - name: list_notes
    uri: notes://all             # the URI clients address
    description: All notes.
    returns: str
    body: |
      return "..."
```

### Prompts

```yaml
prompts:
  - name: summarize
    description: Summarize text.
    params: [ ... ]
    template: |                  # rendered as an f-string; {param} interpolates
      Summarize this: {text}
```

### Parameters

```yaml
params:
  - name: city          # valid Python identifier
    type: str           # see types below
    description: ...     # optional
    default: celsius    # optional; makes the param optional with this default
    optional: true      # optional; with no default, becomes Optional[T] = None
    choices: [a, b]     # required when type is `enum`
```

**Types:** `str`, `int`, `float`, `bool`, `list`, `dict`, `any`, and `enum`
(with `choices`). An `enum` becomes a `typing.Literal[...]`, so clients get a
constrained schema and your editor gets autocomplete.

## Use a generated server with Claude Desktop

Add the generated server to your Claude Desktop config
(`claude_desktop_config.json`):

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

Restart Claude Desktop and the server's tools appear in the client.

## Examples & starter templates

Bundled starters (list them with `mcp-forge templates`):

| Template | Demonstrates |
|---|---|
| `weather` | Tools, `enum` params, defaults, working bodies. |
| `notes` | CRUD tools + a resource + a prompt + shared `prelude` state. |
| `github-issues` | Optional params and multiple tools. |
| `slack-search` | A single search tool with an optional filter. |

A ready-to-build example also lives in [`examples/weather.yaml`](examples/weather.yaml):

```bash
mcp-forge build examples/weather.yaml -o server.py && python server.py
```

## Project layout

```
mcp-forge/
├── src/mcp_forge/
│   ├── spec.py            # Pydantic models = the YAML schema
│   ├── loader.py          # YAML -> validated spec, friendly errors
│   ├── generator.py       # spec -> Python source
│   ├── cli.py             # the `mcp-forge` command
│   └── templates/
│       ├── server.py.j2   # the generated-server skeleton (Jinja2)
│       ├── starters.py    # access bundled specs
│       └── specs/*.yaml   # starter templates
├── examples/              # runnable example specs
└── tests/                 # pytest suite
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

The test suite builds every bundled starter and asserts the generated code parses,
so a broken template fails CI immediately.

Contributions welcome — open an issue or PR. Please keep generated output
deterministic and covered by a test.

## Roadmap

MCP-Forge follows a phased plan (see [`initial_Dev_doc.md`](initial_Dev_doc.md)).
Shipped so far: the core compiler, all three primitives, the CLI, starter
templates, and validated builds. Planned next: a mock-client test harness
(`mcp-forge test`), hot-reload `dev` mode, auth/rate-limit blocks, and a Docker
build target.

## License

[MIT](LICENSE) © Ansar Afsar
