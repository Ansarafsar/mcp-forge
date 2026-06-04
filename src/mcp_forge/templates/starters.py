"""Access the bundled starter specs shipped inside the package."""

from __future__ import annotations

from importlib import resources

_PKG = "mcp_forge.templates.specs"


def list_templates() -> list[str]:
    """Return the names of all bundled starter templates (without .yaml)."""
    names = []
    for entry in resources.files(_PKG).iterdir():
        if entry.name.endswith(".yaml"):
            names.append(entry.name[: -len(".yaml")])
    return sorted(names)


def read_template(name: str) -> str:
    """Return the raw YAML text of the starter named *name*."""
    return resources.files(_PKG).joinpath(f"{name}.yaml").read_text(encoding="utf-8")


def describe(name: str) -> str:
    """Return the `description:` line of a starter, for listings."""
    for line in read_template(name).splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    return ""
