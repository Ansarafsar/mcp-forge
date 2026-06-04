# Examples

Each spec here builds into a working MCP server in one command.

| Spec | Highlights | Build |
|---|---|---|
| [`weather.yaml`](weather.yaml) | Tools, enum params, defaults | `mcp-forge build examples/weather.yaml` |
| [`notes.yaml`](notes.yaml) | CRUD tools + resource + prompt + shared state | `mcp-forge build examples/notes.yaml` |
| [`github-issues.yaml`](github-issues.yaml) | Multiple tools, optional params | `mcp-forge build examples/github-issues.yaml` |
| [`slack-search.yaml`](slack-search.yaml) | Single search tool, optional filter | `mcp-forge build examples/slack-search.yaml` |
| [`secure-weather.yaml`](secure-weather.yaml) | Auth + logging + rate limiting | `mcp-forge build examples/secure-weather.yaml` |

## Run the snapshot tests

```bash
mcp-forge test examples/
```

This builds each spec that has a `*.test.yaml` beside it, launches it, and
checks every case. See [`weather.test.yaml`](weather.test.yaml) and
[`notes.test.yaml`](notes.test.yaml) for the format.

## Try a server live

```bash
mcp-forge run examples/weather.yaml
# or hot-reload while you edit:
mcp-forge dev examples/weather.yaml
```

## Build a Docker image

```bash
mcp-forge build examples/weather.yaml --target docker -o weather-docker
docker build -t weather weather-docker && docker run -i weather
```
