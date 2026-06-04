"""Turn a validated :class:`ForgeSpec` into runnable Python source.

The heavy lifting (building correct Python signatures and indented bodies) is
done in plain Python here, because getting indentation right is far less
error-prone than doing it inside a template. A small Jinja2 template then
assembles the finished pieces into one file.
"""

from __future__ import annotations

import textwrap

from jinja2 import Environment, PackageLoader, select_autoescape

from .spec import (
    TYPE_MAP,
    ForgeSpec,
    ParameterSpec,
    PromptSpec,
    ResourceSpec,
    ToolSpec,
)

_env = Environment(
    loader=PackageLoader("mcp_forge", "templates"),
    autoescape=select_autoescape(enabled_extensions=()),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _annotation(param: ParameterSpec) -> str:
    """Return the Python type annotation string for a parameter."""
    t = param.type.lower()
    if t == "enum":
        choices = ", ".join(repr(c) for c in (param.choices or []))
        ann = f"Literal[{choices}]"
    else:
        ann = TYPE_MAP[t]
    if param.optional and param.default is None:
        ann = f"Optional[{ann}]"
    return ann


def _signature(params: list[ParameterSpec]) -> str:
    """Build a comma-separated parameter list, defaults last."""
    required: list[str] = []
    defaulted: list[str] = []
    for p in params:
        ann = _annotation(p)
        if p.default is not None:
            defaulted.append(f"{p.name}: {ann} = {p.default!r}")
        elif p.optional:
            defaulted.append(f"{p.name}: {ann} = None")
        else:
            required.append(f"{p.name}: {ann}")
    return ", ".join(required + defaulted)


def _docstring(text: str, indent: str = "    ") -> str:
    """Render a clean, safely-escaped docstring block."""
    text = (text or "").strip()
    if not text:
        return ""
    text = text.replace('"""', '\\"\\"\\"')
    if "\n" in text:
        body = textwrap.indent(text, indent)
        return f'{indent}"""\n{body}\n{indent}"""\n'
    return f'{indent}"""{text}"""\n'


def _body(raw: str | None, fallback: str, indent: str = "    ") -> str:
    """Indent a user-supplied body, or emit a sensible fallback."""
    if raw and raw.strip():
        return textwrap.indent(textwrap.dedent(raw).strip("\n"), indent) + "\n"
    return f"{indent}{fallback}\n"


def _render_tool(tool: ToolSpec) -> str:
    sig = _signature(tool.params)
    returns = TYPE_MAP.get(tool.returns.lower(), tool.returns)
    doc = _docstring(tool.description)
    body = _body(tool.body, f'raise NotImplementedError("TODO: implement {tool.name}")')
    return f"@mcp.tool()\ndef {tool.name}({sig}) -> {returns}:\n{doc}{body}"


def _render_resource(res: ResourceSpec) -> str:
    returns = TYPE_MAP.get(res.returns.lower(), res.returns)
    doc = _docstring(res.description)
    body = _body(res.body, f'raise NotImplementedError("TODO: implement {res.name}")')
    return f"@mcp.resource({res.uri!r})\ndef {res.name}() -> {returns}:\n{doc}{body}"


def _render_prompt(prompt: PromptSpec) -> str:
    sig = _signature(prompt.params)
    doc = _docstring(prompt.description)
    template = (prompt.template or "").strip("\n")
    body = "    return f" + repr(template) + "\n" if template else "    return ''\n"
    return f"@mcp.prompt()\ndef {prompt.name}({sig}) -> str:\n{doc}{body}"


def _needs_typing(spec: ForgeSpec) -> set[str]:
    """Figure out which `typing` symbols the generated code references."""
    needed: set[str] = set()
    all_params: list[ParameterSpec] = []
    for t in spec.tools:
        all_params.extend(t.params)
    for p in spec.prompts:
        all_params.extend(p.params)
    for p in all_params:
        if p.type.lower() == "enum":
            needed.add("Literal")
        if p.optional and p.default is None:
            needed.add("Optional")
        if p.type.lower() == "any":
            needed.add("Any")
    for t in spec.tools:
        if t.returns.lower() == "any":
            needed.add("Any")
    return needed


def generate(spec: ForgeSpec) -> str:
    """Return the full Python source for the MCP server described by *spec*."""
    template = _env.get_template("server.py.j2")
    prelude = textwrap.dedent(spec.prelude).strip("\n") if spec.prelude else ""
    return template.render(
        spec=spec,
        prelude=prelude,
        typing_imports=sorted(_needs_typing(spec)),
        tools=[_render_tool(t) for t in spec.tools],
        resources=[_render_resource(r) for r in spec.resources],
        prompts=[_render_prompt(p) for p in spec.prompts],
    )
