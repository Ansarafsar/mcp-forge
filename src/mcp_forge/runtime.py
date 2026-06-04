"""Build the in-server runtime support code for Phase 5 features.

When a spec enables auth, structured logging, or rate limiting, the generated
server needs a handful of helpers (a token bucket, a logging decorator, an auth
guard). Rather than depend on an external package, MCP-Forge inlines exactly the
helpers a given spec uses, so generated servers stay single-file and dependency-light.
"""

from __future__ import annotations

from .spec import ForgeSpec

_HEADER = '''# --- MCP-Forge runtime (generated) -----------------------------------------
import os
import sys
import json
import time
import functools
'''

_AUTH = '''
_FORGE_AUTH_ENV = {env!r}
_FORGE_AUTH_TYPE = {type!r}


def _forge_auth() -> None:
    """Reject the call unless the configured secret is present in the environment."""
    secret = os.environ.get(_FORGE_AUTH_ENV)
    if not secret:
        raise PermissionError(
            f"auth required ({{_FORGE_AUTH_TYPE}}): set environment variable "
            f"{{_FORGE_AUTH_ENV}}"
        )
    # For oauth_stub, this is where real token verification would happen.
'''

_LOG = '''
def _forge_emit(record: dict) -> None:
    """Write one structured log line to stderr (and forward it if configured)."""
    line = json.dumps(record, default=repr, separators=(",", ":"))
    print(line, file=sys.stderr, flush=True)
{forward}

def _forge_log(name: str):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - log then re-raise
                _forge_emit({{
                    "tool": name, "args": kwargs,
                    "ms": round((time.perf_counter() - start) * 1000, 2),
                    "ok": False, "error": repr(exc),
                }})
                raise
            _forge_emit({{
                "tool": name, "args": kwargs,
                "ms": round((time.perf_counter() - start) * 1000, 2),
                "ok": True,
            }})
            return result
        return wrapper
    return deco
'''

_FORWARD = '''    if _FORGE_AUDIT_URL:
        try:
            import urllib.request
            req = urllib.request.Request(
                _FORGE_AUDIT_URL, data=line.encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=2).close()
        except Exception:  # noqa: BLE001 - auditing must never break a tool call
            pass

'''

_RATELIMIT = '''
import threading


class _ForgeTokenBucket:
    """A thread-safe token bucket: *rate* tokens refilled over *per* seconds."""

    def __init__(self, rate: int, per: float) -> None:
        self.capacity = float(rate)
        self.tokens = float(rate)
        self.fill_rate = rate / per
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def take(self) -> bool:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(
                self.capacity, self.tokens + (now - self.timestamp) * self.fill_rate
            )
            self.timestamp = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


_FORGE_BUCKETS: dict[str, _ForgeTokenBucket] = __FORGE_BUCKETS__


def _forge_ratelimit(name: str):
    def deco(fn):
        bucket = _FORGE_BUCKETS.get(name)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if bucket is not None and not bucket.take():
                raise RuntimeError(f"rate limit exceeded for tool {name!r}")
            return fn(*args, **kwargs)

        return wrapper
    return deco
'''

_FOOTER = "# --- end MCP-Forge runtime -------------------------------------------------\n"


def _bucket_for(spec: ForgeSpec, tool_name: str):
    rl = spec.observability.rate_limit if spec.observability else None
    if rl is None:
        return None
    if tool_name in rl.per_tool:
        return rl.per_tool[tool_name]
    return rl.default


def needs_log(spec: ForgeSpec) -> bool:
    obs = spec.observability
    return bool(obs and (obs.logging or obs.audit_url))


def needs_ratelimit(spec: ForgeSpec) -> bool:
    obs = spec.observability
    return bool(obs and obs.rate_limit)


def tool_decorators(spec: ForgeSpec, tool_name: str) -> list[str]:
    """Decorator lines (without @mcp.tool()) to stack onto a tool, outermost first."""
    decos: list[str] = []
    if needs_log(spec):
        decos.append(f"@_forge_log({tool_name!r})")
    if needs_ratelimit(spec) and _bucket_for(spec, tool_name) is not None:
        decos.append(f"@_forge_ratelimit({tool_name!r})")
    return decos


def build_runtime(spec: ForgeSpec) -> str:
    """Return the runtime support block for *spec*, or '' if no features are enabled."""
    parts: list[str] = []

    if spec.auth:
        parts.append(_AUTH.format(env=spec.auth.env, type=spec.auth.type))

    if needs_log(spec):
        audit_url = spec.observability.audit_url if spec.observability else None
        forward = _FORWARD if audit_url else "\n"
        block = ""
        if audit_url:
            block += f"_FORGE_AUDIT_URL = {audit_url!r}\n"
        block += _LOG.format(forward=forward)
        parts.append(block)

    if needs_ratelimit(spec):
        buckets_src = "{"
        rl = spec.observability.rate_limit
        rules = dict(rl.per_tool)
        if rl.default is not None:
            for tool in spec.tools:
                rules.setdefault(tool.name, rl.default)
        buckets_src += ", ".join(
            f"{name!r}: _ForgeTokenBucket({rule.rate}, {rule.per})"
            for name, rule in rules.items()
        )
        buckets_src += "}"
        parts.append(_RATELIMIT.replace("__FORGE_BUCKETS__", buckets_src))

    if not parts:
        return ""
    return _HEADER + "".join(parts) + _FOOTER
