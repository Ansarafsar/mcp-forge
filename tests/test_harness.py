"""Integration tests for the mock client + snapshot harness.

These build a real server and drive it over stdio, so they need the `mcp` SDK
(installed via the `dev` extra). Skipped if it is missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("mcp", reason="requires the mcp SDK to run a generated server")

from mcp_forge import harness  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_weather_snapshot_passes():
    results = harness.run(EXAMPLES / "weather.test.yaml")
    assert len(results) == 1
    fr = results[0]
    assert fr.error is None, fr.error
    assert fr.passed, [(c.name, c.expected, c.actual) for c in fr.cases if not c.passed]
    assert len(fr.cases) == 2


def test_notes_snapshot_passes():
    results = harness.run(EXAMPLES / "notes.test.yaml")
    fr = results[0]
    assert fr.error is None, fr.error
    assert fr.passed


def test_failing_case_is_reported(tmp_path):
    spec = tmp_path / "s.yaml"
    spec.write_text(
        "name: s\ntools:\n  - name: echo\n    params:\n      - name: t\n"
        "        type: str\n    body: |\n      return t\n",
        encoding="utf-8",
    )
    test = tmp_path / "s.test.yaml"
    test.write_text(
        "spec: s.yaml\ncases:\n  - tool: echo\n    args: { t: hi }\n    expect: BYE\n",
        encoding="utf-8",
    )
    fr = harness.run(test)[0]
    assert not fr.passed
    assert fr.cases[0].actual == "hi"
    assert fr.cases[0].expected == "BYE"
