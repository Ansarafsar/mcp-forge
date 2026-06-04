# MCP-Forge

Compile a single **YAML** spec into a runnable **Model Context Protocol** server,
built on the official [`mcp`](https://pypi.org/project/mcp/) SDK.

```yaml
# weather.yaml
name: weather
tools:
  - name: get_weather
    description: Get the current weather for a city.
    params:
      - name: city
        type: str
    returns: str
    body: |
      return f"Weather in {city}: 22 degrees C, clear skies."
```

```console
$ mcp-forge build weather.yaml
OK wrote server.py from weather.yaml
```

## What you get

- **One spec → one server.** Tools, resources, and prompts from declarative YAML.
- **Type-safe output.** Friendly YAML types become Python annotations; the SDK derives
  JSON schemas from them.
- **Offline testing.** A built-in mock MCP client runs snapshot tests with no LLM.
- **Hardening built in.** Opt into auth, structured logging, and rate limiting per spec.
- **Ship anywhere.** Generate a single file or a Docker build context.

## Next steps

- [Quickstart](quickstart.md) — install and build your first server.
- [Spec reference](spec-reference.md) — every field explained.
- [CLI reference](cli.md) — all commands and flags.
- [Testing](testing.md) — snapshot tests with the mock client.
- [Hardening](hardening.md) — auth, logging, and rate limits.
