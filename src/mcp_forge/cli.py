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
from .generator import docker_files, generate
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
        None, "--output", "-o", help="Output file (python target) or directory (docker)."
    ),
    target: str = typer.Option(
        "python", "--target", help="Output target: 'python' or 'docker'."
    ),
    check: bool = typer.Option(
        True, "--check/--no-check", help="Byte-compile the result to catch syntax errors."
    ),
) -> None:
    """Compile a spec into a runnable Python MCP server (or a Docker build context)."""
    try:
        forge_spec = load_spec(spec)
    except SpecError as exc:
        _fail(str(exc))

    if target == "docker":
        out_dir = output or Path(f"{forge_spec.name}-docker")
        out_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in docker_files(forge_spec).items():
            (out_dir / filename).write_text(content, encoding="utf-8")
        if check:
            _byte_compile(out_dir / "server.py")
        console.print(f"[bold green]OK[/] wrote Docker context to [cyan]{out_dir}/[/]")
        console.print(
            f"  build & run: [bold]docker build -t {forge_spec.name} {out_dir} "
            f"&& docker run -i {forge_spec.name}[/]"
        )
        return

    if target != "python":
        _fail(f"unknown target {target!r}. Use 'python' or 'docker'.")

    try:
        code = generate(forge_spec)
    except SpecError as exc:
        _fail(str(exc))

    out = output or Path("server.py")
    out.write_text(code, encoding="utf-8")
    if check:
        _byte_compile(out)

    console.print(f"[bold green]OK[/] wrote [cyan]{out}[/] from [cyan]{spec}[/]")
    console.print(
        f"  run it with: [bold]python {out}[/]  "
        "(or wire it into Claude Desktop's mcpServers config)"
    )


