"""Tests for the MCP-Forge compiler."""

from __future__ import annotations

import ast

import pytest

from mcp_forge import generate, load_spec
from mcp_forge.loader import SpecError
from mcp_forge.spec import ForgeSpec
from mcp_forge.templates import starters


def _write(tmp_path, text: str):
    p = tmp_path / "spec.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_generated_code_is_valid_python_for_every_starter():
    assert starters.list_templates(), "no starter templates found"
    for name in starters.list_templates():
        text = starters.read_template(name)
        # Round-trip through the loader/generator the same way the CLI does.
        spec = _load_text(text)
        code = generate(spec)
        # Raises SyntaxError if the generated code is malformed.
        ast.parse(code)


def _load_text(text: str) -> ForgeSpec:
    import yaml

    return ForgeSpec.model_validate(yaml.safe_load(text))


def test_weather_signature_and_body(tmp_path):
    spec = load_spec(_write(tmp_path, _WEATHER))
    code = generate(spec)
    assert "def get_weather(city: str, units: Literal['celsius', 'fahrenheit'] = 'celsius') -> str:" in code
    assert "clear skies" in code
    assert 'mcp = FastMCP("weather")' in code
    ast.parse(code)


def test_optional_param_becomes_optional_none(tmp_path):
    spec = load_spec(_write(tmp_path, _OPTIONAL))
    code = generate(spec)
    assert "note: Optional[str] = None" in code
    assert "from typing import Optional" in code


def test_resource_and_prompt_render(tmp_path):
    spec = load_spec(_write(tmp_path, _RESPROMPT))
    code = generate(spec)
    assert "@mcp.resource('data://all')" in code
    assert "@mcp.prompt()" in code
    ast.parse(code)


def test_missing_file_raises():
    with pytest.raises(SpecError, match="not found"):
        load_spec("does-not-exist.yaml")


def test_empty_spec_rejected(tmp_path):
    with pytest.raises(SpecError, match="nothing to generate"):
        load_spec(_write(tmp_path, "name: empty\n"))


def test_unknown_param_type_rejected(tmp_path):
    bad = "name: x\ntools:\n  - name: t\n    params:\n      - name: p\n        type: frobnicate\n"
    with pytest.raises(SpecError, match="unknown type"):
        load_spec(_write(tmp_path, bad))


def test_enum_without_choices_rejected(tmp_path):
    bad = "name: x\ntools:\n  - name: t\n    params:\n      - name: p\n        type: enum\n"
    with pytest.raises(SpecError, match="no 'choices'"):
        load_spec(_write(tmp_path, bad))


_WEATHER = """
name: weather
tools:
  - name: get_weather
    description: Get weather.
    params:
      - name: city
        type: str
      - name: units
        type: enum
        choices: [celsius, fahrenheit]
        default: celsius
    returns: str
    body: |
      return "clear skies"
"""

_OPTIONAL = """
name: opt
tools:
  - name: t
    params:
      - name: note
        type: str
        optional: true
    body: |
      return note or ""
"""

_RESPROMPT = """
name: rp
resources:
  - name: all_data
    uri: data://all
    body: |
      return "data"
prompts:
  - name: ask
    params:
      - name: topic
        type: str
    template: |
      Tell me about {topic}.
"""
