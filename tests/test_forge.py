"""Tests for the MCP-Forge compiler."""

from __future__ import annotations

import ast

import pytest

from mcp_forge import generate, load_spec
from mcp_forge.generator import docker_files
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


def test_unknown_type_suggests_close_match(tmp_path):
    bad = "name: x\ntools:\n  - name: t\n    params:\n      - name: p\n        type: integ\n"
    with pytest.raises(SpecError, match="Did you mean 'integer'"):
        load_spec(_write(tmp_path, bad))


def test_auth_injects_guard(tmp_path):
    spec = load_spec(_write(tmp_path, _SECURE))
    code = generate(spec)
    assert "def _forge_auth() -> None:" in code
    assert "_FORGE_AUTH_ENV = 'TOK'" in code
    assert "    _forge_auth()\n" in code
    ast.parse(code)


def test_logging_and_ratelimit_render(tmp_path):
    spec = load_spec(_write(tmp_path, _SECURE))
    code = generate(spec)
    assert "@_forge_log('ping')" in code
    assert "@_forge_ratelimit('ping')" in code
    assert "_ForgeTokenBucket(2, 10.0)" in code
    assert "class _ForgeTokenBucket" in code
    ast.parse(code)


def test_no_runtime_when_no_features(tmp_path):
    spec = load_spec(_write(tmp_path, _WEATHER))
    code = generate(spec)
    assert "_forge_auth" not in code
    assert "_ForgeTokenBucket" not in code


def test_docker_files_complete():
    spec = ForgeSpec.model_validate(
        {"name": "d", "tools": [{"name": "t", "body": "return 'x'"}]}
    )
    files = docker_files(spec)
    assert set(files) == {"server.py", "requirements.txt", "Dockerfile", ".dockerignore"}
    assert "FROM python:" in files["Dockerfile"]
    assert "mcp>=" in files["requirements.txt"]
    ast.parse(files["server.py"])


_SECURE = """
name: secure
auth:
  type: api_key
  env: TOK
observability:
  logging: true
  rate_limit:
    default: { rate: 2, per: 10 }
tools:
  - name: ping
    returns: str
    body: |
      return "pong"
"""

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
