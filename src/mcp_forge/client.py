"""A minimal MCP client that speaks JSON-RPC over stdio.

This is deliberately dependency-free: it does not import the ``mcp`` SDK. It
launches a generated server as a subprocess and exchanges newline-delimited
JSON-RPC messages with it, which is exactly what the MCP stdio transport uses.
It exists so generated servers can be tested offline, without a real LLM client.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Optional

PROTOCOL_VERSION = "2024-11-05"


class MockMCPClientError(Exception):
    """Raised when the server errors, crashes, or violates the protocol."""


class MockMCPClient:
    """Drive a generated MCP server over stdio.

    Use as a context manager::

        with MockMCPClient([sys.executable, "server.py"]) as client:
            print(client.call_tool("get_weather", {"city": "London"}))
    """

    def __init__(self, command: list[str], env: Optional[dict[str, str]] = None) -> None:
        self.command = command
        self.env = {**os.environ, **(env or {})}
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 0

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "MockMCPClient":
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=self.env,
        )
        self._initialize()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 - best-effort shutdown
            self._proc.kill()
        finally:
            self._proc = None

    # -- public API --------------------------------------------------------
    def list_tools(self) -> list[str]:
        result = self._request("tools/list", {})
        return [t["name"] for t in result.get("tools", [])]

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            raise MockMCPClientError(_extract_text(result))
        return _extract_text(result)

    def read_resource(self, uri: str) -> str:
        result = self._request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        if not contents:
            return ""
        return contents[0].get("text", "")

    def get_prompt(self, name: str, arguments: Optional[dict[str, Any]] = None) -> str:
        result = self._request("prompts/get", {"name": name, "arguments": arguments or {}})
        messages = result.get("messages", [])
        if not messages:
            return ""
        content = messages[0].get("content", {})
        return content.get("text", "") if isinstance(content, dict) else str(content)

    # -- protocol plumbing -------------------------------------------------
    def _initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcp-forge-mock", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        msg_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
        while True:
            reply = self._read()
            if reply.get("id") != msg_id:
                # Skip server-initiated notifications / unrelated messages.
                continue
            if "error" in reply:
                err = reply["error"]
                raise MockMCPClientError(f"{method} failed: {err.get('message', err)}")
            return reply.get("result", {})

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, message: dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        assert self._proc and self._proc.stdout
        line = self._proc.stdout.readline()
        if line == "":
            stderr = self._proc.stderr.read() if self._proc.stderr else ""
            raise MockMCPClientError(
                "server closed the connection unexpectedly"
                + (f":\n{stderr.strip()}" if stderr.strip() else "")
            )
        line = line.strip()
        if not line:
            return self._read()
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise MockMCPClientError(f"server sent non-JSON line: {line!r}") from exc


def _extract_text(result: dict[str, Any]) -> str:
    """Pull the text out of a tools/call result's content list."""
    for item in result.get("content", []):
        if item.get("type") == "text":
            return item.get("text", "")
    return ""


def server_command(server_path: str) -> list[str]:
    """The command that runs a generated server file with the current interpreter."""
    return [sys.executable, server_path]
