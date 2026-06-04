"""MCP-Forge command-line interface.

Usage::

    mcp-forge new my-server --template weather
    mcp-forge build my-server.yaml
    mcp-forge validate my-server.yaml
    mcp-forge templates
"""

from __future__ import annotations

import py_compile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .generator import generate
from .loader import SpecError, load_spec
from .templates import starters

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Compile a YAML spec into a runnable Model Context Protocol server.",
)
console = Console()
err_console = Console(stderr=True)


def _fail(message: str) -> None:
    err_console.print(f"[bold red]error:[/] {message}")
    raise typer.Exit(code=1)


@app.command()
def build(
    spec: Path = typer.Argument(..., help="Path to the YAML spec."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Where to write the server (default: server.py)."
    ),
    check: bool = typer.Option(
        True, "--check/--no-check", help="Byte-compile the result to catch syntax errors."
    ),
) -> None:
    """Compile a spec into a runnable Python MCP server."""
    try:
        forge_spec = load_spec(spec)
        code = generate(forge_spec)
    except SpecError as exc:
        _fail(str(exc))

    out = output or Path("server.py")
    out.write_text(code, encoding="utf-8")

    if check:
        try:
            py_compile.compile(str(out), doraise=True)
        except py_compile.PyCompileError as exc:
            _fail(f"generated code has a syntax error:\n{exc}")

    console.print(f"[bold green]OK[/] wrote [cyan]{out}[/] from [cyan]{spec}[/]")
    console.print(
        f"  run it with: [bold]python {out}[/]  "
        "(or wire it into Claude Desktop's mcpServers config)"
    )


@app.command()
def validate(spec: Path = typer.Argument(..., help="Path to the YAML spec.")) -> None:
    """Validate a spec without generating code."""
    try:
        forge_spec = load_spec(spec)
    except SpecError as exc:
        _fail(str(exc))
    console.print(
        f"[bold green]OK[/] [cyan]{spec}[/] is valid - "
        f"{len(forge_spec.tools)} tool(s), "
        f"{len(forge_spec.resources)} resource(s), "
        f"{len(forge_spec.prompts)} prompt(s)"
    )


@app.command()
def new(
    name: str = typer.Argument(..., help="Name of the new spec file (without .yaml)."),
    template: str = typer.Option(
        "weather", "--template", "-t", help="Starter template to copy."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if it exists."),
) -> None:
    """Scaffold a new spec from a starter template."""
    available = starters.list_templates()
    if template not in available:
        _fail(
            f"unknown template {template!r}. Available: {', '.join(available)}"
        )

    out = Path(f"{name}.yaml")
    if out.exists() and not force:
        _fail(f"{out} already exists (use --force to overwrite)")

    content = starters.read_template(template).replace(
        "name: " + template, "name: " + name, 1
    )
    out.write_text(content, encoding="utf-8")
    console.print(f"[bold green]OK[/] created [cyan]{out}[/] from template [cyan]{template}[/]")
    console.print(f"  next: [bold]mcp-forge build {out}[/]")


@app.command()
def templates() -> None:
    """List the available starter templates."""
    table = Table("template", "description")
    for name in starters.list_templates():
        table.add_row(name, starters.describe(name))
    console.print(table)


@app.command()
def version() -> None:
    """Print the MCP-Forge version."""
    console.print(f"mcp-forge {__version__}")


def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
