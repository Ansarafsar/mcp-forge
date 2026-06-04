# Hardening

Opt into production-readiness signals per spec. When enabled, MCP-Forge inlines the
needed helpers into the generated server — it stays a single, dependency-light file.

## Auth

```yaml
auth:
  type: api_key        # api_key | bearer_token | oauth_stub
  env: MCP_API_KEY     # env var that must hold the expected secret
  header: X-API-Key    # informational
```

Every tool call runs an auth guard first. If the configured environment variable is
not set, the call is rejected with a `PermissionError`. `oauth_stub` generates the
same gate plus a marked place to add real token verification.

## Structured logging

```yaml
observability:
  logging: true
```

Each tool call is logged to **stderr** as one JSON line, with the tool name,
arguments, duration in milliseconds, and success/error:

```json
{"tool":"get_weather","args":{"city":"London"},"ms":0.42,"ok":true}
```

stdout stays reserved for the MCP protocol, so logging never corrupts the channel.

### Forward logs to an audit endpoint

```yaml
observability:
  logging: true
  audit_url: http://localhost:8080/ingest
```

Each log line is also POSTed to `audit_url` (best-effort; failures never break a
tool call). This is the integration point for an external audit service.

## Rate limiting

A thread-safe token bucket per tool:

```yaml
observability:
  rate_limit:
    default: { rate: 30, per: 60 }     # 30 calls / 60s for every tool
    per_tool:
      get_weather: { rate: 10, per: 60 } # override for one tool
```

When a tool exceeds its budget the call raises `RuntimeError: rate limit exceeded`.

## Putting it together

See [`examples/secure-weather.yaml`](https://github.com/Ansarafsar/mcp-forge/blob/main/examples/secure-weather.yaml)
for a spec that combines auth, logging, and rate limiting.
