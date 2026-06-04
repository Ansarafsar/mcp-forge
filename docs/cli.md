# CLI reference

| Command | What it does |
|---|---|
| `mcp-forge init <name> [-t TEMPLATE]` | Scaffold a spec **and** a snapshot-test file. |
| `mcp-forge new <name> [-t TEMPLATE]` | Scaffold a spec from a starter template. |
| `mcp-forge build <spec> [-o OUT] [--target python\|docker]` | Compile a spec. |
| `mcp-forge run <spec>` | Build to a temp file and run the server. |
| `mcp-forge dev <spec>` | Run with hot reload on spec change. |
| `mcp-forge test [PATH]` | Run snapshot tests (`*.test.yaml`). |
| `mcp-forge validate <spec>` | Validate a spec without generating code. |
| `mcp-forge templates` | List bundled starter templates. |
| `mcp-forge version` | Print the installed version. |

## build

```bash
mcp-forge build weather.yaml                 # -> server.py
mcp-forge build weather.yaml -o out/srv.py   # custom path
mcp-forge build weather.yaml --no-check      # skip byte-compile
mcp-forge build weather.yaml --target docker # -> <name>-docker/ build context
```

The Docker target emits `server.py`, `requirements.txt`, a `Dockerfile`, and a
`.dockerignore`:

```bash
mcp-forge build weather.yaml --target docker -o weather-docker
docker build -t weather weather-docker && docker run -i weather
```

## dev

`dev` watches the spec file and rebuilds + restarts the server whenever it changes.
Tune the poll interval with `--interval` (seconds).

Run `mcp-forge --help` or `mcp-forge <command> --help` for full details.
