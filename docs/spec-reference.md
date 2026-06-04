# Spec reference

A spec is one YAML file describing one server.

## Top level

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Server name (shown to MCP clients). |
| `version` | string | no | Defaults to `0.1.0`. |
| `description` | string | no | Free-text summary, used in the file header. |
| `mcp_version` | string | no | Protocol version to pin in the output. |
| `prelude` | string | no | Raw Python inserted at module level (imports, shared state). |
| `auth` | mapping | no | See [Hardening](hardening.md). |
| `observability` | mapping | no | See [Hardening](hardening.md). |
| `tools` | list | * | MCP tools. |
| `resources` | list | * | MCP resources. |
| `prompts` | list | * | MCP prompts. |

\* At least one of `tools`, `resources`, or `prompts` must be present.

## Tools

```yaml
tools:
  - name: get_weather          # valid Python identifier
    description: Get weather.   # becomes the tool docstring
    params: [ ... ]            # see Parameters
    returns: str               # return annotation (default: str)
    body: |                    # inline Python; omit for a NotImplementedError stub
      return "..."
```

## Resources

```yaml
resources:
  - name: list_notes
    uri: notes://all           # the URI clients address
    description: All notes.
    returns: str
    body: |
      return "..."
```

## Prompts

```yaml
prompts:
  - name: summarize
    description: Summarize text.
    params: [ ... ]
    template: |                # rendered as an f-string; {param} interpolates
      Summarize this: {text}
```

## Parameters

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
(with `choices`). An `enum` becomes a `typing.Literal[...]`.

## Shared state with `prelude`

`prelude` is raw Python inserted at module level — useful for imports, helpers, or
state shared across tools:

```yaml
prelude: |
  _NOTES: dict[str, dict[str, str]] = {}
```
