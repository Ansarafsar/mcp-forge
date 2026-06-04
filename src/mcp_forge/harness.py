"""Snapshot test harness: run ``*.test.yaml`` files against generated servers.

A test file sits next to a spec and declares expected tool/resource/prompt
outputs. The harness builds the spec to a temporary server, drives it with
:class:`MockMCPClient`, and compares each result to its expectation.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .client import MockMCPClient, MockMCPClientError, server_command
from .generator import generate
from .loader import SpecError, load_spec


@dataclass
class CaseResult:
    name: str
    passed: bool
    expected: Optional[str] = None
    actual: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FileResult:
    path: Path
    cases: list[CaseResult] = field(default_factory=list)
    error: Optional[str] = None  # set if the whole file failed to run

    @property
    def passed(self) -> bool:
        return self.error is None and all(c.passed for c in self.cases)


def discover(path: str | Path) -> list[Path]:
    """Find test files: a single ``*.test.yaml``, or all of them under a directory."""
    p = Path(path)
    if p.is_dir():
        return sorted(p.rglob("*.test.yaml"))
    return [p]


def run(path: str | Path) -> list[FileResult]:
    """Run every discovered test file and return per-file results."""
    return [_run_file(f) for f in discover(path)]


def _run_file(test_path: Path) -> FileResult:
    result = FileResult(path=test_path)
    try:
        doc = yaml.safe_load(test_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 - surface any load error per file
        result.error = f"could not read test file: {exc}"
        return result

    spec_ref = doc.get("spec")
    if spec_ref:
        spec_path = (test_path.parent / spec_ref).resolve()
    else:
        # Default: same name with .yaml instead of .test.yaml.
        spec_path = test_path.with_name(test_path.name.replace(".test.yaml", ".yaml"))

    try:
        spec = load_spec(spec_path)
        code = generate(spec)
    except SpecError as exc:
        result.error = str(exc)
        return result

    env = {str(k): str(v) for k, v in (doc.get("env") or {}).items()}
    cases = doc.get("cases") or []

    with tempfile.TemporaryDirectory() as tmp:
        server_file = Path(tmp) / "server.py"
        server_file.write_text(code, encoding="utf-8")
        try:
            with MockMCPClient(server_command(str(server_file)), env=env) as client:
                for i, case in enumerate(cases):
                    result.cases.append(_run_case(client, case, i))
        except MockMCPClientError as exc:
            result.error = f"server failed to start: {exc}"

    return result


def _run_case(client: MockMCPClient, case: dict[str, Any], index: int) -> CaseResult:
    name = case.get("name") or case.get("tool") or case.get("resource") or f"case[{index}]"
    try:
        if "tool" in case:
            actual = client.call_tool(case["tool"], case.get("args") or {})
        elif "resource" in case:
            actual = client.read_resource(case["resource"])
        elif "prompt" in case:
            actual = client.get_prompt(case["prompt"], case.get("args") or {})
        else:
            return CaseResult(name, passed=False, error="case has no tool/resource/prompt")
    except MockMCPClientError as exc:
        if case.get("expect_error"):
            return CaseResult(name, passed=True, actual=str(exc))
        return CaseResult(name, passed=False, error=str(exc))

    if "expect" in case:
        expected = str(case["expect"]).strip()
        if actual.strip() == expected:
            return CaseResult(name, passed=True, expected=expected, actual=actual)
        return CaseResult(name, passed=False, expected=expected, actual=actual)

    if "expect_contains" in case:
        needle = str(case["expect_contains"])
        passed = needle in actual
        return CaseResult(name, passed=passed, expected=f"contains {needle!r}", actual=actual)

    # No expectation: just assert it ran without error.
    return CaseResult(name, passed=True, actual=actual)