def _byte_compile(path: Path) -> None:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        _fail(f"generated code has a syntax error:\n{exc}")


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
        import difflib

        hint = difflib.get_close_matches(template, available, n=1)
        suggestion = f" Did you mean {hint[0]!r}?" if hint else ""
        _fail(
            f"unknown template {template!r}.{suggestion} Available: {', '.join(available)}"
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
def init(
    name: str = typer.Argument("my-server", help="Project/spec name."),
    template: str = typer.Option("weather", "--template", "-t", help="Starter template."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Scaffold a spec *and* a matching snapshot-test file to start a project."""
    available = starters.list_templates()
    if template not in available:
        import difflib

        hint = difflib.get_close_matches(template, available, n=1)
        suggestion = f" Did you mean {hint[0]!r}?" if hint else ""
        _fail(f"unknown template {template!r}.{suggestion} Available: {', '.join(available)}")

    spec_path = Path(f"{name}.yaml")
    test_path = Path(f"{name}.test.yaml")
    if (spec_path.exists() or test_path.exists()) and not force:
        _fail(f"{spec_path} or {test_path} already exists (use --force to overwrite)")

    spec_path.write_text(
        starters.read_template(template).replace("name: " + template, "name: " + name, 1),
        encoding="utf-8",
    )
    test_path.write_text(
        f"# Snapshot tests for {spec_path.name}. Run: mcp-forge test {test_path.name}\n"
        f"spec: {spec_path.name}\n\ncases: []\n",
        encoding="utf-8",
    )
    console.print(f"[bold green]OK[/] created [cyan]{spec_path}[/] and [cyan]{test_path}[/]")
    console.print(f"  build:  [bold]mcp-forge build {spec_path}[/]")
    console.print(f"  dev:    [bold]mcp-forge dev {spec_path}[/]")


@app.command()
def run(spec: Path = typer.Argument(..., help="Path to the YAML spec.")) -> None:
    """Build a spec to a temp file and run the server (blocks; Ctrl-C to stop)."""
    import subprocess
    import sys
    import tempfile

    try:
        forge_spec = load_spec(spec)
        code = generate(forge_spec)
    except SpecError as exc:
        _fail(str(exc))

    with tempfile.TemporaryDirectory() as tmp:
        server_file = Path(tmp) / "server.py"
        server_file.write_text(code, encoding="utf-8")
        console.print(f"[bold green]OK[/] running [cyan]{spec}[/] (Ctrl-C to stop)")
        try:
            subprocess.run([sys.executable, str(server_file)], check=False)
        except KeyboardInterrupt:
            pass


@app.command()
def dev(
    spec: Path = typer.Argument(..., help="Path to the YAML spec."),
    interval: float = typer.Option(0.5, help="Seconds between change checks."),
) -> None:
    """Run the server and hot-reload it whenever the spec file changes."""
    import subprocess
    import sys
    import tempfile
    import time

    def build_to(path: Path) -> bool:
        try:
            code = generate(load_spec(spec))
        except SpecError as exc:
            err_console.print(f"[bold red]error:[/] {exc}")
            return False
        path.write_text(code, encoding="utf-8")
        return True

    with tempfile.TemporaryDirectory() as tmp:
        server_file = Path(tmp) / "server.py"
        if not build_to(server_file):
            raise typer.Exit(code=1)

        proc = subprocess.Popen([sys.executable, str(server_file)])
        last_mtime = spec.stat().st_mtime
        console.print(f"[bold green]OK[/] dev mode on [cyan]{spec}[/] — watching for changes")
        try:
            while True:
                time.sleep(interval)
                if proc.poll() is not None:
                    console.print("[yellow]server exited; waiting for next change…[/]")
                try:
                    mtime = spec.stat().st_mtime
                except FileNotFoundError:
                    continue
                if mtime != last_mtime:
                    last_mtime = mtime
                    console.print("[cyan]change detected — rebuilding…[/]")
                    if build_to(server_file):
                        if proc.poll() is None:
                            proc.terminate()
                            proc.wait(timeout=5)
                        proc = subprocess.Popen([sys.executable, str(server_file)])
                        console.print("[bold green]OK[/] reloaded")
        except KeyboardInterrupt:
            console.print("\n[dim]stopping…[/]")
        finally:
            if proc.poll() is None:
                proc.terminate()


@app.command()
def templates() -> None:
    """List the available starter templates."""
    table = Table("template", "description")
    for name in starters.list_templates():
        table.add_row(name, starters.describe(name))
    console.print(table)


@app.command()
def test(
    path: Path = typer.Argument(
        Path("."), help="A *.test.yaml file, or a directory to search."
    ),
) -> None:
    """Run snapshot tests (*.test.yaml) against generated servers."""
    from . import harness

    results = harness.run(path)
    if not results or all(not r.cases and r.error is None for r in results):
        _fail(f"no *.test.yaml files found under {path}")

    total = passed = 0
    for fr in results:
        if fr.error:
            console.print(f"[bold red]FAIL[/] {fr.path} — {fr.error}")
            total += 1
            continue
        for case in fr.cases:
            total += 1
            if case.passed:
                passed += 1
                console.print(f"[green]PASS[/] {fr.path.name} :: {case.name}")
            else:
                console.print(f"[bold red]FAIL[/] {fr.path.name} :: {case.name}")
                if case.error:
                    console.print(f"      [red]{case.error}[/]")
                else:
                    _print_diff(case.expected or "", case.actual or "")

    console.print(
        f"\n[bold]{passed}/{total} passed[/]"
        if passed == total
        else f"\n[bold red]{passed}/{total} passed[/]"
    )
    if passed != total:
        raise typer.Exit(code=1)


def _print_diff(expected: str, actual: str) -> None:
    import difflib

    diff = difflib.ndiff(expected.splitlines() or [""], actual.splitlines() or [""])
    for line in diff:
        if line.startswith("- "):
            console.print(f"      [green]expected: {line[2:]}[/]")
        elif line.startswith("+ "):
            console.print(f"      [red]actual:   {line[2:]}[/]")


@app.command()
def version() -> None:
    """Print the MCP-Forge version."""
    console.print(f"mcp-forge {__version__}")


def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
